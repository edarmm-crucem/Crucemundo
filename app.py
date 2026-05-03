import streamlit as st
from datetime import datetime
import urllib.parse
import time

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Panel de Control",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

LOGO_ID     = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGO_URL    = f"https://lh3.googleusercontent.com/d/{LOGO_ID}"
TEMPLATE_ID = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
FOLDER_ID   = "1MxMdeBlUG6v5n2upobsjNbQNQ8F_C_sO"

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

def do_logout():
    st.session_state.clear()
    st.rerun()

def reset_new_session():
    st.session_state["confirm_state"] = "idle"
    st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
body { background:#F3F4F7; font-family: 'DM Sans', sans-serif; }

/* HEADER */
.portal-header {
    background:#FFFFFF;
    border-bottom:1px solid #E7EAF0;
    padding:1rem 2rem;
    display:flex;
    justify-content:space-between;
    align-items:center;
}

/* MAIN */
.main-content { padding:2rem; }

/* CARD */
.action-box {
    max-width:560px;
    background:#FFFFFF;
    border:1px solid #E6E9F0;
    border-radius:22px;
    padding:1.1rem;
    margin-bottom:1rem;
    box-shadow:0 10px 30px rgba(17,24,39,0.06);
    display:flex;
    flex-direction:column;
    gap:0.9rem;
}

.action-top {
    display:flex;
    gap:0.9rem;
}

.action-icon {
    width:42px;
    height:42px;
    border-radius:14px;
    background:#EEF2FF;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:1.2rem;
}

.action-text { flex:1; }

.action-title {
    font-size:1.05rem;
    font-weight:600;
}

.action-desc {
    font-size:0.8rem;
    color:#6B7280;
}

.action-button-wrap button {
    width:100%;
    border-radius:16px;
    height:44px;
    background:#2E5FB8;
    color:white;
    border:none;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# LOGIN
# ──────────────────────────────────────────────────────────────────────────────
if not st.session_state["authenticated"]:
    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Entrar"):
            if email in VALID_USERS and password == VALID_PASSWORD:
                st.session_state["authenticated"] = True
                st.session_state["display_name"] = VALID_USERS[email]
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# APP
# ──────────────────────────────────────────────────────────────────────────────
USER = st.session_state["display_name"]

st.markdown(f"""
<div class="portal-header">
    <div>Hola {USER}</div>
    <div>Panel Control</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

# CARD
st.markdown('<div class="action-box">', unsafe_allow_html=True)

st.markdown(f"""
<div class="action-top">
    <div class="action-icon">📋</div>
    <div class="action-text">
        <div class="action-title">Nueva Confirmación</div>
        <div class="action-desc">Crear sesión MASTER</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="action-button-wrap">', unsafe_allow_html=True)

if st.button("Crear"):
    st.success("Sesión creada")

st.markdown('</div></div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
