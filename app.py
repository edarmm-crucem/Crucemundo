import streamlit as st
from datetime import datetime, date
import urllib.parse
import time
import re

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Panel de Control",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

LOGO_ID = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGO_URL = f"https://lh3.googleusercontent.com/d/{LOGO_ID}"

TEMPLATE_ID_ES = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
TEMPLATE_ID_GRUPOS = "1Z7ktX3PhVkMibWpzdrDDqAT4aPsmjzSJPf1SgZcL5-w"
TEMPLATE_ID_CRUCERO = "1zSJPi6St_Z5Jw1c6eieVnKI4NyEdP7E9n3WTZ9yy3C0"

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

VALID_PASSWORD = "Crucemundo26!"

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
    "salida_year": None,
    "salida_boat": None,
    "salida_name": None,
    "crucero_year": None,
    "crucero_boat": None,
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

def close_all_panels():
    st.session_state["open_salida_form"] = False
    st.session_state["open_crucero_form"] = False

def open_panel(panel_name):
    close_all_panels()

    if panel_name == "salida":
        clear_crucero_state()
        st.session_state["open_salida_form"] = True

    elif panel_name == "crucero":
        clear_salida_state()
        st.session_state["open_crucero_form"] = True

    st.session_state["active_panel"] = panel_name

def clear_all_selectors():
    clear_salida_state()
    clear_crucero_state()
    close_all_panels()
    st.session_state["active_panel"] = None

def do_logout():
    keys_to_delete = [
        "authenticated", "user_email", "display_name", "confirm_state",
        "session_type", "active_panel", "open_salida_form", "open_crucero_form",
        "salida_year", "salida_boat", "salida_name",
        "crucero_year", "crucero_boat",
        "salida_year_widget", "salida_boat_widget", "salida_name_widget",
        "crucero_year_widget", "crucero_boat_widget",
        "nombre_copia", "copy_url", "process_title"
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

# ──────────────────────────────────────────────────────────────────────────────
# GOOGLE DRIVE API
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_drive_service():
    if "gcp_service_account" not in st.secrets:
        raise Exception('Falta [gcp_service_account] en secrets.')

    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)

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

    año = str(fecha_obj.year)
    yy = fecha_obj.strftime("%y")
    mm = fecha_obj.strftime("%m")
    dd = fecha_obj.strftime("%d")
    fecha_es = fecha_obj.strftime("%d/%m/%Y")
    nombre_nuevo = f"{barco}_{yy}{mm}{dd}"

    carpeta_año = get_or_create_folder(DRIVE_ROOT_ID, año)
    carpeta_barco = get_or_create_folder(carpeta_año["id"], barco)

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
        f"Los archivos de sesión deben borrarse a los 30 días."
    )

    copia = copy_file_to_folder(
        TEMPLATE_ID_CRUCERO,
        nombre_nuevo,
        carpeta_barco["id"],
        descripcion
    )

    get_years.clear()
    get_year_folder_id.clear()
    get_boats.clear()
    get_departures.clear()

    return {
        "status": "created",
        "name": nombre_nuevo,
        "url": copia.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{copia['id']}/edit",
        "year": año,
        "boat": barco
    }

# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""

# styling (continúa en el bloque siguiente)
</style>
""", unsafe_allow_html=True)

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
    max-width:1250px !important;
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
div[data-testid="stDateInput"] label {
    color:#4D576D !important;
    font-size:0.78rem !important;
    font-weight:500 !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stDateInput"] input {
    background:#F8FAFC !important;
    border:1px solid #E5EAF2 !important;
    border-radius:12px !important;
    color:#1F2937 !important;
}

div.stButton { width:fit-content !important; }
div.stButton > button,
div[data-testid="stFormSubmitButton"] > button,
.logout-btn > div > button {
    background:#D9E9FF !important;
    color:#214D92 !important;
    border:1
