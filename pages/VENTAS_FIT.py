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

CELLS = [
    "B2","G11","G13","G5","P5","R5",
    "C3","G19","G17","G10",
    "G57","Q10","G23","Q55",
    "G24:G60"
]

# ============================================================
# RATE LIMIT
# ============================================================

class RateLimiter:
    def __init__(self):
        self.calls = deque()
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now = time.time()
            while self.calls and now - self.calls[0] > 60:
                self.calls.popleft()

            if len(self.calls) >= 50:
                time.sleep(1)

            self.calls.append(time.time())

limiter = RateLimiter()

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

def execute(req):
    for i in range(5):
        try:
            limiter.wait()
            return req.execute()
        except:
            time.sleep(2**i)

    raise Exception("Error API")

# ============================================================
# DRIVE
# ============================================================

def list_children(parent, folders=False):

    q = f"'{parent}' in parents and trashed=false"
    if folders:
        q += " and mimeType='application/vnd.google-apps.folder'"

    res = execute(
        drive().files().list(
            q=q,
            fields="files(id,name,mimeType)"
        )
    )

    return res.get("files", [])

def get_years():
    return sorted([
        f["name"] for f in list_children(DRIVEROOTID, True)
        if re.fullmatch(r"\d{4}", f["name"])
    ], reverse=True)

# ============================================================
# SHEETS
# ============================================================

def batch_get(ssid, sheet):

    ranges = [f"'{sheet}'!{c}" for c in CELLS]

    res = execute(
        sheets().spreadsheets().values().batchGet(
            spreadsheetId=ssid,
            ranges=ranges,
            valueRenderOption="UNFORMATTED_VALUE"
        )
    )

    data = {}

    for c, vr in zip(CELLS, res.get("valueRanges", [])):
        vals = vr.get("values", [])

        if len(vals) > 1:
            data[c] = vals
        else:
            data[c] = vals[0][0] if vals and vals[0] else ""

    return data

def get_sheets(ssid):
    meta = execute(
        sheets().spreadsheets().get(spreadsheetId=ssid)
    )
    return [s["properties"]["title"] for s in meta["sheets"]]

# ============================================================
# LOGICA FIABLE
# ============================================================

def read_verified(ssid, sheet):

    # intento 1
    d1 = batch_get(ssid, sheet)
    d2 = batch_get(ssid, sheet)

    if d1 == d2:
        return d1, True

    # intento 2
    d3 = batch_get(ssid, sheet)
    d4 = batch_get(ssid, sheet)

    if d3 == d4:
        return d3, True

    return d4, False

def parse_num(v):
    if not v:
        return 0
    if isinstance(v,(int,float)):
        return float(v)

    t = re.sub(r"[^\d,.-]", "", str(v))
    t = t.replace(".", "").replace(",", ".")

    try:
        return float(t)
    except:
        return 0

def count_personas(r):
    if not r:
        return 0
    return sum(1 for x in r if x and str(x[0]).strip())

# ============================================================
# CORE
# ============================================================

def scan(year, progress):

    # localizar año
    year_id = None
    for f in list_children(DRIVEROOTID, True):
        if f["name"] == year:
            year_id = f["id"]

    if not year_id:
        return [], []

    rows = []
    fallos = []

    boats = list_children(year_id, True)
    total = sum(len(list_children(b["id"])) for b in boats)

    count = 0

    for b in boats:
        for f in list_children(b["id"]):

            count += 1
            progress.progress(count / max(total, 1))

            if not re.match(r"^[A-Z_]+_\d{6}$", f["name"]):
                continue

            try:
                for sh in get_sheets(f["id"]):

                    data, ok = read_verified(f["id"], sh)

                    if not ok:
                        fallos.append({"LIBRO": f["name"], "HOJA": sh})
                        continue

                    if not data.get("G11"):
                        continue

                    rows.append({
                        "BARCO": b["name"],
                        "AGENCIA": data.get("B2"),
                        "CODIGO": data.get("G11"),
                        "GRUPO": data.get("G13"),
                        "CONFIRMACION": data.get("G5"),
                        "FECHA BOOKING": data.get("P5"),
                        "ITINERARIO": data.get("R5"),
                        "FECHA SALIDA": data.get("C3"),
                        "FECHA LLEGADA": data.get("G19"),
                        "NETO": parse_num(data.get("G17")),
                        "BRUTO": parse_num(data.get("Q55")),
                        "ESTADO RESERVA": data.get("G10"),
                        "PAGO": data.get("Q10"),
                        "COMERCIAL": data.get("G23"),
                        "PERSONAS": count_personas(data.get("G24:G60")),
                        "IDIOMA": data.get("G57"),
                    })

            except:
                fallos.append({"LIBRO": f["name"], "HOJA": "ERROR"})

    return rows, fallos

# ============================================================
# UI
# ============================================================

st.title("Ventas FIT – modo fiable")

year = st.selectbox("Año", get_years())

if st.button("Generar"):

    progress = st.progress(0)

    with st.spinner("Procesando..."):
        rows, fallos = scan(year, progress)

    if not rows:
        st.warning("Sin datos")
    else:
        df = pd.DataFrame(rows)
        df.insert(0, "Nº", range(1, len(df)+1))

        st.success("Datos generados ✅")
        st.dataframe(df)

        # ✅ EXCEL BIEN HECHO
        output = io.BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        st.download_button("Descargar Excel", output, "ventas.xlsx")

    # ✅ REPORTE FALLOS
    if fallos:
        st.warning(f"Fallos detectados: {len(fallos)}")
        st.dataframe(pd.DataFrame(fallos))
``
