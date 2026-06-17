# ============================================================
# PÁGINA: VENTAS_FIT
# ============================================================

import re
import io
import time
import random
import threading
from collections import deque
from datetime import datetime
import pytz
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd

# ── rate limiter para Sheets API (60 lecturas/min/usuario) ───
class RateLimiter:
    """Garantiza no superar max_calls llamadas por cada periodo de 'per_seconds' segundos."""
    def __init__(self, max_calls=50, per_seconds=60):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self.calls = deque()
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now = time.monotonic()
            while self.calls and now - self.calls[0] > self.per_seconds:
                self.calls.popleft()
            if len(self.calls) >= self.max_calls:
                sleep_time = self.per_seconds - (now - self.calls[0]) + 0.05
                if sleep_time > 0:
                    time.sleep(sleep_time)
                now = time.monotonic()
                while self.calls and now - self.calls[0] > self.per_seconds:
                    self.calls.popleft()
            self.calls.append(time.monotonic())

sheets_rate_limiter = RateLimiter(max_calls=50, per_seconds=60)

# ── constantes ──────────────────────────────────────────────
DRIVEROOTID   = "11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm"
LOGOID        = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGOURL       = f"https://lh3.googleusercontent.com/d/{LOGOID}"
TIMEZONE      = pytz.timezone("Europe/Madrid")
COLUMNS_ORDER = [
    "BARCO", "AGENCIA", "CODIGO", "GRUPO",
    "CONFIRMACION", "FECHA BOOKING", "ITINERARIO",
    "FECHA SALIDA", "FECHA LLEGADA",
    "NETO", "BRUTO",
    "ESTADO RESERVA", "PAGO", "COMERCIAL",
    "PERSONAS", "IDIOMA",
]

# ── helpers tiempo ───────────────────────────────────────────
# ── helpers tiempo ───────────────────────────────────────────
def now():
    return datetime.now(pytz.utc).astimezone(TIMEZONE).replace(tzinfo=None)

def getsaludo(lang="es"):
    h = now().hour
    if lang == "en":
        if 6 <= h < 14: return "Good morning"
        if 14 <= h < 21: return "Good afternoon"
        return "Good evening"
    if 6 <= h < 14: return "Buenos días"
    if 14 <= h < 21: return "Buenas tardes"
    return "Buenas noches"

# ── helpers retry / rate limit ──────────────────────────────
def execute_with_retry(request, max_intentos=6, base_delay=2.0, rate_limiter=None):
    intentos = 0
    while True:
        if rate_limiter:
            rate_limiter.wait()
        try:
            return request.execute()
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            intentos += 1
            if intentos >= max_intentos:
                raise Exception(f"Fallo de conexión tras {max_intentos} intentos: {e}")
            time.sleep(base_delay * (2 ** (intentos - 1)) + random.uniform(0, 0.5))
        except HttpError as e:
            status = e.resp.status
            if status == 429:
                intentos += 1
                if intentos >= max_intentos:
                    raise Exception(f"Cuota excedida tras {max_intentos} intentos: {e}")
                wait_time = min(base_delay * (2 ** intentos), 65) + random.uniform(0, 1)
                time.sleep(wait_time)
            elif status in (500, 502, 503, 504):
                intentos += 1
                if intentos >= max_intentos:
                    raise
                time.sleep(base_delay * (2 ** (intentos - 1)) + random.uniform(0, 0.5))
            else:
                raise

# ── Google services ──────────────────────────────────────────
@st.cache_resource
def _creds():
    if "gcpserviceaccount" not in st.secrets:
        raise Exception("Falta gcpserviceaccount en secrets.")
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcpserviceaccount"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )

@st.cache_resource
def drive_svc():
    return build("drive", "v3", credentials=_creds())

@st.cache_resource
def sheets_svc():
    return build("sheets", "v4", credentials=_creds())


        
