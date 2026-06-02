
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

/* ===== GLOBAL RESET ===== */
.block-container {
    padding-top: 0.8rem;
    padding-bottom: 0.8rem;
    max-width: 95%;
}

/* Espaciado ultra compacto */
div[data-testid="stVerticalBlock"] > div {
    gap: 0.35rem;
}

/* ===== TIPOGRAFÍA ===== */
html, body, [class*="css"] {
    font-size: 13px;
}

/* Títulos */
h1, h2, h3 {
    margin-bottom: 4px !important;
}

/* ===== INPUTS ===== */
.stTextInput input, .stSelectbox div {
    padding: 4px 6px !important;
    font-size: 12.5px !important;
    border-radius: 4px !important;
}

/* ===== HEADER STYLE ===== */
.header-pro {
    border: 1px solid #9CA3AF;
    padding: 10px;
    border-radius: 6px;
    background: linear-gradient(180deg, #FAFAFA, #F3F4F6);
    font-size: 12.5px;
    line-height: 1.25;
}

/* ===== TARJETAS ===== */
.card-tipo {
    border-radius: 6px;
    padding: 8px;
    font-size: 12.5px;
    text-align: center;
    line-height: 1.2;
    transition: all 0.15s ease;
}

.card-tipo:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}

/* ===== TABLA PRO ===== */
.table-doc {
    border-collapse: collapse;
    width: 100%;
    font-size: 12.5px;
}

.table-doc th {
    background: #E5E7EB;
    border: 1px solid #6B7280;
    padding: 5px;
    text-align: left;
    font-weight: 600;
}

.table-doc td {
    border: 1px solid #9CA3AF;
    padding: 5px;
    vertical-align: middle;
}

/* labels tipo ERP */
.table-doc .label {
    background: #F3F4F6;
    font-weight: 600;
    width: 130px;
    color: #374151;
}

/* valores */
.table-doc .value {
    background: #FFFFFF;
}

/* resaltado */
.table-doc .highlight {
    font-weight: 600;
    color: #111827;
}

/* ===== BADGES ===== */
.badge-ok {
    background: #DCFCE7;
    border: 1px solid #16A34A;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
}

.badge-warning {
    background: #FEF3C7;
    border: 1px solid #D97706;
    padding: 4px 8px;
    border-radius: 4px;
}

