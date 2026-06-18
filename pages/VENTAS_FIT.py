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
    def __init__(self, max_calls=50, per_seconds=60):
        self.max_calls   = max_calls
        self.per_seconds = per_seconds
        self.calls       = deque()
        self.lock        = threading.Lock()

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
    "#",
    "BARCO", "AGENCIA", "CODIGO", "GRUPO",
    "CONFIRMACION", "FECHA BOOKING", "ITINERARIO",
    "FECHA SALIDA", "FECHA LLEGADA",
    "NETO", "BRUTO",
    "ESTADO RESERVA", "PAGO", "COMERCIAL",
    "PERSONAS", "IDIOMA",
]
# Columnas de datos reales (sin el contador "#")
DATA_COLUMNS = COLUMNS_ORDER[1:]

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

# ── Numeric / date helpers ───────────────────────────────────
def parse_numeric(val):
    if val is None or val == "":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    text = str(val).strip()
    text = re.sub(r"[€$£\s%]", "", text)
    if not text:
        return 0.0
    if re.search(r"\d\.\d{3},", text) or (
        text.count(",") == 1 and text.count(".") >= 1
        and text.rfind(",") > text.rfind(".")
    ):
        text = text.replace(".", "").replace(",", ".")
    elif text.count(",") == 1 and "." not in text:
        text = text.replace(",", ".")
    elif text.count(".") >= 1 and "," not in text:
        parts = text.split(".")
        if len(parts[-1]) == 3:
            text = text.replace(".", "")
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group()) if m else 0.0

def fmt_date(val):
    return str(val).strip() if val else ""

# ── Patrón localizador: BARCO_AAMMDD  (p.ej. MELODY_260314) ─
#    Acepta letras, dígitos y guiones en la parte del barco,
#    seguido de _ y exactamente 6 dígitos.
LOCALIZADOR_RE = re.compile(r"^[A-Z0-9\-]+_\d{6}$", re.IGNORECASE)

# ── Celdas que se leen de cada hoja ─────────────────────────
CELLS_NEEDED = [
    "G11",                          # localizador
    "G13",                          # barco
    "G5",  "P5",  "R5",            # agencia, código, grupo
    "C3",                           # fecha booking
    "G19",                          # itinerario
    "G17", "K17",                   # fecha salida / llegada
    "G10",                          # estado reserva
    "G57",                          # pago
    "Q10",                          # comercial
    "G23",                          # idioma
]
RANGE_NETO    = "Q33:R39"
RANGE_PERSONA = "G24:G60"
RANGE_BRUTO   = "Q55"

# ── Lectura de una hoja ──────────────────────────────────────
def read_sheet_data(ssid, sheet_title, year):
    # Construimos la lista de rangos sin duplicados
    a1_list = CELLS_NEEDED + [RANGE_NETO, RANGE_PERSONA, RANGE_BRUTO]
    ranges  = [f"'{sheet_title}'!{a1}" for a1 in a1_list]

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
    def cell(a1):
        vals = data_by_range.get(a1, {}).get("values", [])
        return vals[0][0] if vals and vals[0] else ""

    # ── Filtro de localizador: solo buscamos en G11 ──────────
    localizador = str(cell("G11")).strip()
    if not localizador:
        return None
    # Ignorar hojas de grupo
    if localizador.upper().endswith("_GROUP"):
        return None
    # Debe coincidir con el patrón BARCO_AAMMDD
    if not LOCALIZADOR_RE.match(localizador):
        return None

    # ── NETO: suma de Q33:R39 ────────────────────────────────
    neto_rows = data_by_range.get(RANGE_NETO, {}).get("values", [])
    neto = sum(
        parse_numeric(c)
        for row in neto_rows
        for c in row
        if c not in (None, "")
    )

    # ── PERSONAS: filas no vacías en G24:G60 ─────────────────
    personas_rows = data_by_range.get(RANGE_PERSONA, {}).get("values", [])
    personas = sum(1 for row in personas_rows if row and str(row[0]).strip())

    # ── BRUTO: Q55 ───────────────────────────────────────────
    bruto_vals = data_by_range.get(RANGE_BRUTO, {}).get("values", [])
    bruto = parse_numeric(bruto_vals[0][0]) if bruto_vals and bruto_vals[0] else 0.0

    return {
        "BARCO":          str(cell("G13")).strip(),
        "AGENCIA":        str(cell("G5")).strip(),
        "CODIGO":         str(cell("P5")).strip(),
        "GRUPO":          str(cell("R5")).strip(),
        "CONFIRMACION":   localizador,
        "FECHA BOOKING":  fmt_date(cell("C3")),
        "ITINERARIO":     str(cell("G19")).strip(),
        "FECHA SALIDA":   fmt_date(cell("G17")),
        "FECHA LLEGADA":  fmt_date(cell("K17")),
        "NETO":           round(neto,  2),
        "BRUTO":          round(bruto, 2),
        "ESTADO RESERVA": str(cell("G10")).strip(),
        "PAGO":           str(cell("G57")).strip(),
        "COMERCIAL":      str(cell("Q10")).strip(),
        "PERSONAS":       personas,
        "IDIOMA":         str(cell("G23")).strip(),
    }

