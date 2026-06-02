
# ============================================================
# NEW_CONFIG.py — Formulario inteligente de confirmación
# ============================================================

import re
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.set_page_config(
    page_title="Nueva Confirmación",
    page_icon="favicon1.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# AUTH CHECK
# ============================================================
if not st.session_state.get("authenticated"):
    st.markdown("""
        <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .auth-warn { background: #FEF3C7; border: 1.5px solid #FCD34D; border-radius: 12px;
            padding: 1rem 1.2rem; margin: 2rem auto; max-width: 480px; font-family: sans-serif; }
        .auth-warn-title { font-size: 1rem; font-weight: 800; color: #92400E; margin-bottom: 0.3rem; }
        .auth-warn-sub { font-size: 0.82rem; color: #78350F; }
        </style>
        <div class="auth-warn">
            <div class="auth-warn-title">⚠️ Acceso restringido / Restricted access</div>
            <div class="auth-warn-sub">No tienes acceso. Inicia sesión desde el menú principal.<br>
            <em>You don't have access. Please log in from the main menu.</em></div>
        </div>""", unsafe_allow_html=True)
    st.stop()

# ============================================================
# CONSTANTES
# ============================================================
LOGOID        = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGOURL       = f"https://lh3.googleusercontent.com/d/{LOGOID}"
AGENCYSHEETID = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
AGENCYSHEET   = "Datos"

AGENCYFIELDS  = [
    "Nombre", "CODIGO", "Grupo Gest", "Telefono", "Email", "Direccion",
    "COMISION AGENCIA", "COMISION AGENCIA CON OFERTA ", "COMISION AGENCIA OFERTA 2X1 ",
    "IVA", "IVA SERVICIO OPCIONAL",
]

DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Usuario"

# ============================================================
# GOOGLE SERVICES
# ============================================================
@st.cache_resource
def getgooglecreds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcpserviceaccount"],
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"],
    )

@st.cache_resource
def getsheetsservice():
    return build("sheets", "v4", credentials=getgooglecreds())

@st.cache_data(ttl=300)
def getagencias():
    service = getsheetsservice()
    response = service.spreadsheets().values().get(
        spreadsheetId=AGENCYSHEETID,
        range=f"{AGENCYSHEET}!A:K",
    ).execute()
    rows = response.get("values", [])
    agencies = []
    for idx, row in enumerate(rows, start=1):
        row = row + [""] * (11 - len(row))
        data = {"rownumber": idx}
        for i, field in enumerate(AGENCYFIELDS):
            data[field] = row[i]
        data["searchblob"] = " ".join(
            str(data.get(f, "") or "").strip().lower()
            for f in ["Nombre", "CODIGO", "Grupo Gest", "Telefono", "Email"]
        )
        agencies.append(data)
    return agencies

def searchagencias(query):
    q = str(query or "").strip().lower()
    if len(q) < 2:
        return []
    return [a for a in getagencias() if q in a["searchblob"]]

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');

* { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: "DM Sans", sans-serif !important;
    background: #FFFFFF !important;
}
[data-testid="stAppViewContainer"] { background: #FFFFFF !important; }
[data-testid="stHeader"] { background: transparent !important; }
section[data-testid="stSidebar"] { display: none !important; }
.block-container, [data-testid="stMainBlockContainer"] {
    padding-top: 0 !important; padding-bottom: 1rem !important;
    padding-left: 1rem !important; padding-right: 1rem !important;
    max-width: 1400px !important; margin: 0 auto !important;
}

/* ── Cabecera documento ── */
.doc-header {
    display: flex; align-items: flex-start; justify-content: space-between;
    padding: 0.9rem 0 0.7rem 0; border-bottom: 3px solid #1E3A8A; margin-bottom: 1rem;
}
.doc-header-left { display: flex; flex-direction: column; gap: 0.1rem; }
.doc-title {
    font-size: 1.55rem; font-weight: 900; color: #1E3A8A;
    letter-spacing: 0.04em; text-transform: uppercase; line-height: 1;
}
.doc-subtitle { font-size: 0.72rem; font-weight: 600; color: #6B7280; letter-spacing: 0.08em; text-transform: uppercase; }
.doc-header-center { text-align: center; font-size: 0.68rem; color: #6B7280; line-height: 1.6; }
.doc-header-right { display: flex; align-items: center; }
.doc-logo { height: 46px; width: auto; }

/* ── Selector de tipo ── */
.tipo-btn {
    width: 100%; padding: 0.85rem 1rem; border-radius: 12px;
    border: 2px solid #E5E7EB; background: #F9FAFB;
    text-align: center; margin-bottom: 0.4rem;
}
.tipo-btn-icon { font-size: 1.4rem; margin-bottom: 0.2rem; }
.tipo-btn-label { font-size: 0.80rem; font-weight: 800; color: #1F2937; }
.tipo-btn-sub   { font-size: 0.65rem; color: #6B7280; margin-top: 0.1rem; }

/* ── Panel formulario ── */
.form-panel {
    background: #FAFBFF; border: 1.5px solid #E0E7EF; border-radius: 14px;
    padding: 1.1rem 1.2rem 1.3rem 1.2rem; margin-bottom: 1rem;
}
.form-section-title {
    font-size: 0.70rem; font-weight: 800; color: #6B7280;
    text-transform: uppercase; letter-spacing: 0.10em;
    border-bottom: 1px solid #E5E7EB; padding-bottom: 0.3rem;
    margin-bottom: 0.8rem; margin-top: 0.2rem;
}

/* ── Tabla estilo hoja ── */
.agency-table {
    width: 100%; border-collapse: collapse; font-size: 0.82rem;
    border: 1.5px solid #374151;
}
.agency-table td, .agency-table th {
    border: 1px solid #9CA3AF; padding: 5px 8px;
    vertical-align: middle;
}
.agency-table th {
    background: #F3F4F6; font-weight: 800; font-size: 0.72rem;
    color: #374151; text-transform: uppercase; letter-spacing: 0.05em;
    white-space: nowrap;
}
.agency-table td.label-cell {
    background: #F9FAFB; font-weight: 700; color: #374151;
    font-size: 0.75rem; white-space: nowrap; width: 100px;
    text-align: right; padding-right: 10px;
}
.agency-table td.value-cell {
    font-weight: 600; color: #111827; background: #FFFFFF;
}
.agency-table td.code-cell {
    background: #EFF6FF; font-weight: 800; color: #1E40AF;
    text-align: center; white-space: nowrap;
}
.agency-table td.empty-cell {
    background: #F9FAFB; color: #9CA3AF; font-style: italic;
    font-size: 0.72rem;
}

/* ── Badge tipo activo ── */
.badge-tipo {
    display: inline-flex; align-items: center; gap: 0.4rem;
    padding: 0.3rem 0.8rem; border-radius: 999px;
    font-size: 0.72rem; font-weight: 800; margin-bottom: 0.9rem;
}
.badge-fit-es  { background: #DBEAFE; color: #1D4ED8; border: 1px solid #93C5FD; }
.badge-fit-en  { background: #D1FAE5; color: #065F46; border: 1px solid #6EE7B7; }
.badge-groups  { background: #EDE9FE; color: #5B21B6; border: 1px solid #C4B5FD; }

/* ── Inputs ── */
div[data-testid="stTextInput"] label {
    color: #374151 !important; font-size: 0.76rem !important; font-weight: 700 !important;
}
div[data-testid="stTextInput"] input {
    background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important;
    border-radius: 10px !important; color: #1F2937 !important;
    min-height: 40px !important; font-family: "DM Sans", sans-serif !important;
    font-size: 0.88rem !important; font-weight: 600 !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
}
div.stButton button {
    border-radius: 999px !important; font-size: 0.75rem !important;
    font-weight: 800 !important; font-family: "DM Sans", sans-serif !important;
    padding: 0 1rem !important; min-height: 34px !important;
    box-shadow: 0 2px 6px rgba(15,23,42,0.10) !important;
    border: 2px solid transparent !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
div.stButton button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 14px rgba(15,23,42,0.13) !important;
}

/* ── Pill usuario ── */
.user-pill {
    display: inline-flex; align-items: center; gap: 0.4rem;
    padding: 0.3rem 0.7rem; border-radius: 999px;
    background: #F3F4F6; border: 1px solid #E5E7EB;
    font-size: 0.70rem; font-weight: 700; color: #4B5565;
}

/* ── Resultado búsqueda ── */
.search-result-card {
    background: #F0FDF4; border: 1.5px solid #86EFAC;
    border-radius: 10px; padding: 0.6rem 0.9rem;
    font-size: 0.78rem; color: #166534; font-weight: 700;
    margin-top: 0.6rem;
}
.search-none-card {
    background: #FEF9C3; border: 1.5px solid #FCD34D;
    border-radius: 10px; padding: 0.6rem 0.9rem;
    font-size: 0.78rem; color: #92400E; font-weight: 700;
    margin-bottom: 0.6rem;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# CABECERA — estilo documento
# ============================================================
from datetime import date
today_str = date.today().strftime("%-d/%-m/%Y")

st.markdown(f"""
<div class="doc-header">
    <div class="doc-header-left">
        <div class="doc-title">PROFORMA - CONFIRMACIÓN</div>
        <div class="doc-subtitle">Nueva Confirmación / New Confirmation</div>
        <div style="margin-top:0.5rem;font-size:0.82rem;font-weight:700;color:#374151;">
            FECHA: &nbsp;<span style="color:#1E3A8A;">{today_str}</span>
        </div>
    </div>
    <div class="doc-header-center">
        CRUCEMUNDO SL · CRUCEROS FLUVIALES · WWW.CRUCEMUNDO.ES<br>
        Av. Europa, 86, building 2A, suite 25 cp.08850 Gavà, Spain<br>
        EMAIL: info@crucemundo.com
    </div>
    <div class="doc-header-right">
        <img class="doc-logo" src="{LOGOURL}" alt="Logo">
    </div>
</div>
""", unsafe_allow_html=True)

# Pill usuario + back
nav_col1, nav_col2 = st.columns([6, 1])
with nav_col1:
    st.markdown(f'<span class="user-pill">👤 {DISPLAYUSER}</span>', unsafe_allow_html=True)
with nav_col2:
    if st.button("← Volver / Back", key="btn_back_main"):
        st.switch_page("app.py")

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

# ============================================================
# PASO 1 — SELECTOR DE TIPO
# ============================================================
if "nc_tipo" not in st.session_state:
    st.session_state.nc_tipo = None

st.markdown('<div class="form-section-title">Paso 1 — Selecciona el tipo de confirmación / Select confirmation type</div>', unsafe_allow_html=True)

col_t1, col_t2, col_t3 = st.columns(3, gap="medium")

with col_t1:
    active1 = st.session_state.nc_tipo == "FIT_ES"
    border1 = "#2563EB" if active1 else "#E5E7EB"
    bg1     = "#EFF6FF" if active1 else "#F9FAFB"
    st.markdown(f"""
    <div class="tipo-btn" style="border-color:{border1};background:{bg1};">
        <div class="tipo-btn-icon">📘</div>
        <div class="tipo-btn-label">FIT Español</div>
        <div class="tipo-btn-sub">Confirmación individual ES</div>
    </div>""", unsafe_allow_html=True)
    if st.button("Seleccionar FIT ES", key="btn_tipo_fit_es"):
        st.session_state.nc_tipo           = "FIT_ES"
        st.session_state.nc_agency_query   = ""
        st.session_state.nc_agency_sel     = None
        st.session_state.nc_agency_matches = []
        st.rerun()

with col_t2:
    active2 = st.session_state.nc_tipo == "FIT_EN"
    border2 = "#059669" if active2 else "#E5E7EB"
    bg2     = "#ECFDF5" if active2 else "#F9FAFB"
    st.markdown(f"""
    <div class="tipo-btn" style="border-color:{border2};background:{bg2};">
        <div class="tipo-btn-icon">📗</div>
        <div class="tipo-btn-label">FIT English</div>
        <div class="tipo-btn-sub">Individual confirmation EN</div>
    </div>""", unsafe_allow_html=True)
    if st.button("Select FIT EN", key="btn_tipo_fit_en"):
        st.session_state.nc_tipo           = "FIT_EN"
        st.session_state.nc_agency_query   = ""
        st.session_state.nc_agency_sel     = None
        st.session_state.nc_agency_matches = []
        st.rerun()

with col_t3:
    active3 = st.session_state.nc_tipo == "GROUPS"
    border3 = "#7C3AED" if active3 else "#E5E7EB"
    bg3     = "#F5F3FF" if active3 else "#F9FAFB"
    st.markdown(f"""
    <div class="tipo-btn" style="border-color:{border3};background:{bg3};">
        <div class="tipo-btn-icon">👥</div>
        <div class="tipo-btn-label">GRUPOS / Groups</div>
        <div class="tipo-btn-sub">Confirmación grupal</div>
    </div>""", unsafe_allow_html=True)
    if st.button("Seleccionar GRUPOS", key="btn_tipo_groups"):
        st.session_state.nc_tipo           = "GROUPS"
        st.session_state.nc_agency_query   = ""
        st.session_state.nc_agency_sel     = None
        st.session_state.nc_agency_matches = []
        st.rerun()

# ============================================================
# PASO 2 — FORMULARIO (solo si hay tipo seleccionado)
# ============================================================
if st.session_state.nc_tipo:

    tipo        = st.session_state.nc_tipo
    badge_class = {"FIT_ES": "badge-fit-es", "FIT_EN": "badge-fit-en", "GROUPS": "badge-groups"}[tipo]
    badge_label = {"FIT_ES": "📘 FIT Español",  "FIT_EN": "📗 FIT English", "GROUPS": "👥 Grupos"}[tipo]

    st.markdown(f'<div class="badge-tipo {badge_class}">{badge_label}</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-panel">', unsafe_allow_html=True)
    st.markdown('<div class="form-section-title">Agencia / Agency</div>', unsafe_allow_html=True)

    # ── Buscador ────────────────────────────────────────────
    search_col, btn_col = st.columns([4, 1], gap="small")
    with search_col:
        query = st.text_input(
            "Buscar agencia (nombre, código, teléfono, email...)",
            value=st.session_state.get("nc_agency_query", ""),
            key="nc_agency_query_widget",
            placeholder="Ej: A Babor, ABB, 912952092...",
        )
    with btn_col:
        st.markdown("<div style='height:1.82rem'></div>", unsafe_allow_html=True)
        if st.button("🔎 Buscar", key="btn_buscar_agencia"):
            matches = searchagencias(query)
            st.session_state.nc_agency_query   = query
            st.session_state.nc_agency_matches = matches
            st.session_state.nc_agency_sel     = matches[0] if len(matches) == 1 else None
            st.rerun()

    matches = st.session_state.get("nc_agency_matches", [])
    sel     = st.session_state.get("nc_agency_sel")

    if len(matches) > 1 and not sel:
        st.markdown(f'<div class="search-none-card">⚠️ {len(matches)} coincidencias — selecciona la correcta:</div>', unsafe_allow_html=True)
        options = [f"{a['Nombre']}  ·  {a['CODIGO']}  ·  {a['Telefono']}" for a in matches]
        chosen  = st.selectbox("Selecciona agencia", options, index=None,
                               placeholder="Elige una...", key="nc_agency_select")
        if chosen:
            st.session_state.nc_agency_sel = matches[options.index(chosen)]
            st.rerun()

    elif len(matches) == 0 and st.session_state.get("nc_agency_query"):
        st.markdown('<div class="search-none-card">🔎 No se encontraron coincidencias. Escribe otro término.</div>', unsafe_allow_html=True)

    # ── Tabla estilo documento ───────────────────────────────
    ag        = sel or {}
    nombre    = ag.get("Nombre",    "")
    codigo    = ag.get("CODIGO",    "")
    grupo     = ag.get("Grupo Gest","")
    telefono  = ag.get("Telefono",  "")
    email     = ag.get("Email",     "")
    direccion = ag.get("Direccion", "")

    def cell(v, css="value-cell"):
        return f'<td class="{css}">{v}</td>' if v else '<td class="empty-cell">—</td>'

    st.markdown(f"""
    <table class="agency-table">
        <tr>
            <th colspan="2" style="text-align:left;">AGENCIA</th>
            <td class="value-cell" style="font-weight:800;font-size:0.88rem;" colspan="2">
                {nombre or '<span style="color:#9CA3AF;font-style:italic;">sin seleccionar</span>'}
            </td>
            <th>COD</th>
            {cell(codigo, "code-cell")}
            <th>GRUPO</th>
            {cell(grupo)}
        </tr>
        <tr>
            <td class="label-cell" colspan="2">Dirección</td>
            <td class="value-cell" colspan="5">
                {direccion or '<span style="color:#9CA3AF;font-style:italic;">—</span>'}
            </td>
        </tr>
        <tr>
            <td class="label-cell" colspan="2">Teléfono</td>
            {cell(telefono)}
            <td class="label-cell">Email</td>
            <td class="value-cell" colspan="4">
                {email or '<span style="color:#9CA3AF;font-style:italic;">—</span>'}
            </td>
        </tr>
    </table>
    """, unsafe_allow_html=True)

    if sel:
        st.markdown('<div class="search-result-card">✅ Agencia cargada correctamente desde la base de datos.</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.info("🚧 Próximos campos: Agente/Cliente, Estado Reserva, Localizador, Barco, Fechas, Cabinas, Pax...")
