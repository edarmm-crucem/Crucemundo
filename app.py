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
    st.session_state["authenticated"] = False
    st.session_state["user_email"] = ""
    st.session_state["display_name"] = ""
    st.session_state["confirm_state"] = "idle"
    if "nombre_copia" in st.session_state:
        del st.session_state["nombre_copia"]
    if "copy_url" in st.session_state:
        del st.session_state["copy_url"]
    st.rerun()

def nueva_accion():
    st.session_state["confirm_state"] = "idle"
    if "nombre_copia" in st.session_state:
        del st.session_state["nombre_copia"]
    if "copy_url" in st.session_state:
        del st.session_state["copy_url"]
    st.rerun()

def get_status_meta(state):
    if state == "idle":
        return "En espera", "wait", "wait", "wait", "Sin iniciar"
    if state == "step1":
        return "Preparando", "active", "wait", "wait", "Preparando plantilla"
    if state == "step2":
        return "Copiando", "done", "active", "wait", "Generando copia"
    if state == "step3":
        return "Abriendo", "done", "done", "active", "Preparando apertura"
    if state == "done":
        return "Lista", "done", "done", "done", "Sesión preparada"
    return "En espera", "wait", "wait", "wait", "Sin iniciar"

# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

* { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

[data-testid="stAppViewContainer"] { background:#F3F4F7; }
[data-testid="stHeader"] { background:transparent !important; }
section[data-testid="stSidebar"] { display:none !important; }

.block-container {
    padding:0 !important;
    max-width:100% !important;
}

/* HEADER */
.portal-header {
    background:#FFFFFF;
    border-bottom:1px solid #E7EAF0;
    padding:1rem 3rem;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:1rem;
}
.portal-header-left {
    display:flex;
    align-items:center;
    gap:0.9rem;
}
.portal-logo {
    height:46px;
    width:auto;
    object-fit:contain;
    display:block;
}
.portal-title {
    font-size:1rem;
    font-weight:600;
    color:#1F2937;
    line-height:1.15;
}
.portal-subtitle {
    font-size:0.74rem;
    color:#7C869D;
    margin-top:0.08rem;
}
.user-top {
    font-size:0.74rem;
    color:#566079;
    background:#F8F9FC;
    border:1px solid #E4E7EF;
    border-radius:999px;
    padding:0.42rem 0.78rem;
}

/* MAIN */
.main-content {
    padding:1.3rem 3rem 3rem;
}
.section-eyebrow {
    display:inline-flex;
    align-items:center;
    padding:0.34rem 0.74rem;
    border-radius:999px;
    background:#EAF1FF;
    border:1px solid #D6E3FF;
    color:#2E5FB8;
    font-size:0.67rem;
    font-weight:700;
    letter-spacing:0.08em;
    text-transform:uppercase;
    margin-bottom:0.85rem;
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
    font-size:0.73rem;
    color:#5D6880;
}

/* LOGIN */
.login-page {
    min-height:100vh;
    display:flex;
    align-items:center;
    justify-content:center;
    padding:1rem 1rem;
}
.login-shell {
    width:100%;
    max-width:430px;
}
.login-head {
    width:100%;
    background:#FFFFFF;
    border:1px solid #E6E9F0;
    border-radius:22px;
    padding:1rem 1.25rem 0.9rem;
    box-shadow:0 10px 30px rgba(17,24,39,0.03);
    margin-bottom:0.6rem;
    text-align:left;
}
.login-logo {
    height:74px;
    width:auto;
    display:block;
    margin:0 auto 0.5rem auto;
    object-fit:contain;
}
.login-title {
    font-size:1rem;
    font-weight:600;
    color:#1F2937;
    margin-bottom:0.1rem;
}
.login-subtitle {
    font-size:0.78rem;
    color:#7C869D;
    line-height:1.35;
}
.login-form-box {
    width:100%;
    background:#FFFFFF;
    border:1px solid #DCE2EB;
    border-radius:16px;
    padding:0.55rem 0.7rem 0.4rem;
}
.login-note {
    font-size:0.7rem;
    color:#8A93A8;
    margin-top:0.6rem;
    line-height:1.28;
}

/* INPUTS */
div[data-testid="stTextInput"] label {
    color:#4D576D !important;
    font-size:0.77rem !important;
    font-weight:500 !important;
}
div[data-testid="stTextInput"] input {
    background:#F8FAFC !important;
    border:1px solid #E5EAF2 !important;
    border-radius:12px !important;
    color:#1F2937 !important;
}
div[data-testid="stTextInput"] input::placeholder {
    color:#A0A8B9 !important;
}

/* BUTTONS */
div.stButton > button,
div[data-testid="stFormSubmitButton"] > button {
    background:#D9E9FF !important;
    color:#214D92 !important;
    border:1px solid #BDD6FF !important;
    border-radius:12px !important;
    min-height:40px !important;
    padding:0 1rem !important;
    font-size:0.77rem !important;
    font-weight:600 !important;
    box-shadow:none !important;
}
div.stButton > button:hover,
div[data-testid="stFormSubmitButton"] > button:hover {
    background:#D0E3FF !important;
    border-color:#AFCBFF !important;
    color:#183F7A !important;
}
div.stButton > button:disabled {
    color:#8AA2C7 !important;
    background:#EEF4FF !important;
    border-color:#D8E6FF !important;
}

/* ACTION CARD */
.action-card-wrap {
    max-width:560px;
    margin-bottom:0.8rem;
}
.action-card {
    background:#F5F2EC;
    border:1px solid #E5DED3;
    border-radius:22px;
    padding:0.95rem;
    box-shadow:0 6px 18px rgba(17,24,39,0.025);
}
.action-top {
    display:flex;
    align-items:flex-start;
    gap:0.78rem;
    margin-bottom:0.8rem;
}
.action-icon {
    width:38px;
    height:38px;
    border-radius:12px;
    background:#EEE8DE;
    border:1px solid #E0D7C7;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:1.05rem;
    flex-shrink:0;
}
.action-text {
    display:flex;
    flex-direction:column;
    gap:0.12rem;
    min-width:0;
}
.action-title {
    font-size:1.02rem;
    font-weight:600;
    color:#1F2937;
    line-height:1.08;
}
.action-desc {
    font-size:0.74rem;
    color:#7A808E;
    line-height:1.28;
}
.action-btn-wrap div.stButton {
    width:100% !important;
}
.action-btn-wrap div.stButton > button {
    width:100% !important;
    border-radius:14px !important;
    min-height:42px !important;
    font-size:0.79rem !important;
    justify-content:center !important;
}

/* PROCESS CARD */
.process-card {
    max-width:560px;
    background:#F8F9FC;
    border:1px solid #E3E7F0;
    border-radius:22px;
    padding:1rem 1rem 0.95rem;
    margin-top:0.2rem;
}
.process-head {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:0.8rem;
    margin-bottom:0.95rem;
}
.process-title {
    font-size:0.92rem;
    font-weight:700;
    color:#1F2937;
}
.process-badge {
    font-size:0.68rem;
    font-weight:700;
    color:#54627A;
    background:#EEF2F7;
    border:1px solid #DCE3EE;
    border-radius:999px;
    padding:0.28rem 0.58rem;
}
.timeline {
    display:flex;
    flex-direction:column;
    gap:0.9rem;
}
.timeline-item {
    position:relative;
    display:flex;
    gap:0.75rem;
}
.timeline-item:not(:last-child)::after {
    content:"";
    position:absolute;
    left:8px;
    top:22px;
    width:2px;
    height:calc(100% + 7px);
    background:#E1E6F0;
    border-radius:999px;
}
.timeline-dot {
    width:18px;
    height:18px;
    border-radius:999px;
    border:1px solid #D8DFEA;
    background:#FFFFFF;
    flex-shrink:0;
    margin-top:2px;
}
.timeline-content {
    min-width:0;
}
.timeline-name {
    font-size:0.79rem;
    font-weight:600;
    color:#354052;
    line-height:1.1;
}
.timeline-detail {
    font-size:0.71rem;
    color:#7C869D;
    margin-top:0.16rem;
    line-height:1.3;
}
.timeline-item.done .timeline-dot {
    background:#DDF5E7;
    border-color:#BFE4CE;
}
.timeline-item.active .timeline-dot {
    background:#D9E9FF;
    border-color:#BDD6FF;
    box-shadow:0 0 0 4px rgba(189,214,255,0.35);
}
.timeline-item.wait .timeline-dot {
    background:#FFFFFF;
    border-color:#DCE3EE;
}
.process-result {
    margin-top:0.95rem;
    padding:0.85rem 0.9rem;
    background:#FFFFFF;
    border:1px solid #E3E7F0;
    border-radius:16px;
}
.process-result-title {
    font-size:0.77rem;
    color:#1F2937;
    font-weight:600;
}
.process-result-text {
    font-size:0.71rem;
    color:#657087;
    margin-top:0.16rem;
    line-height:1.34;
}
.process-link {
    display:inline-flex;
    align-items:center;
    gap:0.35rem;
    margin-top:0.68rem;
    background:#D9E9FF;
    color:#214D92 !important;
    border:1px solid #BDD6FF;
    border-radius:12px;
    padding:0.42rem 0.82rem;
    font-size:0.72rem;
    font-weight:600;
    text-decoration:none;
}

/* HISTORY */
.history-row {
    display:flex;
    align-items:center;
    gap:0.78rem;
    padding:0.7rem 0.95rem;
    border-radius:16px;
    background:#FFFFFF;
    border:1px solid #E4E7EF;
    margin-bottom:0.42rem;
    max-width:560px;
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
    font-size:0.76rem;
    color:#394255;
    flex:1;
}
.history-time {
    font-size:0.68rem;
    color:#A2ABBD;
}
.history-link {
    font-size:0.71rem;
    color:#5D6880;
    text-decoration:none;
    font-weight:500;
}

/* FOOTER */
.portal-footer {
    padding:1rem 3rem;
    border-top:1px solid #E4E7EF;
    background:#FFFFFF;
    display:flex;
    justify-content:space-between;
    align-items:center;
}
.footer-text {
    font-size:0.71rem;
    color:#A2ABBD;
}

/* MOBILE */
@media (max-width: 768px) {
    .portal-header,
    .portal-footer,
    .main-content {
        padding-left:1rem;
        padding-right:1rem;
    }

    .login-page {
        padding:0.8rem 0.8rem;
        align-items:flex-start;
    }

    .login-shell {
        max-width:100%;
    }

    .login-head {
        padding:0.95rem 1rem 0.85rem;
        margin-bottom:0.45rem;
    }

    .login-logo {
        height:64px;
        margin-bottom:0.5rem;
    }

    .login-form-box {
        padding:0.55rem 0.65rem 0.35rem;
    }

    .action-card,
    .process-card {
        padding:0.82rem;
        border-radius:18px;
    }

    .action-title {
        font-size:0.95rem;
    }

    .action-desc {
        font-size:0.72rem;
    }
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
        <div class="login-subtitle">
            Entra con tu mail y la contraseña común.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-form-box">', unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Mail", placeholder="support@crucemundo.com")
        password = st.text_input("Contraseña", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            email_clean = email.strip().lower()

            if not email_clean or not password:
                st.error("Debes introducir mail y contraseña.")
            elif email_clean not in VALID_USERS:
                st.error("Usuario no autorizado.")
            elif password != VALID_PASSWORD:
                st.error("Contraseña incorrecta.")
            else:
                st.session_state["authenticated"] = True
                st.session_state["user_email"] = email_clean
                st.session_state["display_name"] = VALID_USERS[email_clean]
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("""
        <div class="login-note">
            El mail valida el acceso y el alias se usará para nombrar la sesión.
        </div>
    """, unsafe_allow_html=True)

    st.markdown('</div></div>', unsafe_allow_html=True)
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# APP
# ──────────────────────────────────────────────────────────────────────────────
USER_EMAIL = st.session_state.get("user_email", "").strip()
DISPLAY_USER = st.session_state.get("display_name", "").strip() or "Sin usuario"
SALUDO = get_saludo()

st.markdown(f"""
<div class="portal-header">
    <div class="portal-header-left">
        <img class="portal-logo" src="{LOGO_URL}" alt="Logo">
        <div>
            <div class="portal-title">{SALUDO}, {DISPLAY_USER}. ¿Qué hacemos hoy?</div>
            <div class="portal-subtitle">Herramientas y automatizaciones · Backend Google Drive</div>
        </div>
    </div>
    <div class="user-top">👤 {DISPLAY_USER}</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)
st.markdown('<div class="section-eyebrow">ACCIONES RÁPIDAS</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="user-pill">👤 {DISPLAY_USER} · {USER_EMAIL}</div>',
    unsafe_allow_html=True
)

now = datetime.now()
fecha_str = now.strftime("%Y%m%d_%H%M")
nombre_copia = f"SESION - {DISPLAY_USER} - MASTER - {fecha_str}"

copy_url = (
    f"https://docs.google.com/spreadsheets/d/{TEMPLATE_ID}/copy"
    f"?copyDestination={FOLDER_ID}"
    f"&title={urllib.parse.quote(nombre_copia)}"
)

confirm_state = st.session_state.get("confirm_state", "idle")

# ── TARJETA DE ACCIÓN
st.markdown('<div class="action-card-wrap">', unsafe_allow_html=True)
st.markdown(f"""
<div class="action-card">
    <div class="action-top">
        <div class="action-icon">📋</div>
        <div class="action-text">
            <div class="action-title">Nueva Confirmación ES</div>
            <div class="action-desc">Crear sesión MASTER de trabajo para {DISPLAY_USER}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="action-btn-wrap">', unsafe_allow_html=True)
button_disabled = confirm_state in ("step1", "step2", "step3")

if st.button("Crear", key="btn_crear", disabled=button_disabled, use_container_width=True):
    st.session_state["confirm_state"] = "step1"
    st.session_state["nombre_copia"] = nombre_copia
    st.session_state["copy_url"] = copy_url
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

saved_name = st.session_state.get("nombre_copia", "Pendiente")
saved_url = st.session_state.get("copy_url", "")
status_label, cls1, cls2, cls3, substatus = get_status_meta(confirm_state)

open_text = "Pendiente"
if confirm_state == "step3":
    open_text = "Preparando apertura"
elif confirm_state == "done":
    open_text = "Lista"

# ── PROCESO SIEMPRE VISIBLE
st.markdown(f"""
<div class="process-card">
    <div class="process-head">
        <div class="process-title">Proceso</div>
        <div class="process-badge">{status_label}</div>
    </div>

    <div class="timeline">
        <div class="timeline-item {cls1}">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
                <div class="timeline-name">Preparación</div>
                <div class="timeline-detail">Plantilla MASTER</div>
            </div>
        </div>

        <div class="timeline-item {cls2}">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
                <div class="timeline-name">Copia</div>
                <div class="timeline-detail">{saved_name if confirm_state != "idle" else "Pendiente"}</div>
            </div>
        </div>

        <div class="timeline-item {cls3}">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
                <div class="timeline-name">Apertura</div>
                <div class="timeline-detail">{open_text}</div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

if confirm_state == "done" and saved_url:
    st.markdown(f"""
    <div class="process-result">
        <div class="process-result-title">Sesión creada</div>
        <div class="process-result-text">
            La última sesión ya está preparada y puedes abrirla cuando quieras.
        </div>
        <a class="process-link" href="{saved_url}" target="_blank">Abrir sesión ↗</a>
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── AVANCE AUTOMÁTICO
if confirm_state == "step1":
    time.sleep(0.6)
    st.session_state["confirm_state"] = "step2"
    st.rerun()

elif confirm_state == "step2":
    time.sleep(0.6)
    st.session_state["confirm_state"] = "step3"
    st.rerun()

elif confirm_state == "step3":
    time.sleep(0.6)
    st.session_state["confirm_state"] = "done"

    existing = [h["nombre"] for h in st.session_state["historial"]]
    if saved_name not in existing:
        st.session_state["historial"].insert(0, {
            "nombre": st.session_state["nombre_copia"],
            "hora": datetime.now().strftime("%H:%M:%S"),
            "url": st.session_state["copy_url"],
        })

    st.rerun()

# ── BOTONES INFERIORES
st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
col_new, col_logout = st.columns([1, 1])

with col_new:
    if st.button("Nueva acción", key="btn_nueva_accion"):
        nueva_accion()

with col_logout:
    if st.button("Cerrar sesión", key="btn_logout"):
        do_logout()

# ── HISTORIAL
if st.session_state.get("historial"):
    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-eyebrow">ESTA SESIÓN</div>', unsafe_allow_html=True)

    for i, entry in enumerate(st.session_state["historial"], 1):
        st.markdown(f"""
        <div class="history-row">
            <div class="history-num">{i}</div>
            <div class="history-name">{entry['nombre']}</div>
            <div class="history-time">{entry['hora']}</div>
            <a class="history-link" href="{entry['url']}" target="_blank">Abrir ↗</a>
        </div>
        """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="portal-footer">
    <span class="footer-text">Panel de Control · v3.5.0</span>
    <span class="footer-text">Carpeta: {FOLDER_ID}</span>
</div>
""", unsafe_allow_html=True)
