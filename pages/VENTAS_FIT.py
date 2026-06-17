# ============================================================
# IMPORTS
# ============================================================

import re
import io
import time
import random
import threading
from collections import deque
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytz
import streamlit as st
import pandas as pd

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import socket

socket.setdefaulttimeout(60)

# ============================================================
# CONFIG
# ============================================================

DRIVEROOTID = "11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm"
TIMEZONE = pytz.timezone("Europe/Madrid")

MAX_WORKERS = 2   # 🔥 ajustable (5 = seguro, 8 = más rápido pero más riesgo 429)

COLUMNS_ORDER = [
    "BARCO", "AGENCIA", "CODIGO", "GRUPO",
    "CONFIRMACION", "FECHA BOOKING", "ITINERARIO",
    "FECHA SALIDA", "FECHA LLEGADA",
    "NETO", "BRUTO",
    "ESTADO RESERVA", "PAGO", "COMERCIAL",
    "PERSONAS", "IDIOMA",
]

# ============================================================
# RATE LIMITER
# ============================================================

class RateLimiter:
    def __init__(self, max_calls=50, per_seconds=60):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self.calls = deque()
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now = time.time()

            while self.calls and now - self.calls[0] > self.per_seconds:
                self.calls.popleft()

            if len(self.calls) >= self.max_calls:
                sleep_time = self.per_seconds - (now - self.calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)

            self.calls.append(time.time())


rate_limiter = RateLimiter()

# ============================================================
# GOOGLE CLIENTS
# ============================================================

@st.cache_resource
def creds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcpserviceaccount"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )

@st.cache_resource
def drive():
    return build("drive", "v3", credentials=creds())

@st.cache_resource
def sheets():
    return build("sheets", "v4", credentials=creds())

# ============================================================
# RETRY
# ============================================================

def execute(req, retries=5):
    for i in range(retries):
        try:
            rate_limiter.wait()
            return req.execute()
        except (HttpError, OSError, ConnectionResetError, BrokenPipeError):
            time.sleep((2 ** i) + random.uniform(0, 1))
    raise Exception("Error API persistente")

# ============================================================
# DRIVE
# ============================================================

def list_children(parent_id, folders_only=False):

    q = f"'{parent_id}' in parents and trashed=false"

    if folders_only:
        q += " and mimeType='application/vnd.google-apps.folder'"

    res = execute(
        drive().files().list(
            q=q,
            fields="files(id,name,mimeType)",
            pageSize=1000,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
    )

    return res.get("files", [])

def get_years():
    return sorted(
        [f["name"] for f in list_children(DRIVEROOTID, True) if re.fullmatch(r"\d{4}", f["name"])],
        reverse=True,
    )

def get_year_id(year):
    for f in list_children(DRIVEROOTID, True):
        if f["name"] == year:
            return f["id"]
    return None

# ============================================================
# SHEETS
# ============================================================

CELLS = [
    "B2","G11","G13","G5","P5","R5",
    "C3","G19","G17","K17","G10",
    "G57","Q10","G23","Q55"
]

def batch_get(ssid, sheet):
    ranges = [f"'{sheet}'!{c}" for c in CELLS]

    resp = execute(
        sheets().spreadsheets().values().batchGet(
            spreadsheetId=ssid,
            ranges=ranges,
            valueRenderOption="UNFORMATTED_VALUE",
        )
    )

    data = {}
    for c, vr in zip(CELLS, resp.get("valueRanges", [])):
        vals = vr.get("values", [])
        data[c] = vals[0][0] if vals and vals[0] else ""

    return data

@st.cache_data(ttl=600)
def get_sheets(ssid):
    meta = execute(
        sheets().spreadsheets().get(
            spreadsheetId=ssid,
            includeGridData=False,
        )
    )
    return [s["properties"]["title"] for s in meta.get("sheets", [])]

# ============================================================
# PARSE
# ============================================================

def parse_numeric(v):
    if not v:
        return 0.0
    if isinstance(v,(int,float)):
        return float(v)

    t = re.sub(r"[€$\s]", "", str(v))
    t = t.replace(".", "").replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", t)
    return float(m.group()) if m else 0.0

# ============================================================
# CORE PARALLEL
# ============================================================

def process_file(boat_name, file_obj):
    rows = []

    if not re.match(r"^[A-Z_]+_\d{6}$", file_obj["name"].strip()):
        return rows

    try:
        sheets_list = get_sheets(file_obj["id"])

        for sh in sheets_list:
            data = batch_get(file_obj["id"], sh)

            if not data.get("G11"):
                continue

            row = {col: "" for col in COLUMNS_ORDER}

            row.update({
                "BARCO": boat_name,
                "AGENCIA": data.get("B2",""),
                "CODIGO": data.get("G11",""),
                "GRUPO": data.get("G13",""),
                "CONFIRMACION": data.get("G5",""),
                "FECHA BOOKING": data.get("P5",""),
                "ITINERARIO": data.get("R5",""),
                "FECHA SALIDA": data.get("C3",""),
                "FECHA LLEGADA": data.get("G19",""),
                "NETO": parse_numeric(data.get("G17")),
                "BRUTO": parse_numeric(data.get("K17")),
                "ESTADO RESERVA": data.get("G10",""),
                "PAGO": data.get("Q10",""),
                "COMERCIAL": data.get("G23",""),
                "PERSONAS": data.get("Q55",""),
                "IDIOMA": data.get("G57",""),
            })

            rows.append(row)

    except Exception as e:
        return [{"ERROR": f"{file_obj['name']} -> {e}"}]

    return rows

def scan_year(year, progress_bar=None):

    year_id = get_year_id(year)
    if not year_id:
        return []

    boats = list_children(year_id, True)

    files_total = []
    for b in boats:
        for f in list_children(b["id"], False):
            files_total.append((b["name"], f))

    results = []
    total = len(files_total)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

        futures = [
            executor.submit(process_file, boat, f)
            for boat, f in files_total
        ]

        for i, future in enumerate(as_completed(futures)):
            results.extend(future.result())

            if progress_bar:
                progress_bar.progress((i + 1) / total)

    return results


# ============================================================
# EXCEL
# ============================================================

def to_excel(df):
    buf = io.BytesIO()
    df[COLUMNS_ORDER].to_excel(buf, index=False)
    buf.seek(0)
    return buf

# ============================================================
# UI (NO TOCADA)
# ============================================================

st.set_page_config(page_title="Ventas FIT", layout="wide")

st.title("Ventas FIT")

try:
    years = get_years()
except Exception as e:
    st.error(f"Error Drive: {e}")
    st.stop()

year = st.selectbox("Año", years)

if st.button("Generar informe"):

    progress = st.progress(0)

    with st.spinner("Procesando..."):

        rows = scan_year(year, progress)

    if not rows:
        st.warning("Sin datos")
    else:
        df = pd.DataFrame(rows)

        st.dataframe(df)

        st.download_button(
            "Descargar Excel",
            to_excel(df),
            file_name=f"ventas_{year}.xlsx"
        )
