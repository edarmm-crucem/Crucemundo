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
    "Nombre","CODIGO","Grupo Gest","Telefono","Email","Direccion",
    "COMISION AGENCIA","COMISION AGENCIA ( CON OFERTA )",
    "COMISION AGENCIA ( OFERTA 2X1 )","IVA","IVA SERVICIO OPCIONAL",
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
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def clean_filename(text):
    """EVITA problemas de Drive / descarga"""
    text = re.sub(r"[^\w\-]", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")

# ──────────────────────────────────────────────────────────────────────────────
# DRIVE / SHEETS
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_google_creds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
    )

@st.cache_resource
def get_drive_service():
    return build("drive", "v3", credentials=get_google_creds())

@st.cache_resource
def get_sheets_service():
    return build("sheets", "v4", credentials=get_google_creds())

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
    sheets = get_sheets_service()

    spreadsheet = sheets.spreadsheets().get(
        spreadsheetId=spreadsheet_id
    ).execute()

    sheet = spreadsheet["sheets"][0]
    sheet_id = sheet["properties"]["sheetId"]
    sheet_title = sheet["properties"]["title"]

    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_title}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": [[barco]]}
    ).execute()

    sheets.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [{
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "title": barco
                    },
                    "fields": "title"
                }
            }]
        }
    ).execute()

# ──────────────────────────────────────────────────────────────────────────────
# 🔥 FIX PRINCIPAL AQUÍ
# ──────────────────────────────────────────────────────────────────────────────
def create_crucero_file(barco, fecha_obj):
    if not barco or not fecha_obj:
        raise Exception("Faltan datos")

    year = str(fecha_obj.year)
    yymmdd = fecha_obj.strftime("%y%m%d")

    # 🔥 FIX: nombre limpio + seguro
    barco_clean = clean_filename(barco)

    nombre_nuevo = f"{barco_clean}_{yymmdd}"

    carpeta_anio = get_or_create_folder(DRIVE_ROOT_ID, year)
    carpeta_barco = get_or_create_folder(carpeta_anio["id"], barco_clean)

    duplicado = find_file_by_name(carpeta_barco["id"], nombre_nuevo)
    if duplicado:
        return {
            "status": "duplicate",
            "name": nombre_nuevo,
            "url": duplicado["webViewLink"]
        }

    copia = copy_file_to_folder(
        TEMPLATE_ID_CRUCERO,
        nombre_nuevo,
        carpeta_barco["id"],
        f"Barco {barco_clean} salida {fecha_obj}"
    )

    update_crucero_sheet(copia["id"], barco_clean)

    return {
        "status": "created",
        "name": nombre_nuevo,
        "url": copia["webViewLink"]
    }

# ──────────────────────────────────────────────────────────────────────────────
# UI LOGIN (igual que tu código)
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
            st.error("Credenciales incorrectas")

    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# BOTÓN CRUCERO (solo parte importante)
# ──────────────────────────────────────────────────────────────────────────────
st.title("Crucero")

barco = st.text_input("Barco")
fecha = st.date_input("Fecha", value=date.today())

if st.button("Crear crucero"):
    try:
        result = create_crucero_file(barco, fecha)

        if result["status"] == "created":
            st.success("Creado correctamente")
            st.markdown(f"[Abrir]({result['url']})")

        else:
            st.warning("Ya existe")
            st.markdown(f"[Abrir existente]({result['url']})")

    except Exception as e:
        st.error(str(e))
