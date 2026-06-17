# ============================================================
# IMPORTS
# ============================================================

import re
import io
import time
import random
import threading
from collections import deque

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

COLUMNS_ORDER = [
    "Nº",
    "BARCO", "AGENCIA", "CODIGO", "GRUPO",
    "CONFIRMACION", "FECHA BOOKING", "ITINERARIO",
    "FECHA SALIDA", "FECHA LLEGADA",
    "NETO", "BRUTO",
    "ESTADO RESERVA", "PAGO", "COMERCIAL",
    "PERSONAS", "IDIOMA",
]

CELLS_NEEDED = [
    "B2","G11","G13","G5","P5","R5",
    "C3","G19","G17","G10",
    "G57","Q10","G23","Q55",
    "G24:G60"
]

# ============================================================
# RATE LIMITER
# ============================================================

class RateLimiter:
    def __init__(self, max_calls=50, per_seconds=60):
        self.calls = deque()
        self.max_calls = max_calls
        self.per_seconds = per_seconds
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
# GOOGLE
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
# EXECUTE
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
        [f["name"] for f in list_children(DRIVEROOTID, True)
         if re.fullmatch(r"\d{4}", f["name"])],
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

def batch_get(ssid, sheet_title):

    ranges = [f"'{sheet_title}'!{c}" for c in CELLS_NEEDED]

    resp = execute(
        sheets().spreadsheets().values().batchGet(
            spreadsheetId=ssid,
            ranges=ranges,
            valueRenderOption="UNFORMATTED_VALUE",
        )
    )

    data = {}

    for c, vr in zip(CELLS_NEEDED, resp.get("valueRanges", [])):
        vals = vr.get("values", [])

        if len(vals) > 1:
            data[c] = vals
        else:
            data[c] = vals[0][0] if vals and vals[0] else ""

    return data

def get_sheet_titles(ssid):
    meta = execute(
        sheets().spreadsheets().get(
            spreadsheetId=ssid,
            includeGridData=False,
        )
    )
    return [s["properties"]["title"] for s in meta.get("sheets", [])]

# ============================================================
# HELPERS
# ============================================================

def parse_numeric(val):
    if not val:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    text = re.sub(r"[€$\s]", "", str(val))
    text = text.replace(".", "").replace(",", ".")

    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group()) if m else 0.0


def count_personas(rango):
    if not rango:
        return 0

    return sum(1 for fila in rango if fila and str(fila[0]).strip())

# ============================================================
# PROCESO LIBRO
# ============================================================

def process_book(book_id, boat_name, book_name):

    rows_book = []

    try:
        sheets_list = get_sheet_titles(book_id)

        for sh in sheets_list:

            d1 = batch_get(book_id, sh)
            d2 = batch_get(book_id, sh)

            if d1 != d2:
                st.warning(f"Inconsistencia en {book_name} / {sh}")

            data = d2

            if not data.get("G11"):
                continue

            row = {
                "BARCO": boat_name,
                "AGENCIA": data.get("B2", ""),
                "CODIGO": data.get("G11", ""),
                "GRUPO": data.get("G13", ""),
                "CONFIRMACION": data.get("G5", ""),
                "FECHA BOOKING": data.get("P5", ""),
                "ITINERARIO": data.get("R5", ""),
                "FECHA SALIDA": data.get("C3", ""),
                "FECHA LLEGADA": data.get("G19", ""),
                "NETO": parse_numeric(data.get("G17")),
                "BRUTO": parse_numeric(data.get("Q55")),
                "ESTADO RESERVA": data.get("G10", ""),
                "PAGO": data.get("Q10", ""),
                "COMERCIAL": data.get("G23", ""),
                "PERSONAS": count_personas(data.get("G24:G60")),
                "IDIOMA": data.get("G57", ""),
            }

            rows_book.append(row)

    except Exception as e:
        st.warning(f"Error libro {book_name}: {e}")

    return rows_book

# ============================================================
# SCAN
# ============================================================

def scan_year(year, progress_bar, table_placeholder):

    year_id = get_year_id(year)
    if not year_id:
        return pd.DataFrame(columns=COLUMNS_ORDER)

    rows_total = []

    boats = list_children(year_id, True)
    total = sum(len(list_children(b["id"], False)) for b in boats)
    processed = 0

    for boat in boats:
        files = list_children(boat["id"], False)

        for f in files:

            processed += 1
            progress_bar.progress(processed / max(total, 1))

            if not re.match(r"^[A-Z_]+_\d{6}$", f["name"].strip()):
                continue

            rows_book = process_book(f["id"], boat["name"], f["name"])

            if rows_book:
                rows_total.extend(rows_book)

                df_temp = pd.DataFrame(rows_total)

                # ✅ numeración segura (NO index)
                df_temp.insert(0, "Nº", range(1, len(df_temp) + 1))

                table_placeholder.dataframe(df_temp)

    df_final = pd.DataFrame(rows_total)

    if not df_final.empty:
        df_final.insert(0, "Nº", range(1, len(df_final) + 1))

    return df_final

# ============================================================
# EXCEL
# ============================================================

def to_excel(df):
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    return buf

# ============================================================
# UI
# ============================================================

st.set_page_config(page_title="Ventas FIT", layout="wide")

st.title("Ventas FIT")

years = get_years()
year = st.selectbox("Año", years)

if st.button("Generar informe"):

    progress = st.progress(0)
    table_placeholder = st.empty()

    with st.spinner("Procesando..."):
        df = scan_year(year, progress, table_placeholder)

    if df.empty:
        st.warning("No hay datos")
    else:
        st.download_button(
            "Descargar Excel",
            to_excel(df),
            file_name=f"ventas_{year}.xlsx"
        )
