# ============================================================
# PÁGINA: VENTAS_FIT
# ============================================================

import base64
import io
import random
import re
import threading
import time
from collections import deque
from datetime import datetime

import pandas as pd
import pytz
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

st.set_page_config(
    page_title="Ventas FIT – Crucemundo Hub",
    page_icon="favicon1.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# RATE LIMITER PARA GOOGLE SHEETS
# ============================================================

class RateLimiter:
    def __init__(self, max_calls=50, per_seconds=60):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self.calls = deque()
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            current = time.monotonic()

            while self.calls and current - self.calls[0] > self.per_seconds:
                self.calls.popleft()

            if len(self.calls) >= self.max_calls:
                sleep_time = self.per_seconds - (current - self.calls[0]) + 0.10
                if sleep_time > 0:
                    time.sleep(sleep_time)

                current = time.monotonic()
                while self.calls and current - self.calls[0] > self.per_seconds:
                    self.calls.popleft()

            self.calls.append(time.monotonic())


sheets_rate_limiter = RateLimiter(max_calls=50, per_seconds=60)

# ============================================================
# CONSTANTES
# ============================================================

DRIVEROOTID = "11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm"
TIMEZONE = pytz.timezone("Europe/Madrid")
GOOGLE_SHEETS_MIME = "application/vnd.google-apps.spreadsheet"
SHEETS_PER_BATCH = 10

COLUMNS_ORDER = [
    "#", "BARCO", "AGENCIA", "CODIGO", "GRUPO", "CONFIRMACION",
    "FECHA BOOKING", "ITINERARIO", "FECHA SALIDA", "FECHA LLEGADA",
    "NETO", "BRUTO", "ESTADO RESERVA", "PAGO", "COMERCIAL",
    "PERSONAS", "IDIOMA",
]
DATA_COLUMNS = COLUMNS_ORDER[1:]

CELLS_NEEDED = [
    "G11", "G13", "G5", "P5", "R5", "C3", "G19", "G17", "K17",
    "G10", "G57", "Q10", "G23",
]
RANGE_NETO = "Q33:R39"
RANGE_PERSONA = "G24"
RANGE_BRUTO = "Q55"
ALL_RANGES_NEEDED = CELLS_NEEDED + [RANGE_NETO, RANGE_PERSONA, RANGE_BRUTO]

LOCALIZADOR_RE = re.compile(r"^[A-Z]{2,3}\d{6}-\d+$", re.IGNORECASE)
SALIDA_PATTERN = re.compile(r"^[A-Z0-9_]+_\d{6}$", re.IGNORECASE)

# ============================================================
# LOGO Y TIEMPO
# ============================================================

def get_logo_base64():
    try:
        with open("crucemundo_final.gif", "rb") as file:
            encoded = base64.b64encode(file.read()).decode("utf-8")
            return "data:image/gif;base64," + encoded
    except Exception:
        return ""


LOGOURL = get_logo_base64()


def now():
    return datetime.now(pytz.utc).astimezone(TIMEZONE).replace(tzinfo=None)


def getsaludo(lang="es"):
    hour = now().hour
    if lang == "en":
        if 6 <= hour < 14:
            return "Good morning"
        if 14 <= hour < 21:
            return "Good afternoon"
        return "Good evening"

    if 6 <= hour < 14:
        return "Buenos días"
    if 14 <= hour < 21:
        return "Buenas tardes"
    return "Buenas noches"

# ============================================================
# HELPERS GENERALES
# ============================================================

def chunks(items, size):
    for position in range(0, len(items), size):
        yield items[position:position + size]


def escape_sheet_title(title):
    return str(title).replace("'", "''")


def confirmacion_prefix(value):
    return str(value).split("-")[0].strip()

# ============================================================
# RETRY Y SERVICIOS GOOGLE
# ============================================================

def execute_with_retry(request, max_intentos=6, base_delay=2.0, rate_limiter=None):
    intentos = 0
    while True:
        if rate_limiter:
            rate_limiter.wait()
        try:
            return request.execute()
        except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError) as error:
            intentos += 1
            if intentos >= max_intentos:
                raise Exception(
                    f"Fallo de conexión tras {max_intentos} intentos: {error}"
                ) from error
            time.sleep(base_delay * (2 ** (intentos - 1)) + random.uniform(0, 0.5))
        except HttpError as error:
            status = getattr(error.resp, "status", None)
            if status == 429:
                intentos += 1
                if intentos >= max_intentos:
                    raise Exception(
                        f"Cuota excedida tras {max_intentos} intentos: {error}"
                    ) from error
                time.sleep(min(base_delay * (2 ** intentos), 65) + random.uniform(0, 1))
            elif status in (500, 502, 503, 504):
                intentos += 1
                if intentos >= max_intentos:
                    raise
                time.sleep(base_delay * (2 ** (intentos - 1)) + random.uniform(0, 0.5))
            else:
                raise