.badge-error {
    background: #FEE2E2;
    border: 1px solid #DC2626;
    padding: 4px 8px;
    border-radius: 4px;
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
if sel:
    st.markdown(f"""
    <table class="table-doc">
    
    <tr>
        <th colspan="2">AGENCIA</th>
        <td colspan="2" class="highlight">{nombre or '—'}</td>
        <th>COD</th>
        <td class="highlight">{codigo or '—'}</td>
    </tr>
    
    <tr>
        <td class="label">Grupo</td>
        <td class="value">{grupo or '—'}</td>
    
        <td class="label">Teléfono</td>
        <td class="value">{telefono or '—'}</td>
    
        <td class="label">Email</td>
        <td class="value">{email or '—'}</td>
    </tr>
    
    <tr>
        <td class="label">Dirección</td>
        <td colspan="5" class="value">{direccion or '—'}</td>
    </tr>
    
    </table>
    
    """, unsafe_allow_html=True)

    # ============================================================
    # AGENTE / CLIENTE
    # ============================================================
    st.markdown("<div style='height:0.7rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="form-panel">', unsafe_allow_html=True)
    st.markdown('<div class="form-section-title">Agente / Cliente</div>', unsafe_allow_html=True)

    agente_cliente = st.text_input(
        "Nombre del agente o cliente / Agent or client name",
        value=st.session_state.get("nc_agente_cliente", ""),
        key="nc_agente_cliente_widget",
        placeholder="Ej: María García",
    )
    if agente_cliente != st.session_state.get("nc_agente_cliente", ""):
        st.session_state.nc_agente_cliente = agente_cliente

    st.markdown("</div>", unsafe_allow_html=True)

    # ============================================================
    # ESTADO RESERVA
    # ============================================================
    st.markdown('<div class="form-panel">', unsafe_allow_html=True)
    st.markdown('<div class="form-section-title">Estado de la Reserva / Booking Status</div>', unsafe_allow_html=True)

    ESTADOS = ["", "CONFIRMADO", "NO CONFIRMADO", "CANCELADO"]
    estado_actual = st.session_state.get("nc_estado_reserva", "")

    estado_sel = st.selectbox(
        "Estado / Status",
        options=ESTADOS,
        index=ESTADOS.index(estado_actual) if estado_actual in ESTADOS else 0,
        key="nc_estado_reserva_widget",
        format_func=lambda x: {
            "":              "— Selecciona un estado —",
            "CONFIRMADO":    "✅  CONFIRMADO",
            "NO CONFIRMADO": "⚠️  NO CONFIRMADO",
            "CANCELADO":     "❌  CANCELADO",
        }.get(x, x),
    )
    if estado_sel != st.session_state.get("nc_estado_reserva", ""):
        st.session_state.nc_estado_reserva = estado_sel

    # Badge visual del estado seleccionado
    if estado_sel == "CONFIRMADO":
    st.markdown('<div class="badge-ok">✅ CONFIRMADO</div>', unsafe_allow_html=True)

elif estado_sel == "NO CONFIRMADO":
    st.markdown('<div class="badge-warning">⚠️ NO CONFIRMADO</div>', unsafe_allow_html=True)

elif estado_sel == "CANCELADO":
    st.markdown('<div class="badge-error">❌ CANCELADO</div>', unsafe_allow_html=True)


# ============================================================
    # LOCALIZADOR CRUCEMUNDO
    # ============================================================
    LOCALIZADOR_REMOTE_ID = "1c1oiBTLDRtDAAKQp8hE7uA1FfStp4DJAYhwa7F_yCNQ"

    SHIPCODEMAP = {
        "MS_ALBERTINA":     "ALB",
        "MS_ARENA":         "ARN",
        "MS_CRUCEVITA":     "CV",
        "MS_DOURO_CRUISER": "DC",
        "MS_FIDELIO":       "FID",
        "MS_LEONORA":       "LEO",
        "MS_RIVER_DIAMOND": "RDA",
        "MS_RIVER_SAPPHIRE":"RSA",
        "MS_SWISS_SPLENDOR":"SPL",
        "MS_VISTA_GRACIA":  "VGR",
        "MS_VISTAMILLA":    "VMI",
        "MS_VISTA_RIO":     "VRI",
        "MS_CRUCE_RIO":     "CRI",
    }

    def generar_localizador(barco, fecha_salida):
        """
        Replica MASTER_CONFIRMATION_GeneraLOCALIZADOR en Python.
        - Hoja índice 0 del remoto: contadores  (col A = clave, col B = valor)
        - Hoja índice 1 del remoto: registro    (timestamp, codigo, barco, fecha)
        Devuelve el código generado o lanza Exception.
        """
        prefijo = SHIPCODEMAP.get(barco)
        if not prefijo:
            raise Exception(f"Barco no configurado: {barco}")

        anio2      = fecha_salida.strftime("%y")
        mes        = fecha_salida.strftime("%m")
        dia        = fecha_salida.strftime("%d")
        clave      = prefijo + anio2          # ej: VRI26
        parte_fecha = anio2 + mes + dia       # ej: 260522

        service = getsheetsservice()

        # ── Leer hoja contadores (índice 0) ──────────────────
        spreadsheet  = service.spreadsheets().get(
            spreadsheetId=LOCALIZADOR_REMOTE_ID
        ).execute()
        sheets       = spreadsheet.get("sheets", [])
        if len(sheets) < 2:
            raise Exception("El archivo remoto necesita al menos 2 hojas.")

        title_cont = sheets[0]["properties"]["title"]
        title_reg  = sheets[1]["properties"]["title"]

        resp = service.spreadsheets().values().get(
            spreadsheetId=LOCALIZADOR_REMOTE_ID,
            range=f"{title_cont}!A:B",
        ).execute()
        rows = resp.get("values", [])

        contador    = 1
        fila_update = None

        for i, row in enumerate(rows):
            if row and str(row[0]).strip() == clave:
                contador    = int(row[1]) + 1 if len(row) > 1 and str(row[1]).isdigit() else 1
                fila_update = i + 1   # 1-based
                break

        # ── Actualizar o crear contador ───────────────────────
        if fila_update:
            service.spreadsheets().values().update(
                spreadsheetId=LOCALIZADOR_REMOTE_ID,
                range=f"{title_cont}!B{fila_update}",
                valueInputOption="RAW",
                body={"values": [[contador]]},
            ).execute()
        else:
            service.spreadsheets().values().append(
                spreadsheetId=LOCALIZADOR_REMOTE_ID,
                range=f"{title_cont}!A:B",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [[clave, contador]]},
            ).execute()

        # ── Generar código ────────────────────────────────────
        codigo = f"{prefijo}{parte_fecha}-{str(contador).zfill(3)}"

        # ── Registrar en hoja índice 1 ────────────────────────
        from datetime import datetime as dt
        ahora    = dt.now().strftime("%d/%m/%Y %H:%M")
        fecha_str = fecha_salida.strftime("%d/%m/%Y")

        service.spreadsheets().values().append(
            spreadsheetId=LOCALIZADOR_REMOTE_ID,
            range=f"{title_reg}!A:D",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [[ahora, codigo, barco, fecha_str]]},
        ).execute()

        return codigo

    # ── UI del bloque localizador ─────────────────────────────
    st.markdown('<div class="form-panel">', unsafe_allow_html=True)
    st.markdown('<div class="form-section-title">Localizador Crucemundo</div>', unsafe_allow_html=True)

    loc_col1, loc_col2, loc_col3 = st.columns([2, 2, 1], gap="medium")

    with loc_col1:
        barco_options = [""] + list(SHIPCODEMAP.keys())
        barco_sel = st.selectbox(
            "Barco / Ship",
            options=barco_options,
            index=barco_options.index(st.session_state.get("nc_barco", ""))
                  if st.session_state.get("nc_barco", "") in barco_options else 0,
            key="nc_barco_widget",
            format_func=lambda x: x.replace("_", " ") if x else "— Selecciona barco —",
        )
        if barco_sel != st.session_state.get("nc_barco", ""):
            st.session_state.nc_barco       = barco_sel
            st.session_state.nc_localizador = ""
            st.rerun()

    with loc_col2:
        fecha_salida_loc = st.date_input(
            "Fecha de salida / Departure date",
            value=st.session_state.get("nc_fecha_salida_loc", date.today()),
            format="DD/MM/YYYY",
            key="nc_fecha_salida_loc_widget",
        )
        st.session_state.nc_fecha_salida_loc = fecha_salida_loc

    with loc_col3:
        st.markdown("<div style='height:1.82rem'></div>", unsafe_allow_html=True)
        generar_disabled = not (
            st.session_state.get("nc_barco") and
            st.session_state.get("nc_fecha_salida_loc")
        )
        if st.button("⚡ Generar", key="btn_generar_localizador", disabled=generar_disabled):
            if st.session_state.get("nc_localizador"):
                st.warning("Ya existe un localizador generado para esta confirmación. Reinicia si quieres uno nuevo.")
            else:
                try:
                    with st.spinner("Generando localizador..."):
                        codigo = generar_localizador(
                            st.session_state.nc_barco,
                            st.session_state.nc_fecha_salida_loc,
                        )
                    st.session_state.nc_localizador = codigo
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error generando localizador: {exc}")

    # ── Mostrar resultado ─────────────────────────────────────
    loc_generado = st.session_state.get("nc_localizador", "")
    if loc_generado:
        st.markdown(f"""
        <div style="margin-top:0.7rem;display:flex;align-items:center;gap:1rem;
             background:#F0FDF4;border:1.5px solid #86EFAC;border-radius:10px;
             padding:0.7rem 1rem;">
            <div style="font-size:0.72rem;font-weight:700;color:#166534;
                 text-transform:uppercase;letter-spacing:0.08em;">
                Localizador asignado
            </div>
            <div style="font-size:1.15rem;font-weight:900;color:#1E3A8A;
                 letter-spacing:0.08em;font-family:monospace;">
                {loc_generado}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="margin-top:0.6rem;background:#F8FAFC;border:1.5px dashed #CBD5E1;
             border-radius:10px;padding:0.65rem 1rem;font-size:0.78rem;
             color:#94A3B8;font-weight:600;">
            Selecciona barco y fecha, luego pulsa ⚡ Generar
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="form-panel" style="border-color:#FCD34D;background:#FFFBEB;">', unsafe_allow_html=True)
    st.markdown('<div class="form-section-title" style="color:#92400E;">Localizador Crucemundo</div>', unsafe_allow_html=True)
    st.warning("⏳ Pendiente de integrar el script de asignación automática de localizador. Pega el script y lo conectamos.")
    st.markdown("</div>", unsafe_allow_html=True)


    

    st.info("🚧 Próximos campos: Agente/Cliente, Estado Reserva, Localizador, Barco, Fechas, Cabinas, Pax...")