# ── Drive helpers ────────────────────────────────────────────
def list_children(parent_id, folders_only=False):
    svc = drive_svc()
    q = f"'{parent_id}' in parents and trashed=false"
    if folders_only:
        q += " and mimeType='application/vnd.google-apps.folder'"
    items, token = [], None
    while True:
        r = svc.files().list(
            q=q,
            fields="nextPageToken, files(id,name,mimeType,webViewLink)",
            supportsAllDrives=True, includeItemsFromAllDrives=True,
            corpora="allDrives", pageToken=token, pageSize=1000,
        ).execute()
        items.extend(r.get("files", []))
        token = r.get("nextPageToken")
        if not token:
            break
    return items

def find_child_folder(parent_id, name):
    for f in list_children(parent_id, folders_only=True):
        if f["name"].strip() == name.strip():
            return f
    return None

@st.cache_data(ttl=300)
def get_year_folder_id(year):
    f = find_child_folder(DRIVEROOTID, year)
    return f["id"] if f else None
    
def get_years():
    folders = list_children(DRIVEROOTID, folders_only=True)
    return sorted(
        [f["name"].strip() for f in folders if re.fullmatch(r"\d{4}", f["name"].strip())],
        reverse=True,
    )
@st.cache_data(ttl=300)
def get_year_folder_id(year):
    f = find_child_folder(DRIVEROOTID, year)
    return f["id"] if f else None

# ── Sheets helpers ───────────────────────────────────────────
def get_sheet_titles_ids(ssid):
    request = sheets_svc().spreadsheets().get(
        spreadsheetId=ssid,
        includeGridData=False,
    )
    ss = execute_with_retry(request, rate_limiter=sheets_rate_limiter)
    return [
        {"title": s["properties"]["title"], "sheetId": s["properties"]["sheetId"]}
        for s in ss.get("sheets", [])
    ]

def batch_get(ssid, sheet_title, a1_list):
    ranges = [f"'{sheet_title}'!{a1}" for a1 in a1_list]
    resp = sheets_svc().spreadsheets().values().batchGet(
        spreadsheetId=ssid,
        ranges=ranges,
        majorDimension="ROWS",
        valueRenderOption="UNFORMATTED_VALUE",   # ← añade esto
    ).execute()
    out = {}
    for a1, vr in zip(a1_list, resp.get("valueRanges", [])):
        vals = vr.get("values", [])
        out[a1] = vals[0][0] if vals and vals[0] else ""
    return out
    
def get_column_values(ssid, sheet_title, col_a1):
    resp = sheets_svc().spreadsheets().values().get(
        spreadsheetId=ssid,
        range=f"'{sheet_title}'!{col_a1}",
        majorDimension="COLUMNS",
    ).execute()
    vals = resp.get("values", [[]])
    return [v for v in (vals[0] if vals else []) if str(v).strip()]

def parse_numeric(val):
    if val is None or val == "":
        return 0.0
    # si ya es número (la API a veces devuelve floats)
    if isinstance(val, (int, float)):
        return float(val)
    text = str(val).strip()
    # quita símbolos de moneda y espacios
    text = re.sub(r"[€$£\s%]", "", text)
    if not text:
        return 0.0
    # detecta formato europeo: punto como separador de miles, coma como decimal
    # ej: "1.234,56" → "1234.56"
    if re.search(r"\d\.\d{3},", text) or (text.count(",") == 1 and text.count(".") >= 1 and text.rfind(",") > text.rfind(".")):
        text = text.replace(".", "").replace(",", ".")
    # detecta formato con solo coma decimal: "1234,56"
    elif text.count(",") == 1 and "." not in text:
        text = text.replace(",", ".")
    # si solo tiene puntos como separador de miles sin coma: "1.234" → "1234"
    elif text.count(".") >= 1 and "," not in text:
        # distingue "1.234" (miles) de "1.23" (decimal)
        parts = text.split(".")
        if len(parts[-1]) == 3:
            text = text.replace(".", "")
        # si no, lo deja como está (punto decimal normal)
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group()) if m else 0.0
def fmt_date(val):
    return str(val).strip() if val else ""

