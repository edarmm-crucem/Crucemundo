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

VALID_PASSWORD = st.secrets["app_password"]

# ──────────────────────────────────────────────────────────────────────────────
# STATE
# ──────────────────────────────────────────────────────────────────────────────
defaults = {
    "authenticated": False,
    "user_email": "",
    "display_name": "",
    "confirm_state": "idle",
    "open_crucero_form": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def clean_filename(text):
    """Evita errores Drive / descarga"""
    text = str(text)
    text = re.sub(r"[^\w\-]", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")

# ──────────────────────────────────────────────────────────────────────────────
# GOOGLE SERVICES
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_creds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
    )

@st.cache_resource
def drive():
    return build("drive", "v3", credentials=get_creds())

@st.cache_resource
def sheets():
    return build("sheets", "v4", credentials=get_creds())

# ──────────────────────────────────────────────────────────────────────────────
# DRIVE CORE
# ──────────────────────────────────────────────────────────────────────────────
def get_or_create_folder(parent_id, name):
    service = drive()
    q = f"'{parent_id}' in parents and name='{name}' and trashed=false"

    res = service.files().list(q=q, fields="files(id,name)").execute()
    files = res.get("files", [])

    if files:
        return files[0]

    body = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }

    return service.files().create(body=body, fields="id,name").execute()

def find_file(folder_id, name):
    service = drive()
    q = f"'{folder_id}' in parents and name='{name}' and trashed=false"
    res = service.files().list(q=q, fields="files(id,name,webViewLink)").execute()
    files = res.get("files", [])
    return files[0] if files else None

def copy_file(template_id, name, folder_id):
    service = drive()
    body = {
        "name": name,
        "parents": [folder_id]
    }

    return service.files().copy(
        fileId=template_id,
        body=body,
        fields="id,name,webViewLink"
    ).execute()

# ──────────────────────────────────────────────────────────────────────────────
# CRUCERO FIX FINAL
# ──────────────────────────────────────────────────────────────────────────────
def create_crucero(barco, fecha):
    if not barco or not fecha:
        raise Exception("Faltan datos")

    year = str(fecha.year)
    yymmdd = fecha.strftime("%y%m%d")

    # 🔥 FIX CRÍTICO
    barco_clean = clean_filename(barco)
    filename = f"{barco_clean}_{yymmdd}"

    folder_year = get_or_create_folder(DRIVE_ROOT_ID, year)
    folder_ship = get_or_create_folder(folder_year["id"], barco_clean)

    existing = find_file(folder_ship["id"], filename)
    if existing:
        return {
            "status": "exists",
            "url": existing["webViewLink"],
            "name": filename
        }

    copy = copy_file(TEMPLATE_ID_CRUCERO, filename, folder_ship["id"])

    return {
        "status": "created",
        "url": copy["webViewLink"],
        "name": filename
    }

# ──────────────────────────────────────────────────────────────────────────────
# LOGIN
# ──────────────────────────────────────────────────────────────────────────────
if not st.session_state["authenticated"]:
    st.title("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Entrar"):
        if email in VALID_USERS and password == VALID_PASSWORD:
            st.session_state["authenticated"] = True
            st.session_state["display_name"] = VALID_USERS[email]
            st.rerun()
        else:
            st.error("Login incorrecto")

    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────────────────────
st.title("🛳️ Crucemundo Hub")

st.subheader(f"Hola {st.session_state['display_name']}")

if st.button("Abrir panel crucero"):
    st.session_state["open_crucero_form"] = True

if st.session_state["open_crucero_form"]:
    st.markdown("## Crear crucero")

    barco = st.text_input("Barco")
    fecha = st.date_input("Fecha", value=date.today())

    preview = f"{clean_filename(barco)}_{fecha.strftime('%y%m%d')}"
    st.caption(f"Nombre archivo: {preview}")

    if st.button("Crear"):
        try:
            result = create_crucero(barco, fecha)

            if result["status"] == "created":
                st.success("Crucero creado")
                st.markdown(f"[Abrir]({result['url']})")

            else:
                st.warning("Ya existe")
                st.markdown(f"[Abrir existente]({result['url']})")

        except Exception as e:
            st.error(str(e))
