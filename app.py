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

# Usuario real de sesión
USER_NAME = st.session_state.get("google_user", "").strip()

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
.block-container { padding:0 !important; max-width:100% !important; }

/* HEADER */
.portal-header {
    background:#fff;
    border-bottom:1px solid #E4E7EF;
    padding:1.05rem 3rem;
    display:flex;
    align-items:center;
    gap:1.1rem;
}
.portal-logo {
    height:44px;
    width:auto;
    object-fit:contain;
}
.portal-title {
    font-family:'Sora',sans-serif;
    font-size:1.12rem;
    font-weight:600;
    color:#1A1F36;
}
.portal-subtitle {
    font-family:'DM Sans',sans-serif;
    font-size:0.75rem;
    color:#8C93A8;
    margin-top:0.08rem;
}

.main-content {
    padding:2rem 3rem 3rem;
}
.section-eyebrow {
    font-family:'Sora',sans-serif;
    font-size:0.62rem;
    font-weight:600;
    letter-spacing:0.12em;
    text-transform:uppercase;
    color:#5B6BF8;
    margin-bottom:0.3rem;
}
.section-heading {
    font-family:'Sora',sans-serif;
    font-size:1.03rem;
    font-weight:600;
    color:#1A1F36;
    margin-bottom:1rem;
}