# ── Lectura de una hoja ──────────────────────────────────────
CELLS_NEEDED = [
    "B2", "G11", "G13",
    "G5", "P5", "R5",
    "C3", "G19", "G17", "K17",
    "G10", "G57", "Q10", "G23", "Q55",
]

def read_sheet_data(ssid, sheet_title, year):
    a1_list = CELLS_NEEDED + ["Q33:R39", "G24:G60", "Q55"]
    ranges = [f"'{sheet_title}'!{a1}" for a1 in a1_list]

    request = sheets_svc().spreadsheets().values().batchGet(
        spreadsheetId=ssid,
        ranges=ranges,
        majorDimension="ROWS",
        valueRenderOption="UNFORMATTED_VALUE",
    )
    try:
        resp = execute_with_retry(request, rate_limiter=sheets_rate_limiter)
    except Exception as e:
        raise Exception(f"Error en batchGet de '{sheet_title}': {e}")

    value_ranges = resp.get("valueRanges", [])
    data_by_range = dict(zip(a1_list, value_ranges))

    # ── celdas sueltas ──
    cells = {}
    for a1 in CELLS_NEEDED:
        vals = data_by_range.get(a1, {}).get("values", [])
        cells[a1] = vals[0][0] if vals and vals[0] else ""

    # comprobación de localizador ANTES de seguir procesando
    localizador = str(cells.get("G11", "")).strip()
    if not localizador:
        return None
    if localizador.upper().endswith("_GROUP"):
        return None

    year_short = str(year)[2:]  # "2026" → "26"
    m = re.search(r"(\d{6})-\d{3}$", localizador)
    if not m:
        return None
    if not m.group(1).startswith(year_short):
        return None

    # ── NETO: suma de Q33:R39 ──
    neto_rows = data_by_range.get("Q33:R39", {}).get("values", [])
    neto = sum(
        parse_numeric(cell)
        for row in neto_rows
        for cell in row
        if cell not in (None, "")
    )

    # ── PERSONAS: cuenta de no vacíos en G24:G60 ──
    # majorDimension="ROWS" => cada fila es una lista de 1 elemento (columna G)
    personas_rows = data_by_range.get("G24:G60", {}).get("values", [])
    personas = sum(1 for row in personas_rows if row and str(row[0]).strip())

    # ── BRUTO: Q55 ──
    bruto_vals = data_by_range.get("Q55", {}).get("values", [])
    bruto = parse_numeric(bruto_vals[0][0]) if bruto_vals and bruto_vals[0] else 0.0

    return {
        "BARCO":          str(cells.get("G13", "")).strip(),
        "AGENCIA":        str(cells.get("G5",  "")).strip(),
        "CODIGO":         str(cells.get("P5",  "")).strip(),
        "GRUPO":          str(cells.get("R5",  "")).strip(),
        "CONFIRMACION":   localizador,
        "FECHA BOOKING":  fmt_date(cells.get("C3",  "")),
        "ITINERARIO":     str(cells.get("G19", "")).strip(),
        "FECHA SALIDA":   fmt_date(cells.get("G17", "")),
        "FECHA LLEGADA":  fmt_date(cells.get("K17", "")),
        "NETO":           round(neto,  2),
        "BRUTO":          round(bruto, 2),
        "ESTADO RESERVA": str(cells.get("G10", "")).strip(),
        "PAGO":           str(cells.get("G57", "")).strip(),
        "COMERCIAL":      str(cells.get("Q10", "")).strip(),
        "PERSONAS":       personas,
        "IDIOMA":         str(cells.get("G23", "")).strip(),
    }
# ── Lectura de un libro completo ─────────────────────────────
def read_book(ssid, year):
    results = []
    try:
        sheets = get_sheet_titles_ids(ssid)
    except Exception as e:
        st.warning(f"No se pudo leer la lista de hojas del libro `{ssid}`: {e}")
        return []
    for sh in sheets:
        try:
            row = read_sheet_data(ssid, sh["title"], year)
            if row:
                results.append(row)
        except Exception as e:
            st.warning(f"Error leyendo hoja '{sh['title']}' del libro `{ssid}`: {e}")
    return results