# ── Lectura de un libro completo ─────────────────────────────
# Lee todas las hojas de un spreadsheet y llama a on_row_cb
# por cada fila válida encontrada, para pintado progresivo.
def read_book(ssid, year, on_row_cb=None):
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
                if on_row_cb:
                    on_row_cb(row)
        except Exception as e:
            st.warning(f"Error leyendo hoja '{sh['title']}' del libro `{ssid}`: {e}")
    return results

# ── Escaneo anual ────────────────────────────────────────────
SALIDA_PATTERN = re.compile(r"^[A-Z_]+_\d{6}$")

def scan_year(year, progress_cb=None, on_row_verified=None):
    year_id = get_year_folder_id(year)
    if not year_id:
        return []

    boat_folders = list_children(year_id, folders_only=True)
    file_map = {}
    total_files = 0
    for bf in boat_folders:
        files  = list_children(bf["id"], folders_only=False)
        salidas = [f for f in files if SALIDA_PATTERN.match(f["name"].strip())]
        file_map[bf["name"]] = salidas
        total_files += len(salidas)

    results  = []
    processed = 0
    for boat_name, salidas in file_map.items():
        for fobj in salidas:
            fname = fobj["name"].strip()
            ssid  = fobj["id"]
            if progress_cb:
                progress_cb(processed, total_files, f"{boat_name} / {fname}")
            rows = read_book(ssid, year, on_row_cb=on_row_verified)
            results.extend(rows)
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

# ── Pills ────────────────────────────────────────────────────
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

# ── Render tabla ─────────────────────────────────────────────
def build_table_html(rows):
    """Construye el HTML completo de la tabla a partir de una lista de dicts."""
    header_cells = "".join(f"<th>{c}</th>" for c in COLUMNS_ORDER)
    rows_html = ""
    for i, r in enumerate(rows, start=1):
        rows_html += f"""<tr>
          <td class="num">{i}</td>
          <td>{r['BARCO']}</td><td>{r['AGENCIA']}</td><td>{r['CODIGO']}</td><td>{r['GRUPO']}</td>
          <td><b>{r['CONFIRMACION']}</b></td><td>{r['FECHA BOOKING']}</td><td>{r['ITINERARIO']}</td>
          <td>{r['FECHA SALIDA']}</td><td>{r['FECHA LLEGADA']}</td>
          <td class="num">{r['NETO']:,.2f} €</td><td class="num">{r['BRUTO']:,.2f} €</td>
          <td>{estado_pill(r['ESTADO RESERVA'])}</td><td>{pago_pill(r['PAGO'])}</td>
          <td>{r['COMERCIAL']}</td><td class="num">{int(r['PERSONAS'])}</td><td>{r['IDIOMA']}</td>
        </tr>"""
    return (
        f'<div class="vf-table-wrap">'
        f'<table class="vf-table">'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>'
    )

def build_summary_html(rows):
    df_live = pd.DataFrame(rows, columns=DATA_COLUMNS)
    return f"""
    <div class="summary-row">
      <div class="sum-card"><div class="sum-label">Reservas</div><div class="sum-value">{len(df_live):,}</div></div>
      <div class="sum-card"><div class="sum-label">Personas</div><div class="sum-value">{int(df_live['PERSONAS'].sum()):,}</div></div>
      <div class="sum-card"><div class="sum-label">Neto Total</div><div class="sum-value">{df_live['NETO'].sum():,.2f} €</div></div>
      <div class="sum-card"><div class="sum-label">Bruto Total</div><div class="sum-value">{df_live['BRUTO'].sum():,.2f} €</div></div>
    </div>"""

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

# ── Auth guard ───────────────────────────────────────────────
if not st.session_state.get("authenticated"):
    st.warning("Debes iniciar sesión primero. Vuelve a la página principal.")
    if st.button("← Volver al Hub"):
        st.switch_page("app.py")
    st.stop()

DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Sin usuario"
SALUDO      = getsaludo("es")

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

# ── Controles de año ─────────────────────────────────────────
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

# ── Session state ────────────────────────────────────────────
if "vf_results" not in st.session_state:
    st.session_state.vf_results     = None
if "vf_year_loaded" not in st.session_state:
    st.session_state.vf_year_loaded = None

