# ============================================================
# 1. IMPORTS
# ============================================================
import streamlit as st
from datetime import datetime, date
import urllib.parse
import re
import requests

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth.transport.requests import Request


# ============================================================
# 2. CONFIG
# ============================================================
LOGO_ID = "1N7eaCKP1Jeg8KuDXRjJ8tZLhnKStMZ8"

TEMPLATE_ID_ES = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
TEMPLATE_ID_GRUPOS = "1Z7ktX3PhVkMibWpzdrDDqAT4aPsmjzSJPf1SgZcL5-w"
TEMPLATE_ID_CRUCERO = "1zSJPi6St_Z5Jw1c6eieVnKI4NyEdP7E9n3WTZ9yy3C0"

EXCURSIONES_SHEET_ID = "1ojMHeoosUyel8BA2XTmDsmyDJf_vvJrrJNOyxn2u1jg"
AGENCY_SHEET_ID = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
AGENCY_SHEET_NAME = "Datos"

DRIVE_ROOT_ID = "11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm"
FOLDER_CVCFIT = "1MxMdeBlUG6v5n2upobsjNbQNQ8F_C_sO"

VALID_USERS = {
    "support@crucemundo.com": "Albina",
    "edarmm@gmail.com": "Esteban",
}
VALID_PASSWORD = st.secrets["app_password"]


# ============================================================
# 3. STATE (LIMPIO)
# ============================================================
DEFAULTS = {
    "authenticated": False,
    "activepanel": None,
    "cvcfit_result": None,
}

def init_state():
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

def reset_state():
    st.session_state.clear()
    st.rerun()


# ============================================================
# 4. GOOGLE SERVICES
# ============================================================
@st.cache_resource
def get_creds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
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
# 5. HELPERS GENERALES
# ============================================================
def normalize(text):
    return str(text).strip().lower()

def safe_filename(text):
    return re.sub(r'[\\/:*?"<>|]', "", str(text)).strip()

def first_line(text):
    return str(text).splitlines()[0] if text else ""


# ============================================================
# 6. DRIVE HELPERS
# ============================================================
def list_files(folder_id):
    return drive().files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id,name,webViewLink,modifiedTime)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        corpora="allDrives",
        pageSize=1000,
    ).execute().get("files", [])


# ============================================================
# 7. SHEETS HELPERS
# ============================================================
def get_cell(spreadsheet_id, sheet, cell):
    values = sheets().spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet}'!{cell}"
    ).execute().get("values", [])
    return values[0][0] if values else ""


# ============================================================
# 8. EXPORT PDF
# ============================================================
def export_pdf(spreadsheet_id, gid):
    creds = get_creds().with_scopes([
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
    ])
    creds.refresh(Request())

    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=pdf&gid={gid}"
    res = requests.get(url, headers={"Authorization": f"Bearer {creds.token}"})
    res.raise_for_status()
    return res.content


# ============================================================
# 9. CVC FIT (PRO)
# ============================================================
def find_cvcfit(locator):
    locator = normalize(locator)
    files = list_files(FOLDER_CVCFIT)

    for i, f in enumerate(files, 1):
        yield {"type": "progress", "msg": f"{i}/{len(files)} → {f['name']}"}

        try:
            val = first_line(get_cell(f["id"], "Booking ES", "G11"))

            if normalize(val) == locator:

                nombre = first_line(get_cell(f["id"], "Booking ES", "G24"))
                pdf = export_pdf(f["id"], 0)

                yield {
                    "type": "done",
                    "file": f,
                    "nombre": nombre,
                    "pdf": pdf
                }
                return

        except:
            continue

    raise Exception("No encontrado")


# ============================================================
# 10. LOGIN
# ============================================================
def login():
    st.title("Login")

    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.form_submit_button("Entrar"):
            if email in VALID_USERS and password == VALID_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas")


# ============================================================
# 11. UI COMPONENTS
# ============================================================
def action(title, key, panel):
    if st.button(title, key=key):
        st.session_state["activepanel"] = panel


# ============================================================
# 12. PANEL CVC FIT
# ============================================================
def panel_cvcfit():
    st.header("CVC Fit")

    locator = st.text_input("Localizador")

    if st.button("Generar PDF") and locator:
        progress = st.progress(0)
        log = st.empty()

        try:
            gen = find_cvcfit(locator)
            result = None

            for i, event in enumerate(gen):

                if event["type"] == "progress":
                    progress.progress(min(100, i * 5))
                    log.write(event["msg"])

                elif event["type"] == "done":
                    result = event
                    progress.progress(100)

            if result:
                st.success("Encontrado")
                st.write(result["nombre"])

                st.download_button(
                    "Descargar PDF",
                    data=result["pdf"],
                    file_name=f"CVC_FIT_{result['nombre']}.pdf"
                )

                st.markdown(f"[Abrir Sheet]({result['file']['webViewLink']})")

        except Exception as e:
            st.error(str(e))


# ============================================================
# 13. MAIN
# ============================================================
init_state()
st.set_page_config(layout="wide")

if not st.session_state["authenticated"]:
    login()
    st.stop()

st.title("Crucemundo Hub")

col1, col2, col3 = st.columns(3)

with col1:
    action("CVC Fit", "cvc", "cvcfit")

with col2:
    st.markdown(f"[Excursiones](https://docs.google.com/spreadsheets/d/{EXCURSIONES_SHEET_ID})")

with col3:
    if st.button("Logout"):
        reset_state()

# PANEL SWITCH
if st.session_state["activepanel"] == "cvcfit":
    panel_cvcfit()