def read_book_verified(ssid, year, max_intentos=5):
    intentos = 0
    ultima_pasada = None
    while intentos < max_intentos:
        pasada1 = read_book(ssid, year)
        pasada2 = read_book(ssid, year)
        if pasada1 == pasada2:
            return pasada1
        intentos += 1
        ultima_pasada = pasada2

    st.warning(
        f"⚠️ El libro `{ssid}` no dio resultados consistentes tras {max_intentos} intentos. "
        f"Se usará la última lectura obtenida, revísala si algo no encaja."
    )
    return ultima_pasada
    
SALIDA_PATTERN = re.compile(r"^[A-Z_]+_\d{6}$")
def scan_year(year, progress_cb=None, on_row_verified=None):
    year_id = get_year_folder_id(year)
    if not year_id:
        return []

    boat_folders = list_children(year_id, folders_only=True)
    file_map = {}
    total_files = 0
    for bf in boat_folders:
        files = list_children(bf["id"], folders_only=False)
        salidas = [f for f in files if SALIDA_PATTERN.match(f["name"].strip())]
        file_map[bf["name"]] = salidas
        total_files += len(salidas)

    results = []
    processed = 0
    for boat_name, salidas in file_map.items():
        for fobj in salidas:
            fname = fobj["name"].strip()
            ssid  = fobj["id"]
            if progress_cb:
                progress_cb(processed, total_files, f"{boat_name} / {fname}")
            rows = read_book_verified(ssid, year)
            for row in rows:
                results.append(row)
                if on_row_verified:
                    on_row_verified(row)
            processed += 1

    if progress_cb:
        progress_cb(total_files, total_files, "Completado")
    return results

# ── Export Excel ─────────────────────────────────────────────
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="VENTAS FIT")
        ws = writer.sheets["VENTAS FIT"]
        for col in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)
    buf.seek(0)
    return buf.read()

