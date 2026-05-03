import streamlit as st
from datetime import datetime
import urllib.parse

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Panel de Control",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── IDs ──────────────────────────────────────────────────────────────────────
LOGO_ID     = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGO_URL    = f"https://drive.google.com/uc?export=view&id={LOGO_ID}"
TEMPLATE_ID = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
FOLDER_ID   = "1MxMdeBlUG6v5n2upobsjNbQNQ8F_C_sO"

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

* { box-sizing: border-box; }

[data-testid="stAppViewContainer"] { background: #0B0F19; min-height: 100vh; }
[data-testid="stHeader"] { background: transparent !important; }
section[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }

.portal-header {
    padding: 2.2rem 4rem 2rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    display: flex; align-items: center; gap: 1.8rem;
    background: linear-gradient(180deg, #0F1624 0%, #0B0F19 100%);
}
.portal-logo { height: 58px; width: auto; object-fit: contain; }
.portal-title { font-family:'Sora',sans-serif; font-size:1.7rem; font-weight:600; color:#F1F5F9; letter-spacing:-0.02em; }
.portal-subtitle { font-family:'DM Sans',sans-serif; font-size:0.83rem; color:#3D4F6A; margin-top:0.2rem; font-weight:300; }

.main-content { padding: 2.5rem 4rem 3rem; }

.section-eyebrow {
    font-family:'Sora',sans-serif; font-size:0.65rem; font-weight:600;
    letter-spacing:0.14em; text-transform:uppercase; color:#6366F1; margin-bottom:0.4rem;
}
.section-heading {
    font-family:'Sora',sans-serif; font-size:1.2rem; font-weight:600;
    color:#CBD5E1; margin-bottom:1.4rem; letter-spacing:-0.01em;
}

.tools-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:1rem; }

.tool-card {
    background:#111827; border:1px solid rgba(255,255,255,0.07);
    border-radius:16px; padding:1.5rem; position:relative; overflow:hidden;
    transition: border-color 0.2s, transform 0.2s, background 0.2s;
    min-height:180px; display:flex; flex-direction:column; justify-content:space-between;
}
.tool-card-active { border-color:rgba(99,102,241,0.35); }
.tool-card-active:hover { border-color:rgba(99,102,241,0.6); background:#141C2E; transform:translateY(-2px); }
.tool-card-inactive { border-color:rgba(255,255,255,0.04); opacity:0.4; }

.card-glow {
    position:absolute; top:-30px; right:-30px; width:120px; height:120px;
    border-radius:50%; background:radial-gradient(circle,rgba(99,102,241,0.12) 0%,transparent 70%);
    pointer-events:none;
}
.card-top { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:0.8rem; }
.card-icon-wrap {
    width:44px; height:44px; border-radius:11px;
    background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.2);
    display:flex; align-items:center; justify-content:center; font-size:1.25rem;
}
.card-status-badge { font-family:'DM Sans',sans-serif; font-size:0.65rem; font-weight:500; padding:0.22rem 0.6rem; border-radius:50px; letter-spacing:0.04em; text-transform:uppercase; }
.badge-active { background:rgba(16,185,129,0.1); color:#34D399; border:1px solid rgba(16,185,129,0.2); }
.badge-soon { background:rgba(255,255,255,0.05); color:#4B5A75; border:1px solid rgba(255,255,255,0.08); }
.card-name { font-family:'Sora',sans-serif; font-size:0.97rem; font-weight:600; color:#E2E8F0; margin-bottom:0.3rem; line-height:1.3; }
.card-desc { font-family:'DM Sans',sans-serif; font-size:0.8rem; color:#4B5A75; line-height:1.5; margin-bottom:1rem; flex:1; }
.card-action { display:flex; align-items:center; justify-content:space-between; }
.card-action-label { font-family:'DM Sans',sans-serif; font-size:0.75rem; color:#6366F1; font-weight:500; }
.card-action-arrow { width:30px; height:30px; border-radius:8px; background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.25); display:flex; align-items:center; justify-content:center; color:#818CF8; font-size:0.85rem; }

.result-panel {
    margin-top:1.5rem; background:#111827; border:1px solid rgba(16,185,129,0.25);
    border-radius:14px; padding:1.3rem 1.5rem;
    display:flex; align-items:center; gap:1.2rem;
}
.result-icon { width:44px; height:44px; flex-shrink:0; border-radius:11px; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.2); display:flex; align-items:center; justify-content:center; font-size:1.3rem; }
.result-title { font-family:'Sora',sans-serif; font-size:0.9rem; font-weight:600; color:#6EE7B7; margin-bottom:0.2rem; }
.result-name { font-family:'DM Sans',sans-serif; font-size:0.82rem; color:#4B5A75; }
.result-link { margin-left:auto; font-family:'Sora',sans-serif; font-size:0.8rem; font-weight:500; color:#818CF8; background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.25); border-radius:8px; padding:0.5rem 1rem; text-decoration:none; white-space:nowrap; }

.history-row { display:flex; align-items:center; gap:1rem; padding:0.85rem 1rem; border-radius:10px; background:#0F1624; border:1px solid rgba(255,255,255,0.05); margin-bottom:0.5rem; }
.history-num { width:24px; height:24px; border-radius:6px; background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.2); display:flex; align-items:center; justify-content:center; font-family:'Sora',sans-serif; font-size:0.7rem; font-weight:600; color:#818CF8; flex-shrink:0; }
.history-name { font-family:'DM Sans',sans-serif; font-size:0.83rem; color:#94A3B8; flex:1; }
.history-time { font-family:'DM Sans',sans-serif; font-size:0.75rem; color:#2D3A4F; }
.history-link { font-family:'DM Sans',sans-serif; font-size:0.75rem; color:#6366F1; text-decoration:none; }

.portal-footer { padding:1.2rem 4rem; border-top:1px solid rgba(255,255,255,0.05); display:flex; justify-content:space-between; align-items:center; }
.footer-text { font-family:'DM Sans',sans-serif; font-size:0.75rem; color:#1E2A3D; }

.stButton > button {
    background: linear-gradient(135deg,#6366F1 0%,#4F46E5 100%) !important;
    color:#fff !important; border:none !important; border-radius:10px !important;
    font-family:'Sora',sans-serif !important; font-size:0.88rem !important;
    font-weight:500 !important; padding:0.6rem 1.5rem !important;
    box-shadow:0 4px 18px rgba(99,102,241,0.3) !important; transition:all 0.2s !important;
}
.stButton > button:hover { box-shadow:0 6px 24px rgba(99,102,241,0.45) !important; transform:translateY(-1px) !important; }
[data-testid="stSuccess"] { background:rgba(16,185,129,0.08) !important; border:1px solid rgba(16,185,129,0.2) !important; border-radius:10px !important; }
[data-testid="stInfo"] { border-radius:10px !important; }
div[data-testid="stExpander"] { background:#111827 !important; border:1px solid rgba(255,255,255,0.06) !important; border-radius:12px !important; }
</style>
""", unsafe_allow_html=True)

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="portal-header">
    <img class="portal-logo" src="{LOGO_URL}" alt="Logo"
         onerror="this.style.display='none'">
    <div>
        <div class="portal-title">Panel de Control</div>
        <div class="portal-subtitle">Herramientas y automatizaciones &nbsp;·&nbsp; Backend Google Drive</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-content">', unsafe_allow_html=True)

st.markdown('<div class="section-eyebrow">⚡ Acciones rápidas</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Herramientas disponibles</div>', unsafe_allow_html=True)

# ── Definición de herramientas ─────────────────────────────────────────────────
TOOLS = [
    {
        "id": "confirmacion_es",
        "icon": "📋",
        "name": "Crear nueva confirmación ES",
        "desc": "Genera una copia de la plantilla en tu carpeta de Drive y la abre lista para usar.",
        "active": True,
    },
    {
        "id": "soon_1",
        "icon": "📊",
        "name": "Próximamente",
        "desc": "Aquí irá la siguiente herramienta.",
        "active": False,
    },
    {
        "id": "soon_2",
        "icon": "📁",
        "name": "Próximamente",
        "desc": "Aquí irá otra herramienta.",
        "active": False,
    },
]

# ── Render de tarjetas ─────────────────────────────────────────────────────────
cols = st.columns(len(TOOLS), gap="medium")

for col, tool in zip(cols, TOOLS):
    with col:
        badge_class = "badge-active" if tool["active"] else "badge-soon"
        badge_text  = "Activo" if tool["active"] else "Próximo"
        card_class  = "tool-card tool-card-active" if tool["active"] else "tool-card tool-card-inactive"
        glow        = '<div class="card-glow"></div>' if tool["active"] else ""
        action_html = """
            <div class="card-action">
                <span class="card-action-label">Crear y abrir →</span>
                <div class="card-action-arrow">↗</div>
            </div>""" if tool["active"] else ""

        st.markdown(f"""
        <div class="{card_class}">
            {glow}
            <div>
                <div class="card-top">
                    <div class="card-icon-wrap">{tool['icon']}</div>
                    <span class="card-status-badge {badge_class}">{badge_text}</span>
                </div>
                <div class="card-name">{tool['name']}</div>
                <div class="card-desc">{tool['desc']}</div>
            </div>
            {action_html}
        </div>
        """, unsafe_allow_html=True)

        if tool["active"]:
            if st.button("✨  Crear nueva confirmación ES", key=f"btn_{tool['id']}",
                         use_container_width=True):
                st.session_state["fire_confirmacion_es"] = True

# ── Acción: copiar plantilla ───────────────────────────────────────────────────
if st.session_state.get("fire_confirmacion_es"):
    st.session_state["fire_confirmacion_es"] = False

    fecha_str    = datetime.now().strftime("%Y-%m-%d_%H%M")
    nombre_copia = f"Confirmacion_ES_{fecha_str}"

    # URL nativa de Google Drive:
    # /copy crea una copia del archivo. El parámetro `parents` fuerza la carpeta destino.
    copy_url = (
        f"https://docs.google.com/spreadsheets/d/{TEMPLATE_ID}/copy"
        f"?title={urllib.parse.quote(nombre_copia)}"
        f"&parents={FOLDER_ID}"
    )

    # Guardar en historial
    if "historial" not in st.session_state:
        st.session_state.historial = []

    st.session_state.historial.insert(0, {
        "nombre": nombre_copia,
        "hora": datetime.now().strftime("%H:%M:%S"),
        "url": copy_url,
    })

    st.markdown(f"""
    <div class="result-panel">
        <div class="result-icon">✅</div>
        <div>
            <div class="result-title">Copia lista para crear</div>
            <div class="result-name">{nombre_copia}</div>
        </div>
        <a class="result-link" href="{copy_url}" target="_blank">Abrir en Drive ↗</a>
    </div>
    """, unsafe_allow_html=True)

    st.info(
        "**¿Cómo funciona?** Google Drive te pedirá confirmar la copia. "
        "Al aceptar, se creará el archivo en la carpeta destino y se abrirá automáticamente."
    )

# ── Historial de sesión ────────────────────────────────────────────────────────
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

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="portal-footer">
    <span class="footer-text">Panel de Control &nbsp;·&nbsp; v1.1.0</span>
    <span class="footer-text">Carpeta Drive: <code style="color:#243450;font-size:0.72rem;">{FOLDER_ID}</code></span>
</div>
""", unsafe_allow_html=True)