# ── Escaneo ──────────────────────────────────────────────────
if run_scan and selected_year:
    st.session_state.vf_results     = None
    st.session_state.vf_year_loaded = None

    prog_bar   = st.progress(0.0, text="Iniciando escaneo…")
    status_ph  = st.empty()
    summary_ph = st.empty()
    table_ph   = st.empty()
    audit_ph   = st.empty()

    rows_acumuladas = []

    def update_progress(done, total, label):
        pct = done / total if total else 0
        prog_bar.progress(min(pct, 1.0), text=f"Procesando {done}/{total}: {label}")
        status_ph.caption(label)

    def on_row_verified(row):
        rows_acumuladas.append(row)
        audit_ph.caption(
            f"✅ Filas acumuladas: {len(rows_acumuladas)} · "
            f"Última: {row['CONFIRMACION']} ({row['BARCO']})"
        )
        # Repintamos la tabla tras cada nueva fila; Streamlit actualiza el placeholder
        summary_ph.markdown(build_summary_html(rows_acumuladas), unsafe_allow_html=True)
        table_ph.html(build_table_html(rows_acumuladas))

    try:
        rows = scan_year(selected_year, progress_cb=update_progress, on_row_verified=on_row_verified)
        # Pintado final completo (por si la última tanda no pintó)
        if rows:
            summary_ph.markdown(build_summary_html(rows), unsafe_allow_html=True)
            table_ph.html(build_table_html(rows))
        st.session_state.vf_results     = rows
        st.session_state.vf_year_loaded = selected_year
        if not rows:
            st.info("No se han encontrado reservas para el año seleccionado.")
    except Exception as e:
        # Conservamos lo que ya se acumuló antes del error
        st.session_state.vf_results     = rows_acumuladas
        st.session_state.vf_year_loaded = selected_year
        st.exception(e)
        st.warning(f"Escaneo interrumpido. Se han procesado {len(rows_acumuladas)} reservas antes del error.")
    finally:
        prog_bar.empty()
        status_ph.empty()
        audit_ph.empty()
        summary_ph.empty()
        table_ph.empty()

# ── Resultado + filtros ──────────────────────────────────────
rows        = st.session_state.get("vf_results")
year_loaded = st.session_state.get("vf_year_loaded")

if rows:
    df_all = pd.DataFrame(rows, columns=DATA_COLUMNS)

    st.markdown(
        f'<span class="web-chip-blue">FILTROS · AÑO {year_loaded} · {len(df_all)} registros</span>',
        unsafe_allow_html=True,
    )

    fc1, fc2, fc3, fc4, fc5, fc6 = st.columns([2, 2, 2, 2, 2, 2], gap="medium")
    with fc1:
        sel_barco     = st.multiselect("BARCO",         options=sorted(df_all["BARCO"].dropna().unique()),          default=[], key="f_barco")
    with fc2:
        sel_agencia   = st.multiselect("AGENCIA",       options=sorted(df_all["AGENCIA"].dropna().unique()),        default=[], key="f_agencia")
    with fc3:
        sel_estado    = st.multiselect("ESTADO RESERVA",options=sorted(df_all["ESTADO RESERVA"].dropna().unique()), default=[], key="f_estado")
    with fc4:
        sel_comercial = st.multiselect("COMERCIAL",     options=sorted(df_all["COMERCIAL"].dropna().unique()),      default=[], key="f_comercial")
    with fc5:
        sel_pago      = st.multiselect("PAGO",          options=sorted(df_all["PAGO"].dropna().unique()),           default=[], key="f_pago")
    with fc6:
        sel_idioma    = st.multiselect("IDIOMA",        options=sorted(df_all["IDIOMA"].dropna().unique()),         default=[], key="f_idioma")

    search_col, _ = st.columns([3, 7])
    with search_col:
        txt_search = st.text_input("🔍 Buscar en tabla", key="f_txt", placeholder="Localizador, agencia, itinerario…")

    df = df_all.copy()
    if sel_barco:      df = df[df["BARCO"].isin(sel_barco)]
    if sel_agencia:    df = df[df["AGENCIA"].isin(sel_agencia)]
    if sel_estado:     df = df[df["ESTADO RESERVA"].isin(sel_estado)]
    if sel_comercial:  df = df[df["COMERCIAL"].isin(sel_comercial)]
    if sel_pago:       df = df[df["PAGO"].isin(sel_pago)]
    if sel_idioma:     df = df[df["IDIOMA"].isin(sel_idioma)]
    if txt_search.strip():
        mask = df.apply(
            lambda r: txt_search.strip().lower() in " ".join(str(v) for v in r.values).lower(),
            axis=1,
        )
        df = df[mask]

    # ── Resumen filtrado ──────────────────────────────────────
    st.markdown(build_summary_html(df.to_dict("records")), unsafe_allow_html=True)

    # ── Exportar ──────────────────────────────────────────────
    export_col, _ = st.columns([2, 8])
    with export_col:
        st.download_button(
            label="⬇ Exportar a Excel",
            data=to_excel_bytes(df),
            file_name=f"VENTAS_FIT_{year_loaded}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="vf_export",
        )

    # ── Tabla final ───────────────────────────────────────────
    if df.empty:
        st.info("Sin resultados para los filtros aplicados.")
    else:
        st.html(build_table_html(df.to_dict("records")))

st.markdown(
    '<div class="portal-footer"><div class="footer-text">Crucemundo Hub · Ventas FIT</div></div>',
    unsafe_allow_html=True,
)
