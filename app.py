import streamlit as st
import json
from datetime import datetime
import urllib.parse

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Portal Laboral",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── LOGO GOOGLE DRIVE ────────────────────────────────────────────────────────
LOGO_ID = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGO_URL = f"https://drive.google.com/uc?export=view&id={LOGO_ID}"

# ─── TEMPLATE SHEET ID ────────────────────────────────────────────────────────
TEMPLATE_SHEET_ID = "TU_ID_DE_SHEET_AQUI"  # Reemplaza con el ID real de tu plantilla

# ─── ENLACES DE TRABAJO ───────────────────────────────────────────────────────
JOB_LINKS = [
    {
        "title": "InfoJobs",
        "description": "El portal de empleo líder en España. Miles de ofertas actualizadas.",
        "url": "https://www.infojobs.net",
        "icon": "🔍",
        "category": "General",
        "color": "#FF6B35"
    },
    {
        "title": "LinkedIn Jobs",
        "description": "Red profesional global. Conecta con reclutadores directamente.",
        "url": "https://www.linkedin.com/jobs",
        "icon": "💼",
        "category": "Redes",
        "color": "#0077B5"
    },
    {
        "title": "Indeed España",
        "description": "Millones de empleos de miles de webs en un solo lugar.",
        "url": "https://es.indeed.com",
        "icon": "🌐",
        "category": "General",
        "color": "#2164F3"
    },
    {
        "title": "Tecnoempleo",
        "description": "Especializado en tecnología, IT y perfiles digitales.",
        "url": "https://www.tecnoempleo.com",
        "icon": "💻",
        "category": "Tecnología",
        "color": "#00C896"
    },
    {
        "title": "Trabajos.com",
        "description": "Ofertas de empleo en toda España por sector y región.",
        "url": "https://www.trabajos.com",
        "icon": "📋",
        "category": "General",
        "color": "#7C3AED"
    },
    {
        "title": "Glassdoor",
        "description": "Ofertas + opiniones de empresas y salarios reales.",
        "url": "https://www.glassdoor.es",
        "icon": "🏢",
        "category": "Internacional",
        "color": "#0CAA41"
    },
]

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Base ── */
* { box-sizing: border-box; margin: 0; padding: 0; }

[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0D1117 0%, #161B22 50%, #0D1117 100%);
    min-height: 100vh;
}

[data-testid="stHeader"] { background: transparent; }

section[data-testid="stSidebar"] { display: none; }

.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── Hero Section ── */
.hero-section {
    background: linear-gradient(160deg, #0D1117 0%, #1A1F2E 40%, #0D1117 100%);
    padding: 3rem 4rem 2.5rem;
    border-bottom: 1px solid rgba(99,102,241,0.2);
    position: relative;
    overflow: hidden;
}

.hero-section::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -10%;
    width: 60%;
    height: 200%;
    background: radial-gradient(ellipse, rgba(99,102,241,0.08) 0%, transparent 70%);
    pointer-events: none;
}

.hero-section::after {
    content: '';
    position: absolute;
    top: 20%;
    right: -5%;
    width: 40%;
    height: 160%;
    background: radial-gradient(ellipse, rgba(16,185,129,0.06) 0%, transparent 70%);
    pointer-events: none;
}

.header-flex {
    display: flex;
    align-items: center;
    gap: 2rem;
    margin-bottom: 1.5rem;
    position: relative;
    z-index: 1;
}

.logo-container img {
    height: 72px;
    width: auto;
    object-fit: contain;
    filter: drop-shadow(0 0 20px rgba(99,102,241,0.4));
}

.header-text h1 {
    font-family: 'Sora', sans-serif;
    font-size: 2.4rem;
    font-weight: 700;
    color: #F0F6FF;
    letter-spacing: -0.02em;
    line-height: 1.15;
}

