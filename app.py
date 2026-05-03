import streamlit as st
from datetime import datetime
import urllib.parse

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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&family=DM+Sans:wght@300;400;500&display=swap');

* { box-sizing: border-box; }

[data-testid="stAppViewContainer"] { background: #F5F6FA; }
[data-testid="stHeader"] { background: transparent !important; }
section[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }

.portal-header {
    background: #fff;
    border-bottom: 1px solid #E4E7EF;
    padding: 1.2rem 3rem;
    display: flex;
    align-items: center;
    gap: 1.2rem;
}
.portal-logo {
    height: 48px;
    width: auto;
    object-fit: contain;
}
.portal-title {
    font-family: 'Sora', sans-serif;
    font-size: 1.25rem;
    font-weight: 600;
    color: #1A1F36;
    letter-spacing: -0.01em;
}
.portal-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.78rem;
    color: #8C93A8;
    margin-top: 0.1rem;
}

.main-content { padding: 2rem 3rem 3rem; }

.section-eyebrow {
    font-family: 'Sora', sans-serif;
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #5B6BF8;
    margin-bottom: 0.3rem;
}
.section-heading {
    font-family: 'Sora', sans-serif;
    font-size: 1.05rem;
    font-weight: 600;
    color: #1A1F36;
    margin-bottom: 1.2rem;
}

