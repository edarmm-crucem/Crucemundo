# ============================================================
# NEW_CONFIG.py — Formulario compacto estilo spreadsheet
# ============================================================

import re
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import date, timedelta

st.set_page_config(
    page_title="Nueva Confirmación",
    page_icon="favicon1.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "nc_barco" not in st.session_state:
    st.session_state.nc_barco = ""

if "nc_dias" not in st.session_state:
    st.session_state.nc_dias = 1

if "nc_fecha_salida_loc" not in st.session_state:
    st.session_state.nc_fecha_salida_loc = date.today()

if "nc_localizador" not in st.session_state:
    st.session_state.nc_localizador = ""
    
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

@st.cache_data(ttl=300)
def getbarcos():
    SHEET_ID = "1K-Tn_E3QEhCplOP-IFHbKZc-vtKAxFEUBbZVK14EjJI"

    service = getsheetsservice()

    resp = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range="A:A"
    ).execute()

    values = resp.get("values", [])

    barcos = []

    for row in values:
        if row and str(row[0]).strip():
            barcos.append(str(row[0]).strip())

    # únicos manteniendo orden
    barcos_unicos = list(dict.fromkeys(barcos))

    return barcos_unicos

def searchagencias(query):
    q = str(query or "").strip().lower()
    if len(q) < 2:
        return []
    return [a for a in getagencias() if q in a["searchblob"]]

# ============================================================
# CSS — estilo spreadsheet compacto
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@400;600;700&display=swap');

* { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: "IBM Plex Sans", sans-serif !important;
    background: #F0F2F5 !important;
}
[data-testid="stAppViewContainer"] { background: #F0F2F5 !important; }
[data-testid="stHeader"] { background: transparent !important; }
section[data-testid="stSidebar"] { display: none !important; }
.block-container, [data-testid="stMainBlockContainer"] {
    padding-top: 0.5rem !important;
    padding-bottom: 1rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
    max-width: 1280px !important;
    margin: 0 auto !important;
}

/* ── Cabecera compacta ── */
.doc-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #1E3A8A;
    color: #fff;
    padding: 0.45rem 0.9rem;
    border-radius: 6px 6px 0 0;
    margin-bottom: 0;
}
.doc-title {
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: #fff;
}
.doc-meta {
    font-size: 0.65rem;
    color: #93C5FD;
    font-weight: 600;
    letter-spacing: 0.05em;
}
.doc-logo { height: 30px; width: auto; filter: brightness(0) invert(1); opacity: 0.9; }

/* ── Grid principal tipo hoja de cálculo ── */
.sheet-wrap {
    background: #fff;
    border: 1.5px solid #94A3B8;
    border-radius: 0 0 6px 6px;
    overflow: hidden;
}

/* ── Fila de hoja ── */
.sh-row {
    display: grid;
    border-bottom: 1px solid #CBD5E1;
    min-height: 32px;
}
.sh-row:last-child { border-bottom: none; }

/* ── Celda etiqueta (color informativo) ── */
.sh-lbl {
    background: #F8FAFC;
    border-right: 1px solid #CBD5E1;

    color: #475569;

    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;

    padding: 0 8px;

    display: flex;
    align-items: center;
}
/* ── Celda de valor informativo (auto-rellenado) ── */
.sh-val-info {
    background: #FFFFFF;
    border: 1px solid #D1D5DB;
    color: #111827;
    font-family: "IBM Plex Sans", sans-serif;
    font-size: 0.80rem;
    font-weight: 600;
    padding: 0 8px;
    display: flex;
    align-items: center;
    border-radius: 4px;
}
.sh-val-info.empty {
    color: #9CA3AF;
    font-style: italic;
}
/* ── Celda de código destacada ── */
.sh-val-code {
    background: #FFFFFF;
    border: 2px solid #2563EB;
    color: #2563EB;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.80rem;
    font-weight: 800;
    padding: 0 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
}
/* ── Sección cabecera de grupo ── */
.sh-group-hdr {
    background: #1E3A8A;
    color: #BFDBFE;
    font-size: 0.60rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    padding: 3px 10px;
    border-bottom: 1px solid #2563EB;
}
/* ── Row de número de fila (estilo Excel) ── */
.sh-rownum {
    background: #F1F5F9;
    border-right: 1.5px solid #94A3B8;
    color: #94A3B8;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.60rem;
    font-weight: 600;
    width: 26px;
    min-width: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    user-select: none;
    flex-shrink: 0;
}

