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

# ──────────────────────────────────────────────────────────────────────────────
# STATE (igual que el tuyo)
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
# HELPERS (igual)
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

# ──────────────────────────────────────────────────────────────────────────────
# LOGIN (igual)
# ──────────────────────────────────────────────────────────────────────────────
if not st.session_state["authenticated"]:
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Entrar"):
        if email in VALID_USERS and password == VALID_PASSWORD:
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = email
            st.session_state["display_name"] = VALID_USERS[email]
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────────────────
DISPLAY_USER = st.session_state["display_name"]
SALUDO = get_saludo()
SALUDO_EN = get_saludo_en()

st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
        <h3>{SALUDO}, {DISPLAY_USER}</h3>
        <p>{SALUDO_EN}, {DISPLAY_USER}</p>
    </div>
    <div>👤 {DISPLAY_USER}</div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# 🔥 MODIFICACIÓN AQUÍ (ACCIONES RÁPIDAS)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;justify-content:space-between;align-items:center;margin:0.5rem 0 1rem;">
    <div class="section-eyebrow" style="margin:0;">
        ACCIONES RÁPIDAS · QUICK ACTIONS
    </div>

    <a href="https://www.crucemundo.es" target="_blank"
       style="
            display:inline-flex;
            align-items:center;
            padding:0.35rem 0.75rem;
            border-radius:999px;
            background:#ffffff;
            border:1px solid #E4E7EF;
            font-size:0.70rem;
            font-weight:600;
            color:#214D92;
            text-decoration:none;
            white-space:nowrap;
       ">
        🌐 Web Crucemundo
    </a>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# RESTO DE TU APP (NO TOCADO)
# ──────────────────────────────────────────────────────────────────────────────

st.write("Aquí sigue todo tu dashboard igual…")