/* TARJETA MUCHO MÁS ESTRECHA */
.card-row-wrap {
    max-width:330px;
    margin-bottom:0.65rem;
}
.tool-card-compact {
    background:#fff;
    border:1.5px solid #E4E7EF;
    border-radius:12px;
    padding:0.68rem 0.78rem;
    display:flex;
    align-items:center;
    gap:0.65rem;
    min-height:62px;
}
.tool-card-soon {
    max-width:290px;
    background:#fff;
    border:1.5px solid #E4E7EF;
    border-radius:12px;
    padding:0.68rem 0.78rem;
    display:flex;
    align-items:center;
    gap:0.65rem;
    min-height:62px;
    margin-bottom:0.45rem;
    opacity:0.45;
}
.card-icon-wrap {
    width:31px;
    height:31px;
    flex-shrink:0;
    border-radius:8px;
    background:#EEF0FD;
    border:1px solid #D4D8FB;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:0.96rem;
}
.card-body {
    flex:1;
    min-width:0;
}
.card-name {
    font-family:'Sora',sans-serif;
    font-size:0.77rem;
    font-weight:600;
    color:#1A1F36;
    line-height:1.18;
}
.card-desc {
    font-family:'DM Sans',sans-serif;
    font-size:0.68rem;
    color:#8C93A8;
    margin-top:0.08rem;
    line-height:1.25;
}
.badge-active, .badge-soon {
    font-family:'DM Sans',sans-serif;
    font-size:0.52rem;
    font-weight:500;
    padding:0.10rem 0.36rem;
    border-radius:999px;
    text-transform:uppercase;
    letter-spacing:0.05em;
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

/* BOTÓN AL LADO, CERCA */
.compact-btn {
    margin-top:0;
}
.compact-btn > div > button {
    background:#FFFFFF !important;
    color:#2B3147 !important;
    border:1.5px solid #D9DDEA !important;
    border-radius:10px !important;
    min-height:62px !important;
    height:62px !important;
    min-width:72px !important;
    padding:0 0.72rem !important;
    font-family:'DM Sans',sans-serif !important;
    font-size:0.72rem !important;
    font-weight:500 !important;
    box-shadow:none !important;
    white-space:nowrap !important;
}
.compact-btn > div > button:hover {
    background:#F7F8FC !important;
    border-color:#C9D0E3 !important;
}
.compact-btn > div > button:disabled {
    color:#A7AEC3 !important;
    background:#F7F8FC !important;
    border-color:#E1E5EF !important;
}

/* PANEL DE PROCESO */
.progress-panel {
    max-width:560px;
    background:#fff;
    border:1.5px solid #E4E7EF;
    border-radius:12px;
    padding:1.08rem 1.2rem;
    margin-top:0.55rem;
}
.progress-title {
    font-family:'Sora',sans-serif;
    font-size:0.82rem;
    font-weight:600;
    color:#1A1F36;
    margin-bottom:0.5rem;
}
.progress-note {
    font-family:'DM Sans',sans-serif;
    font-size:0.72rem;
    color:#8C93A8;
    margin-bottom:0.95rem;
    line-height:1.35;
}
.step {
    display:flex;
    align-items:flex-start;
    gap:0.7rem;
    margin-bottom:0.62rem;
}
.step:last-child {
    margin-bottom:0;
}
.step-dot {
    width:20px;
    height:20px;
    border-radius:50%;
    flex-shrink:0;
    margin-top:0.05rem;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:0.62rem;
    font-weight:700;
}
.sd-done {
    background:#E8FAF2;
    border:1.5px solid #B6E8D3;
    color:#18835A;
}
.sd-active {
    background:#EEF0FD;
    border:1.5px solid #C5CAF8;
    color:#5B6BF8;
}
.sd-wait {
    background:#F5F6FA;
    border:1.5px solid #DDE0EA;
    color:#B0B6CC;
}
.st-done {
    font-family:'DM Sans',sans-serif;
    font-size:0.77rem;
    color:#3D4468;
}
.st-active {
    font-family:'DM Sans',sans-serif;
    font-size:0.77rem;
    color:#1A1F36;
    font-weight:500;
}
.st-wait {
    font-family:'DM Sans',sans-serif;
    font-size:0.77rem;
    color:#B0B6CC;
}
.step-detail {
    font-family:'DM Sans',sans-serif;
    font-size:0.68rem;
    color:#8C93A8;
    font-style:italic;
    margin-top:0.05rem;
}

/* CAJA FINAL */
.done-box {
    margin-top:1rem;
    padding:0.85rem 0.9rem;
    background:#EEF4FF;
    border:1px solid #D8E4FF;
    border-radius:8px;
}
.done-title {
    font-family:'DM Sans',sans-serif;
    font-size:0.77rem;
    color:#2B4EA2;
    font-weight:500;
}
.done-text {
    font-family:'DM Sans',sans-serif;
    font-size:0.72rem;
    color:#5B6785;
    margin-top:0.18rem;
    line-height:1.35;
}
.done-link {
    display:inline-flex;
    align-items:center;
    gap:0.4rem;
    margin-top:0.75rem;
    background:#5B6BF8;
    color:#fff !important;
    border:none;
    border-radius:8px;
    padding:0.48rem 1rem;
    font-family:'DM Sans',sans-serif;
    font-size:0.75rem;
    font-weight:500;
    text-decoration:none;
}

/* BOTÓN RESET */
.clean-btn > div > button {
    background:#fff !important;
    color:#2B3147 !important;
    border:1.5px solid #D9DDEA !important;
    border-radius:10px !important;
    font-family:'DM Sans',sans-serif !important;
    font-size:0.78rem !important;
    font-weight:500 !important;
    min-height:40px !important;
    padding:0 1rem !important;
    box-shadow:none !important;
}
.clean-btn > div > button:hover {
    background:#F7F8FC !important;
    border-color:#C9D0E3 !important;
}

/* HISTORIAL */
.history-row {
    display:flex;
    align-items:center;
    gap:0.8rem;
    padding:0.62rem 1rem;
    border-radius:8px;
    background:#fff;
    border:1px solid #E4E7EF;
    margin-bottom:0.4rem;
    max-width:560px;
}
.history-num {
    width:20px;
    height:20px;
    border-radius:5px;
    background:#EEF0FD;
    border:1px solid #D4D8FB;
    display:flex;
    align-items:center;
    justify-content:center;
    font-family:'Sora',sans-serif;
    font-size:0.6rem;
    font-weight:600;
    color:#5B6BF8;
    flex-shrink:0;
}
.history-name {
    font-family:'DM Sans',sans-serif;
    font-size:0.76rem;
    color:#3D4468;
    flex:1;
}
.history-time {
    font-family:'DM Sans',sans-serif;
    font-size:0.68rem;
    color:#B0B6CC;
}
.history-link {
    font-family:'DM Sans',sans-serif;
    font-size:0.7rem;
    color:#5B6BF8;
    text-decoration:none;
    font-weight:500;
}

/* FOOTER */
.portal-footer {
    padding:1rem 3rem;
    border-top:1px solid #E4E7EF;
    background:#fff;
    display:flex;
    justify-content:space-between;
    align-items:center;
}
.footer-text {
    font-family:'DM Sans',sans-serif;
    font-size:0.7rem;
    color:#B0B6CC;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="portal-header">
    <img class="portal-logo" src="{LOGO_URL}" alt="Logo">
    <div>
        <div class="portal-title">Panel de Control</div>
        <div class="portal-subtitle">Herramientas y automatizaciones · Backend Google Drive</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-content">', unsafe_allow_html=True)
st.markdown('<div class="section-eyebrow">⚡ Acciones rápidas</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Herramientas disponibles</div>', unsafe_allow_html=True)

# Nombre del archivo
now = datetime.now()
fecha_str = now.strftime("%Y%m%d_%H%M")

if USER_NAME:
    nombre_copia = f"SESION - {USER_NAME} - MASTER - {fecha_str}"
else:
    nombre_copia = f"SESION - MASTER - {fecha_str}"

copy_url = (
    f"https://docs.google.com/spreadsheets/d/{TEMPLATE_ID}/copy"
    f"?title={urllib.parse.quote(nombre_copia)}"
    f"&parents={FOLDER_ID}"
)

TOOLS = [
    {
        "id": "confirmacion_es",
        "icon": "📋",
        "name": "Crear nueva confirmación ES",
        "desc": "Crea tu sesion de trabajo",
        "active": True
    },
    {
        "id": "soon_1",
        "icon": "📊",
        "name": "Próximamente",
        "desc": "Nueva herramienta",
        "active": False
    },
    {
        "id": "soon_2",
        "icon": "📁",
        "name": "Próximamente",
        "desc": "Nueva herramienta",
        "active": False
    },
]

confirm_state = st.session_state.get("confirm_state", "idle")

# ──────────────────────────────────────────────────────────────────────────────
# TARJETAS
# ──────────────────────────────────────────────────────────────────────────────
for tool in TOOLS:
    if tool["active"]:
        st.markdown('<div class="card-row-wrap">', unsafe_allow_html=True)
        col_card, col_btn = st.columns([4.9, 1.1], gap="small")

        with col_card:
            st.markdown(f"""
            <div class="tool-card-compact">
                <div class="card-icon-wrap">{tool['icon']}</div>
                <div class="card-body">
                    <div class="card-name">{tool['name']}</div>
                    <div class="card-desc">{tool['desc']}</div>
                </div>
                <span class="badge-active">Activo</span>
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
            <span class="badge-soon">Próximo</span>
        </div>
        """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# PROCESO
# ──────────────────────────────────────────────────────────────────────────────
saved_name = st.session_state.get("nombre_copia", nombre_copia)
saved_url  = st.session_state.get("copy_url", copy_url)

if confirm_state in ("step1", "step2", "step3", "done"):
    step_map = {"step1": 0, "step2": 1, "step3": 2, "done": 3}
    cur = step_map[confirm_state]

    def dot(i):
        if i < cur:
            return '<div class="step-dot sd-done">✓</div>'
        if i == cur:
            return '<div class="step-dot sd-active">→</div>'
        return f'<div class="step-dot sd-wait">{i+1}</div>'

    def txt(i):
        if i < cur:
            return "st-done"
        if i == cur:
            return "st-active"
        return "st-wait"

    # Textos que cambian de verdad en cada fase
    if confirm_state == "step1":
        steps = [
            ("Preparando sesión", "Iniciando la plantilla MASTER"),
            ("Creando copia", "Pendiente"),
            ("Sesión lista", "Pendiente"),
        ]
        panel_note = "Estamos creando la sesión de trabajo automáticamente."
    elif confirm_state == "step2":
        steps = [
            ("Preparando sesión", "Plantilla MASTER localizada"),
            ("Creando copia", saved_name),
            ("Sesión lista", "Pendiente"),
        ]
        panel_note = "La copia se está generando en tu carpeta de trabajo."
    elif confirm_state == "step3":
        steps = [
            ("Preparando sesión", "Plantilla MASTER localizada"),
            ("Creando copia", saved_name),
            ("Sesión lista", "Preparando apertura"),
        ]
        panel_note = "La sesión ya casi está lista. En breve podrás abrirla."
    else:
        steps = [
            ("Preparando sesión", "Plantilla MASTER localizada"),
            ("Creando copia", saved_name),
            ("Sesión lista", "Copia preparada correctamente"),
        ]
        panel_note = "La sesión se ha creado correctamente."

    html = '<div class="progress-panel">'
    html += '<div class="progress-title">⚙️ Proceso</div>'
    html += f'<div class="progress-note">{panel_note}</div>'

    for i, (label, detail) in enumerate(steps):
        html += f'''
        <div class="step">
            {dot(i)}
            <div>
                <div class="{txt(i)}">{label}</div>
                <div class="step-detail">{detail}</div>
            </div>
        </div>
        '''

    if confirm_state == "done":
        html += f'''
        <div class="done-box">
            <div class="done-title">Sesión creada</div>
            <div class="done-text">La copia está preparada. Si no se abre sola, pulsa para abrir tu sesión de trabajo.</div>
            <a class="done-link" href="{saved_url}" target="_blank">Abrir sesión ↗</a>
        </div>
        '''

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    # Flujo automático por fases
    if confirm_state == "step1":
        time.sleep(0.9)
        st.session_state["confirm_state"] = "step2"
        st.rerun()

    elif confirm_state == "step2":
        time.sleep(0.9)
        st.session_state["confirm_state"] = "step3"
        st.rerun()

    elif confirm_state == "step3":
        time.sleep(0.9)
        st.session_state["confirm_state"] = "done"

        if "historial" not in st.session_state:
            st.session_state.historial = []

        existing = [h["nombre"] for h in st.session_state.historial]
        if saved_name not in existing:
            st.session_state.historial.insert(0, {
                "nombre": saved_name,
                "hora": datetime.now().strftime("%H:%M:%S"),
                "url": saved_url,
            })

        st.rerun()

    # Intento de apertura automática
    if confirm_state == "done" and not st.session_state.get("opened_" + saved_name):
        st.session_state["opened_" + saved_name] = True
        st.markdown(
            f'<script>setTimeout(()=>window.open("{saved_url}","_blank"),300);</script>',
            unsafe_allow_html=True
        )

    # Reset
    if confirm_state == "done":
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="clean-btn">', unsafe_allow_html=True)
        if st.button("↩ Nueva sesión", key="btn_reset"):
            st.session_state["confirm_state"] = "idle"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# HISTORIAL
# ──────────────────────────────────────────────────────────────────────────────
if st.session_state.get("historial"):
    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-eyebrow">🕐 Esta sesión</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Archivos creados</div>', unsafe_allow_html=True)

    for i, entry in enumerate(st.session_state.historial, 1):
        st.markdown(f"""
        <div class="history-row">
            <div class="history-num">{i}</div>
            <div class="history-name">{entry['nombre']}</div>
            <div class="history-time">{entry['hora']}</div>
            <a class="history-link" href="{entry['url']}" target="_blank">Abrir ↗</a>
        </div>
        """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="portal-footer">
    <span class="footer-text">Panel de Control · v1.6.0</span>
    <span class="footer-text">Carpeta: {FOLDER_ID}</span>
</div>
""", unsafe_allow_html=True)
