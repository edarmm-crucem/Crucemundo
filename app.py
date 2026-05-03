import streamlit as st
from datetime import datetime
import urllib.parse
import time
import re

from google.oauth2 import service_account
from googleapiclient.discovery import build

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
    "open_salida_form": False,
    "salida_year": "",
    "salida_boat": "",
    "salida_name": "",
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
    st.session_state["session_type"] = ""
    st.session_state["open_salida_form"] = False
    st.session_state["salida_year"] = ""
    st.session_state["salida_boat"] = ""
    st.session_state["salida_name"] = ""
    for key in ["nombre_copia", "copy_url", "process_title"]:
        if key in st.session_state:
            del st.session_state[key]
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

# ──────────────────────────────────────────────────────────────────────────────
# GOOGLE DRIVE API
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_drive_service():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
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
            fields="nextPageToken, files(id, name, mimeType, webViewLink)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            pageToken=page_token,
            pageSize=1000
        ).execute()

        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken", None)
        if not page_token:
            break

    return results

@st.cache_data(ttl=300)
def get_years():
    folders = list_folder_items(DRIVE_ROOT_ID, folders_only=True)
    years = [f["name"].strip() for f in folders if re.fullmatch(r"\d{4}", f["name"].strip())]
    return sorted(years, reverse=True)

@st.cache_data(ttl=300)
def get_year_folder_id(year_name):
    folders = list_folder_items(DRIVE_ROOT_ID, folders_only=True)
    for f in folders:
        if f["name"].strip() == year_name:
            return f["id"]
    return None

@st.cache_data(ttl=300)
def get_boats(year_name):
    year_folder_id = get_year_folder_id(year_name)
    if not year_folder_id:
        return []

    boat_names = set()
    subfolders = list_folder_items(year_folder_id, folders_only=True)

    for sub in subfolders:
        files = list_folder_items(sub["id"], folders_only=False)
        for file in files:
            name = file["name"].strip()
            if "_" in name:
                parts = name.split("_")
                if len(parts) > 1:
                    boat = "_".join(parts[:-1]).strip()
                    if boat:
                        boat_names.add(boat)

    return sorted(boat_names)

@st.cache_data(ttl=300)
def get_departures(year_name, boat_name):
    year_folder_id = get_year_folder_id(year_name)
    if not year_folder_id:
        return []

    departures = []
    subfolders = list_folder_items(year_folder_id, folders_only=True)
    pattern = re.compile(rf"^{re.escape(boat_name)}_(\d{{6}})$")

    for sub in subfolders:
        files = list_folder_items(sub["id"], folders_only=False)
        for file in files:
            name = file["name"].strip()
            if pattern.match(name):
                departures.append({
                    "nombre": name,
                    "id": file["id"],
                    "url": file.get("webViewLink", f"https://docs.google.com/spreadsheets/d/{file['id']}/edit")
                })

    departures.sort(key=lambda x: x["nombre"])
    return departures

# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

* { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background:#FFFFFF !important;
}

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
    max-width:1100px !important;
    margin:0 auto !important;
}

.login-page {
    min-height:auto;
    display:flex;
    align-items:flex-start;
    justify-content:center;
    padding:0.2rem 1rem 1rem;
}
.login-shell {
    width:100%;
    max-width:390px;
    margin:0 auto;
}
.login-head {
    text-align:center;
    margin-bottom:0.55rem;
}
.login-logo {
    height:56px;
    width:auto;
    margin:0 auto 0.65rem auto;
    display:block;
}
.login-title {
    font-size:1.08rem;
    font-weight:700;
    color:#1F2937;
}
.login-subtitle {
    font-size:0.78rem;
    color:#7C869D;
    margin-top:0.28rem;
}
.login-form-box {
    background:transparent !important;
    border:none !important;
    padding:0 !important;
}
.login-note {
    margin-top:0.65rem;
    text-align:center;
    font-size:0.72rem;
    color:#8A93A5;
}

div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label {
    color:#4D576D !important;
    font-size:0.78rem !important;
    font-weight:500 !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background:#F8FAFC !important;
    border:1px solid #E5EAF2 !important;
    border-radius:12px !important;
    color:#1F2937 !important;
}

div.stButton {
    width:fit-content !important;
}
div.stButton > button,
div[data-testid="stFormSubmitButton"] > button,
.logout-btn > div > button {
    background:#D9E9FF !important;
    color:#214D92 !important;
    border:1px solid #BDD6FF !important;
    border-radius:12px !important;
    min-height:40px !important;
    padding:0 1rem !important;
    font-size:0.77rem !important;
    font-weight:600 !important;
    box-shadow:none !important;
    width:auto !important;
}
div.stButton > button:hover,
div[data-testid="stFormSubmitButton"] > button:hover,
.logout-btn > div > button:hover {
    background:#D0E3FF !important;
    border-color:#AFCBFF !important;
    color:#183F7A !important;
}

