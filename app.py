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
# SESSION
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
def do_logout():
    st.session_state["authenticated"] = False
    st.session_state["user_email"] = ""
    st.session_state["display_name"] = ""
    st.session_state["confirm_state"] = "idle"
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
    symbol = {"done": "✓", "active": "→", "wait": "•"}[state]

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
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&family=DM+Sans:wght@300;400;500&display=swap');

* { box-sizing: border-box; }

[data-testid="stAppViewContainer"] { background:#F5F6FA; }
[data-testid="stHeader"] { background:transparent !important; }
section[data-testid="stSidebar"] { display:none !important; }

.block-container {
    padding-top:0 !important;
    padding-bottom:0 !important;
    padding-left:0 !important;
    padding-right:0 !important;
    max-width:100% !important;
}

/* HEADER */
.portal-header {
    background:#fff;
    border-bottom:1px solid #E4E7EF;
    padding:0.85rem 2.2rem;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:1rem;
}
.portal-header-left {
    display:flex;
    align-items:center;
    gap:0.85rem;
}
.portal-logo {
    height:36px;
    width:auto;
    object-fit:contain;
}
.portal-title {
    font-family:'Sora',sans-serif;
    font-size:0.96rem;
    font-weight:600;
    color:#1A1F36;
}
.portal-subtitle {
    font-family:'DM Sans',sans-serif;
    font-size:0.67rem;
    color:#8C93A8;
    margin-top:0.02rem;
}
.user-top {
    font-family:'DM Sans',sans-serif;
    font-size:0.67rem;
    color:#5B6785;
    background:#F7F8FC;
    border:1px solid #E4E7EF;
    border-radius:999px;
    padding:0.36rem 0.68rem;
}

/* MAIN */
.main-content {
    padding:1rem 2.2rem 2rem;
}
.section-eyebrow {
    font-family:'Sora',sans-serif;
    font-size:0.56rem;
    font-weight:600;
    letter-spacing:0.11em;
    text-transform:uppercase;
    color:#5B6BF8;
    margin-bottom:0.2rem;
}
.section-heading {
    font-family:'Sora',sans-serif;
    font-size:0.88rem;
    font-weight:600;
    color:#1A1F36;
    margin-bottom:0.7rem;
}

/* LOGIN ARRIBA */
.login-wrap {
    display:flex;
    align-items:flex-start;
    justify-content:center;
    padding:0.8rem 1.2rem 1.4rem;
}
.login-card {
    width:100%;
    max-width:350px;
    background:#fff;
    border:1px solid #E4E7EF;
    border-radius:14px;
    padding:0.95rem 0.95rem 0.85rem;
    box-shadow:0 10px 30px rgba(16,24,40,0.05);
}
.login-logo {
    height:34px;
    width:auto;
    margin-bottom:0.55rem;
}
.login-title {
    font-family:'Sora',sans-serif;
    font-size:0.9rem;
    font-weight:600;
    color:#1A1F36;
    margin-bottom:0.12rem;
}
.login-subtitle {
    font-family:'DM Sans',sans-serif;
    font-size:0.7rem;
    color:#8C93A8;
    margin-bottom:0.65rem;
    line-height:1.3;
}
.login-note {
    font-family:'DM Sans',sans-serif;
    font-size:0.64rem;
    color:#8C93A8;
    margin-top:0.55rem;
}

/* TARJETA MUCHO MÁS CORTA */
.card-row-wrap {
    max-width:280px;
    margin-bottom:0.28rem;
}
.tool-card-compact {
    width:100%;
    background:#fff;
    border:1px solid #E4E7EF;
    border-radius:10px;
    padding:0.34rem 0.46rem;
    display:flex;
    align-items:center;
    gap:0.4rem;
    min-height:42px;
}
.tool-card-soon {
    max-width:250px;
    background:#fff;
    border:1px solid #E4E7EF;
    border-radius:10px;
    padding:0.34rem 0.46rem;
    display:flex;
    align-items:center;
    gap:0.4rem;
    min-height:42px;
    margin-bottom:0.25rem;
    opacity:0.45;
}
.card-icon-wrap {
    width:22px;
    height:22px;
    flex-shrink:0;
    border-radius:6px;
    background:#EEF0FD;
    border:1px solid #D4D8FB;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:0.7rem;
}
.card-body {
    flex:1;
    min-width:0;
}
.card-name {
    font-family:'Sora',sans-serif;
    font-size:0.62rem;
    font-weight:600;
    color:#1A1F36;
    line-height:1.05;
}
.card-desc {
    font-family:'DM Sans',sans-serif;
    font-size:0.55rem;
    color:#8C93A8;
    margin-top:0.02rem;
    line-height:1.05;
}
.badge-active, .badge-soon {
    font-family:'DM Sans',sans-serif;
    font-size:0.39rem;
    font-weight:500;
    padding:0.05rem 0.18rem;
    border-radius:999px;
    text-transform:uppercase;
    letter-spacing:0.03em;
    white-space:nowrap;
}
.badge-active {
    background:#E8FAF2;
    color:#18835A;
    border:1px solid #B6E8D3;
}
.badge-soon {
    background:#F3F4F8;
    color:#8C93A8;
    border:1px solid #DDE0EA;
}

/* BOTONES */
.compact-btn > div > button {
    background:#FFFFFF !important;
    color:#2B3147 !important;
    border:1px solid #D9DDEA !important;
    border-radius:9px !important;
    min-height:42px !important;
    height:42px !important;
    min-width:54px !important;
    padding:0 0.42rem !important;
    font-family:'DM Sans',sans-serif !important;
    font-size:0.6rem !important;
    font-weight:500 !important;
    box-shadow:none !important;
    white-space:nowrap !important;
}
.compact-btn > div > button:hover,
.clean-btn > div > button:hover,
.logout-btn > div > button:hover,
div[data-testid="stFormSubmitButton"] > button:hover {
    background:#F7F8FC !important;
    border-color:#C9D0E3 !important;
}
.compact-btn > div > button:disabled {
    color:#A7AEC3 !important;
    background:#F7F8FC !important;
    border-color:#E1E5EF !important;
}
.clean-btn > div > button,
.logout-btn > div > button,
div[data-testid="stFormSubmitButton"] > button {
    background:#fff !important;
    color:#2B3147 !important;
    border:1px solid #D9DDEA !important;
    border-radius:9px !important;
    font-family:'DM Sans',sans-serif !important;
    font-size:0.72rem !important;
    font-weight:500 !important;
    min-height:36px !important;
    padding:0 0.9rem !important;
    box-shadow:none !important;
}

/* USER */
.user-pill {
    display:inline-flex;
    align-items:center;
    gap:0.4rem;
    margin:0.05rem 0 0.7rem;
    padding:0.32rem 0.58rem;
    border-radius:999px;
    background:#fff;
    border:1px solid #E4E7EF;
    font-family:'DM Sans',sans-serif;
    font-size:0.64rem;
    color:#5B6785;
}

/* PROCESS */
.progress-panel {
    max-width:560px;
    background:#fff;
    border:1px solid #E4E7EF;
    border-radius:12px;
    padding:0.9rem 1rem;
    margin-top:0.45rem;
}
.progress-title {
    font-family:'Sora',sans-serif;
    font-size:0.77rem;
    font-weight:600;
    color:#1A1F36;
    margin-bottom:0.38rem;
}
.progress-note {
    font-family:'DM Sans',sans-serif;
    font-size:0.68rem;
    color:#8C93A8;
    margin-bottom:0.78rem;
    line-height:1.3;
}
.step {
    display:flex;
    align-items:flex-start;
    gap:0.6rem;
    margin-bottom:0.52rem;
}
.step:last-child { margin-bottom:0; }
.step-dot {
    width:18px;
    height:18px;
    border-radius:50%;
    flex-shrink:0;
    margin-top:0.03rem;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:0.58rem;
    font-weight:700;
}
.sd-done {
    background:#E8FAF2;
    border:1px solid #B6E8D3;
    color:#18835A;
}
.sd-active {
    background:#EEF0FD;
    border:1px solid #C5CAF8;
    color:#5B6BF8;
}
.sd-wait {
    background:#F5F6FA;
    border:1px solid #DDE0EA;
    color:#B0B6CC;
}
.st-done, .st-active, .st-wait {
    font-family:'DM Sans',sans-serif;
    font-size:0.72rem;
}
.st-done { color:#3D4468; }
.st-active { color:#1A1F36; font-weight:500; }
.st-wait { color:#B0B6CC; }
.step-detail {
    font-family:'DM Sans',sans-serif;
    font-size:0.64rem;
    color:#8C93A8;
    font-style:italic;
    margin-top:0.04rem;
}
.done-box {
    margin-top:0.82rem;
    padding:0.76rem 0.82rem;
    background:#EEF4FF;
    border:1px solid #D8E4FF;
    border-radius:8px;
}
.done-title {
    font-family:'DM Sans',sans-serif;
    font-size:0.73rem;
    color:#2B4EA2;
    font-weight:500;
}
.done-text {
    font-family:'DM Sans',sans-serif;
    font-size:0.68rem;
    color:#5B6785;
    margin-top:0.14rem;
    line-height:1.28;
}
.done-link {
    display:inline-flex;
    align-items:center;
    gap:0.4rem;
    margin-top:0.62rem;
    background:#5B6BF8;
    color:#fff !important;
    border:none;
    border-radius:8px;
    padding:0.42rem 0.82rem;
    font-family:'DM Sans',sans-serif;
    font-size:0.7rem;
    font-weight:500;
    text-decoration:none;
}

/* HISTORY */
.history-row {
    display:flex;
    align-items:center;
    gap:0.72rem;
    padding:0.55rem 0.85rem;
    border-radius:8px;
    background:#fff;
    border:1px solid #E4E7EF;
    margin-bottom:0.35rem;
    max-width:560px;
}
.history-num {
    width:18px;
    height:18px;
    border-radius:5px;
    background:#EEF0FD;
    border:1px solid #D4D8FB;
    display:flex;
    align-items:center;
    justify-content:center;
    font-family:'Sora',sans-serif;
    font-size:0.55rem;
    font-weight:600;
    color:#5B6BF8;
    flex-shrink:0;
}
.history-name {
    font-family:'DM Sans',sans-serif;
    font-size:0.72rem;
    color:#3D4468;
    flex:1;
}
.history-time {
    font-family:'DM Sans',sans-serif;
    font-size:0.64rem;
    color:#B0B6CC;
}
.history-link {
    font-family:'DM Sans',sans-serif;
    font-size:0.67rem;
    color:#5B6BF8;
    text-decoration:none;
    font-weight:500;
}

/* FOOTER */
.portal-footer {
    padding:0.8rem 2.2rem;
    border-top:1px solid #E4E7EF;
    background:#fff;
    display:flex;
    justify-content:space-between;
    align-items:center;
}
.footer-text {
    font-family:'DM Sans',sans-serif;
    font-size:0.66rem;
    color:#B0B6CC;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# LOGIN
# ──────────────────────────────────────────────────────────────────────────────
if not st.session_state["authenticated"]:
    left, center, right = st.columns([1.25, 1, 1.25])

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

st.markdown(f"""
<div class="portal-header">
    <div class="portal-header-left">
        <img class="portal-logo" src="{LOGO_URL}" alt="Logo">
        <div>
            <div class="portal-title">Panel de Control</div>
            <div class="portal-subtitle">Herramientas y automatizaciones · Backend Google Drive</div>
        </div>
    </div>
    <div class="user-top">👤 {DISPLAY_USER}</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)
st.markdown('<div class="section-eyebrow">⚡ Acciones rápidas</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Herramientas disponibles</div>', unsafe_allow_html=True)
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

TOOLS = [
    {"id": "confirmacion_es", "icon": "📋", "name": "Sesión", "desc": "Crear copia", "active": True},
    {"id": "soon_1", "icon": "📊", "name": "Próx.", "desc": "Nueva", "active": False},
    {"id": "soon_2", "icon": "📁", "name": "Próx.", "desc": "Nueva", "active": False},
]

confirm_state = st.session_state.get("confirm_state", "idle")

for tool in TOOLS:
    if tool["active"]:
        st.markdown('<div class="card-row-wrap">', unsafe_allow_html=True)
        col_card, col_btn = st.columns([3.0, 0.8], gap="small")

        with col_card:
            st.markdown(f"""
            <div class="tool-card-compact">
                <div class="card-icon-wrap">{tool['icon']}</div>
                <div class="card-body">
                    <div class="card-name">{tool['name']}</div>
                    <div class="card-desc">{tool['desc']}</div>
                </div>
                <span class="badge-active">On</span>
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

    else:
        st.markdown(f"""
        <div class="tool-card-soon">
            <div class="card-icon-wrap">{tool['icon']}</div>
            <div class="card-body">
                <div class="card-name">{tool['name']}</div>
                <div class="card-desc">{tool['desc']}</div>
            </div>
            <span class="badge-soon">Off</span>
        </div>
        """, unsafe_allow_html=True)

saved_name = st.session_state.get("nombre_copia", nombre_copia)
saved_url  = st.session_state.get("copy_url", copy_url)

if confirm_state in ("step1", "step2", "step3", "done"):
    st.markdown('<div class="progress-panel">', unsafe_allow_html=True)
    st.markdown('<div class="progress-title">⚙️ Proceso</div>', unsafe_allow_html=True)

    if confirm_state == "step1":
        st.markdown('<div class="progress-note">Preparando la sesión de trabajo.</div>', unsafe_allow_html=True)
        render_step("Preparando", "Plantilla MASTER", "active")
        render_step("Creando copia", "Pendiente", "wait")
        render_step("Sesión lista", "Pendiente", "wait")

    elif confirm_state == "step2":
        st.markdown('<div class="progress-note">Google Drive está generando la copia.</div>', unsafe_allow_html=True)
        render_step("Preparando", "Plantilla localizada", "done")
        render_step("Creando copia", saved_name, "active")
        render_step("Sesión lista", "Pendiente", "wait")

    elif confirm_state == "step3":
        st.markdown('<div class="progress-note">Preparando la apertura en Drive.</div>', unsafe_allow_html=True)
        render_step("Preparando", "Plantilla localizada", "done")
        render_step("Creando copia", saved_name, "done")
        render_step("Sesión lista", "Preparando apertura", "active")

    elif confirm_state == "done":
        st.markdown('<div class="progress-note">La sesión ya está preparada.</div>', unsafe_allow_html=True)
        render_step("Preparando", "Plantilla localizada", "done")
        render_step("Creando copia", saved_name, "done")
        render_step("Sesión lista", "Copia preparada", "done")

        st.markdown(f"""
        <div class="done-box">
            <div class="done-title">Sesión creada</div>
            <div class="done-text">
                Drive mostrará su ventana de confirmación de copia.
                Si no se abre sola, pulsa el botón.
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

st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
c1, c2 = st.columns([1, 1])

with c1:
    st.markdown('<div class="clean-btn">', unsafe_allow_html=True)
    if st.button("Nueva sesión", key="btn_reset", on_click=reset_new_session):
        pass
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
    if st.button("Cerrar sesión", key="btn_logout", on_click=do_logout):
        pass
    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.get("historial"):
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-eyebrow">🕐 Esta sesión</div>', unsafe_allow_html=True)
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
    <span class="footer-text">Panel de Control · v2.1.0</span>
    <span class="footer-text">Carpeta: {FOLDER_ID}</span>
</div>
""", unsafe_allow_html=True)