# ============================================================
# PÁGINA
# ============================================================
st.set_page_config(
    page_title="Ventas FIT – Crucemundo Hub",
    page_icon="favicon1.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:"DM Sans",sans-serif;background:#FFFFFF!important;}
[data-testid="stAppViewContainer"]{background:#FFFFFF!important;}
[data-testid="stHeader"]{background:transparent!important;}
section[data-testid="stSidebar"]{display:none!important;}
.block-container,.stMainBlockContainer,[data-testid="stMainBlockContainer"]{
    padding-top:0!important;padding-bottom:1rem!important;
    padding-left:1rem!important;padding-right:1rem!important;
    max-width:1900px!important;margin:0 auto!important;
}
.portal-header{padding:0.1rem 0 0.55rem 0;display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:0.55rem;}
.portal-header-left{display:flex;align-items:center;gap:0.9rem;}
.portal-logo{height:42px;width:auto;object-fit:contain;display:block;}
.portal-title{font-size:0.96rem;font-weight:800;color:#1F2937;line-height:1.15;}
.portal-subtitle{font-size:0.72rem;color:#667085;line-height:1.2;margin-top:0.12rem;}
.user-top{font-size:0.72rem;color:#566079;white-space:nowrap;}
.web-chip-blue{display:inline-flex;align-items:center;justify-content:center;
    padding:0.38rem 0.82rem;border-radius:999px;font-size:0.71rem;font-weight:800;
    background:#E0ECFF;border:1px solid #BFD4FF;color:#1E4FBF!important;cursor:default;}
div.stButton>button{
    border-radius:999px!important;padding:0 1rem!important;
    font-size:0.78rem!important;font-weight:800!important;
    font-family:"DM Sans",sans-serif!important;
    border:2px solid transparent!important;
    background:linear-gradient(180deg,#2F6DF6 0%,#245FE0 100%)!important;
    color:#fff!important;
    box-shadow:0 4px 14px rgba(37,99,235,0.22)!important;
    transition:transform .15s,box-shadow .15s!important;
}
div.stButton>button:hover{transform:translateY(-1px);box-shadow:0 8px 20px rgba(37,99,235,0.28)!important;}
div.stButton>button:disabled{background:#CBD5E1!important;box-shadow:none!important;}
div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stMultiSelect"] label{
    color:#334155!important;font-size:0.80rem!important;font-weight:700!important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"]>div,
div[data-testid="stTextInput"] input,
div[data-testid="stMultiSelect"] div[data-baseweb="select"]>div{
    background:#fff!important;border:1.6px solid #CBD5E1!important;
    border-radius:14px!important;color:#1F2937!important;
    min-height:44px!important;font-family:"DM Sans",sans-serif!important;
    font-size:0.88rem!important;font-weight:600!important;
    box-shadow:0 2px 8px rgba(15,23,42,0.05)!important;
}
.vf-table-wrap{overflow-x:auto;margin-top:1rem;}
.vf-table{width:100%;border-collapse:collapse;font-family:"DM Sans",sans-serif;}
.vf-table th{
    background:#F0F4FA;color:#334155;font-size:0.72rem;font-weight:800;
    padding:0.55rem 0.65rem;border-bottom:2px solid #DCE5F0;
    white-space:nowrap;text-align:left;position:sticky;top:0;z-index:1;
}
.vf-table td{
    font-size:0.75rem;color:#1F2937;padding:0.48rem 0.65rem;
    border-bottom:1px solid #EEF2F7;vertical-align:top;font-weight:500;
}
.vf-table tr:hover td{background:#F8FAFF;}
.vf-table td.num{text-align:right;font-variant-numeric:tabular-nums;}
.pill{display:inline-flex;align-items:center;padding:0.22rem 0.5rem;
      border-radius:999px;font-size:0.68rem;font-weight:800;white-space:nowrap;}
.pill-conf{background:#DCFCE7;color:#166534;border:1px solid #86EFAC;}
.pill-noconf{background:#FEF3C7;color:#92400E;border:1px solid #FCD34D;}
.pill-canc{background:#FEE2E2;color:#991B1B;border:1px solid #FCA5A5;}
.pill-pago{background:#DBEAFE;color:#1D4ED8;border:1px solid #93C5FD;}
.pill-pte{background:#FEF3C7;color:#92400E;border:1px solid #FCD34D;}
.pill-neutral{background:#F1F5F9;color:#475569;border:1px solid #CBD5E1;}
.summary-row{display:flex;gap:1rem;flex-wrap:wrap;margin:0.75rem 0 1rem;}
.sum-card{flex:1;min-width:120px;background:#F8FAFF;border:1px solid #DCE5F0;
          border-radius:16px;padding:0.65rem 0.9rem;}
.sum-label{font-size:0.68rem;color:#64748B;font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
.sum-value{font-size:1.22rem;font-weight:800;color:#1F2937;margin-top:0.18rem;}
.portal-footer{margin-top:1rem;padding:.5rem 0 0;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;}
.footer-text{font-size:.71rem;color:#A2ABBD;}
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("authenticated"):
    st.warning("Debes iniciar sesión primero. Vuelve a la página principal.")
    if st.button("← Volver al Hub"):
        st.switch_page("app.py")
    st.stop()

DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Sin usuario"
SALUDO    = getsaludo("es")
SALUDOEN  = getsaludo("en")

st.markdown(f"""
<div class="portal-header">
  <div class="portal-header-left">
    <img class="portal-logo" src="{LOGOURL}" alt="Logo">
    <div>
      <div class="portal-title">{SALUDO}, {DISPLAYUSER}. Ventas FIT</div>
      <div class="portal-subtitle">Resumen de reservas FIT por año · Google Drive backend</div>
    </div>
  </div>
  <div class="user-top">{DISPLAYUSER}</div>
</div>
""", unsafe_allow_html=True)

back_col, _ = st.columns([1, 9])
with back_col:
    if st.button("← Hub", key="back_to_hub"):
        st.switch_page("app.py")

st.markdown('<hr style="border:none;border-top:2px solid #E2E8F0;margin:.4rem 0 1rem;">', unsafe_allow_html=True)

col_year, col_btn, col_spacer = st.columns([2, 1.2, 6], gap="medium")
with col_year:
    try:
        years = get_years()
    except Exception as e:
        st.error(f"Error al obtener años: {e}")
        st.stop()
    selected_year = st.selectbox(
        "AÑO / YEAR", options=years, index=None,
        placeholder="Selecciona un año…", key="vf_year",
    )

with col_btn:
    st.markdown("<div style='margin-top:1.6rem;'>", unsafe_allow_html=True)
    run_scan = st.button("Generar informe", key="vf_run", disabled=not selected_year)
    st.markdown("</div>", unsafe_allow_html=True)

if st.button("🔍 Debug un libro", key="debug_libro"):
    try:
        year_id = get_year_folder_id("2026")
        if not year_id:
            st.warning("No se encontró la carpeta del año 2026")
        else:
            boat_folders = list_children(year_id, folders_only=True)
            encontrado = False
            for bf in boat_folders:
                files = list_children(bf["id"], folders_only=False)
                salidas = [f for f in files if re.match(r"^[A-Z_]+_\d{6}$", f["name"].strip())]
                if salidas:
                    fobj = salidas[0]
                    st.write(f"**Barco:** {bf['name']} · **Libro:** {fobj['name']}")
                    sheets = get_sheet_titles_ids(fobj["id"])
                    st.write(f"**Total hojas:** {len(sheets)}")
                    for sh in sheets:
                        g11 = batch_get(fobj["id"], sh["title"], ["G11"]).get("G11", "")
                        st.write(f"Hoja: `{sh['title']}` → G11: `{repr(g11)}`")
                    encontrado = True
                    break
            if not encontrado:
                st.warning("Ninguna carpeta de barco tiene archivos que coincidan con el patrón de nombre esperado.")
    except Exception as e:
        st.exception(e)

if "vf_results" not in st.session_state:
    st.session_state.vf_results = None
if "vf_year_loaded" not in st.session_state:
    st.session_state.vf_year_loaded = None

if run_scan and selected_year:
    st.session_state.vf_results = None
    st.session_state.vf_year_loaded = None

    prog_bar   = st.progress(0.0, text="Iniciando escaneo…")
    status_ph  = st.empty()
    summary_ph = st.empty()
    table_ph   = st.empty()

    rows_acumuladas = []

    def update_progress(done, total, label):
        pct = done / total if total else 0
        prog_bar.progress(min(pct, 1.0), text=f"Procesando {done}/{total}: {label}")
        status_ph.caption(label)

    def pintar_tabla(rows):
        def _estado(v):
            u = str(v).strip().upper()
            if "CONFIRM" in u: return f'<span class="pill pill-conf">{v}</span>'
            if "CANCEL"  in u: return f'<span class="pill pill-canc">{v}</span>'
            if "NO CONF" in u: return f'<span class="pill pill-noconf">{v}</span>'
            return f'<span class="pill pill-neutral">{v}</span>'

        def _pago(v):
            u = str(v).strip().upper()
            if "PAGADO" in u: return f'<span class="pill pill-conf">{v}</span>'
            if "PTE"    in u: return f'<span class="pill pill-pte">{v}</span>'
            if "DEPOSI" in u: return f'<span class="pill pill-pago">{v}</span>'
            return f'<span class="pill pill-neutral">{v}</span>'

        df_live = pd.DataFrame(rows, columns=COLUMNS_ORDER)
        summary_ph.markdown(f"""
        <div class="summary-row">
          <div class="sum-card"><div class="sum-label">Reservas</div><div class="sum-value">{len(df_live):,}</div></div>
          <div class="sum-card"><div class="sum-label">Personas</div><div class="sum-value">{int(df_live['PERSONAS'].sum()):,}</div></div>
          <div class="sum-card"><div class="sum-label">Neto Total</div><div class="sum-value">{df_live['NETO'].sum():,.2f} €</div></div>
          <div class="sum-card"><div class="sum-label">Bruto Total</div><div class="sum-value">{df_live['BRUTO'].sum():,.2f} €</div></div>
        </div>
        """, unsafe_allow_html=True)

        header_cells = "".join(f"<th>{c}</th>" for c in COLUMNS_ORDER)
        rows_html = ""
        for r in rows:
            rows_html += f"""<tr>
              <td>{r['BARCO']}</td><td>{r['AGENCIA']}</td><td>{r['CODIGO']}</td><td>{r['GRUPO']}</td>
              <td><b>{r['CONFIRMACION']}</b></td><td>{r['FECHA BOOKING']}</td><td>{r['ITINERARIO']}</td>
              <td>{r['FECHA SALIDA']}</td><td>{r['FECHA LLEGADA']}</td>
              <td class="num">{r['NETO']:,.2f} €</td><td class="num">{r['BRUTO']:,.2f} €</td>
              <td>{_estado(r['ESTADO RESERVA'])}</td><td>{_pago(r['PAGO'])}</td>
              <td>{r['COMERCIAL']}</td><td class="num">{int(r['PERSONAS'])}</td><td>{r['IDIOMA']}</td>
            </tr>"""
        table_ph.html(f'<div class="vf-table-wrap"><table class="vf-table"><thead><tr>{header_cells}</tr></thead><tbody>{rows_html}</tbody></table></div>')

    def on_row_verified(row):
        rows_acumuladas.append(row)
        if len(rows_acumuladas) % 3 == 0:
            pintar_tabla(rows_acumuladas)
    
    try:
        rows = scan_year(selected_year, progress_cb=update_progress, on_row_verified=on_row_verified)
        prog_bar.empty()
        status_ph.empty()
        st.session_state.vf_results     = rows
        st.session_state.vf_year_loaded = selected_year
        if not rows:
            st.info("No se han encontrado reservas para el año seleccionado.")
    except Exception as e:
        prog_bar.empty()
        status_ph.empty()
        st.session_state.vf_results = rows_acumuladas  # ← conserva lo ya pintado aunque falle
        st.session_state.vf_year_loaded = selected_year
        st.exception(e)
        st.warning(f"Escaneo interrumpido. Se han procesado {len(rows_acumuladas)} reservas antes del error.")
    
    rows = st.session_state.get("vf_results")
    year_loaded = st.session_state.get("vf_year_loaded")
    
    if rows:
        df_all = pd.DataFrame(rows, columns=COLUMNS_ORDER)
    
        st.markdown(f'<span class="web-chip-blue">FILTROS · AÑO {year_loaded} · {len(df_all)} registros</span>', unsafe_allow_html=True)
    
        fc1, fc2, fc3, fc4, fc5, fc6 = st.columns([2, 2, 2, 2, 2, 2], gap="medium")
        with fc1:
            sel_barco = st.multiselect("BARCO", options=sorted(df_all["BARCO"].dropna().unique()), default=[], key="f_barco")
        with fc2:
            sel_agencia = st.multiselect("AGENCIA", options=sorted(df_all["AGENCIA"].dropna().unique()), default=[], key="f_agencia")
        with fc3:
            sel_estado = st.multiselect("ESTADO RESERVA", options=sorted(df_all["ESTADO RESERVA"].dropna().unique()), default=[], key="f_estado")
        with fc4:
            sel_comercial = st.multiselect("COMERCIAL", options=sorted(df_all["COMERCIAL"].dropna().unique()), default=[], key="f_comercial")
        with fc5:
            sel_pago = st.multiselect("PAGO", options=sorted(df_all["PAGO"].dropna().unique()), default=[], key="f_pago")
        with fc6:
            sel_idioma = st.multiselect("IDIOMA", options=sorted(df_all["IDIOMA"].dropna().unique()), default=[], key="f_idioma")
    
        search_col, _ = st.columns([3, 7])
        with search_col:
            txt_search = st.text_input("🔍 Buscar en tabla", key="f_txt", placeholder="Localizador, agencia, itinerario…")
    
        df = df_all.copy()
        if sel_barco:     df = df[df["BARCO"].isin(sel_barco)]
        if sel_agencia:   df = df[df["AGENCIA"].isin(sel_agencia)]
        if sel_estado:    df = df[df["ESTADO RESERVA"].isin(sel_estado)]
        if sel_comercial: df = df[df["COMERCIAL"].isin(sel_comercial)]
        if sel_pago:      df = df[df["PAGO"].isin(sel_pago)]
        if sel_idioma:    df = df[df["IDIOMA"].isin(sel_idioma)]
        if txt_search.strip():
            mask = df.apply(lambda r: txt_search.strip().lower() in " ".join(str(v) for v in r.values).lower(), axis=1)
            df = df[mask]
    
        st.markdown(f"""
        <div class="summary-row">
          <div class="sum-card"><div class="sum-label">Reservas</div><div class="sum-value">{len(df):,}</div></div>
          <div class="sum-card"><div class="sum-label">Personas</div><div class="sum-value">{int(df['PERSONAS'].sum()):,}</div></div>
          <div class="sum-card"><div class="sum-label">Neto Total</div><div class="sum-value">{df['NETO'].sum():,.2f} €</div></div>
          <div class="sum-card"><div class="sum-label">Bruto Total</div><div class="sum-value">{df['BRUTO'].sum():,.2f} €</div></div>
        </div>
        """, unsafe_allow_html=True)

    st.download_button(
        label="⬇ Exportar a Excel",
        data=to_excel_bytes(df),
        file_name=f"VENTAS_FIT_{year_loaded}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="vf_export",
    )

def estado_pill(v):
    u = str(v).strip().upper()
    if "CONFIRM" in u: return f'<span class="pill pill-conf">{v}</span>'
    if "CANCEL"  in u: return f'<span class="pill pill-canc">{v}</span>'
    if "NO CONF" in u: return f'<span class="pill pill-noconf">{v}</span>'
    return f'<span class="pill pill-neutral">{v}</span>'

def pago_pill(v):
    u = str(v).strip().upper()
    if "PAGADO" in u:  return f'<span class="pill pill-conf">{v}</span>'
    if "PTE"    in u:  return f'<span class="pill pill-pte">{v}</span>'
    if "DEPOSI" in u:  return f'<span class="pill pill-pago">{v}</span>'
    return f'<span class="pill pill-neutral">{v}</span>'

    if df.empty:
        st.info("Sin resultados para los filtros aplicados.")
    else:
        header_cells = "".join(f"<th>{c}</th>" for c in COLUMNS_ORDER)
        rows_html = ""
        for _, r in df.iterrows():
            rows_html += f"""<tr>
              <td>{r['BARCO']}</td><td>{r['AGENCIA']}</td><td>{r['CODIGO']}</td><td>{r['GRUPO']}</td>
              <td><b>{r['CONFIRMACION']}</b></td><td>{r['FECHA BOOKING']}</td><td>{r['ITINERARIO']}</td>
              <td>{r['FECHA SALIDA']}</td><td>{r['FECHA LLEGADA']}</td>
              <td class="num">{r['NETO']:,.2f} €</td><td class="num">{r['BRUTO']:,.2f} €</td>
              <td>{estado_pill(r['ESTADO RESERVA'])}</td><td>{pago_pill(r['PAGO'])}</td>
              <td>{r['COMERCIAL']}</td><td class="num">{int(r['PERSONAS'])}</td><td>{r['IDIOMA']}</td>
            </tr>"""
        st.html(f'<div class="vf-table-wrap"><table class="vf-table"><thead><tr>{header_cells}</tr></thead><tbody>{rows_html}</tbody></table></div>')

st.markdown('<div class="portal-footer"><div class="footer-text">Crucemundo Hub · Ventas FIT</div></div>', unsafe_allow_html=True)
