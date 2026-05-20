import streamlit as st
import pytz
from datetime import datetime

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Página 01",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# AUTH
# ============================================================
if not st.session_state.get("authenticated"):
    st.warning("No tienes acceso. Vuelve al inicio.")
    st.stop()

# ============================================================
# UTILIDADES
# ============================================================
TIMEZONE = pytz.timezone("Europe/Madrid")
def now():
    return datetime.now(pytz.utc).astimezone(TIMEZONE).replace(tzinfo=None)
def getsaludo(lang="es"):
    hour = now().hour
    if lang == "en":
        if 6 <= hour < 14: return "Good morning"
        if 14 <= hour < 21: return "Good afternoon"
        return "Good evening"
    if 6 <= hour < 14: return "Buenos días"
    if 14 <= hour < 21: return "Buenas tardes"
    return "Buenas noches"

# ============================================================
# VARIABLES DE SESIÓN
# ============================================================
DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Sin usuario"
SALUDO = getsaludo("es")
SALUDOEN = getsaludo("en")
LOGOID = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGOURL = f"https://lh3.googleusercontent.com/d/{LOGOID}"

# ============================================================
# CSS CABECERA
# ============================================================
st.markdown(
    '''
    <style>
        .portal-header { padding: 0.1rem 0 0.55rem 0; display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 0.55rem; }
        .portal-header-left { display: flex; align-items: center; gap: 0.9rem; }
        .portal-logo { height: 42px; width: auto; object-fit: contain; display: block; }
        .portal-title, .portal-title-en { font-size: 0.96rem; font-weight: 800; color: #1F2937; line-height: 1.15; }
        .portal-title-en { margin-top: 0.12rem; }
        .portal-subtitle, .portal-subtitle-en { font-size: 0.72rem; color: #667085; line-height: 1.2; }
        .portal-subtitle { margin-top: 0.12rem; }
        .portal-subtitle-en { margin-top: 0.08rem; }
        .user-top { font-size: 0.72rem; color: #566079; white-space: nowrap; }
    </style>
    ''',
    unsafe_allow_html=True,
)

# ============================================================
# CABECERA
# ============================================================
st.markdown(
    f'''
    <div class="portal-header">
        <div class="portal-header-left">
            <img class="portal-logo" src="{LOGOURL}" alt="Logo">
            <div>
                <div class="portal-title">{SALUDO}, {DISPLAYUSER}. ¿Qué hacemos hoy?</div>
                <div class="portal-title-en">{SALUDOEN}, {DISPLAYUSER}. What are we doing today?</div>
                <div class="portal-subtitle">Herramientas y automatizaciones · Backend Google Drive</div>
                <div class="portal-subtitle-en">Tools and automations · Google Drive backend</div>
            </div>
        </div>
        <div class="user-top">{DISPLAYUSER}</div>
    </div>
    ''',
    unsafe_allow_html=True,
)

# ============================================================
# CONTENIDO
# ============================================================
st.markdown("---")
st.info("Esta página está en construcción. Aquí irá el contenido de **Acciones**.")