.header-text h1 span {
    background: linear-gradient(90deg, #818CF8, #34D399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.header-text p {
    font-family: 'DM Sans', sans-serif;
    font-size: 1rem;
    color: #8B97B0;
    margin-top: 0.4rem;
    font-weight: 300;
}

.stats-row {
    display: flex;
    gap: 2rem;
    position: relative;
    z-index: 1;
}

.stat-pill {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 50px;
    padding: 0.45rem 1.1rem;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.82rem;
    color: #8B97B0;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

.stat-pill strong {
    color: #E2E8F0;
    font-weight: 500;
}

/* ── Section Labels ── */
.section-label {
    font-family: 'Sora', sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #6366F1;
    margin-bottom: 0.5rem;
}

.section-title {
    font-family: 'Sora', sans-serif;
    font-size: 1.5rem;
    font-weight: 600;
    color: #E2E8F0;
    margin-bottom: 1.5rem;
    letter-spacing: -0.01em;
}

/* ── Content Area ── */
.content-area {
    padding: 2.5rem 4rem;
}

/* ── Job Cards ── */
.job-cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
    margin-bottom: 3rem;
}

.job-card {
    background: rgba(22, 27, 34, 0.8);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 1.4rem;
    transition: all 0.25s ease;
    position: relative;
    overflow: hidden;
    text-decoration: none;
    display: block;
    cursor: pointer;
}

.job-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--accent);
    transform: scaleX(0);
    transition: transform 0.3s ease;
    border-radius: 14px 14px 0 0;
}

.job-card:hover {
    border-color: rgba(255,255,255,0.15);
    background: rgba(30, 36, 48, 0.9);
    transform: translateY(-2px);
}

.job-card:hover::before {
    transform: scaleX(1);
}

.card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 0.8rem;
}

.card-icon {
    width: 42px;
    height: 42px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.08);
}

.card-badge {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.7rem;
    font-weight: 500;
    padding: 0.25rem 0.65rem;
    border-radius: 50px;
    background: rgba(99,102,241,0.12);
    color: #A5B4FC;
    border: 1px solid rgba(99,102,241,0.2);
}

.card-title {
    font-family: 'Sora', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: #E2E8F0;
    margin-bottom: 0.35rem;
}

.card-description {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.85rem;
    color: #6B7A99;
    line-height: 1.5;
    margin-bottom: 1rem;
}

.card-link-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.card-url {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.75rem;
    color: #4B5563;
    font-weight: 400;
}

.card-arrow {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: rgba(99,102,241,0.12);
    border: 1px solid rgba(99,102,241,0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #818CF8;
    font-size: 0.8rem;
    transition: all 0.2s;
}

.job-card:hover .card-arrow {
    background: rgba(99,102,241,0.25);
    border-color: rgba(99,102,241,0.4);
}

/* ── Confirmation Panel ── */
.confirm-panel {
    background: rgba(22, 27, 34, 0.8);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 2rem;
    margin-bottom: 3rem;
    position: relative;
    overflow: hidden;
}

.confirm-panel::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #6366F1, #34D399);
    border-radius: 16px 16px 0 0;
}

.confirm-title {
    font-family: 'Sora', sans-serif;
    font-size: 1.1rem;
    font-weight: 600;
    color: #E2E8F0;
    margin-bottom: 0.4rem;
}

.confirm-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.88rem;
    color: #6B7A99;
    margin-bottom: 1.4rem;
    line-height: 1.5;
}

/* ── Buttons ── */
.btn-primary {
    font-family: 'Sora', sans-serif;
    font-size: 0.88rem;
    font-weight: 500;
    padding: 0.65rem 1.4rem;
    border-radius: 10px;
    border: none;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    transition: all 0.2s ease;
    text-decoration: none;
    background: linear-gradient(135deg, #6366F1, #4F46E5);
    color: white;
}

/* ── Success/Error Alerts ── */
.alert {
    padding: 0.9rem 1.2rem;
    border-radius: 10px;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.88rem;
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
    margin-top: 1rem;
}

.alert-success {
    background: rgba(16,185,129,0.1);
    border: 1px solid rgba(16,185,129,0.25);
    color: #6EE7B7;
}

.alert-error {
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.25);
    color: #FCA5A5;
}