@st.cache_resource
def _creds():
    if "gcpserviceaccount" not in st.secrets:
        raise Exception("Falta la sección gcpserviceaccount en secrets.toml.")
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcpserviceaccount"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )


@st.cache_resource
def drive_svc():
    return build("drive", "v3", credentials=_creds(), cache_discovery=False)


@st.cache_resource
def sheets_svc():
    return build("sheets", "v4", credentials=_creds(), cache_discovery=False)

# ============================================================
# GOOGLE DRIVE
# ============================================================

def list_children(parent_id, folders_only=False):
    query = f"'{parent_id}' in parents and trashed=false"
    if folders_only:
        query += " and mimeType='application/vnd.google-apps.folder'"

    items = []
    page_token = None
    while True:
        request = drive_svc().files().list(
            q=query,
            fields="nextPageToken, files(id,name,mimeType,webViewLink)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            pageToken=page_token,
            pageSize=1000,
        )
        response = execute_with_retry(request)
        items.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return items


def find_child_folder(parent_id, name):
    requested_name = str(name).strip()
    for folder in list_children(parent_id, folders_only=True):
        if folder.get("name", "").strip() == requested_name:
            return folder
    return None


@st.cache_data(ttl=300, show_spinner=False)
def get_year_folder_id(year):
    folder = find_child_folder(DRIVEROOTID, year)
    return folder["id"] if folder else None


@st.cache_data(ttl=300, show_spinner=False)
def get_years():
    folders = list_children(DRIVEROOTID, folders_only=True)
    years = [
        folder.get("name", "").strip()
        for folder in folders
        if re.fullmatch(r"\d{4}", folder.get("name", "").strip())
    ]
    return sorted(years, reverse=True)

# ============================================================
# GOOGLE SHEETS Y CONVERSIÓN
# ============================================================

def get_sheet_titles_ids(spreadsheet_id):
    request = sheets_svc().spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        includeGridData=False,
        fields="sheets.properties(sheetId,title,hidden)",
    )
    spreadsheet = execute_with_retry(request, rate_limiter=sheets_rate_limiter)
    return [
        {
            "title": sheet.get("properties", {}).get("title", ""),
            "sheetId": sheet.get("properties", {}).get("sheetId"),
            "hidden": sheet.get("properties", {}).get("hidden", False),
        }
        for sheet in spreadsheet.get("sheets", [])
    ]


def parse_numeric(value):
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = re.sub(r"[€$£\s%]", "", str(value).strip())
    if not text:
        return 0.0

    if re.search(r"\d\.\d{3},", text) or (
        text.count(",") == 1
        and text.count(".") >= 1
        and text.rfind(",") > text.rfind(".")
    ):
        text = text.replace(".", "").replace(",", ".")
    elif text.count(",") == 1 and "." not in text:
        text = text.replace(",", ".")
    elif text.count(".") >= 1 and "," not in text:
        parts = text.split(".")
        if len(parts[-1]) == 3:
            text = text.replace(".", "")

    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group()) if match else 0.0


def fmt_date(value):
    return "" if value in (None, "") else str(value).strip()