div.st-key-btn_crear_es button,
div.st-key-btn_crear_grupos button,
div.st-key-btn_ir_salida button,
div.st-key-btn_open_salida button {
    background:#FFFFFF !important;
    color:#214D92 !important;
    border:1px solid rgba(33,77,146,0.14) !important;
    border-radius:999px !important;
    min-height:38px !important;
    padding:0 1.15rem !important;
    font-size:0.76rem !important;
    font-weight:600 !important;
    box-shadow:none !important;
}
div.st-key-btn_crear_es button:hover,
div.st-key-btn_crear_grupos button:hover,
div.st-key-btn_ir_salida button:hover,
div.st-key-btn_open_salida button:hover {
    background:#F8FBFF !important;
    color:#163D78 !important;
    border-color:rgba(33,77,146,0.24) !important;
}

div.st-key-btn_crear_es_dis button,
div.st-key-btn_crear_grupos_dis button {
    border-radius:999px !important;
    background:#F4F6FA !important;
    color:#94A0B8 !important;
    border:1px solid #E0E6F0 !important;
}

.portal-header {
    padding:0.1rem 0 0.55rem 0;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:1rem;
    margin-bottom:0.55rem;
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
    font-size:0.96rem;
    font-weight:600;
    color:#1F2937;
    line-height:1.15;
}
.portal-subtitle {
    font-size:0.72rem;
    color:#7C869D;
    margin-top:0.08rem;
}
.user-top {
    font-size:0.72rem;
    color:#566079;
    white-space:nowrap;
}

.main-content { padding:0; }
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
    margin-bottom:0.75rem;
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
    min-height:176px;
    border-radius:22px;
    padding:1rem;
    margin-bottom:0.1rem;
    display:flex;
    flex-direction:column;
    justify-content:space-between;
    gap:0.9rem;
    border:1px solid transparent;
}
.card-es {
    background:#F3F7FF;
    border-color:#D9E5FF;
}
.card-grupos {
    background:#F4FBF6;
    border-color:#D8EEDC;
}
.card-salida {
    background:#FFF8F1;
    border-color:#F1DFC7;
}
.action-top {
    display:flex;
    align-items:flex-start;
    gap:0.75rem;
}
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
.card-es .action-icon {
    background:#E6EEFF;
    border:1px solid #D2DFFF;
}
.card-grupos .action-icon {
    background:#E7F5EA;
    border:1px solid #D0EAD7;
}
.card-salida .action-icon {
    background:#FFF0DD;
    border:1px solid #F2DEC0;
}
.action-text {
    display:flex;
    flex-direction:column;
    gap:0.18rem;
    min-width:0;
}
.action-title {
    font-size:0.95rem;
    font-weight:700;
    color:#1F2937;
    line-height:1.1;
}
.action-desc {
    font-size:0.73rem;
    color:#6F7B91;
    line-height:1.3;
}
.action-button-wrap {
    display:flex !important;
    justify-content:flex-start !important;
    align-items:center !important;
    width:100% !important;
    margin-top:0.1rem;
}

.selector-box {
    margin-top:1rem;
    width:100%;
    max-width:720px;
    padding:1rem;
    border-radius:18px;
    background:#FFFCF7;
    border:1px solid #F1E7D9;
}