/* ── Footer ── */
.footer {
    padding: 1.5rem 4rem;
    border-top: 1px solid rgba(255,255,255,0.06);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.footer-text {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.78rem;
    color: #3D4A63;
}

.footer-dot {
    width: 4px; height: 4px;
    background: #6366F1;
    border-radius: 50%;
    display: inline-block;
    margin: 0 0.5rem;
    vertical-align: middle;
}

/* ── Streamlit overrides ── */
.stButton > button {
    background: linear-gradient(135deg, #6366F1, #4F46E5) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    padding: 0.65rem 1.4rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(99,102,241,0.3) !important;
}

.stButton > button:hover {
    box-shadow: 0 6px 20px rgba(99,102,241,0.45) !important;
    transform: translateY(-1px) !important;
}

.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #E2E8F0 !important;
    font-family: 'DM Sans', sans-serif !important;
}

.stSelectbox > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #E2E8F0 !important;
}

div[data-testid="stExpander"] {
    background: rgba(22, 27, 34, 0.8) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
}

.streamlit-expanderHeader {
    font-family: 'Sora', sans-serif !important;
    color: #E2E8F0 !important;
}

[data-testid="stSuccess"], [data-testid="stError"], [data-testid="stInfo"] {
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
}

</style>
""", unsafe_allow_html=True)


# ─── HERO SECTION ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-section">
    <div class="header-flex">
        <div class="logo-container">
            <img src="{LOGO_URL}" alt="Logo Portal Laboral"
                 onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
            <div style="display:none; width:72px; height:72px; background:linear-gradient(135deg,#6366F1,#34D399);
                        border-radius:14px; align-items:center; justify-content:center;
                        font-size:2rem;">💼</div>
        </div>
        <div class="header-text">
            <h1>Portal <span>Laboral</span></h1>
            <p>Tu centro de gestión de búsqueda de empleo — todo en un lugar</p>
        </div>
    </div>
    <div class="stats-row">
        <div class="stat-pill"><strong>{len(JOB_LINKS)}</strong> portales de empleo</div>
        <div class="stat-pill"><strong>Google Drive</strong> como backend</div>
        <div class="stat-pill">Actualizado <strong>{datetime.now().strftime("%d %b %Y")}</strong></div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─── MAIN CONTENT ─────────────────────────────────────────────────────────────
st.markdown('<div class="content-area">', unsafe_allow_html=True)

# ── Sección: Portales de empleo ───
col_label, _ = st.columns([3, 1])
with col_label:
    st.markdown('<div class="section-label">🔗 Recursos</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Portales de Empleo</div>', unsafe_allow_html=True)

# Cards grid
cards_html = '<div class="job-cards-grid">'
for job in JOB_LINKS:
    domain = job["url"].replace("https://www.", "").replace("https://", "").split("/")[0]
    cards_html += f"""
    <a class="job-card" href="{job['url']}" target="_blank"
       style="--accent: {job['color']};">
        <div class="card-header">
            <div class="card-icon">{job['icon']}</div>
            <span class="card-badge">{job['category']}</span>
        </div>
        <div class="card-title">{job['title']}</div>
        <div class="card-description">{job['description']}</div>
        <div class="card-link-row">
            <span class="card-url">{domain}</span>
            <div class="card-arrow">↗</div>
        </div>
    </a>"""
cards_html += '</div>'

st.markdown(cards_html, unsafe_allow_html=True)

st.markdown("---")

# ── Sección: Confirmación / Nueva candidatura ───
st.markdown('<div class="section-label">📋 Gestión</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Registrar Candidatura</div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="confirm-panel">
    <div class="confirm-title">📄 Nueva Hoja de Seguimiento</div>
    <div class="confirm-subtitle">
        Se creará una copia de tu plantilla de Google Sheets para registrar esta candidatura.<br>
        La copia se guardará automáticamente en tu Google Drive — nunca se modifica el original.
    </div>
</div>
""", unsafe_allow_html=True)

