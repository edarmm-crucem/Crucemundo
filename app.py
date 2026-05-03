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
    else:
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

def reset_new_session():
    st.session_state["confirm_state"] = "idle"
    if "nombre_copia" in st.session_state:
        del st.session_state["nombre_copia"]
    if "copy_url" in st.session_state:
        del st.session_state["copy_url"]
    st.rerun()

def render_step(label, detail, state):
    dot_class = {"done": "sd-done", "active": "sd-active", "wait": "sd-wait"}[state]
    text_class = {"done": "st-done", "active": "st-active", "wait": "st-wait"}[state]
    symbol = {"done": "✓", "active": "•", "wait": "•"}[state]

    st.markdown(f"""
    <div class="step">
        <div class="step-dot {dot_class}">{symbol}</div>
        <div>
            <div class="{text_class}">{label}</div>
            <div class="step-detail">{detail}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

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

[data-testid="stAppViewContainer"] { background:#F4F5F8; }
[data-testid="stHeader"] { background:transparent !important; }
section[data-testid="stSidebar"] { display:none !important; }

.block-container {
    padding:0 !important;
    max-width:100% !important;
}

/* HEADER */
.portal-header {
    background:#FFFFFF;
    border-bottom:1px solid #E6E8EF;
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
    height:42px;
    width:auto;
    object-fit:contain;
    display:block;
}
.portal-title {
    font-size:1rem;
    font-weight:600;
    color:#1D2433;
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
    padding:1.7rem 3rem 3rem;
}
.section-eyebrow {
    font-size:0.66rem;
    font-weight:600;
    letter-spacing:0.08em;
    text-transform:uppercase;
    color:#5D6B85;
    margin-bottom:0.22rem;
}
.section-heading {
    font-size:1rem;
    font-weight:600;
    color:#1D2433;
    margin-bottom:0.95rem;
}

/* LOGIN */
.login-wrap {
    display:flex;
    align-items:flex-start;
    justify-content:center;
    padding:1.4rem 2rem 2rem;
}
.login-card {
    width:100%;
    max-width:430px;
    background:#fff;
    border:1px solid #E5E8F0;
    border-radius:16px;
    padding:1.45rem 1.45rem 1.2rem;
    box-shadow:0 12px 30px rgba(17,24,39,0.04);
}
.login-logo {
    height:46px;
    width:auto;
    margin:0 auto 0.95rem auto;
    display:block;
}
.login-title {
    font-size:1.02rem;
    font-weight:600;
    color:#1D2433;
    margin-bottom:0.18rem;
}
.login-subtitle {
    font-size:0.79rem;
    color:#7C869D;
    margin-bottom:1rem;
    line-height:1.35;
}
.login-note {
    font-size:0.72rem;
    color:#8A93A8;
    margin-top:0.8rem;
}

/* PILL */
.user-pill {
    display:inline-flex;
    align-items:center;
    gap:0.4rem;
    margin:0.08rem 0 1rem;
    padding:0.38rem 0.68rem;
    border-radius:999px;
    background:#fff;
    border:1px solid #E4E7EF;
    font-size:0.73rem;
    color:#5D6880;
}

/* BLOQUE TARJETA + BOTÓN */
.session-row {
    max-width: 320px;
}
.session-card {
    width: 100%;
    max-width: 185px;  /* aquí cambias el ancho de la tarjeta */
    background:#FFFFFF;
    border:1px solid #E3E6EE;
    border-radius:12px;
    padding:0.45rem 0.52rem;
    display:flex;
    align-items:center;
    gap:0.45rem;
    min-height:50px;
}
.card-icon-wrap {
    width:28px;
    height:28px;
    flex-shrink:0;
    border-radius:8px;
    background:#F2F4F9;
    border:1px solid #E3E7F1;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:0.9rem;
}
.card-body {
    flex:1;
    min-width:0;
}
.card-name {
    font-size:0.8rem;
    font-weight:600;
    color:#1D2433;
    line-height:1.05;
}
.card-desc {
    font-size:0.68rem;
    color:#7C869D;
    margin-top:0.08rem;
    line-height:1.15;
}

/* BOTÓN CREAR */
.compact-btn {
    padding-top: 6px;
}
.compact-btn > div > button {
    background:#FFFFFF !important;
    color:#394255 !important;
    border:1px solid #DCE1EB !important;
    border-radius:10px !important;
    min-height:36px !important;
    height:36px !important;
    min-width:72px !important;
    padding:0 0.7rem !important;
    font-size:0.74rem !important;
    font-weight:500 !important;
    box-shadow:none !important;
    white-space:nowrap !important;
}
.compact-btn > div > button:hover,
.clean-btn > div > button:hover,
.logout-btn > div > button:hover,
div[data-testid="stFormSubmitButton"] > button:hover {
    background:#F7F8FB !important;
    border-color:#CDD4E2 !important;
}
.compact-btn > div > button:disabled {
    color:#AAB2C4 !important;
    background:#F7F8FB !important;
    border-color:#E3E7EF !important;
}
.clean-btn > div > button,
.logout-btn > div > button,
div[data-testid="stFormSubmitButton"] > button {
    background:#FFFFFF !important;
    color:#394255 !important;
    border:1px solid #DCE1EB !important;
    border-radius:10px !important;
    font-size:0.76rem !important;
    font-weight:500 !important;
    min-height:40px !important;
    padding:0 1rem !important;
    box-shadow:none !important;
}

/* PROCESO */
.progress-panel {
    max-width:560px;
    background:#FFFFFF;
    border:1px solid #E4E7EF;
    border-radius:14px;
    padding:1rem 1.05rem;
    margin-top:0.45rem;
}
.progress-title {
    font-size:0.84rem;
    font-weight:600;
    color:#1D2433;
    margin-bottom:0.35rem;
}
.progress-note {
    font-size:0.73rem;
    color:#7C869D;
    margin-bottom:0.9rem;
    line-height:1.35;
}
.step {
    display:flex;
    align-items:flex-start;
    gap:0.68rem;
    margin-bottom:0.62rem;
}
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
.sd-done {
    background:#EEF7F1;
    border:1px solid #D8ECDF;
    color:#2E7D58;
}
.sd-active {
    background:#F2F4F9;
    border:1px solid #DDE2EC;
    color:#6E778B;
}
.sd-wait {
    background:#F8F9FC;
    border:1px solid #E6E9F0;
    color:#B1B8C9;
}
.st-done, .st-active, .st-wait {
    font-size:0.76rem;
}
.st-done { color:#394255; }
.st-active { color:#1D2433; font-weight:600; }
.st-wait { color:#A2ABBD; }
.step-detail {
    font-size:0.69rem;
    color:#8790A4;
    margin-top:0.06rem;
}
.done-box {
    margin-top:0.95rem;
    padding:0.85rem 0.9rem;
    background:#F6F8FC;
    border:1px solid #E1E6F0;
    border-radius:10px;
}
.done-title {
    font-size:0.77rem;
    color:#1D2433;
    font-weight:600;
}
.done-text {
    font-size:0.71rem;
    color:#657087;
    margin-top:0.16rem;
    line-height:1.34;
}
.done-link {
    display:inline-flex;
    align-items:center;
    gap:0.35rem;
    margin-top:0.68rem;
    background:#FFFFFF;
    color:#394255 !important;
    border:1px solid #DCE1EB;
    border-radius:9px;
    padding:0.42rem 0.82rem;
    font-size:0.72rem;
    font-weight:500;
    text-decoration:none;
}

/* HISTORIAL */
.history-row {
    display:flex;
    align-items:center;
    gap:0.78rem;
    padding:0.64rem 0.95rem;
    border-radius:10px;
    background:#FFFFFF;
    border:1px solid #E4E7EF;
    margin-bottom:0.42rem;
    max-width:560px;
}
.history-num {
    width:20px;
    height:20px;
    border-radius:6px;
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
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# LOGIN
# ──────────────────────────────────────────────────────────────────────────────
if not st.session_state["authenticated"]:
    left, center, right = st.columns([1.15, 1, 1.15])

    with center:
        st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="login-card">
            <img class="login-logo" src="{LOGO_URL}" alt="Logo">
            <div class="login-title">Acceso</div>
            <div class="login-subtitle">
                Entra con tu mail y la contraseña común.
            </div>
        """, unsafe_allow_html=True)

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

        st.markdown("""
            <div class="login-note">
                El mail valida el acceso y el alias se usará para nombrar la sesión.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

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
st.markdown('<div class="section-eyebrow">Acciones</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Sesión de trabajo</div>', unsafe_allow_html=True)
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

st.markdown('<div class="session-row">', unsafe_allow_html=True)
col_card, col_btn = st.columns([2.4, 1], gap="small")

with col_card:
    st.markdown("""
    <div class="session-card">
        <div class="card-icon-wrap">📋</div>
        <div class="card-body">
            <div class="card-name">Nueva sesión</div>
            <div class="card-desc">Crear copia MASTER</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_btn:
    st.markdown('<div class="compact-btn">', unsafe_allow_html=True)
    if confirm_state == "idle":
        if st.button("Crear", key="btn_crear"):
            st.session_state["confirm_state"] = "step1"
            st.session_state["nombre_copia"] = nombre_copia
            st.session_state["copy_url"] = copy_url
            st.rerun()
    else:
        st.button("Crear", key="btn_crear_dis", disabled=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

saved_name = st.session_state.get("nombre_copia", nombre_copia)
saved_url = st.session_state.get("copy_url", copy_url)

if confirm_state in ("step1", "step2", "step3", "done"):
    st.markdown('<div class="progress-panel">', unsafe_allow_html=True)
    st.markdown('<div class="progress-title">Proceso</div>', unsafe_allow_html=True)

    if confirm_state == "step1":
        st.markdown('<div class="progress-note">Preparando la plantilla.</div>', unsafe_allow_html=True)
        render_step("Preparación", "Plantilla MASTER", "active")
        render_step("Copia", "Pendiente", "wait")
        render_step("Apertura", "Pendiente", "wait")

    elif confirm_state == "step2":
        st.markdown('<div class="progress-note">Generando copia en Drive.</div>', unsafe_allow_html=True)
        render_step("Preparación", "Correcto", "done")
        render_step("Copia", saved_name, "active")
        render_step("Apertura", "Pendiente", "wait")

    elif confirm_state == "step3":
        st.markdown('<div class="progress-note">Preparando la apertura.</div>', unsafe_allow_html=True)
        render_step("Preparación", "Correcto", "done")
        render_step("Copia", saved_name, "done")
        render_step("Apertura", "Listando acceso", "active")

    elif confirm_state == "done":
        st.markdown('<div class="progress-note">La sesión está preparada.</div>', unsafe_allow_html=True)
        render_step("Preparación", "Correcto", "done")
        render_step("Copia", saved_name, "done")
        render_step("Apertura", "Lista", "done")

        st.markdown(f"""
        <div class="done-box">
            <div class="done-title">Sesión creada</div>
            <div class="done-text">
                Si Drive no se abre automáticamente, usa este acceso.
            </div>
            <a class="done-link" href="{saved_url}" target="_blank">Abrir sesión ↗</a>
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
        if saved_name not in existing:
            st.session_state["historial"].insert(0, {
                "nombre": saved_name,
                "hora": datetime.now().strftime("%H:%M:%S"),
                "url": saved_url,
            })
        st.rerun()

    if confirm_state == "done" and not st.session_state.get("opened_" + saved_name):
        st.session_state["opened_" + saved_name] = True
        st.markdown(
            f'<script>setTimeout(()=>window.open("{saved_url}","_blank"),300);</script>',
            unsafe_allow_html=True
        )

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
col_reset, col_logout = st.columns([1, 1])

with col_reset:
    st.markdown('<div class="clean-btn">', unsafe_allow_html=True)
    if st.button("Nueva sesión", key="btn_reset"):
        reset_new_session()
    st.markdown('</div>', unsafe_allow_html=True)

with col_logout:
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("Cerrar sesión", key="btn_logout"):
        do_logout()
    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.get("historial"):
    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-eyebrow">Esta sesión</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Archivos creados</div>', unsafe_allow_html=True)

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
    <span class="footer-text">Panel de Control · v2.7.0</span>
    <span class="footer-text">Carpeta: {FOLDER_ID}</span>
</div>
""", unsafe_allow_html=True)
