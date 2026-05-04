import streamlit as st
from datetime import datetime, date
import urllib.parse
import time
import re

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Crucemundo Hub",
    page_icon="🛳️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

LOGO_ID = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGO_URL = f"https://lh3.googleusercontent.com/d/{LOGO_ID}"

TEMPLATE_ID_ES = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
TEMPLATE_ID_GRUPOS = "1Z7ktX3PhVkMibWpzdrDDqAT4aPsmjzSJPf1SgZcL5-w"
TEMPLATE_ID_CRUCERO = "1zSJPi6St_Z5Jw1c6eieVnKI4NyEdP7E9n3WTZ9yy3C0"
EXCURSIONES_SHEET_ID = "1ojMHeoosUyel8BA2XTmDsmyDJf_vvJrrJNOyxn2u1jg"

AGENCY_SHEET_ID = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
AGENCY_SHEET_NAME = "Datos"

FOLDER_ID = "1MxMdeBlUG6v5n2upobsjNbQNQ8F_C_sO"
DRIVE_ROOT_ID = "11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm"

VALID_USERS = {
    "support@crucemundo.com": "Albina",
    "sales@crucemundo.com": "Sales",
    "cruise@crucemundo.com": "Cruise",
    "tania@crucemundo.com": "Tania",
    "incoming@crucemundo.com": "Incoming",
    "operations@crucemundo.com": "Operations",
    "edarmm@gmail.com": "Esteban",
}

VALID_PASSWORD = st.secrets["app_password"]

AGENCY_FIELDS = [
    "Nombre",
    "CODIGO",
    "Grupo Gest",
    "Telefono",
    "Email",
    "Direccion",
    "COMISION AGENCIA",
    "COMISION AGENCIA ( CON OFERTA )",
    "COMISION AGENCIA ( OFERTA 2X1 )",
    "IVA",
    "IVA SERVICIO OPCIONAL",
]

