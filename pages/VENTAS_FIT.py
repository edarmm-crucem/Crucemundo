import re
import io
import time
import random
import threading
from collections import deque
from datetime import datetime

import pytz
import streamlit as st
import pandas as pd

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# ============================================================
# CONFIG
# ============================================================

DRIVEROOTID = "11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm"
TIMEZONE = pytz.timezone("Europe/Madrid")


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
def get_creds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcpserviceaccount"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )


@st.cache_resource
def drive():
    return build("drive", "v3", credentials=get_creds())


@st.cache_resource
def sheets():
    return build("sheets", "v4", credentials=get_creds())


# ============================================================
# RETRY
# ============================================================

def execute(request):
    for i in range(6):
        try:
            rate_limiter.wait()
            return request.execute()
        except HttpError as e:
            if e.resp.status in [429, 500, 502, 503, 504]:
                time.sleep((2 ** i) + random.random())
            else:
                raise
    raise Exception("Error persistente en API")


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
    folders = list_children(DRIVEROOTID, True)
    return sorted(
        [f["name"] for f in folders if re.match(r"^\d{4}$", f["name"])],
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
    "B2", "G11", "G13", "G5", "P5", "R5",
    "C3", "G19", "G17", "K17", "G10",
    "G57", "Q10", "G23", "Q55"
]


def batch_read(ssid, sheet_name):
    ranges = [f"'{sheet_name}'!{c}" for c in CELLS]

    result = execute(
        sheets().spreadsheets().values().batchGet(
            spreadsheetId=ssid,
            ranges=ranges,
            valueRenderOption="UNFORMATTED_VALUE",
        )
    )

    data = {}
    for c, vr in zip(CELLS, result.get("valueRanges", [])):
        vals = vr.get("values", [])
        data[c] = vals[0][0] if vals and vals[0] else ""

    return data


def get_sheets(ssid):
    meta = execute(
        sheets().spreadsheets().get(
            spreadsheetId=ssid,
            includeGridData=False,
        )
    )

    return [s["properties"]["title"] for s in meta["sheets"]]


# ============================================================
# PARSE
# ============================================================

def parse_float(val):
    if val is None or val == "":
        return 0.0

    if isinstance(val, (int, float)):
        return float(val)

    text = str(val)
    text = re.sub(r"[€$£\s]", "", text)

    text = text.replace(".", "").replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", text)

    return float(m.group()) if m else 0.0


# ============================================================
# CORE SCAN
# ============================================================

def scan_year(year):
    year_id = get_year_id(year)
    if not year_id:
        return []

    rows = []

    boats = list_children(year_id, True)

    for boat in boats:
        files = list_children(boat["id"], False)

        for f in files:
            if not re.match(r"^[A-Z_]+_\d{6}$", f["name"]):
                continue

            try:
                sheets_list = get_sheets(f["id"])

                for sh in sheets_list:
                    data = batch_read(f["id"], sh)

                    if not data["G11"]:
                        continue

                    rows.append({
                        "BARCO": boat["name"],
                        "CODIGO": data["G11"],
                        "AGENCIA": data["B2"],
                        "NETO": parse_float(data["G19"]),
                        "BRUTO": parse_float(data["G17"]),
                        "FECHA": data["G5"],
                    })

            except Exception as e:
                st.warning(f"Error en {f['name']}: {e}")

    return rows


# ============================================================
# UI
# ============================================================

st.title("Ventas FIT Optimizado")

years = get_years()
year = st.selectbox("Año", years)

if st.button("Generar"):

    with st.spinner("Procesando..."):
        data = scan_year(year)

    if not data:
        st.info("Sin datos")
    else:
        df = pd.DataFrame(data)
        st.dataframe(df)

        excel = io.BytesIO()
        df.to_excel(excel, index=False)
        excel.seek(0)

        st.download_button(
            "Descargar Excel",
            excel,
            file_name=f"ventas_{year}.xlsx"
        )