/* ── Badge de estado ── */
.status-confirmed { background:#DCFCE7; color:#166534; border:1px solid #86EFAC; }
.status-pending   { background:#FEF3C7; color:#92400E; border:1px solid #FCD34D; }
.status-cancelled { background:#FEE2E2; color:#991B1B; border:1px solid #FCA5A5; }
.status-badge {
    display:inline-flex; align-items:center; gap:0.3rem;
    padding:2px 10px; border-radius:999px;
    font-size:0.65rem; font-weight:800; letter-spacing:0.05em;
}

/* ── Localizador generado ── */
.loc-display {
    font-family: "IBM Plex Mono", monospace;
    font-size: 1rem;
    font-weight: 800;
    color: #111827;
    letter-spacing: 0.12em;

    background: #FFFFFF;
    border: 2px solid #111827;
    border-radius: 4px;

    padding: 4px 12px;
    display: inline-block;
}

/* ── Streamlit input override — ultra compacto ── */
div[data-testid="stTextInput"] {
    margin-bottom: 0 !important;
}
div[data-testid="stTextInput"] label {
    display: none !important;
}
div[data-testid="stTextInput"] input {
    background: #FFFBEB !important;
    border: none !important;
    border-radius: 0 !important;
    color: #1F2937 !important;
    height: 30px !important;
    min-height: 30px !important;
    font-family: "IBM Plex Sans", sans-serif !important;
    font-size: 0.80rem !important;
    font-weight: 600 !important;
    padding: 0 8px !important;
    box-shadow: none !important;
    outline: none !important;
}
div[data-testid="stTextInput"] input:focus {
    background: #FFFDE7 !important;
    box-shadow: inset 0 0 0 2px #2563EB !important;
}
div[data-testid="stTextInput"] > div {
    border: none !important;
    box-shadow: none !important;
}

div[data-testid="stSelectbox"] {
    margin-bottom: 0 !important;
}
div[data-testid="stSelectbox"] label { display: none !important; }
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background: #FFFBEB !important;
    border: none !important;
    border-radius: 0 !important;
    height: 30px !important;
    min-height: 30px !important;
    font-family: "IBM Plex Sans", sans-serif !important;
    font-size: 0.80rem !important;
    font-weight: 600 !important;
    padding: 0 8px !important;
    box-shadow: none !important;
    color: #1F2937 !important;
}

div[data-testid="stDateInput"] {
    margin-bottom: 0 !important;
}
div[data-testid="stDateInput"] label { display: none !important; }
div[data-testid="stDateInput"] input {
    background: #FFFBEB !important;
    border: none !important;
    border-radius: 0 !important;
    height: 30px !important;
    min-height: 30px !important;
    font-family: "IBM Plex Sans", sans-serif !important;
    font-size: 0.80rem !important;
    font-weight: 600 !important;
    padding: 0 8px !important;
    box-shadow: none !important;
}
div[data-testid="stDateInput"] > div {
    border: none !important;
    box-shadow: none !important;
}

div.stButton button {
    font-family: "IBM Plex Sans", sans-serif !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    height: 26px !important;
    min-height: 26px !important;
    padding: 0 10px !important;
    border-radius: 4px !important;
    border: 1.5px solid transparent !important;
    box-shadow: none !important;
    line-height: 1 !important;
}

/* ── Pill usuario ── */
.user-pill {
    display: inline-flex; align-items: center; gap: 0.3rem;
    padding: 2px 8px; border-radius: 999px;
    background: #EFF6FF; border: 1px solid #BFDBFE;
    font-size: 0.65rem; font-weight: 700; color: #1E40AF;
}

/* Ocultar decoración streamlit */
div[data-testid="stTextInput"] > div > div { border: none !important; }
div[data-testid="stSelectbox"] > div > div { border: none !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CABECERA
# ============================================================
from datetime import date
today_str = date.today().strftime("%-d/%-m/%Y")

st.markdown(f"""
<div class="doc-header">
    <div>
        <div class="doc-title">📋 PROFORMA · CONFIRMACIÓN</div>
        <div class="doc-meta">CRUCEMUNDO SL · CRUCEROS FLUVIALES · {today_str}</div>
    </div>
    <img class="doc-logo" src="{LOGOURL}" alt="Logo">
</div>
""", unsafe_allow_html=True)

# Nav fila
nav1, nav2 = st.columns([7, 1])
with nav1:
    st.markdown(f'<div style="margin:4px 0 2px 0"><span class="user-pill">👤 {DISPLAYUSER}</span></div>', unsafe_allow_html=True)
with nav2:
    if st.button("← Volver", key="btn_back_main"):
        st.switch_page("app.py")

# ============================================================
# INICIO SHEET WRAP
# ============================================================
st.markdown('<div class="sheet-wrap">', unsafe_allow_html=True)

# ============================================================
# FILA 1 — TIPO DE CONFIRMACIÓN
# ============================================================
if "nc_tipo" not in st.session_state:
    st.session_state.nc_tipo = None

st.markdown('<div class="sh-group-hdr">TIPO DE CONFIRMACIÓN / CONFIRMATION TYPE</div>', unsafe_allow_html=True)

tipo_col = st.columns([0.3, 2, 1, 1, 1, 3], gap="small")
with tipo_col[0]:
    st.markdown('<div class="sh-rownum" style="height:38px;">1</div>', unsafe_allow_html=True)
with tipo_col[1]:
    st.markdown('<div class="sh-lbl" style="height:38px;">Tipo / Type</div>', unsafe_allow_html=True)
with tipo_col[2]:
    if st.button("📘 FIT ES", key="btn_tipo_fit_es"):
        st.session_state.update({"nc_tipo": "FIT_ES", "nc_agency_query": "", "nc_agency_sel": None, "nc_agency_matches": []})
        st.rerun()
with tipo_col[3]:
    if st.button("📗 FIT EN", key="btn_tipo_fit_en"):
        st.session_state.update({"nc_tipo": "FIT_EN", "nc_agency_query": "", "nc_agency_sel": None, "nc_agency_matches": []})
        st.rerun()
with tipo_col[4]:
    if st.button("👥 Grupos", key="btn_tipo_groups"):
        st.session_state.update({"nc_tipo": "GROUPS", "nc_agency_query": "", "nc_agency_sel": None, "nc_agency_matches": []})
        st.rerun()
with tipo_col[5]:
    tipo = st.session_state.nc_tipo
    if tipo == "FIT_ES":
        st.markdown('<div style="height:38px;display:flex;align-items:center;padding:0 8px"><span class="status-badge status-confirmed">📘 FIT ESPAÑOL seleccionado</span></div>', unsafe_allow_html=True)
    elif tipo == "FIT_EN":
        st.markdown('<div style="height:38px;display:flex;align-items:center;padding:0 8px"><span class="status-badge" style="background:#D1FAE5;color:#065F46;border:1px solid #6EE7B7;">📗 FIT ENGLISH selected</span></div>', unsafe_allow_html=True)
    elif tipo == "GROUPS":
        st.markdown('<div style="height:38px;display:flex;align-items:center;padding:0 8px"><span class="status-badge" style="background:#EDE9FE;color:#5B21B6;border:1px solid #C4B5FD;">👥 GRUPOS seleccionado</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="sh-val-info empty" style="height:38px;">— sin seleccionar —</div>', unsafe_allow_html=True)

# ============================================================
# RESTO DEL FORMULARIO (solo si hay tipo)
# ============================================================
if st.session_state.nc_tipo:

    # ── BLOQUE AGENCIA ────────────────────────────────────────
    st.markdown('<div class="sh-group-hdr">AGENCIA / AGENCY</div>', unsafe_allow_html=True)

    # Fila búsqueda
    def sh_row(cols_spec):
        return st.columns(cols_spec, gap="small")

    # Fila 2 — Buscador
    r2 = st.columns([0.3, 1.5, 4, 1], gap="small")
    with r2[0]: st.markdown('<div class="sh-rownum" style="height:32px;">2</div>', unsafe_allow_html=True)
    with r2[1]: st.markdown('<div class="sh-lbl" style="height:32px;">🔎 Buscar agencia</div>', unsafe_allow_html=True)
    with r2[2]:
        query = st.text_input("q", value=st.session_state.get("nc_agency_query", ""),
                              key="nc_agency_query_widget", placeholder="Nombre, código, tel, email...")
    with r2[3]:
        if st.button("Buscar", key="btn_buscar_agencia"):
            matches = searchagencias(query)
            st.session_state.nc_agency_query   = query
            st.session_state.nc_agency_matches = matches
            st.session_state.nc_agency_sel     = matches[0] if len(matches) == 1 else None
            st.rerun()

    matches = st.session_state.get("nc_agency_matches", [])
    sel     = st.session_state.get("nc_agency_sel")

    # Selector si hay múltiples
    if len(matches) > 1 and not sel:
        r_sel = st.columns([0.3, 1.5, 5], gap="small")
        with r_sel[0]: st.markdown('<div class="sh-rownum" style="height:32px;">↓</div>', unsafe_allow_html=True)
        with r_sel[1]: st.markdown('<div class="sh-lbl" style="height:32px;color:#D97706;">⚠ Múltiples resultados</div>', unsafe_allow_html=True)
        with r_sel[2]:
            options = [f"{a['Nombre']}  ·  {a['CODIGO']}  ·  {a['Telefono']}" for a in matches]
            chosen  = st.selectbox("sel", options, index=None, placeholder="Elige una agencia...", key="nc_agency_select")
            if chosen:
                st.session_state.nc_agency_sel = matches[options.index(chosen)]
                st.rerun()
    elif len(matches) == 0 and st.session_state.get("nc_agency_query"):
        st.markdown('<div style="background:#FEF9C3;border-bottom:1px solid #CBD5E1;padding:4px 10px;font-size:0.72rem;color:#92400E;font-weight:700;">🔎 Sin coincidencias — prueba otro término</div>', unsafe_allow_html=True)

    # Datos agencia
    ag        = sel or {}
    nombre    = ag.get("Nombre", "")
    codigo    = ag.get("CODIGO", "")
    grupo     = ag.get("Grupo Gest", "")
    telefono  = ag.get("Telefono", "")
    email     = ag.get("Email", "")
    direccion = ag.get("Direccion", "")

    def info_cell(v, fallback="—"):
        cls = "sh-val-info" if v else "sh-val-info empty"
        return f'<div class="{cls}" style="height:32px;">{v or fallback}</div>'

    # Fila 3 — Nombre + Código + Grupo
    r3 = st.columns([0.3, 1, 3.5, 0.7, 1.2, 0.7, 1.2], gap="small")
    with r3[0]: st.markdown('<div class="sh-rownum" style="height:32px;">3</div>', unsafe_allow_html=True)
    with r3[1]: st.markdown('<div class="sh-lbl" style="height:32px;">Agencia</div>', unsafe_allow_html=True)
    with r3[2]: st.markdown(info_cell(nombre), unsafe_allow_html=True)
    with r3[3]: st.markdown('<div class="sh-lbl" style="height:32px;">Cód.</div>', unsafe_allow_html=True)
    with r3[4]: st.markdown(f'<div class="sh-val-code" style="height:32px;">{codigo or "—"}</div>', unsafe_allow_html=True)
    with r3[5]: st.markdown('<div class="sh-lbl" style="height:32px;">Grupo</div>', unsafe_allow_html=True)
    with r3[6]: st.markdown(info_cell(grupo), unsafe_allow_html=True)

    # Fila 4 — Teléfono + Email
    r4 = st.columns([0.3, 1, 1.8, 0.7, 3.7], gap="small")
    with r4[0]: st.markdown('<div class="sh-rownum" style="height:32px;">4</div>', unsafe_allow_html=True)
    with r4[1]: st.markdown('<div class="sh-lbl" style="height:32px;">Teléfono</div>', unsafe_allow_html=True)
    with r4[2]: st.markdown(info_cell(telefono), unsafe_allow_html=True)
    with r4[3]: st.markdown('<div class="sh-lbl" style="height:32px;">Email</div>', unsafe_allow_html=True)
    with r4[4]: st.markdown(info_cell(email), unsafe_allow_html=True)

    # Fila 5 — Dirección
    r5 = st.columns([0.3, 1, 6.7], gap="small")
    with r5[0]: st.markdown('<div class="sh-rownum" style="height:32px;">5</div>', unsafe_allow_html=True)
    with r5[1]: st.markdown('<div class="sh-lbl" style="height:32px;">Dirección</div>', unsafe_allow_html=True)
    with r5[2]: st.markdown(info_cell(direccion), unsafe_allow_html=True)

    if sel:
        st.markdown('<div style="background:#DCFCE7;border-bottom:1px solid #CBD5E1;padding:3px 10px 3px 36px;font-size:0.68rem;color:#166534;font-weight:700;">✅ Agencia cargada desde base de datos</div>', unsafe_allow_html=True)

    # ── BLOQUE AGENTE / ESTADO ────────────────────────────────
    st.markdown('<div class="sh-group-hdr">AGENTE · ESTADO · REFERENCIA</div>', unsafe_allow_html=True)

    # Fila 6 — Agente + Estado
    r6 = st.columns([0.3, 1, 2.5, 0.8, 2.2, 1.2], gap="small")
    with r6[0]: st.markdown('<div class="sh-rownum" style="height:32px;">6</div>', unsafe_allow_html=True)
    with r6[1]: st.markdown('<div class="sh-lbl" style="height:32px;">Agente/Cliente</div>', unsafe_allow_html=True)
    with r6[2]:
        agente = st.text_input("agente", value=st.session_state.get("nc_agente_cliente", ""),
                               key="nc_agente_cliente_widget", placeholder="Nombre del agente o cliente...")
        if agente != st.session_state.get("nc_agente_cliente", ""):
            st.session_state.nc_agente_cliente = agente
    with r6[3]: st.markdown('<div class="sh-lbl" style="height:32px;">Estado</div>', unsafe_allow_html=True)
    with r6[4]:
        ESTADOS = ["", "CONFIRMADO", "NO CONFIRMADO", "CANCELADO"]
        estado_actual = st.session_state.get("nc_estado_reserva", "")
        estado_sel = st.selectbox("estado", options=ESTADOS,
            index=ESTADOS.index(estado_actual) if estado_actual in ESTADOS else 0,
            key="nc_estado_reserva_widget",
            format_func=lambda x: {"": "— estado —", "CONFIRMADO": "✅ CONFIRMADO",
                                    "NO CONFIRMADO": "⚠️ NO CONFIRMADO", "CANCELADO": "❌ CANCELADO"}.get(x, x))
        if estado_sel != st.session_state.get("nc_estado_reserva", ""):
            st.session_state.nc_estado_reserva = estado_sel
    with r6[5]:
        if estado_sel == "CONFIRMADO":
            st.markdown('<div style="height:32px;display:flex;align-items:center;padding:0 8px"><span class="status-badge status-confirmed">✅ OK</span></div>', unsafe_allow_html=True)
        elif estado_sel == "NO CONFIRMADO":
            st.markdown('<div style="height:32px;display:flex;align-items:center;padding:0 8px"><span class="status-badge status-pending">⚠️ PEND.</span></div>', unsafe_allow_html=True)
        elif estado_sel == "CANCELADO":
            st.markdown('<div style="height:32px;display:flex;align-items:center;padding:0 8px"><span class="status-badge status-cancelled">❌ CANC.</span></div>', unsafe_allow_html=True)

    # ============================================================
# CRUCERO
# ============================================================

st.markdown(
    '<div class="sh-group-hdr">CRUCERO · FECHAS · LOCALIZADOR</div>',
    unsafe_allow_html=True
)

barcos = getbarcos()

# ------------------------------------------------------------
# FILA 7
# ------------------------------------------------------------

r7 = st.columns([0.3, 1, 3, 1, 2], gap="small")

with r7[0]:
    st.markdown(
        '<div class="sh-rownum" style="height:32px;">7</div>',
        unsafe_allow_html=True
    )

with r7[1]:
    st.markdown(
        '<div class="sh-lbl" style="height:32px;">Barco</div>',
        unsafe_allow_html=True
    )

with r7[2]:

    barco_sel = st.selectbox(
        "barco",
        options=[""] + barcos,
        index=(
            [""] + barcos
        ).index(st.session_state.get("nc_barco", ""))
        if st.session_state.get("nc_barco", "") in barcos
        else 0,
        key="nc_barco_widget"
    )

    st.session_state.nc_barco = barco_sel

with r7[3]:
    st.markdown(
        '<div class="sh-lbl" style="height:32px;">Salida</div>',
        unsafe_allow_html=True
    )

with r7[4]:

    fecha_salida = st.date_input(
        "fecha_salida",
        value=st.session_state.get("nc_fecha_salida_loc", date.today()),
        format="DD/MM/YYYY",
        key="nc_fecha_salida_widget"
    )

    st.session_state.get("nc_fecha_salida_loc", date.today()) = fecha_salida

# ------------------------------------------------------------
# FILA 8
# ------------------------------------------------------------

r8 = st.columns([0.3, 1, 1.5, 1, 1.5], gap="small")

with r8[0]:
    st.markdown(
        '<div class="sh-rownum" style="height:32px;">8</div>',
        unsafe_allow_html=True
    )

with r8[1]:
    st.markdown(
        '<div class="sh-lbl" style="height:32px;">Días</div>',
        unsafe_allow_html=True
    )

with r8[2]:

    dias = st.number_input(
        "dias",
        min_value=1,
        step=1,
        value=st.session_state.get("nc_dias", 1),
        key="nc_dias_widget"
    )

    st.session_state.get("nc_dias", 1) = dias

with r8[3]:
    st.markdown(
        '<div class="sh-lbl" style="height:32px;">Noches</div>',
        unsafe_allow_html=True
    )

with r8[4]:

    noches = max(dias - 1, 0)

    st.markdown(
        f'''
        <div class="sh-val-info" style="height:32px;">
            {noches}
        </div>
        ''',
        unsafe_allow_html=True
    )

# ------------------------------------------------------------
# FILA 9
# ------------------------------------------------------------

fecha_llegada = fecha_salida + timedelta(days=dias - 1)

r9 = st.columns([0.3, 1, 2], gap="small")

with r9[0]:
    st.markdown(
        '<div class="sh-rownum" style="height:32px;">9</div>',
        unsafe_allow_html=True
    )

with r9[1]:
    st.markdown(
        '<div class="sh-lbl" style="height:32px;">Llegada</div>',
        unsafe_allow_html=True
    )

with r9[2]:

    st.markdown(
        f'''
        <div class="sh-val-info" style="height:32px;">
            {fecha_llegada.strftime("%d/%m/%Y")}
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    
    
    
    # ── BLOQUE LOCALIZADOR ────────────────────────────────────
    st.markdown('<div class="sh-group-hdr">LOCALIZADOR CRUCEMUNDO</div>', unsafe_allow_html=True)

    LOCALIZADOR_REMOTE_ID = "1c1oiBTLDRtDAAKQp8hE7uA1FfStp4DJAYhwa7F_yCNQ"

    SHIPCODEMAP = {
        "MS_ALBERTINA":      "ALB",
        "MS_ARENA":          "ARN",
        "MS_CRUCEVITA":      "CV",
        "MS_DOURO_CRUISER":  "DC",
        "MS_FIDELIO":        "FID",
        "MS_LEONORA":        "LEO",
        "MS_RIVER_DIAMOND":  "RDA",
        "MS_RIVER_SAPPHIRE": "RSA",
        "MS_SWISS_SPLENDOR": "SPL",
        "MS_VISTA_GRACIA":   "VGR",
        "MS_VISTAMILLA":     "VMI",
        "MS_VISTA_RIO":      "VRI",
        "MS_CRUCE_RIO":      "CRI",
    }


r10 = st.columns([0.3, 1, 1.2, 3], gap="small")

with r10[0]:
    st.markdown(
        '<div class="sh-rownum" style="height:32px;">10</div>',
        unsafe_allow_html=True
    )

with r10[1]:
    st.markdown(
        '<div class="sh-lbl" style="height:32px;">Localizador</div>',
        unsafe_allow_html=True
    )

with r10[2]:

    generar_disabled = not (
        st.session_state.get("nc_barco")
        and st.session_state.get("nc_fecha_salida_loc")
    )

    if st.button(
        "⚡ Generar",
        key="btn_generar_localizador",
        disabled=generar_disabled
    ):

        if st.session_state.get("nc_localizador"):

            st.warning(
                "Ya existe un localizador generado."
            )

        else:

            try:

                with st.spinner("Generando localizador..."):

                    codigo = generar_localizador(
                        st.session_state.get("nc_barco", ""),
                        st.session_state.get("nc_fecha_salida_loc", date.today())
                    )

                st.session_state.nc_localizador = codigo

                st.rerun()

            except Exception as exc:

                st.error(str(exc))

with r10[3]:

    localizador = st.session_state.get(
        "nc_localizador",
        ""
    )

    if localizador:

        st.markdown(
            f'''
            <div class="loc-display">
                {localizador}
            </div>
            ''',
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            '''
            <div class="sh-val-info empty" style="height:32px;">
                pendiente de generar
            </div>
            ''',
            unsafe_allow_html=True
        )

    def generar_localizador(barco, fecha_salida):
        prefijo = SHIPCODEMAP.get(barco)
        if not prefijo:
            raise Exception(f"Barco no configurado: {barco}")
        anio2       = fecha_salida.strftime("%y")
        mes         = fecha_salida.strftime("%m")
        dia         = fecha_salida.strftime("%d")
        clave       = prefijo + anio2
        parte_fecha = anio2 + mes + dia
        service     = getsheetsservice()
        spreadsheet = service.spreadsheets().get(spreadsheetId=LOCALIZADOR_REMOTE_ID).execute()
        sheets      = spreadsheet.get("sheets", [])
        if len(sheets) < 2:
            raise Exception("El archivo remoto necesita al menos 2 hojas.")
        title_cont  = sheets[0]["properties"]["title"]
        title_reg   = sheets[1]["properties"]["title"]
        resp        = service.spreadsheets().values().get(
            spreadsheetId=LOCALIZADOR_REMOTE_ID, range=f"{title_cont}!A:B").execute()
        rows        = resp.get("values", [])
        contador    = 1
        fila_update = None
        for i, row in enumerate(rows):
            if row and str(row[0]).strip() == clave:
                contador    = int(row[1]) + 1 if len(row) > 1 and str(row[1]).isdigit() else 1
                fila_update = i + 1
                break
        if fila_update:
            service.spreadsheets().values().update(
                spreadsheetId=LOCALIZADOR_REMOTE_ID, range=f"{title_cont}!B{fila_update}",
                valueInputOption="RAW", body={"values": [[contador]]}).execute()
        else:
            service.spreadsheets().values().append(
                spreadsheetId=LOCALIZADOR_REMOTE_ID, range=f"{title_cont}!A:B",
                valueInputOption="RAW", insertDataOption="INSERT_ROWS",
                body={"values": [[clave, contador]]}).execute()
        codigo    = f"{prefijo}{parte_fecha}-{str(contador).zfill(3)}"
        from datetime import datetime as dt
        ahora     = dt.now().strftime("%d/%m/%Y %H:%M")
        fecha_str = fecha_salida.strftime("%d/%m/%Y")
        service.spreadsheets().values().append(
            spreadsheetId=LOCALIZADOR_REMOTE_ID, range=f"{title_reg}!A:D",
            valueInputOption="RAW", insertDataOption="INSERT_ROWS",
            body={"values": [[ahora, codigo, barco, fecha_str]]}).execute()
        return codigo

    # Fila 7 — Barco + Fecha + Generar
    r7 = st.columns([0.3, 0.8, 2.2, 0.8, 1.6, 0.8, 2], gap="small")
    with r7[0]: st.markdown('<div class="sh-rownum" style="height:32px;">7</div>', unsafe_allow_html=True)
    with r7[1]: st.markdown('<div class="sh-lbl" style="height:32px;">Barco</div>', unsafe_allow_html=True)
    with r7[2]:
        barco_options = [""] + list(SHIPCODEMAP.keys())
        barco_sel = st.selectbox("barco", options=barco_options,
            index=barco_options.index(st.session_state.get("nc_barco", ""))
                  if st.session_state.get("nc_barco", "") in barco_options else 0,
            key="nc_barco_widget",
            format_func=lambda x: x.replace("_", " ") if x else "— barco —")
        if barco_sel != st.session_state.get("nc_barco", ""):
            st.session_state.nc_barco = barco_sel
            st.session_state.nc_localizador = ""
            st.rerun()
    with r7[3]: st.markdown('<div class="sh-lbl" style="height:32px;">F. Salida</div>', unsafe_allow_html=True)
    with r7[4]:
        fecha_salida_loc = st.date_input("fecha_loc",
            value=st.session_state.get("nc_fecha_salida_loc", date.today()),
            format="DD/MM/YYYY", key="nc_fecha_salida_loc_widget")
        st.session_state.nc_fecha_salida_loc = fecha_salida_loc
    with r7[5]:
        generar_disabled = not (st.session_state.get("nc_barco") and st.session_state.get("nc_fecha_salida_loc"))
        if st.button("⚡ Generar", key="btn_generar_localizador", disabled=generar_disabled):
            if st.session_state.get("nc_localizador"):
                st.warning("Ya existe un localizador. Reinicia para generar uno nuevo.")
            else:
                try:
                    with st.spinner("Generando..."):
                        codigo = generar_localizador(
                            st.session_state.get("nc_barco", ""),
                            st.session_state.get("nc_fecha_salida_loc", date.today()))
                    st.session_state.nc_localizador = codigo
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error: {exc}")
    with r7[6]:
        loc_generado = st.session_state.get("nc_localizador", "")
        if loc_generado:
            st.markdown(f'<div style="height:32px;display:flex;align-items:center;padding:0 4px;"><span class="loc-display">{loc_generado}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="sh-val-info empty" style="height:32px;">pendiente de generar</div>', unsafe_allow_html=True)

# ============================================================
# CIERRE SHEET WRAP
# ============================================================
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
st.info("🚧 Próximas filas: Cabinas, Pax, Fechas de crucero, Observaciones...")