.progress-panel {
    width:100%;
    max-width:520px;
    padding:0;
    margin-top:0.7rem;
    display:flex;
    flex-direction:column;
}
.progress-title {
    font-size:0.83rem;
    font-weight:600;
    color:#1F2937;
    margin-bottom:0.35rem;
}
.step {
    display:flex;
    align-items:flex-start;
    gap:0.65rem;
    margin-bottom:0.6rem;
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
.step-content {
    display:flex;
    flex-direction:column;
    min-width:0;
    flex:1;
}
.st-done, .st-active, .st-wait {
    font-size:0.76rem;
}
.st-done { color:#394255; }
.st-active { color:#1F2937; font-weight:600; }
.st-wait { color:#A2ABBD; }
.step-detail {
    font-size:0.7rem;
    color:#8790A4;
    margin-top:0.08rem;
}
.done-box {
    margin-top:0.8rem;
    padding:0 !important;
    background:transparent !important;
    border:none !important;
}
.done-title {
    font-size:0.76rem;
    color:#1F2937;
    font-weight:600;
}
.done-text {
    font-size:0.71rem;
    color:#657087;
    margin-top:0.15rem;
    line-height:1.3;
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
.history-time {
    font-size:0.68rem;
    color:#A2ABBD;
    white-space:nowrap;
}
.history-link {
    font-size:0.71rem;
    color:#5D6880;
    text-decoration:none;
    font-weight:500;
    white-space:nowrap;
}

.portal-footer {
    margin-top:1rem;
    padding:0.5rem 0 0 0;
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:0.8rem;
    flex-wrap:wrap;
}
.footer-text {
    font-size:0.71rem;
    color:#A2ABBD;
}

@media (max-width: 900px) {
    .portal-header {
        flex-direction:column;
        align-items:flex-start;
    }
    .portal-footer {
        flex-direction:column;
        align-items:flex-start;
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
            Introduce tu mail y la contraseña.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-form-box">', unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Mail", placeholder="support@crucemundo.com")
        password = st.text_input("Contraseña/Password", type="password", placeholder="••••••••")
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
confirm_state = st.session_state.get("confirm_state", "idle")

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

col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    st.markdown(f"""
    <div class="action-box card-es">
        <div class="action-top">
            <div class="action-icon">📋</div>
            <div class="action-text">
                <div class="action-title">Nueva Confirmación ES</div>
                <div class="action-desc">Crear sesión MASTER de trabajo para {DISPLAY_USER}</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)

    if confirm_state in ("idle", "done"):
        if st.button("Crear Sesión ES", key="btn_crear_es"):
            iniciar_proceso(
                session_type="es",
                template_id=TEMPLATE_ID_ES,
                prefix_name="MASTER",
                process_title="Estado del Proceso: Crear Sesión MASTER_CONFIRMATION"
            )
    else:
        st.button("Crear Sesión ES", key="btn_crear_es_dis", disabled=True)

    st.markdown('</div></div>', unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="action-box card-grupos">
        <div class="action-top">
            <div class="action-icon">👥</div>
            <div class="action-text">
                <div class="action-title">Nueva Confirmación GRUPOS</div>
                <div class="action-desc">Crear sesión MASTER GRUPOS de trabajo para {DISPLAY_USER}</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)

    if confirm_state in ("idle", "done"):
        if st.button("Crear Sesión GRUPOS", key="btn_crear_grupos"):
            iniciar_proceso(
                session_type="grupos",
                template_id=TEMPLATE_ID_GRUPOS,
                prefix_name="MASTER GRUPOS",
                process_title="Estado del Proceso: Crear Sesión MASTER_GRUPOS"
            )
    else:
        st.button("Crear Sesión GRUPOS", key="btn_crear_grupos_dis", disabled=True)

    st.markdown('</div></div>', unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="action-box card-salida">
        <div class="action-top">
            <div class="action-icon">🧭</div>
            <div class="action-text">
                <div class="action-title">Ir a Salida</div>
                <div class="action-desc">Buscar una salida existente por año, barco y código de salida</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)

    if st.button("Buscar Salida", key="btn_ir_salida"):
        st.session_state["open_salida_form"] = not st.session_state["open_salida_form"]
        st.rerun()

    st.markdown('</div></div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# DEBUG DE LA TARJETA IR A SALIDA
# ──────────────────────────────────────────────────────────────────────────────
if st.session_state.get("open_salida_form"):
    st.markdown('<div class="selector-box">', unsafe_allow_html=True)
    st.markdown("#### Seleccionar salida")

    try:
        years = get_years()
        st.write("Años encontrados:", years)
    except Exception as e:
        st.exception(e)

    st.markdown('</div>', unsafe_allow_html=True)

saved_name = st.session_state.get("nombre_copia", "")
saved_url = st.session_state.get("copy_url", "")
process_title = st.session_state.get("process_title", "Estado del Proceso")

if confirm_state in ("step1", "step2", "step3", "done"):
    st.markdown('<div class="progress-panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="progress-title">{process_title}</div>', unsafe_allow_html=True)

    if confirm_state == "step1":
        render_step("Progreso", "Preparando plantilla...", "active")
    elif confirm_state == "step2":
        render_step("Progreso", "Generando copia en Drive...", "active")
    elif confirm_state == "step3":
        render_step("Progreso", "Abriendo sesión...", "active")
    elif confirm_state == "done":
        render_step("Progreso", "Completo", "done")
        st.markdown(f"""
        <div class="done-box">
            <div class="done-title">Sesión creada</div>
            <div class="done-text">
                Puedes abrir tu sesión en el botón de abajo.
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
if st.button("Cerrar sesión", key="btn_logout"):
    do_logout()
st.markdown('</div>', unsafe_allow_html=True)

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
    <span class="footer-text">Panel de Control · v3.4.1 DEBUG</span>
    <span class="footer-text">Carpeta: {FOLDER_ID}</span>
</div>
""", unsafe_allow_html=True)