# ──────────────────────────────────────────────────────────────────────────────
# STATE
# ──────────────────────────────────────────────────────────────────────────────
defaults = {
    "authenticated": False,
    "user_email": "",
    "display_name": "",
    "confirm_state": "idle",
    "historial": [],
    "session_type": "",
    "active_panel": None,
    "open_salida_form": False,
    "open_crucero_form": False,
    "open_nueva_agencia_form": False,
    "open_buscar_agencia_form": False,
    "salida_year": None,
    "salida_boat": None,
    "salida_name": None,
    "crucero_year": None,
    "crucero_boat": None,
    "agency_matches": [],
    "agency_selected_idx": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def get_saludo():
    hora = datetime.now().hour
    if 6 <= hora < 14:
        return "Buenos días"
    elif 14 <= hora < 21:
        return "Buenas tardes"
    return "Buenas noches"

def get_saludo_en():
    hora = datetime.now().hour
    if 6 <= hora < 14:
        return "Good morning"
    elif 14 <= hora < 21:
        return "Good afternoon"
    return "Good evening"

def clear_salida_state():
    for k in [
        "salida_year", "salida_boat", "salida_name",
        "salida_year_widget", "salida_boat_widget", "salida_name_widget"
    ]:
        st.session_state.pop(k, None)

def clear_crucero_state():
    for k in [
        "crucero_year", "crucero_boat",
        "crucero_year_widget", "crucero_boat_widget"
    ]:
        st.session_state.pop(k, None)

def clear_agencia_state():
    for k in [
        "agency_matches", "agency_selected_idx", "agency_search_query",
        "ag_nombre", "ag_codigo", "ag_grupo_gest", "ag_telefono", "ag_email",
        "ag_direccion", "ag_comision", "ag_comision_oferta", "ag_comision_2x1",
        "ag_iva", "ag_iva_servicio_opcional"
    ]:
        st.session_state.pop(k, None)

def close_all_panels():
    st.session_state["open_salida_form"] = False
    st.session_state["open_crucero_form"] = False
    st.session_state["open_nueva_agencia_form"] = False
    st.session_state["open_buscar_agencia_form"] = False

def open_panel(panel_name):
    close_all_panels()

    if panel_name == "salida":
        clear_crucero_state()
        clear_agencia_state()
        st.session_state["open_salida_form"] = True
    elif panel_name == "crucero":
        clear_salida_state()
        clear_agencia_state()
        st.session_state["open_crucero_form"] = True
    elif panel_name == "nueva_agencia":
        clear_salida_state()
        clear_crucero_state()
        clear_agencia_state()
        st.session_state["open_nueva_agencia_form"] = True
    elif panel_name == "buscar_agencia":
        clear_salida_state()
        clear_crucero_state()
        clear_agencia_state()
        st.session_state["open_buscar_agencia_form"] = True

    st.session_state["active_panel"] = panel_name

def clear_all_selectors():
    clear_salida_state()
    clear_crucero_state()
    clear_agencia_state()
    close_all_panels()
    st.session_state["active_panel"] = None

def do_logout():
    keys_to_delete = [
        "authenticated", "user_email", "display_name", "confirm_state",
        "session_type", "active_panel", "open_salida_form", "open_crucero_form",
        "open_nueva_agencia_form", "open_buscar_agencia_form",
        "salida_year", "salida_boat", "salida_name",
        "crucero_year", "crucero_boat",
        "salida_year_widget", "salida_boat_widget", "salida_name_widget",
        "crucero_year_widget", "crucero_boat_widget",
        "nombre_copia", "copy_url", "process_title",
        "agency_matches", "agency_selected_idx", "agency_search_query",
        "ag_nombre", "ag_codigo", "ag_grupo_gest", "ag_telefono", "ag_email",
        "ag_direccion", "ag_comision", "ag_comision_oferta", "ag_comision_2x1",
        "ag_iva", "ag_iva_servicio_opcional"
    ]
    for k in keys_to_delete:
        st.session_state.pop(k, None)
    st.rerun()

def render_step(label, detail, state):
    dot_class = {"done": "sd-done", "active": "sd-active", "wait": "sd-wait"}[state]
    text_class = {"done": "st-done", "active": "st-active", "wait": "st-wait"}[state]
    symbol = {"done": "✓", "active": "•", "wait": "•"}[state]

    st.markdown(f"""
    <div class="step">
        <div class="step-dot {dot_class}">{symbol}</div>
        <div class="step-content">
            <div class="{text_class}">{label}</div>
            <div class="step-detail">{detail}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def iniciar_proceso(session_type, template_id, prefix_name, process_title):
    clear_all_selectors()

    now = datetime.now()
    fecha_str = now.strftime("%Y%m%d_%H%M")
    display_user = st.session_state.get("display_name", "").strip() or "Sin usuario"

    nombre_copia = f"SESION - {display_user} - {prefix_name} - {fecha_str}"
    copy_url = (
        f"https://docs.google.com/spreadsheets/d/{template_id}/copy"
        f"?copyDestination={FOLDER_ID}"
        f"&title={urllib.parse.quote(nombre_copia)}"
    )

    st.session_state["confirm_state"] = "step1"
    st.session_state["session_type"] = session_type
    st.session_state["nombre_copia"] = nombre_copia
    st.session_state["copy_url"] = copy_url
    st.session_state["process_title"] = process_title
    st.rerun()

def reset_salida_downstream(level):
    if level == "year":
        st.session_state["salida_boat"] = None
        st.session_state["salida_name"] = None
        st.session_state.pop("salida_boat_widget", None)
        st.session_state.pop("salida_name_widget", None)
    elif level == "boat":
        st.session_state["salida_name"] = None
        st.session_state.pop("salida_name_widget", None)

def on_year_change():
    st.session_state["salida_year"] = st.session_state.get("salida_year_widget")
    reset_salida_downstream("year")

def on_boat_change():
    st.session_state["salida_boat"] = st.session_state.get("salida_boat_widget")
    reset_salida_downstream("boat")

def on_salida_change():
    st.session_state["salida_name"] = st.session_state.get("salida_name_widget")

def reset_crucero_downstream(level):
    if level == "year":
        st.session_state["crucero_boat"] = None
        st.session_state.pop("crucero_boat_widget", None)

def on_crucero_year_change():
    st.session_state["crucero_year"] = st.session_state.get("crucero_year_widget")
    reset_crucero_downstream("year")

def on_crucero_boat_change():
    st.session_state["crucero_boat"] = st.session_state.get("crucero_boat_widget")

def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip().lower()

def normalize_phone(value):
    if value is None:
        return ""
    return re.sub(r"\D+", "", str(value))

def percent_to_sheet_decimal(value):
    if value is None:
        return ""
    return round(float(value) / 100, 4)

# ──────────────────────────────────────────────────────────────────────────────
# GOOGLE DRIVE / SHEETS API
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_google_creds():
    if "gcp_service_account" not in st.secrets:
        raise Exception("Falta [gcp_service_account] en secrets.")

    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
    )

@st.cache_resource
def get_drive_service():
    creds = get_google_creds()
    return build("drive", "v3", credentials=creds)

@st.cache_resource
def get_sheets_service():
    creds = get_google_creds()
    return build("sheets", "v4", credentials=creds)

def list_folder_items(parent_id, folders_only=False):
    service = get_drive_service()
    q = f"'{parent_id}' in parents and trashed=false"
    if folders_only:
        q += " and mimeType='application/vnd.google-apps.folder'"

    results = []
    page_token = None

    while True:
        response = service.files().list(
            q=q,
            fields="nextPageToken, files(id, name, mimeType, webViewLink, description)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            pageToken=page_token,
            pageSize=1000
        ).execute()

        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return results

def find_child_folder(parent_id, folder_name):
    folders = list_folder_items(parent_id, folders_only=True)
    for f in folders:
        if f["name"].strip() == folder_name.strip():
            return f
    return None

def create_folder(parent_id, folder_name):
    service = get_drive_service()
    body = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    return service.files().create(
        body=body,
        fields="id, name",
        supportsAllDrives=True
    ).execute()

def get_or_create_folder(parent_id, folder_name):
    existing = find_child_folder(parent_id, folder_name)
    if existing:
        return existing
    return create_folder(parent_id, folder_name)

def find_file_by_name(parent_id, file_name):
    items = list_folder_items(parent_id, folders_only=False)
    for f in items:
        if f["name"].strip() == file_name.strip():
            return f
    return None

def copy_file_to_folder(file_id, new_name, parent_folder_id, description=None):
    service = get_drive_service()
    body = {
        "name": new_name,
        "parents": [parent_folder_id],
    }
    if description:
        body["description"] = description

    return service.files().copy(
        fileId=file_id,
        body=body,
        fields="id, name, webViewLink",
        supportsAllDrives=True
    ).execute()

def update_crucero_sheet(spreadsheet_id, barco):
    sheets_service = get_sheets_service()

    spreadsheet = sheets_service.spreadsheets().get(
        spreadsheetId=spreadsheet_id
    ).execute()

    sheets = spreadsheet.get("sheets", [])
    if not sheets:
        raise Exception("El spreadsheet no contiene hojas.")

    first_sheet = sheets[0]
    first_sheet_id = first_sheet["properties"]["sheetId"]
    first_sheet_title = first_sheet["properties"]["title"]

    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{first_sheet_title}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": [[barco]]}
    ).execute()

    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": first_sheet_id,
                            "title": barco
                        },
                        "fields": "title"
                    }
                }
            ]
        }
    ).execute()

def append_agency_row(agency_data):
    sheets_service = get_sheets_service()

    values = [[
        agency_data.get("Nombre", ""),
        agency_data.get("CODIGO", ""),
        agency_data.get("Grupo Gest", ""),
        agency_data.get("Telefono", ""),
        agency_data.get("Email", ""),
        agency_data.get("Direccion", ""),
        agency_data.get("COMISION AGENCIA", ""),
        agency_data.get("COMISION AGENCIA ( CON OFERTA )", ""),
        agency_data.get("COMISION AGENCIA ( OFERTA 2X1 )", ""),
        agency_data.get("IVA", ""),
        agency_data.get("IVA SERVICIO OPCIONAL", ""),
    ]]

    sheets_service.spreadsheets().values().append(
        spreadsheetId=AGENCY_SHEET_ID,
        range=f"{AGENCY_SHEET_NAME}!A:K",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values}
    ).execute()

def get_agencies():
    sheets_service = get_sheets_service()

    response = sheets_service.spreadsheets().values().get(
        spreadsheetId=AGENCY_SHEET_ID,
        range=f"{AGENCY_SHEET_NAME}!A:K"
    ).execute()

    rows = response.get("values", [])
    agencies = []

    for idx, row in enumerate(rows, start=1):
        row = row + [""] * (11 - len(row))
        data = {
            "row_number": idx,
            "Nombre": row[0],
            "CODIGO": row[1],
            "Grupo Gest": row[2],
            "Telefono": row[3],
            "Email": row[4],
            "Direccion": row[5],
            "COMISION AGENCIA": row[6],
            "COMISION AGENCIA ( CON OFERTA )": row[7],
            "COMISION AGENCIA ( OFERTA 2X1 )": row[8],
            "IVA": row[9],
            "IVA SERVICIO OPCIONAL": row[10],
        }

        joined = " | ".join([
            normalize_text(data["Nombre"]),
            normalize_text(data["CODIGO"]),
            normalize_text(data["Grupo Gest"]),
            normalize_text(data["Telefono"]),
            normalize_text(data["Email"]),
            normalize_text(data["Direccion"]),
        ])

        data["_search_blob"] = joined
        data["_phone_norm"] = normalize_phone(data["Telefono"])
        agencies.append(data)

    return agencies

def search_agencies(query):
    agencies = get_agencies()
    q = normalize_text(query)
    q_phone = normalize_phone(query)

    if not q and not q_phone:
        return []

    matches = []
    for ag in agencies:
        if q and q in ag["_search_blob"]:
            matches.append(ag)
            continue
        if q_phone and q_phone in ag["_phone_norm"]:
            matches.append(ag)

    return matches

@st.cache_data(ttl=300)
def get_years():
    folders = list_folder_items(DRIVE_ROOT_ID, folders_only=True)
    years = [f["name"].strip() for f in folders if re.fullmatch(r"\d{4}", f["name"].strip())]
    return sorted(years, reverse=True)

@st.cache_data(ttl=300)
def get_year_folder_id(year_name):
    folder = find_child_folder(DRIVE_ROOT_ID, year_name)
    return folder["id"] if folder else None

@st.cache_data(ttl=300)
def get_boats(year_name):
    year_folder_id = get_year_folder_id(year_name)
    if not year_folder_id:
        return []

    folders = list_folder_items(year_folder_id, folders_only=True)
    boats = sorted({f["name"].strip() for f in folders if f["name"].strip()})
    return boats

@st.cache_data(ttl=300)
def get_departures(year_name, boat_name):
    year_folder_id = get_year_folder_id(year_name)
    if not year_folder_id:
        return []

    boat_folder = find_child_folder(year_folder_id, boat_name)
    if not boat_folder:
        return []

    files = list_folder_items(boat_folder["id"], folders_only=False)
    pattern = re.compile(rf"^{re.escape(boat_name)}_(\d{{6}})$")

    departures = []
    for file in files:
        name = file["name"].strip()
        if pattern.match(name):
            departures.append({
                "nombre": name,
                "id": file["id"],
                "url": file.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{file['id']}/edit"
            })

    departures.sort(key=lambda x: x["nombre"])
    return departures

def create_crucero_file(barco, fecha_obj):
    if not barco or not fecha_obj:
        raise Exception("Faltan datos de barco o fecha.")

    anio = str(fecha_obj.year)
    yy = fecha_obj.strftime("%y")
    mm = fecha_obj.strftime("%m")
    dd = fecha_obj.strftime("%d")
    fecha_es = fecha_obj.strftime("%d/%m/%Y")
    nombre_nuevo = f"{barco}_{yy}{mm}{dd}"

    carpeta_anio = get_or_create_folder(DRIVE_ROOT_ID, anio)
    carpeta_barco = get_or_create_folder(carpeta_anio["id"], barco)

    duplicado = find_file_by_name(carpeta_barco["id"], nombre_nuevo)
    if duplicado:
        return {
            "status": "duplicate",
            "name": nombre_nuevo,
            "url": duplicado.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{duplicado['id']}/edit"
        }

    descripcion = (
        f"Barco: {barco} | Salida: {fecha_es} | "
        f"Creado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | "
        "Los archivos de sesión deben borrarse a los 30 días."
    )

    copia = copy_file_to_folder(
        TEMPLATE_ID_CRUCERO,
        nombre_nuevo,
        carpeta_barco["id"],
        descripcion
    )

    spreadsheet_id = copia["id"]
    update_crucero_sheet(spreadsheet_id, barco)

    get_years.clear()
    get_year_folder_id.clear()
    get_boats.clear()
    get_departures.clear()

    return {
        "status": "created",
        "name": nombre_nuevo,
        "url": copia.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{copia['id']}/edit",
        "year": anio,
        "boat": barco
    }

# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
* { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background:#FFFFFF !important; }
[data-testid="stAppViewContainer"] { background:#FFFFFF !important; }
[data-testid="stHeader"] { background:transparent !important; }
section[data-testid="stSidebar"] { display:none !important; }

.block-container,
section.stMain .block-container,
.stMainBlockContainer,
[data-testid="stMainBlockContainer"] {
    padding-top:0rem !important;
    padding-bottom:1rem !important;
    padding-left:1rem !important;
    padding-right:1rem !important;
    max-width:1700px !important;
    margin:0 auto !important;
}

.login-page { min-height:auto; display:flex; align-items:flex-start; justify-content:center; padding:0.2rem 1rem 1rem; }
.login-shell { width:100%; max-width:390px; margin:0 auto; }
.login-head { text-align:center; margin-bottom:0.55rem; }
.login-logo { height:56px; width:auto; margin:0 auto 0.65rem auto; display:block; }
.login-title { font-size:1.08rem; font-weight:700; color:#1F2937; }
.login-subtitle { font-size:0.78rem; color:#7C869D; margin-top:0.28rem; }
.login-form-box { background:transparent !important; border:none !important; padding:0 !important; }
.login-note { margin-top:0.65rem; text-align:center; font-size:0.72rem; color:#8A93A5; }

div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stDateInput"] label,
div[data-testid="stNumberInput"] label {
    color:#4D576D !important;
    font-size:0.78rem !important;
    font-weight:500 !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stDateInput"] input,
div[data-testid="stNumberInput"] input {
    background:#F8FAFC !important;
    border:1px solid #E5EAF2 !important;
    border-radius:12px !important;
    color:#1F2937 !important;
}

div.stButton { width:fit-content !important; }
div.stButton > button,
div[data-testid="stFormSubmitButton"] > button,
.logout-btn > div > button {
    color:#214D92 !important;
    border:1px solid rgba(33,77,146,0.14) !important;
    border-radius:999px !important;
    min-height:38px !important;
    padding:0 1.15rem !important;
    font-size:0.76rem !important;
    font-weight:600 !important;
    box-shadow:none !important;
}

div.st-key-btn_crear_es button { background:#EEF4FF !important; }
div.st-key-btn_crear_grupos button { background:#ECF8EF !important; }
div.st-key-btn_ir_salida button { background:#FFF3E4 !important; }
div.st-key-btn_crear_crucero_open button,
div.st-key-btn_crear_crucero_action button { background:#F1EBFF !important; }
div.st-key-btn_excursiones button { background:#E9F7FB !important; }
div.st-key-btn_nueva_agencia button,
div.st-key-btn_guardar_agencia button { background:#EAF8F0 !important; }
div.st-key-btn_buscar_agencia button,
div.st-key-btn_ejecutar_busqueda_agencia button { background:#FFF4EA !important; }

div.st-key-btn_crear_es button:hover { background:#E5EEFF !important; }
div.st-key-btn_crear_grupos button:hover { background:#E3F3E7 !important; }
div.st-key-btn_ir_salida button:hover { background:#FFEBCF !important; }
div.st-key-btn_crear_crucero_open button:hover,
div.st-key-btn_crear_crucero_action button:hover { background:#E8DFFF !important; }
div.st-key-btn_excursiones button:hover { background:#DEF2F8 !important; }
div.st-key-btn_nueva_agencia button:hover,
div.st-key-btn_guardar_agencia button:hover { background:#DDF3E7 !important; }
div.st-key-btn_buscar_agencia button:hover,
div.st-key-btn_ejecutar_busqueda_agencia button:hover { background:#FFE9D7 !important; }

div.st-key-btn_crear_es button:hover,
div.st-key-btn_crear_grupos button:hover,
div.st-key-btn_ir_salida button:hover,
div.st-key-btn_crear_crucero_open button:hover,
div.st-key-btn_crear_crucero_action button:hover,
div.st-key-btn_excursiones button:hover,
div.st-key-btn_nueva_agencia button:hover,
div.st-key-btn_guardar_agencia button:hover,
div.st-key-btn_buscar_agencia button:hover,
div.st-key-btn_ejecutar_busqueda_agencia button:hover,
.logout-btn > div > button:hover {
    color:#163D78 !important;
    border-color:rgba(33,77,146,0.24) !important;
}

.portal-header {
    padding:0.1rem 0 0.55rem 0;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:1rem;
    margin-bottom:0.55rem;
}
.portal-header-left { display:flex; align-items:center; gap:0.9rem; }
.portal-logo { height:42px; width:auto; object-fit:contain; display:block; }

.portal-title,
.portal-title-en {
    font-size:0.96rem;
    font-weight:700;
    color:#1F2937;
    line-height:1.15;
}
.portal-title-en { margin-top:0.12rem; }

.portal-subtitle,
.portal-subtitle-en {
    font-size:0.72rem;
    color:#7C869D;
    line-height:1.2;
}
.portal-subtitle { margin-top:0.12rem; }
.portal-subtitle-en { margin-top:0.08rem; }

.user-top {
    font-size:0.72rem;
    color:#566079;
    white-space:nowrap;
}

.main-content { padding:0; }

.section-head-row{
    display:flex;
    align-items:center;
    justify-content:flex-start;
    gap:0.55rem;
    margin-bottom:0.75rem;
    flex-wrap:wrap;
}

.section-eyebrow {
    display:inline-flex;
    align-items:center;
    padding:0.34rem 0.74rem;
    border-radius:999px;
    background:#EAF1FF;
    border:1px solid #D6E3FF;
    color:#2E5FB8;
    font-size:0.66rem;
    font-weight:700;
    letter-spacing:0.08em;
    text-transform:uppercase;
    margin-bottom:0 !important;
}

.web-chip{
    display:inline-flex;
    align-items:center;
    justify-content:center;
    padding:0.34rem 0.74rem;
    border-radius:999px;
    background:#FFF3BF;
    border:1px solid #F4D35E;
    color:#7A5900 !important;
    font-size:0.70rem;
    font-weight:700;
    line-height:1;
    text-decoration:none;
    white-space:nowrap;
}

.web-chip:hover{
    background:#FFE58F;
    border-color:#E9C046;
    color:#5F4500 !important;
}

.user-pill {
    display:inline-flex;
    align-items:center;
    gap:0.4rem;
    margin:0.02rem 0 1rem;
    padding:0.38rem 0.68rem;
    border-radius:999px;
    background:#fff;
    border:1px solid #E4E7EF;
    font-size:0.72rem;
    color:#5D6880;
    max-width:100%;
    word-break:break-word;
}

.action-box {
    width:100%;
    min-height:210px;
    border-radius:22px;
    padding:1rem;
    margin-bottom:0.85rem;
    display:flex;
    flex-direction:column;
    justify-content:space-between;
    gap:0.9rem;
    border:1px solid transparent;
}

.card-es { background:#F3F7FF; border-color:#D9E5FF; }
.card-grupos { background:#F4FBF6; border-color:#D8EEDC; }
.card-salida { background:#FFF8F1; border-color:#F1DFC7; }
.card-crucero { background:#F7F4FF; border-color:#E4DDF9; }
.card-excursiones { background:#EEF8FB; border-color:#D5EAF1; }
.card-nueva-agencia { background:#F1FAF4; border-color:#D7EEDC; }
.card-buscar-agencia { background:#FFF7EF; border-color:#F4E1CA; }

.action-top { display:flex; align-items:flex-start; gap:0.75rem; }

.action-icon {
    width:38px;
    height:38px;
    border-radius:12px;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:1rem;
    flex-shrink:0;
}
.card-es .action-icon { background:#E6EEFF; border:1px solid #D2DFFF; }
.card-grupos .action-icon { background:#E7F5EA; border:1px solid #D0EAD7; }
.card-salida .action-icon { background:#FFF0DD; border:1px solid #F2DEC0; }
.card-crucero .action-icon { background:#EEE8FF; border:1px solid #DDD2FF; }
.card-excursiones .action-icon { background:#E2F2F7; border:1px solid #CFE6EE; }
.card-nueva-agencia .action-icon { background:#E2F4E7; border:1px solid #CFE5D6; }
.card-buscar-agencia .action-icon { background:#FDEBD9; border:1px solid #F2D9B9; }

.action-text {
    display:flex;
    flex-direction:column;
    gap:0.10rem;
    min-width:0;
}

.action-title,
.action-title-en {
    font-size:0.95rem;
    font-weight:700;
    color:#1F2937;
    line-height:1.1;
}
.action-title-en { margin-top:0.05rem; }

.action-desc,
.action-desc-en {
    font-size:0.73rem;
    color:#6F7B91;
    line-height:1.28;
}
.action-desc { margin-top:0.18rem; }
.action-desc-en { margin-top:0.04rem; }

.action-button-wrap {
    display:flex !important;
    justify-content:flex-start !important;
    align-items:center !important;
    width:100% !important;
    margin-top:0.1rem;
}

.panel-inline {
    margin-top:1rem;
    padding-top:0.2rem;
    width:100%;
    max-width:1040px;
}

.done-link {
    display:inline-flex;
    align-items:center;
    gap:0.35rem;
    margin-top:0.65rem;
    background:#D9E9FF;
    color:#214D92 !important;
    border:1px solid #BDD6FF;
    border-radius:999px;
    padding:0.42rem 0.88rem;
    font-size:0.71rem;
    font-weight:600;
    text-decoration:none;
}

.step { display:flex; align-items:flex-start; gap:0.65rem; margin-bottom:0.6rem; }
.step:last-child { margin-bottom:0; }
.step-dot {
    width:18px;
    height:18px;
    border-radius:50%;
    flex-shrink:0;
    margin-top:0.05rem;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:0.55rem;
    font-weight:700;
}
.sd-done { background:#EEF7F1; border:1px solid #D8ECDF; color:#2E7D58; }
.sd-active { background:#F2F4F9; border:1px solid #DDE2EC; color:#6E778B; }
.sd-wait { background:#F8F9FC; border:1px solid #E6E9F0; color:#B1B8C9; }
.step-content { display:flex; flex-direction:column; min-width:0; flex:1; }
.st-done, .st-active, .st-wait { font-size:0.76rem; }
.st-done { color:#394255; }
.st-active { color:#1F2937; font-weight:600; }
.st-wait { color:#A2ABBD; }
.step-detail {
    font-size:0.7rem;
    color:#8790A4;
    margin-top:0.08rem;
    word-wrap:break-word !important;
    overflow-wrap:break-word !important;
    white-space:normal !important;
}

.agency-card {
    background:#FBFCFF;
    border:1px solid #E6EBF3;
    border-radius:18px;
    padding:1rem;
    margin-top:0.75rem;
}
.agency-grid {
    display:grid;
    grid-template-columns:repeat(2, minmax(0, 1fr));
    gap:0.85rem 1rem;
}
.agency-item-label {
    font-size:0.68rem;
    color:#7E889D;
    text-transform:uppercase;
    letter-spacing:0.04em;
    margin-bottom:0.16rem;
}
.agency-item-value {
    font-size:0.8rem;
    color:#1F2937;
    line-height:1.35;
    word-break:break-word;
}

.history-row {
    display:flex;
    align-items:center;
    gap:0.75rem;
    padding:0.28rem 0;
    margin-bottom:0.35rem;
    width:100%;
    max-width:620px;
}
.history-num {
    width:22px;
    height:22px;
    border-radius:7px;
    background:#F2F4F9;
    border:1px solid #E3E7F1;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:0.62rem;
    font-weight:600;
    color:#5D6880;
    flex-shrink:0;
}
.history-name {
    font-size:0.75rem;
    color:#394255;
    flex:1;
    word-wrap:break-word;
    overflow-wrap:break-word;
    white-space:normal;
}
.history-time { font-size:0.68rem; color:#A2ABBD; white-space:nowrap; }
.history-link { font-size:0.71rem; color:#5D6880; text-decoration:none; font-weight:500; white-space:nowrap; }

.portal-footer {
    margin-top:1rem;
    padding:0.5rem 0 0 0;
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:0.8rem;
    flex-wrap:wrap;
}
.footer-text { font-size:0.71rem; color:#A2ABBD; }

@media (max-width: 1400px) {
    .agency-grid { grid-template-columns:1fr; }
}
@media (max-width: 1300px) {
    .portal-header { flex-direction:column; align-items:flex-start; }
    .portal-footer { flex-direction:column; align-items:flex-start; }
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# LOGIN
# ──────────────────────────────────────────────────────────────────────────────
if not st.session_state["authenticated"]:
    st.markdown('<div class="login-page"><div class="login-shell">', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="login-head">
        <img class="login-logo" src="{LOGO_URL}" alt="Logo">
        <div class="login-title">Acceso</div>
        <div class="login-subtitle">Access</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-form-box">', unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Mail / Email", placeholder="support@crucemundo.com")
        password = st.text_input("Contraseña / Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Entrar / Login")

        if submitted:
            email_clean = email.strip().lower()

            if not email_clean or not password:
                st.error("Debes introducir mail y contraseña / Please enter email and password.")
            elif email_clean not in VALID_USERS:
                st.error("Usuario no autorizado / Unauthorized user.")
            elif password != VALID_PASSWORD:
                st.error("Contraseña incorrecta / Incorrect password.")
            else:
                st.session_state["authenticated"] = True
                st.session_state["user_email"] = email_clean
                st.session_state["display_name"] = VALID_USERS[email_clean]
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-note">El mail valida el acceso y el alias se usará para nombrar la sesión · Email validates access and the alias will be used to name the session.</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# APP
# ──────────────────────────────────────────────────────────────────────────────
USER_EMAIL = st.session_state.get("user_email", "").strip()
DISPLAY_USER = st.session_state.get("display_name", "").strip() or "Sin usuario"
SALUDO = get_saludo()
SALUDO_EN = get_saludo_en()
confirm_state = st.session_state.get("confirm_state", "idle")
excursiones_url = f"https://docs.google.com/spreadsheets/d/{EXCURSIONES_SHEET_ID}/edit"

st.markdown(f"""
<div class="portal-header">
    <div class="portal-header-left">
        <img class="portal-logo" src="{LOGO_URL}" alt="Logo">
        <div>
            <div class="portal-title">{SALUDO}, {DISPLAY_USER}. ¿Qué hacemos hoy?</div>
            <div class="portal-title-en">{SALUDO_EN}, {DISPLAY_USER}. What are we doing today?</div>
            <div class="portal-subtitle">Herramientas y automatizaciones · Backend Google Drive</div>
            <div class="portal-subtitle-en">Tools and automations · Google Drive backend</div>
        </div>
    </div>
    <div class="user-top">👤 {DISPLAY_USER}</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

st.markdown("""
<div class="section-head-row">
    <div class="section-eyebrow">ACCIONES RÁPIDAS · QUICK ACTIONS</div>
    <a class="web-chip" href="https://www.crucemundo.es" target="_blank" rel="noopener noreferrer">
        Ir a Crucemundo
    </a>
    <a class="web-chip" href="https://www.gmail.es" target="_blank" rel="noopener noreferrer">
        Gmail

</div>
""", unsafe_allow_html=True)

st.markdown(f'<div class="user-pill">👤 {DISPLAY_USER} · {USER_EMAIL}</div>', unsafe_allow_html=True)

# FILA 1
row1_col1, row1_col2, row1_col3, row1_col4, row1_col5 = st.columns(5, gap="medium")

with row1_col1:
    st.markdown(f"""
    <div class="action-box card-es">
        <div class="action-top">
            <div class="action-icon">📋</div>
            <div class="action-text">
                <div class="action-title">Nueva Confirmación</div>
                <div class="action-title-en">New Confirmation</div>
                <div class="action-desc">Crear sesión MASTER de trabajo para {DISPLAY_USER}</div>
                <div class="action-desc-en">Create MASTER working session for {DISPLAY_USER}</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)

    if confirm_state in ("idle", "done"):
        if st.button("Crear Sesión ES", key="btn_crear_es"):
            iniciar_proceso("es", TEMPLATE_ID_ES, "MASTER", "Estado del Proceso · Process Status: Crear Sesión MASTER_CONFIRMATION")
    else:
        st.button("Crear Sesión ES", key="btn_crear_es_dis", disabled=True)

    st.markdown('</div></div>', unsafe_allow_html=True)

with row1_col2:
    st.markdown(f"""
    <div class="action-box card-grupos">
        <div class="action-top">
            <div class="action-icon">👥</div>
            <div class="action-text">
                <div class="action-title">Nueva Confirmación GRUPOS</div>
                <div class="action-title-en">New GROUPS Confirmation</div>
                <div class="action-desc">Crear sesión MASTER GRUPOS de trabajo para {DISPLAY_USER}</div>
                <div class="action-desc-en">Create MASTER GROUPS working session for {DISPLAY_USER}</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)

    if confirm_state in ("idle", "done"):
        if st.button("Crear Sesión GRUPOS", key="btn_crear_grupos"):
            iniciar_proceso("grupos", TEMPLATE_ID_GRUPOS, "MASTER GRUPOS", "Estado del Proceso · Process Status: Crear Sesión MASTER_GRUPOS")
    else:
        st.button("Crear Sesión GRUPOS", key="btn_crear_grupos_dis", disabled=True)

    st.markdown('</div></div>', unsafe_allow_html=True)

with row1_col3:
    st.markdown("""
    <div class="action-box card-salida">
        <div class="action-top">
            <div class="action-icon">🧭</div>
            <div class="action-text">
                <div class="action-title">Ir a Salida</div>
                <div class="action-title-en">Go to Departure</div>
                <div class="action-desc">Buscar una salida existente por año, barco y código de salida</div>
                <div class="action-desc-en">Find an existing departure by year, ship and departure code</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)

    if st.button("Buscar Salida", key="btn_ir_salida"):
        open_panel("salida")
        st.rerun()

    st.markdown('</div></div>', unsafe_allow_html=True)

with row1_col4:
    st.markdown("""
    <div class="action-box card-crucero">
        <div class="action-top">
            <div class="action-icon">🚢</div>
            <div class="action-text">
                <div class="action-title">Crear crucero</div>
                <div class="action-title-en">Create Cruise</div>
                <div class="action-desc">Crear salida nueva desde plantilla y guardarla en año/barco</div>
                <div class="action-desc-en">Create a new departure from template and save it in year/ship</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)

    if st.button("Nuevo Crucero", key="btn_crear_crucero_open"):
        open_panel("crucero")
        st.rerun()

    st.markdown('</div></div>', unsafe_allow_html=True)

with row1_col5:
    st.markdown("""
    <div class="action-box card-excursiones">
        <div class="action-top">
            <div class="action-icon">🏝️</div>
            <div class="action-text">
                <div class="action-title">Excursiones</div>
                <div class="action-title-en">Excursions</div>
                <div class="action-desc">Abrir la hoja de Excursiones</div>
                <div class="action-desc-en">Open the Excursions sheet</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)

    st.markdown(
        f'<a class="done-link" href="{excursiones_url}" target="_blank">Abrir Excursiones ↗</a>',
        unsafe_allow_html=True
    )

    st.markdown('</div></div>', unsafe_allow_html=True)

# FILA 2
row2_col1, row2_col2, row2_col3, row2_col4, row2_col5 = st.columns(5, gap="medium")

with row2_col1:
    st.markdown("""
    <div class="action-box card-nueva-agencia">
        <div class="action-top">
            <div class="action-icon">🏢</div>
            <div class="action-text">
                <div class="action-title">Nueva Agencia</div>
                <div class="action-title-en">New Agency</div>
                <div class="action-desc">Crear una agencia y guardarla en la hoja Datos</div>
                <div class="action-desc-en">Create an agency and save it in Datos sheet</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)

    if st.button("Nueva Agencia", key="btn_nueva_agencia"):
        open_panel("nueva_agencia")
        st.rerun()

    st.markdown('</div></div>', unsafe_allow_html=True)

with row2_col2:
    st.markdown("""
    <div class="action-box card-buscar-agencia">
        <div class="action-top">
            <div class="action-icon">🔎</div>
            <div class="action-text">
                <div class="action-title">Buscar Agencia</div>
                <div class="action-title-en">Find Agency</div>
                <div class="action-desc">Buscar por cualquier dato y mostrar la ficha completa</div>
                <div class="action-desc-en">Search by any known value and show the full record</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)

    if st.button("Buscar Agencia", key="btn_buscar_agencia"):
        open_panel("buscar_agencia")
        st.rerun()

    st.markdown('</div></div>', unsafe_allow_html=True)

with row2_col3:
    st.empty()
with row2_col4:
    st.empty()
with row2_col5:
    st.empty()

if st.session_state.get("open_salida_form"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("#### Seleccionar salida · Select departure")

    try:
        years = get_years()
        current_year = st.session_state.get("salida_year")
        if current_year not in years:
            current_year = None

        selected_year = st.selectbox(
            "AÑO / YEAR",
            options=years,
            index=years.index(current_year) if current_year in years else None,
            placeholder="Selecciona un año / Select a year",
            key="salida_year_widget",
            on_change=on_year_change
        )

        if selected_year != st.session_state.get("salida_year"):
            st.session_state["salida_year"] = selected_year

        boats = get_boats(selected_year) if selected_year else []
        current_boat = st.session_state.get("salida_boat")
        if current_boat not in boats:
            current_boat = None

        selected_boat = st.selectbox(
            "BARCO / SHIP",
            options=boats,
            index=boats.index(current_boat) if current_boat in boats else None,
            placeholder="Selecciona un barco / Select a ship",
            key="salida_boat_widget",
            on_change=on_boat_change,
            disabled=not selected_year
        )

        if selected_boat != st.session_state.get("salida_boat"):
            st.session_state["salida_boat"] = selected_boat

        departures = get_departures(selected_year, selected_boat) if selected_year and selected_boat else []
        departure_names = [d["nombre"] for d in departures]

        current_departure = st.session_state.get("salida_name")
        if current_departure not in departure_names:
            current_departure = None

        selected_departure = st.selectbox(
            "SALIDA / DEPARTURE",
            options=departure_names,
            index=departure_names.index(current_departure) if current_departure in departure_names else None,
            placeholder="Selecciona una salida / Select a departure",
            key="salida_name_widget",
            on_change=on_salida_change,
            disabled=not selected_boat
        )

        if selected_departure != st.session_state.get("salida_name"):
            st.session_state["salida_name"] = selected_departure

        if selected_departure:
            selected_obj = next((d for d in departures if d["nombre"] == selected_departure), None)
            if selected_obj:
                st.markdown(
                    f'<a class="done-link" href="{selected_obj["url"]}" target="_blank">Abrir salida / Open departure ↗</a>',
                    unsafe_allow_html=True
                )
    except Exception as e:
        st.exception(e)

    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.get("open_crucero_form"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("#### Crear crucero · Create cruise")

    try:
        years = get_years()
        current_c_year = st.session_state.get("crucero_year")
        if current_c_year not in years:
            current_c_year = None

        crucero_year = st.selectbox(
            "AÑO DESTINO / TARGET YEAR",
            options=years,
            index=years.index(current_c_year) if current_c_year in years else None,
            placeholder="Selecciona un año / Select a year",
            key="crucero_year_widget",
            on_change=on_crucero_year_change
        )

        if crucero_year != st.session_state.get("crucero_year"):
            st.session_state["crucero_year"] = crucero_year

        crucero_boats = get_boats(crucero_year) if crucero_year else []
        current_c_boat = st.session_state.get("crucero_boat")
        if current_c_boat not in crucero_boats:
            current_c_boat = None

        crucero_boat = st.selectbox(
            "BARCO / SHIP",
            options=crucero_boats,
            index=crucero_boats.index(current_c_boat) if current_c_boat in crucero_boats else None,
            placeholder="Selecciona un barco / Select a ship",
            key="crucero_boat_widget",
            on_change=on_crucero_boat_change,
            disabled=not crucero_year
        )

        if crucero_boat != st.session_state.get("crucero_boat"):
            st.session_state["crucero_boat"] = crucero_boat

        fecha_salida = st.date_input(
            "FECHA DE SALIDA / DEPARTURE DATE",
            value=date.today(),
            format="DD/MM/YYYY"
        )

        if crucero_boat and fecha_salida:
            preview_name = f"{crucero_boat}_{fecha_salida.strftime('%y%m%d')}"
            st.caption(f"Nombre previsto / Expected name: {preview_name}")

        if st.button("Crear Crucero", key="btn_crear_crucero_action", disabled=not (crucero_year and crucero_boat and fecha_salida)):
            if int(crucero_year) != fecha_salida.year:
                st.error("El año seleccionado no coincide con el año de la fecha / Selected year does not match the date year.")
            else:
                result = create_crucero_file(crucero_boat, fecha_salida)
                if result["status"] == "duplicate":
                    st.warning(f'Ya existe / Already exists: "{result["name"]}".')
                    st.markdown(
                        f'<a class="done-link" href="{result["url"]}" target="_blank">Abrir archivo existente / Open existing file ↗</a>',
                        unsafe_allow_html=True
                    )
                else:
                    st.success(f'Archivo creado / File created: "{result["name"]}".')
                    st.markdown(
                        f'<a class="done-link" href="{result["url"]}" target="_blank">Abrir crucero / Open cruise ↗</a>',
                        unsafe_allow_html=True
                    )
    except Exception as e:
        st.exception(e)

    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.get("open_nueva_agencia_form"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("#### Nueva Agencia · New Agency")

    with st.form("form_nueva_agencia", clear_on_submit=False):
        row_a1, row_a2 = st.columns(2, gap="medium")
        with row_a1:
            ag_nombre = st.text_input("Nombre", key="ag_nombre")
        with row_a2:
            ag_codigo = st.text_input("CODIGO", key="ag_codigo")

        row_b1, row_b2 = st.columns(2, gap="medium")
        with row_b1:
            ag_grupo_gest = st.text_input("Grupo Gest", key="ag_grupo_gest")
        with row_b2:
            ag_telefono = st.text_input("Telefono", key="ag_telefono")

        row_c1, row_c2 = st.columns(2, gap="medium")
        with row_c1:
            ag_email = st.text_input("Email", key="ag_email")
        with row_c2:
            ag_direccion = st.text_input("Direccion", key="ag_direccion")

        st.markdown("##### Comisiones e IVA")

        row_d1, row_d2, row_d3 = st.columns(3, gap="medium")
        with row_d1:
            ag_comision = st.number_input(
                "COMISION AGENCIA (%)",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=0.5,
                format="%0.2f",
                key="ag_comision"
            )
        with row_d2:
            ag_comision_oferta = st.number_input(
                "COMISION AGENCIA ( CON OFERTA ) (%)",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=0.5,
                format="%0.2f",
                key="ag_comision_oferta"
            )
        with row_d3:
            ag_comision_2x1 = st.number_input(
                "COMISION AGENCIA ( OFERTA 2X1 ) (%)",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=0.5,
                format="%0.2f",
                key="ag_comision_2x1"
            )

        row_e1, row_e2 = st.columns(2, gap="medium")
        with row_e1:
            ag_iva = st.number_input(
                "IVA (%)",
                min_value=0.0,
                max_value=100.0,
                value=21.0,
                step=0.5,
                format="%0.2f",
                key="ag_iva"
            )
        with row_e2:
            ag_iva_servicio_opcional = st.number_input(
                "IVA SERVICIO OPCIONAL (%)",
                min_value=0.0,
                max_value=100.0,
                value=21.0,
                step=0.5,
                format="%0.2f",
                key="ag_iva_servicio_opcional"
            )

        guardar_agencia = st.form_submit_button("Guardar Agencia")

        if guardar_agencia:
            if not ag_nombre.strip():
                st.error("El campo Nombre es obligatorio.")
            elif not ag_codigo.strip():
                st.error("El campo CODIGO es obligatorio.")
            else:
                agency_data = {
                    "Nombre": ag_nombre.strip(),
                    "CODIGO": ag_codigo.strip(),
                    "Grupo Gest": ag_grupo_gest.strip(),
                    "Telefono": ag_telefono.strip(),
                    "Email": ag_email.strip(),
                    "Direccion": ag_direccion.strip(),
                    "COMISION AGENCIA": percent_to_sheet_decimal(ag_comision),
                    "COMISION AGENCIA ( CON OFERTA )": percent_to_sheet_decimal(ag_comision_oferta),
                    "COMISION AGENCIA ( OFERTA 2X1 )": percent_to_sheet_decimal(ag_comision_2x1),
                    "IVA": percent_to_sheet_decimal(ag_iva),
                    "IVA SERVICIO OPCIONAL": percent_to_sheet_decimal(ag_iva_servicio_opcional),
                }

                try:
                    append_agency_row(agency_data)
                    st.success(f'Agencia guardada correctamente: {agency_data["Nombre"]}')
                except Exception as e:
                    st.exception(e)

    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.get("open_buscar_agencia_form"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("#### Buscar Agencia · Find Agency")

    search_query = st.text_input(
        "Introduce lo que sepas: nombre, código, grupo, teléfono, email o dirección",
        key="agency_search_query",
        placeholder="Ej: viajes pepe / AG123 / 912345678 / info@..."
    )

    if st.button("Buscar coincidencias", key="btn_ejecutar_busqueda_agencia"):
        try:
            matches = search_agencies(search_query)
            st.session_state["agency_matches"] = matches
            st.session_state["agency_selected_idx"] = None
        except Exception as e:
            st.exception(e)

    matches = st.session_state.get("agency_matches", [])

    if search_query and matches == []:
        st.info("No hay coincidencias.")

    if len(matches) == 1:
        st.success("Se ha encontrado 1 coincidencia.")
        selected_agency = matches[0]

        st.markdown('<div class="agency-card"><div class="agency-grid">', unsafe_allow_html=True)
        for field in AGENCY_FIELDS:
            st.markdown(f"""
            <div>
                <div class="agency-item-label">{field}</div>
                <div class="agency-item-value">{selected_agency.get(field, "") or "—"}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    elif len(matches) > 1:
        st.warning(f"Hay {len(matches)} coincidencias. Selecciona la correcta.")
        options = [
            f'{i+1}. {ag["Nombre"]} | {ag["CODIGO"]} | {ag["Telefono"]} | {ag["Email"]}'
            for i, ag in enumerate(matches)
        ]

        selected_label = st.selectbox(
            "Elige la agencia correcta",
            options=options,
            index=None,
            placeholder="Selecciona una coincidencia"
        )

        if selected_label:
            selected_idx = options.index(selected_label)
            selected_agency = matches[selected_idx]

            st.markdown('<div class="agency-card"><div class="agency-grid">', unsafe_allow_html=True)
            for field in AGENCY_FIELDS:
                st.markdown(f"""
                <div>
                    <div class="agency-item-label">{field}</div>
                    <div class="agency-item-value">{selected_agency.get(field, "") or "—"}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

saved_name = st.session_state.get("nombre_copia", "")
saved_url = st.session_state.get("copy_url", "")
process_title = st.session_state.get("process_title", "Estado del Proceso / Process Status")

if confirm_state in ("step1", "step2", "step3", "done"):
    st.markdown('<div class="panel-inline" style="max-width:520px;">', unsafe_allow_html=True)
    st.markdown(f"#### {process_title}")

    if confirm_state == "step1":
        render_step("Progreso / Progress", "Preparando plantilla / Preparing template...", "active")
    elif confirm_state == "step2":
        render_step("Progreso / Progress", "Generando copia en Drive / Creating Drive copy...", "active")
    elif confirm_state == "step3":
        render_step("Progreso / Progress", "Abriendo sesión / Opening session...", "active")
    elif confirm_state == "done":
        render_step("Progreso / Progress", "Completo / Complete", "done")
        st.markdown(f"""
        <div style="margin-top:0.8rem;">
            <div style="font-size:0.76rem;color:#1F2937;font-weight:600;">Sesión creada / Session created</div>
            <div style="font-size:0.71rem;color:#657087;margin-top:0.15rem;line-height:1.3;">
                Puedes abrir tu sesión en el botón de abajo · You can open your session with the button below.
            </div>
            <a class="done-link" href="{saved_url}" target="_blank">Abrir sesión / Open session ↗</a>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    if confirm_state == "step1":
        time.sleep(0.7)
        st.session_state["confirm_state"] = "step2"
        st.rerun()
    elif confirm_state == "step2":
        time.sleep(0.7)
        st.session_state["confirm_state"] = "step3"
        st.rerun()
    elif confirm_state == "step3":
        time.sleep(0.7)
        st.session_state["confirm_state"] = "done"
        existing = [h["nombre"] for h in st.session_state["historial"]]
        if saved_name and saved_name not in existing:
            st.session_state["historial"].insert(0, {
                "nombre": saved_name,
                "hora": datetime.now().strftime("%H:%M:%S"),
                "url": saved_url,
            })
        st.rerun()

    if confirm_state == "done" and saved_name and not st.session_state.get("opened_" + saved_name):
        st.session_state["opened_" + saved_name] = True
        st.markdown(
            f'<script>setTimeout(()=>window.open("{saved_url}","_blank"),300);</script>',
            unsafe_allow_html=True
        )

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
if st.button("Cerrar sesión / Logout", key="btn_logout"):
    do_logout()
st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.get("historial"):
    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-eyebrow">ESTA SESIÓN · THIS SESSION</div>', unsafe_allow_html=True)

    for i, entry in enumerate(st.session_state["historial"], 1):
        st.markdown(f"""
        <div class="history-row">
            <div class="history-num">{i}</div>
            <div class="history-name">{entry['nombre']}</div>
            <div class="history-time">{entry['hora']}</div>
            <a class="history-link" href="{entry['url']}" target="_blank">Abrir / Open ↗</a>
        </div>
        """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="portal-footer">
    <span class="footer-text">Panel de Control · Control Panel · v4.2.0</span>
    <span class="footer-text">Raíz Drive / Drive Root: {DRIVE_ROOT_ID}</span>
</div>
""", unsafe_allow_html=True)