def extract_sheet_row(data_by_range):
    def cell(a1):
        values = data_by_range.get(a1, {}).get("values", [])
        return values[0][0] if values and values[0] else ""

    localizador = str(cell("G11")).strip()
    if not localizador:
        return None
    if localizador.upper().endswith("_GROUP"):
        return None
    if not LOCALIZADOR_RE.fullmatch(localizador):
        return None

    neto_rows = data_by_range.get(RANGE_NETO, {}).get("values", [])
    neto = sum(
        parse_numeric(value)
        for row in neto_rows
        for value in row
        if value not in (None, "")
    )

    persona_values = data_by_range.get(RANGE_PERSONA, {}).get("values", [])
    if persona_values and persona_values[0]:
        texto_personas = str(persona_values[0][0]).strip()
        personas = len([line for line in texto_personas.splitlines() if line.strip()])
    else:
        personas = 0

    bruto_values = data_by_range.get(RANGE_BRUTO, {}).get("values", [])
    bruto = parse_numeric(bruto_values[0][0]) if bruto_values and bruto_values[0] else 0.0

    return {
        "BARCO": str(cell("G13")).strip(),
        "AGENCIA": str(cell("G5")).strip(),
        "CODIGO": str(cell("P5")).strip(),
        "GRUPO": str(cell("R5")).strip(),
        "CONFIRMACION": localizador,
        "FECHA BOOKING": fmt_date(cell("C3")),
        "ITINERARIO": str(cell("G19")).strip(),
        "FECHA SALIDA": fmt_date(cell("G17")),
        "FECHA LLEGADA": fmt_date(cell("K17")),
        "NETO": round(neto, 2),
        "BRUTO": round(bruto, 2),
        "ESTADO RESERVA": str(cell("G10")).strip(),
        "PAGO": str(cell("G57")).strip(),
        "COMERCIAL": str(cell("Q10")).strip(),
        "PERSONAS": personas,
        "IDIOMA": str(cell("G23")).strip(),
    }


def read_book(spreadsheet_id, on_row_cb=None, on_sheet_cb=None, warning_cb=None):
    try:
        sheets = get_sheet_titles_ids(spreadsheet_id)
    except Exception as error:
        message = f"No se pudo obtener la lista de pestañas del libro `{spreadsheet_id}`: {error}"
        warning_cb(message) if warning_cb else st.warning(message)
        return []

    results = []
    for sheet_group in chunks(sheets, SHEETS_PER_BATCH):
        requested_ranges = []
        range_mapping = []

        for sheet in sheet_group:
            title = sheet["title"]
            escaped = escape_sheet_title(title)
            for a1_range in ALL_RANGES_NEEDED:
                requested_ranges.append(f"'{escaped}'!{a1_range}")
                range_mapping.append((title, a1_range))

        try:
            request = sheets_svc().spreadsheets().values().batchGet(
                spreadsheetId=spreadsheet_id,
                ranges=requested_ranges,
                majorDimension="ROWS",
                valueRenderOption="FORMATTED_VALUE",
            )
            response = execute_with_retry(request, rate_limiter=sheets_rate_limiter)
        except Exception as error:
            names = ", ".join(sheet["title"] for sheet in sheet_group)
            message = f"Error leyendo las pestañas [{names}] del libro `{spreadsheet_id}`: {error}"
            warning_cb(message) if warning_cb else st.warning(message)
            for sheet in sheet_group:
                if on_sheet_cb:
                    on_sheet_cb(sheet.get("title", ""))
            continue

        value_ranges = response.get("valueRanges", [])
        grouped_data = {sheet["title"]: {} for sheet in sheet_group}

        for index, (title, a1_range) in enumerate(range_mapping):
            grouped_data[title][a1_range] = (
                value_ranges[index] if index < len(value_ranges) else {"values": []}
            )

        for sheet in sheet_group:
            title = sheet["title"]
            try:
                row = extract_sheet_row(grouped_data[title])
                if row:
                    results.append(row)
                    if on_row_cb:
                        on_row_cb(row)
            except Exception as error:
                message = f"Error procesando la pestaña '{title}' del libro `{spreadsheet_id}`: {error}"
                warning_cb(message) if warning_cb else st.warning(message)
            finally:
                if on_sheet_cb:
                    on_sheet_cb(title)

    return results

# ============================================================
# ESCANEO ANUAL
# ============================================================