/* ── Tarjeta compacta ── */
.tool-card {
    background: #fff;
    border: 1px solid #E4E7EF;
    border-radius: 12px;
    padding: 1.1rem 1.2rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    transition: box-shadow 0.18s, border-color 0.18s;
    max-width: 380px;
}
.tool-card:hover { box-shadow: 0 4px 16px rgba(91,107,248,0.1); border-color: #C5CAF8; }
.tool-card-inactive { opacity: 0.45; max-width: 380px; }

.card-icon-wrap {
    width: 40px; height: 40px; flex-shrink: 0;
    border-radius: 10px;
    background: #EEF0FD;
    border: 1px solid #D4D8FB;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.15rem;
}
.card-body { flex: 1; min-width: 0; }
.card-name {
    font-family: 'Sora', sans-serif;
    font-size: 0.88rem;
    font-weight: 600;
    color: #1A1F36;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.card-desc {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.75rem;
    color: #8C93A8;
    margin-top: 0.15rem;
    line-height: 1.4;
}
.badge-active {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.6rem;
    font-weight: 500;
    padding: 0.18rem 0.55rem;
    border-radius: 50px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: #E8FAF2;
    color: #18835A;
    border: 1px solid #B6E8D3;
    white-space: nowrap;
    flex-shrink: 0;
}
.badge-soon {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.6rem;
    font-weight: 500;
    padding: 0.18rem 0.55rem;
    border-radius: 50px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: #F3F4F8;
    color: #8C93A8;
    border: 1px solid #DDE0EA;
    white-space: nowrap;
    flex-shrink: 0;
}

/* historial */
.history-row {
    display: flex; align-items: center; gap: 0.8rem;
    padding: 0.7rem 1rem;
    border-radius: 8px;
    background: #fff;
    border: 1px solid #E4E7EF;
    margin-bottom: 0.45rem;
    max-width: 600px;
}
.history-num {
    width: 22px; height: 22px; border-radius: 6px;
    background: #EEF0FD; border: 1px solid #D4D8FB;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Sora', sans-serif; font-size: 0.65rem; font-weight: 600; color: #5B6BF8;
    flex-shrink: 0;
}
.history-name { font-family: 'DM Sans', sans-serif; font-size: 0.82rem; color: #3D4468; flex: 1; }
.history-time { font-family: 'DM Sans', sans-serif; font-size: 0.72rem; color: #B0B6CC; }
.history-link { font-family: 'DM Sans', sans-serif; font-size: 0.75rem; color: #5B6BF8; text-decoration: none; font-weight: 500; }

/* footer */
.portal-footer {
    padding: 1rem 3rem;
    border-top: 1px solid #E4E7EF;
    background: #fff;
    display: flex; justify-content: space-between; align-items: center;
}
.footer-text { font-family: 'DM Sans', sans-serif; font-size: 0.72rem; color: #B0B6CC; }

/* Streamlit overrides */
.stButton > button {
    background: #5B6BF8 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Sora', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.2rem !important;
    box-shadow: 0 2px 8px rgba(91,107,248,0.25) !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background: #4656E8 !important;
    box-shadow: 0 4px 14px rgba(91,107,248,0.35) !important;
}
[data-testid="stSuccess"] {
    background: #F0FBF6 !important;
    border: 1px solid #B6E8D3 !important;
    border-radius: 8px !important;
    color: #18835A !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stInfo"] { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="portal-header">
    <img class="portal-logo" src="{LOGO_URL}" alt="Logo">
    <div>
        <div class="portal-title">Panel de Control</div>
        <div class="portal-subtitle">Herramientas y automatizaciones · Backend Google Drive</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-content">', unsafe_allow_html=True)

st.markdown('<div class="section-eyebrow">⚡ Acciones rápidas</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Herramientas disponibles</div>', unsafe_allow_html=True)

TOOLS = [
    {"id": "confirmacion_es", "icon": "📋", "name": "Crear nueva confirmación ES",
     "desc": "Copia la plantilla a tu carpeta de Drive", "active": True},
    {"id": "soon_1", "icon": "📊", "name": "Próximamente", "desc": "Nueva herramienta", "active": False},
    {"id": "soon_2", "icon": "📁", "name": "Próximamente", "desc": "Nueva herramienta", "active": False},
]

for tool in TOOLS:
    col_card, col_btn = st.columns([3, 1], gap="small")
    with col_card:
        badge = f'<span class="badge-active">Activo</span>' if tool["active"] else '<span class="badge-soon">Próximo</span>'
        card_class = "tool-card" if tool["active"] else "tool-card tool-card-inactive"
        st.markdown(f"""
        <div class="{card_class}">
            <div class="card-icon-wrap">{tool['icon']}</div>
            <div class="card-body">
                <div class="card-name">{tool['name']}</div>
                <div class="card-desc">{tool['desc']}</div>
            </div>
            {badge}
        </div>
        """, unsafe_allow_html=True)
    with col_btn:
        if tool["active"]:
            st.markdown("<div style='margin-top:0.55rem;'></div>", unsafe_allow_html=True)
            if st.button("✨ Crear", key=f"btn_{tool['id']}"):
                st.session_state["fire_" + tool["id"]] = True

# ─── ACCIÓN: CREAR CONFIRMACIÓN ES ────────────────────────────────────────────
if st.session_state.get("fire_confirmacion_es"):
    st.session_state["fire_confirmacion_es"] = False

    fecha_str    = datetime.now().strftime("%Y-%m-%d_%H%M")
    nombre_copia = f"Confirmacion_ES_{fecha_str}"

    copy_url = (
        f"https://docs.google.com/spreadsheets/d/{TEMPLATE_ID}/copy"
        f"?title={urllib.parse.quote(nombre_copia)}"
        f"&parents={FOLDER_ID}"
    )

    if "historial" not in st.session_state:
        st.session_state.historial = []
    st.session_state.historial.insert(0, {
        "nombre": nombre_copia,
        "hora": datetime.now().strftime("%H:%M:%S"),
        "url": copy_url,
    })

    # Abrir automáticamente la URL via JS
    st.markdown(f"""
    <script>window.open("{copy_url}", "_blank");</script>
    """, unsafe_allow_html=True)

    st.success(f"✅ Abriendo Drive para crear: **{nombre_copia}**")
    st.link_button("📂 Abrir Drive (si no se abrió)", url=copy_url)

# ─── HISTORIAL ────────────────────────────────────────────────────────────────
if st.session_state.get("historial"):
    st.markdown("<br>", unsafe_allow_html=True)
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

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="portal-footer">
    <span class="footer-text">Panel de Control · v1.2.0</span>
    <span class="footer-text">Carpeta: {FOLDER_ID}</span>
</div>
""", unsafe_allow_html=True)