# Formulario de candidatura
with st.form("candidatura_form", clear_on_submit=False):
    col1, col2 = st.columns(2)

    with col1:
        empresa = st.text_input("🏢 Empresa", placeholder="Nombre de la empresa...")
        puesto = st.text_input("💼 Puesto solicitado", placeholder="Ej: Desarrollador Backend...")
        url_oferta = st.text_input("🔗 URL de la oferta", placeholder="https://...")

    with col2:
        portal = st.selectbox("📍 Portal de origen",
                              ["InfoJobs", "LinkedIn", "Indeed", "Tecnoempleo",
                               "Trabajos.com", "Glassdoor", "Otro"])
        fecha = st.date_input("📅 Fecha de solicitud", value=datetime.today())
        notas = st.text_area("📝 Notas", placeholder="Observaciones sobre la oferta...",
                             height=100)

    submitted = st.form_submit_button("✨  Crear hoja de seguimiento en Drive")

    if submitted:
        if empresa and puesto:
            # Construir nombre para la copia
            fecha_str = fecha.strftime("%Y%m%d")
            nombre_copia = f"[{fecha_str}] {empresa} — {puesto}"

            # URL para copiar el sheet via Google Drive
            copy_url = (
                f"https://docs.google.com/spreadsheets/d/{TEMPLATE_SHEET_ID}/copy"
                f"?title={urllib.parse.quote(nombre_copia)}"
            )

            st.success(f"""
✅ **¡Listo!** Se abrirá Google Drive para crear tu copia.
**Nombre de la hoja:** {nombre_copia}
""")

            st.link_button(
                f"📂  Abrir en Google Drive → Crear copia",
                url=copy_url,
                use_container_width=False
            )

            # Guardar en session state como historial
            if "candidaturas" not in st.session_state:
                st.session_state.candidaturas = []

            st.session_state.candidaturas.append({
                "empresa": empresa,
                "puesto": puesto,
                "portal": portal,
                "fecha": str(fecha),
                "url": url_oferta,
                "notas": notas,
                "hoja": nombre_copia
            })

        else:
            st.error("⚠️ Por favor, rellena al menos **Empresa** y **Puesto**.")

# ── Historial de sesión ───────────────────────────────────────────────────────
if "candidaturas" in st.session_state and st.session_state.candidaturas:
    st.markdown("---")
    st.markdown('<div class="section-label">📊 Historial</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Candidaturas de esta sesión</div>', unsafe_allow_html=True)

    with st.expander(f"Ver {len(st.session_state.candidaturas)} candidatura(s) registrada(s)"):
        for i, c in enumerate(reversed(st.session_state.candidaturas), 1):
            col_a, col_b, col_c = st.columns([2, 2, 1])
            with col_a:
                st.markdown(f"**{c['empresa']}**")
                st.caption(c['puesto'])
            with col_b:
                st.markdown(f"📍 {c['portal']}")
                st.caption(f"📅 {c['fecha']}")
            with col_c:
                st.caption(f"📄 {c['hoja'][:30]}...")
            if i < len(st.session_state.candidaturas):
                st.divider()

# ── Configuración ─────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("⚙️  Configuración del portal"):
    st.markdown("**ID de la plantilla Google Sheets**")
    nuevo_id = st.text_input(
        "Sheet Template ID",
        value=TEMPLATE_SHEET_ID,
        help="El ID se encuentra en la URL de tu Google Sheets: docs.google.com/spreadsheets/d/**ID**/edit"
    )
    if nuevo_id != TEMPLATE_SHEET_ID:
        st.info(f"ℹ️ Para aplicar el cambio, actualiza `TEMPLATE_SHEET_ID` en el archivo `app.py` con: `{nuevo_id}`")

    st.markdown("**ID del logo (Google Drive)**")
    st.caption(f"Logo actual: `{LOGO_ID}`")
    st.markdown(f"[Ver logo actual ↗](https://drive.google.com/file/d/{LOGO_ID}/view)")

# ── Cerrar content-area ───────────────────────────────────────────────────────
st.markdown('</div>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="footer">
    <span class="footer-text">
        Portal Laboral
        <span class="footer-dot"></span>
        Backend: Google Drive
        <span class="footer-dot"></span>
        v1.0.0
    </span>
    <span class="footer-text">
        {datetime.now().strftime("%Y")} — Publicado en Streamlit Cloud
    </span>
</div>
""", unsafe_allow_html=True)