def scan_year(year, progress_cb=None, on_row_verified=None, on_sheet_ping=None, warning_cb=None):
    year_id = get_year_folder_id(year)
    if not year_id:
        raise Exception(f"No se encontró la carpeta correspondiente al año {year}.")

    boat_folders = list_children(year_id, folders_only=True)
    file_map = {}
    total_files = 0

    for boat_folder in boat_folders:
        boat_name = boat_folder.get("name", "").strip()
        files = list_children(boat_folder["id"], folders_only=False)
        salidas = sorted(
            [
                file
                for file in files
                if file.get("mimeType") == GOOGLE_SHEETS_MIME
                and SALIDA_PATTERN.fullmatch(file.get("name", "").strip())
            ],
            key=lambda item: item.get("name", "").strip(),
        )
        if salidas:
            file_map[boat_name] = salidas
            total_files += len(salidas)

    if total_files == 0:
        return []

    results = []
    processed = 0
    for boat_name in sorted(file_map):
        for file_object in file_map[boat_name]:
            file_name = file_object.get("name", "").strip()
            spreadsheet_id = file_object["id"]

            if progress_cb:
                progress_cb(processed, total_files, f"{boat_name} / {file_name}")

            try:
                rows = read_book(
                    spreadsheet_id,
                    on_row_cb=on_row_verified,
                    on_sheet_cb=on_sheet_ping,
                    warning_cb=warning_cb,
                )
                results.extend(rows)
            except Exception as error:
                message = f"No se pudo procesar el libro '{file_name}': {error}"
                warning_cb(message) if warning_cb else st.warning(message)
            finally:
                processed += 1
                if progress_cb:
                    progress_cb(processed, total_files, f"{boat_name} / {file_name}")

    if progress_cb:
        progress_cb(total_files, total_files, "Completado")
    return results

# ============================================================
# EXCEL Y RESUMEN
# ============================================================

def to_excel_bytes(df: pd.DataFrame) -> bytes:
    export_df = df.copy()
    for column in DATA_COLUMNS:
        if column not in export_df.columns:
            export_df[column] = ""
    export_df = export_df[DATA_COLUMNS]

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, sheet_name="DETALLE", index=False)

        for group_column, sheet_name in [
            ("BARCO", "BARCOS"),
            ("AGENCIA", "AGENCIAS"),
            ("COMERCIAL", "COMERCIALES"),
        ]:
            summary = (
                export_df.groupby(group_column, dropna=False)
                .agg(
                    RESERVAS=("CONFIRMACION", "count"),
                    PERSONAS=("PERSONAS", "sum"),
                    NETO=("NETO", "sum"),
                    BRUTO=("BRUTO", "sum"),
                )
                .reset_index()
                .sort_values("NETO", ascending=False)
            )
            summary.to_excel(writer, sheet_name=sheet_name, index=False)

        for sheet in writer.sheets.values():
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for column_cells in sheet.columns:
                max_length = max(len(str(cell.value or "")) for cell in column_cells)
                sheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 4, 60)

    buffer.seek(0)
    return buffer.read()


def build_summary_html(rows):
    df_live = pd.DataFrame(rows, columns=DATA_COLUMNS)
    personas = pd.to_numeric(df_live.get("PERSONAS", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
    neto = pd.to_numeric(df_live.get("NETO", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
    bruto = pd.to_numeric(df_live.get("BRUTO", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
    return f"""
    <div class="summary-row">
      <div class="sum-card"><div class="sum-label">Reservas</div><div class="sum-value">{len(df_live):,}</div></div>
      <div class="sum-card"><div class="sum-label">Personas</div><div class="sum-value">{int(personas):,}</div></div>
      <div class="sum-card"><div class="sum-label">Neto Total</div><div class="sum-value">{neto:,.2f} €</div></div>
      <div class="sum-card"><div class="sum-label">Bruto Total</div><div class="sum-value">{bruto:,.2f} €</div></div>
    </div>
    """

# ============================================================
# ESTILOS
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:"DM Sans",sans-serif;background:#FFFFFF!important;}
[data-testid="stAppViewContainer"]{background:#FFFFFF!important;}
[data-testid="stHeader"]{background:transparent!important;}
section[data-testid="stSidebar"]{display:none!important;}
.block-container,.stMainBlockContainer,[data-testid="stMainBlockContainer"]{padding-top:0!important;padding-bottom:1rem!important;padding-left:1rem!important;padding-right:1rem!important;max-width:1900px!important;margin:0 auto!important;}
.portal-header{padding:.1rem 0 .55rem;display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:.55rem;}
.portal-header-left{display:flex;align-items:center;gap:.9rem;}
.portal-logo{height:75px;width:auto;object-fit:contain;display:block;}
.portal-title{font-size:.96rem;font-weight:800;color:#1F2937;line-height:1.15;}
.portal-subtitle{font-size:.72rem;color:#667085;line-height:1.2;margin-top:.12rem;}
.user-top{font-size:.72rem;color:#566079;white-space:nowrap;}
.web-chip-blue{display:inline-flex;align-items:center;justify-content:center;padding:.38rem .82rem;border-radius:999px;font-size:.71rem;font-weight:800;background:#E0ECFF;border:1px solid #BFD4FF;color:#1E4FBF!important;}
div.stButton>button{border-radius:999px!important;padding:0 1rem!important;font-size:.78rem!important;font-weight:800!important;font-family:"DM Sans",sans-serif!important;border:2px solid transparent!important;background:linear-gradient(180deg,#2F6DF6 0%,#245FE0 100%)!important;color:#fff!important;box-shadow:0 4px 14px rgba(37,99,235,.22)!important;}
div.stButton>button:disabled{background:#CBD5E1!important;box-shadow:none!important;}
div[data-testid="stSelectbox"] label,div[data-testid="stTextInput"] label,div[data-testid="stMultiSelect"] label{color:#334155!important;font-size:.80rem!important;font-weight:700!important;}
div[data-testid="stSelectbox"] div[data-baseweb="select"]>div,div[data-testid="stTextInput"] input,div[data-testid="stMultiSelect"] div[data-baseweb="select"]>div{background:#fff!important;border:1.6px solid #CBD5E1!important;border-radius:14px!important;color:#1F2937!important;min-height:44px!important;font-family:"DM Sans",sans-serif!important;font-size:.88rem!important;font-weight:600!important;box-shadow:0 2px 8px rgba(15,23,42,.05)!important;}
.summary-row{display:flex;gap:1rem;flex-wrap:wrap;margin:.75rem 0 1rem;}
.sum-card{flex:1;min-width:120px;background:#F8FAFF;border:1px solid #DCE5F0;border-radius:16px;padding:.65rem .9rem;}
.sum-label{font-size:.68rem;color:#64748B;font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
.sum-value{font-size:1.22rem;font-weight:800;color:#1F2937;margin-top:.18rem;}
.portal-footer{margin-top:1rem;padding:.5rem 0 0;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;}
.footer-text{font-size:.71rem;color:#A2ABBD;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# AUTENTICACIÓN Y CABECERA
# ============================================================

if not st.session_state.get("authenticated"):
    st.warning("Debes iniciar sesión primero. Vuelve a la página principal.")
    if st.button("← Volver al Hub"):
        st.switch_page("app.py")
    st.stop()

DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Sin usuario"
SALUDO = getsaludo("es")
logo_html = f'<img class="portal-logo" src="{LOGOURL}" alt="Logo">' if LOGOURL else ""

st.markdown(f"""
<div class="portal-header">
  <div class="portal-header-left">
    {logo_html}
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

# ============================================================
# CONTROLES Y ESTADO
# ============================================================

col_year, col_btn, _ = st.columns([2, 1.2, 6], gap="medium")
with col_year:
    try:
        years = get_years()
    except Exception as error:
        st.error(f"Error al obtener los años: {error}")
        st.stop()
    selected_year = st.selectbox(
        "AÑO / YEAR", options=years, index=None,
        placeholder="Selecciona un año…", key="vf_year",
    )

with col_btn:
    st.markdown("<div style='margin-top:1.6rem;'>", unsafe_allow_html=True)
    run_scan = st.button("Generar informe", key="vf_run", disabled=not selected_year)
    st.markdown("</div>", unsafe_allow_html=True)

for key, default in {
    "vf_results": None,
    "vf_year_loaded": None,
    "vf_extracted_at": None,
    "vf_last_errors": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================================
# EJECUCIÓN DEL ESCANEO
# ============================================================

if run_scan and selected_year:
    st.session_state.vf_results = None
    st.session_state.vf_year_loaded = None
    st.session_state.vf_extracted_at = None
    st.session_state.vf_last_errors = []

    progress_bar = st.progress(0.0, text="Preparando escaneo...")
    status_box = st.empty()
    warnings_box = st.empty()
    accumulated_rows = []
    scan_warnings = []
    progress_state = {"done": 0, "total": 0, "label": "Preparando", "sheets": 0, "last_sheet": ""}

    def render_scan_status():
        done = progress_state["done"]
        total = progress_state["total"]
        percentage = done / total if total else 0.0
        progress_bar.progress(
            min(max(percentage, 0.0), 1.0),
            text=f"{done:,}/{total:,} libros" if total else "Preparando escaneo...",
        )
        status_box.info(
            f"**Libro actual:**  \n{progress_state['label']}\n\n"
            f"**Libros procesados:**  \n{done:,}/{total:,}\n\n"
            f"**Hojas revisadas:**  \n{progress_state['sheets']:,}\n\n"
            f"**Última hoja:**  \n{progress_state['last_sheet'] or 'Preparando lectura...'}\n\n"
            f"**Reservas encontradas:**  \n{len(accumulated_rows):,}"
        )

    def update_progress(done, total, label):
        progress_state.update({"done": done, "total": total, "label": label})
        render_scan_status()

    def on_row_verified(row):
        accumulated_rows.append(row)

    def on_sheet_ping(sheet_title):
        progress_state["sheets"] += 1
        progress_state["last_sheet"] = sheet_title
        if progress_state["sheets"] % 5 == 0:
            render_scan_status()

    def register_warning(message):
        scan_warnings.append(message)
        warnings_box.warning(
            "**Últimas incidencias:**\n\n" + "\n\n".join(
                f"- {warning}" for warning in scan_warnings[-5:]
            )
        )

    try:
        rows = scan_year(
            selected_year,
            progress_cb=update_progress,
            on_row_verified=on_row_verified,
            on_sheet_ping=on_sheet_ping,
            warning_cb=register_warning,
        )
        st.session_state.vf_results = rows
        st.session_state.vf_year_loaded = selected_year
        st.session_state.vf_extracted_at = now().strftime("%d/%m/%Y %H:%M")
        st.session_state.vf_last_errors = scan_warnings.copy()
        if rows:
            st.success(f"Informe generado correctamente: {len(rows):,} reservas encontradas.")
        else:
            st.info("No se han encontrado reservas para el año seleccionado.")
    except Exception as error:
        st.session_state.vf_results = accumulated_rows.copy()
        st.session_state.vf_year_loaded = selected_year
        st.session_state.vf_extracted_at = now().strftime("%d/%m/%Y %H:%M")
        st.session_state.vf_last_errors = scan_warnings.copy()
        st.error(
            f"El escaneo no se completó, pero se conservaron {len(accumulated_rows):,} reservas."
        )
        st.exception(error)
    finally:
        progress_bar.empty()
        status_box.empty()
        warnings_box.empty()

# ============================================================
# RESULTADOS, FILTROS Y TABLA
# ============================================================

rows = st.session_state.get("vf_results")
year_loaded = st.session_state.get("vf_year_loaded")
extracted_at = st.session_state.get("vf_extracted_at")
last_errors = st.session_state.get("vf_last_errors", [])

if rows is not None:
    df_all = pd.DataFrame(rows, columns=DATA_COLUMNS)
    if not df_all.empty:
        df_all["NETO"] = pd.to_numeric(df_all["NETO"], errors="coerce").fillna(0.0)
        df_all["BRUTO"] = pd.to_numeric(df_all["BRUTO"], errors="coerce").fillna(0.0)
        df_all["PERSONAS"] = pd.to_numeric(df_all["PERSONAS"], errors="coerce").fillna(0).astype(int)
        df_all["_CONF_PREFIX"] = df_all["CONFIRMACION"].apply(confirmacion_prefix)
    else:
        df_all["_CONF_PREFIX"] = pd.Series(dtype=str)

    fecha_txt = f" · Extraído el {extracted_at}" if extracted_at else ""
    st.markdown(
        f'<span class="web-chip-blue">FILTROS · AÑO {year_loaded} · {len(df_all):,} registros{fecha_txt}</span>',
        unsafe_allow_html=True,
    )

    if last_errors:
        with st.expander(f"Ver incidencias del escaneo ({len(last_errors)})"):
            for warning in last_errors:
                st.warning(warning)

    columns = st.columns([2, 2, 2, 2, 2, 2, 2], gap="medium")
    filter_specs = [
        ("BARCO", "BARCO", "f_barco"),
        ("AGENCIA", "AGENCIA", "f_agencia"),
        ("CONFIRMACION", "_CONF_PREFIX", "f_conf"),
        ("ESTADO RESERVA", "ESTADO RESERVA", "f_estado"),
        ("COMERCIAL", "COMERCIAL", "f_comercial"),
        ("PAGO", "PAGO", "f_pago"),
        ("IDIOMA", "IDIOMA", "f_idioma"),
    ]
    selections = {}
    for container, (label, field, key) in zip(columns, filter_specs):
        with container:
            selections[field] = st.multiselect(
                label,
                options=sorted(df_all[field].dropna().astype(str).unique()),
                default=[],
                key=key,
            )

    search_col, _ = st.columns([3, 7])
    with search_col:
        txt_search = st.text_input(
            "🔍 Buscar en tabla", key="f_txt",
            placeholder="Localizador, agencia, itinerario…",
        )

    df = df_all.copy()
    for field, selected in selections.items():
        if selected:
            df = df[df[field].isin(selected)]

    if txt_search.strip():
        search_text = txt_search.strip().lower()
        searchable = df[DATA_COLUMNS].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
        df = df[searchable.str.contains(search_text, na=False, regex=False)]

    st.markdown(build_summary_html(df[DATA_COLUMNS].to_dict("records")), unsafe_allow_html=True)

    export_col, _ = st.columns([2, 8])
    with export_col:
        st.download_button(
            label="⬇ Exportar a Excel",
            data=to_excel_bytes(df[DATA_COLUMNS]),
            file_name=f"VENTAS_FIT_{year_loaded}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="vf_export",
            disabled=df.empty,
        )

    if df.empty:
        st.info("Sin resultados para los filtros aplicados.")
    else:
        df_show = df[DATA_COLUMNS].copy().reset_index(drop=True)
        df_show.insert(0, "#", range(1, len(df_show) + 1))

        def estado_txt(value):
            original = str(value).strip()
            upper = original.upper()
            if "NO CONF" in upper or "PENDIENTE" in upper:
                return f"⚠️ {original}"
            if "CANCEL" in upper:
                return f"❌ {original}"
            if "CONFIRM" in upper:
                return f"✅ {original}"
            return original

        def pago_txt(value):
            original = str(value).strip()
            upper = original.upper()
            if "NO PAGADO" in upper:
                return f"⏳ {original}"
            if "PAGADO" in upper:
                return f"✅ {original}"
            if "PTE" in upper or "PENDIENTE" in upper:
                return f"⏳ {original}"
            if "DEPOSI" in upper:
                return f"💳 {original}"
            return original

        df_show["ESTADO RESERVA"] = df_show["ESTADO RESERVA"].apply(estado_txt)
        df_show["PAGO"] = df_show["PAGO"].apply(pago_txt)

        st.dataframe(
            df_show,
            use_container_width=True,
            height=600,
            hide_index=True,
            column_config={
                "#": st.column_config.NumberColumn("#", format="%d", width="small"),
                "NETO": st.column_config.NumberColumn("NETO", format="%.2f €"),
                "BRUTO": st.column_config.NumberColumn("BRUTO", format="%.2f €"),
                "PERSONAS": st.column_config.NumberColumn("PERSONAS", format="%d"),
                "CONFIRMACION": st.column_config.TextColumn("CONFIRMACION", width="medium"),
                "ITINERARIO": st.column_config.TextColumn("ITINERARIO", width="large"),
                "AGENCIA": st.column_config.TextColumn("AGENCIA", width="medium"),
                "ESTADO RESERVA": st.column_config.TextColumn("ESTADO RESERVA", width="medium"),
                "PAGO": st.column_config.TextColumn("PAGO", width="medium"),
            },
        )

st.markdown(
    '<div class="portal-footer"><div class="footer-text">Crucemundo Hub · Ventas FIT</div></div>',
    unsafe_allow_html=True,
)
