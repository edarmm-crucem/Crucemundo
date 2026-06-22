# ============================================================
# PÁGINA: OCUPACION_GLOBAL
# Vista global de ocupación de todos los barcos y salidas
# ============================================================

import streamlit as st
import pytz
import re
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from collections import defaultdict

st.set_page_config(
    page_title="Ocupación Global – Crucemundo Hub",
    page_icon="favicon1.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Auth guard ────────────────────────────────────────────────────────────────
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

# ── Constantes ────────────────────────────────────────────────────────────────
LOGOID          = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGOURL         = f"https://lh3.googleusercontent.com/d/{LOGOID}"
FOLDER_CRM_ROOT = "1aPckLqAn_sKHaMJPBdA0hnW2jegT1rT-"   # carpeta raíz con todos los CRM
TIMEZONE        = pytz.timezone("Europe/Madrid")

# ── Helpers tiempo ────────────────────────────────────────────────────────────
def now():
    return datetime.now(pytz.utc).astimezone(TIMEZONE).replace(tzinfo=None)

def getsaludo():
    h = now().hour
    if 6 <= h < 14:  return "Buenos días"
    if 14 <= h < 21: return "Buenas tardes"
    return "Buenas noches"

DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Sin usuario"
SALUDO      = getsaludo()

# ── Google Services ───────────────────────────────────────────────────────────
@st.cache_resource
def _creds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcpserviceaccount"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )

def drive_svc():
    return build("drive", "v3", credentials=_creds())

def sheets_svc():
    return build("sheets", "v4", credentials=_creds())

# ── Descubrir CRMs en la carpeta raíz (estructura plana o con subcarpetas) ────
@st.cache_data(ttl=120)
def descubrir_crms() -> list:
    """
    Busca todos los Google Sheets dentro de FOLDER_CRM_ROOT (y subcarpetas 1 nivel).
    Devuelve lista de dicts: {id, name, barco, anio}
    Nombre esperado: BARCO_ANIO_CRM  (p.ej. MS_VISTA_RIO_2026_CRM)
    """
    svc = drive_svc()
    crms = []

    def _list_files(parent_id):
        items, token = [], None
        while True:
            res = svc.files().list(
                q=f"'{parent_id}' in parents and trashed=false",
                fields="nextPageToken, files(id,name,mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageSize=200,
                pageToken=token,
            ).execute()
            items.extend(res.get("files", []))
            token = res.get("nextPageToken")
            if not token:
                break
        return items

    raiz = _list_files(FOLDER_CRM_ROOT)
    for item in raiz:
        if item["mimeType"] == "application/vnd.google-apps.spreadsheet":
            _parse_crm(item, crms)
        elif item["mimeType"] == "application/vnd.google-apps.folder":
            # Un nivel de subcarpeta (por barco o año)
            for sub in _list_files(item["id"]):
                if sub["mimeType"] == "application/vnd.google-apps.spreadsheet":
                    _parse_crm(sub, crms)

    return sorted(crms, key=lambda x: (x["barco"], x["anio"]))

def _parse_crm(item: dict, out: list):
    """Extrae barco y año del nombre del CRM y lo añade a out."""
    name = item["name"].strip()
    # Patrón: cualquier_cosa_YYYY_CRM  (el año es 4 dígitos)
    m = re.search(r"_(\d{4})_CRM$", name, re.IGNORECASE)
    if not m:
        return
    anio  = m.group(1)
    barco = name[:m.start()].replace("_", " ").strip()
    out.append({"id": item["id"], "name": name, "barco": barco, "anio": anio})

# ── Leer salidas de un CRM ────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def leer_salidas_crm(crm_id: str) -> list:
    """Devuelve lista de títulos de hojas (salidas) del CRM."""
    try:
        ss = sheets_svc().spreadsheets().get(spreadsheetId=crm_id).execute()
        return [s["properties"]["title"] for s in ss.get("sheets", [])]
    except Exception:
        return []

# ── Calcular métricas de ocupación de una salida ─────────────────────────────
@st.cache_data(ttl=60)
def ocupacion_salida(crm_id: str, salida: str) -> dict:
    """
    Lee la hoja 'salida' del CRM y devuelve métricas de ocupación.
    Columnas esperadas: cabina(A) categoria(B) estado(C) agencia(D) pax(E) ...
    """
    try:
        result = sheets_svc().spreadsheets().values().get(
            spreadsheetId=crm_id,
            range=f"'{salida}'!A:E"
        ).execute()
        rows = result.get("values", [])
    except Exception:
        return {"error": True}

    if len(rows) < 2:
        return {"error": True}

    header = [h.lower().strip() for h in rows[0]]
    try:
        idx_est = header.index("estado")
        idx_pax = header.index("pax")
    except ValueError:
        return {"error": True}

    total, vendidas, reservas, libres, pax_total = 0, 0, 0, 0, 0
    for r in rows[1:]:
        if not r:
            continue
        # Ignorar filas de cupo (columna H/I) que no tienen cabina
        cabina_val = r[0].strip() if r else ""
        if not cabina_val or cabina_val.lower() in ("cabina", "cupo_agencia", ""):
            continue
        total += 1
        estado = r[idx_est].strip().upper() if idx_est < len(r) else "LIBRE"
        if estado == "VENDIDA":
            vendidas += 1
            try:
                pax_total += int(r[idx_pax]) if idx_pax < len(r) and r[idx_pax].strip() else 0
            except (ValueError, IndexError):
                pass
        elif estado == "RESERVA":
            reservas += 1
        else:
            libres += 1

    pct_vend = round(vendidas / total * 100, 1) if total else 0
    pct_res  = round(reservas / total * 100, 1) if total else 0

    return {
        "error":    False,
        "total":    total,
        "vendidas": vendidas,
        "reservas": reservas,
        "libres":   libres,
        "pax":      pax_total,
        "pct_vend": pct_vend,
        "pct_res":  pct_res,
    }

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800;900&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: "DM Sans", sans-serif;
    background: #F8FAFC !important;
}
[data-testid="stAppViewContainer"] { background: #F8FAFC !important; }
[data-testid="stHeader"]           { background: transparent !important; }
[data-testid="stSidebarNav"]       { display: none !important; }
section[data-testid="stSidebar"]   { display: none !important; }
.block-container, [data-testid="stMainBlockContainer"] {
    padding-top: 0 !important;
    padding-bottom: 2rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 1800px !important;
    margin: 0 auto !important;
}

/* ── Header ── */
.glob-header {
    padding: 0.8rem 0 0.6rem;
    display: flex; align-items: center; justify-content: space-between;
    gap: 1rem; margin-bottom: 0.5rem;
}
.glob-header-left { display: flex; align-items: center; gap: 1rem; }
.glob-logo        { height: 40px; width: auto; object-fit: contain; }
.glob-title       { font-size: 0.92rem; font-weight: 700; color: #1F2937; line-height: 1.2; }
.glob-sub         { font-size: 0.7rem; color: #6B7280; margin-top: 0.1rem; }
.glob-badge       { font-size: 1.1rem; font-weight: 900; color: #1E3A8A; letter-spacing: 0.03em; }

/* ── Filtros ── */
.filter-row { display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; margin-bottom: 1.2rem; }
.filter-chip {
    padding: 0.3rem 0.8rem; border-radius: 999px; font-size: 0.72rem; font-weight: 700;
    background: #E0ECFF; border: 1.5px solid #BFDBFE; color: #1E4FBF; cursor: pointer;
    transition: all 0.15s;
}
.filter-chip:hover { background: #BFDBFE; }

/* ── Tarjeta de barco ── */
.ship-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    padding: 1.2rem 1.4rem 1rem;
    margin-bottom: 1.6rem;
    box-shadow: 0 1px 4px rgba(15,23,42,0.06);
}
.ship-card-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 1rem; gap: 0.6rem;
}
.ship-name {
    font-size: 1rem; font-weight: 900; color: #0F172A;
    letter-spacing: 0.01em; display: flex; align-items: center; gap: 0.5rem;
}
.ship-year {
    font-size: 0.68rem; font-weight: 700; color: #64748B;
    background: #F1F5F9; border: 1px solid #CBD5E1;
    padding: 0.15rem 0.55rem; border-radius: 999px;
}
.ship-summary {
    font-size: 0.7rem; color: #94A3B8; font-weight: 600;
}

/* ── Grid de salidas ── */
.departures-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 0.75rem;
}

/* ── Tarjeta de salida ── */
.dep-card {
    border-radius: 12px;
    border: 1.5px solid #E2E8F0;
    padding: 0.85rem 1rem 0.7rem;
    background: #FAFAFA;
    position: relative;
    overflow: hidden;
    transition: box-shadow 0.15s;
}
.dep-card:hover { box-shadow: 0 4px 16px rgba(15,23,42,0.09); }

/* Franja lateral de color según ocupación */
.dep-card::before {
    content: "";
    position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
    border-radius: 12px 0 0 12px;
}
.dep-card.full::before   { background: #EF4444; }
.dep-card.high::before   { background: #F97316; }
.dep-card.mid::before    { background: #EAB308; }
.dep-card.low::before    { background: #22C55E; }
.dep-card.empty::before  { background: #CBD5E1; }
.dep-card.err::before    { background: #E2E8F0; }

.dep-date {
    font-size: 0.78rem; font-weight: 800; color: #1F2937;
    letter-spacing: 0.04em; margin-bottom: 0.55rem;
}

/* Barra de ocupación */
.occ-bar-wrap {
    background: #E5E7EB; border-radius: 6px; height: 10px;
    width: 100%; overflow: hidden; margin-bottom: 0.3rem;
}
.occ-bar-fill {
    height: 10px; border-radius: 6px;
    transition: width 0.4s ease;
}

/* Metrics row */
.dep-metrics {
    display: flex; justify-content: space-between;
    margin-top: 0.5rem; gap: 0.2rem;
}
.dep-metric {
    display: flex; flex-direction: column; align-items: center;
    flex: 1;
}
.dep-metric-val {
    font-size: 0.9rem; font-weight: 800; color: #0F172A; line-height: 1.1;
}
.dep-metric-lbl {
    font-size: 0.57rem; font-weight: 700; color: #94A3B8;
    text-transform: uppercase; letter-spacing: 0.08em;
}
.dep-metric-lbl-en {
    font-size: 0.52rem; font-style: italic; color: #CBD5E1;
}

.dep-pct-big {
    font-size: 1.35rem; font-weight: 900; line-height: 1;
    margin-bottom: 0.1rem;
}
.dep-res-tag {
    font-size: 0.62rem; font-weight: 700;
    padding: 1px 6px; border-radius: 999px;
    background: #FEF3C7; color: #92400E;
    display: inline-block; margin-top: 0.25rem;
}
.dep-err {
    font-size: 0.72rem; color: #94A3B8; font-style: italic;
    padding: 0.5rem 0;
}

/* ── KPI globales ── */
.kpi-row {
    display: flex; gap: 1rem; margin-bottom: 1.4rem; flex-wrap: wrap;
}
.kpi-card {
    flex: 1; min-width: 140px;
    background: #FFFFFF; border: 1px solid #E2E8F0;
    border-radius: 14px; padding: 0.8rem 1rem;
    box-shadow: 0 1px 3px rgba(15,23,42,0.05);
}
.kpi-val  { font-size: 1.6rem; font-weight: 900; color: #0F172A; line-height: 1.1; }
.kpi-lbl  { font-size: 0.68rem; font-weight: 700; color: #64748B;
            text-transform: uppercase; letter-spacing: 0.08em; margin-top: 0.2rem; }
.kpi-lbl-en { font-size: 0.6rem; font-style: italic; color: #CBD5E1; }

/* ── Separador ── */
.section-divider {
    border: none; border-top: 1.5px solid #E2E8F0; margin: 0.6rem 0 1.4rem;
}

/* ── Estado vacío ── */
.empty-state {
    text-align: center; padding: 3rem 1rem; color: #94A3B8;
    font-size: 0.9rem; font-weight: 600;
}

div.stButton > button {
    border-radius: 999px !important; padding: 0 1rem !important;
    font-size: 0.78rem !important; font-weight: 800 !important;
    border: 2px solid transparent !important;
    background: linear-gradient(180deg, #2F6DF6 0%, #245FE0 100%) !important;
    color: #fff !important;
    box-shadow: 0 4px 14px rgba(37,99,235,0.2) !important;
    transition: transform .15s, box-shadow .15s !important;
    font-family: "DM Sans", sans-serif !important;
}
div.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(37,99,235,0.28) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Cabecera ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="glob-header">
    <div class="glob-header-left">
        <img class="glob-logo" src="{LOGOURL}" alt="Logo">
        <div>
            <div class="glob-title">{SALUDO}, <strong>{DISPLAYUSER}</strong></div>
            <div class="glob-sub">Panel Global de Ocupación · Global Occupancy Dashboard</div>
        </div>
    </div>
    <div class="glob-badge">🌍 Flota Global · {datetime.now().year}</div>
</div>
<hr class="section-divider">
""", unsafe_allow_html=True)

# ── Botón de refresco + back ──────────────────────────────────────────────────
col_back, col_ref, col_sp = st.columns([1, 1, 8])
with col_back:
    if st.button("← Hub", key="back_hub"):
        st.switch_page("app.py")
with col_ref:
    if st.button("🔄 Actualizar", key="refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Cargar CRMs disponibles ───────────────────────────────────────────────────
with st.spinner("Descubriendo barcos y salidas… / *Discovering ships and departures…*"):
    crms = descubrir_crms()

if not crms:
    st.markdown(
        '<div class="empty-state">🔍 No se encontraron CRMs en la carpeta configurada.<br>'
        '<span style="font-size:0.8rem;font-style:italic;">No CRMs found in the configured folder.</span></div>',
        unsafe_allow_html=True
    )
    st.stop()

# ── Filtros (años disponibles) ────────────────────────────────────────────────
anios_disponibles = sorted(list(set(c["anio"] for c in crms)), reverse=True)
barcos_disponibles = sorted(list(set(c["barco"] for c in crms)))

col_f1, col_f2, col_f3 = st.columns([2, 3, 5])
with col_f1:
    anio_sel = st.selectbox(
        "Año / Year",
        ["Todos / All"] + anios_disponibles,
        index=1 if len(anios_disponibles) > 0 else 0,
        key="sel_anio"
    )
with col_f2:
    barco_sel = st.selectbox(
        "Barco / Ship",
        ["Todos / All"] + barcos_disponibles,
        key="sel_barco"
    )
with col_f3:
    umbral_pct = st.slider(
        "Mostrar solo salidas con ocupación ≥ / Show departures with occupancy ≥",
        min_value=0, max_value=100, value=0, step=5,
        format="%d%%"
    )

# Filtrar CRMs según selección
crms_filtrados = [
    c for c in crms
    if (anio_sel == "Todos / All" or c["anio"] == anio_sel)
    and (barco_sel == "Todos / All" or c["barco"] == barco_sel)
]

if not crms_filtrados:
    st.info("No hay datos para los filtros seleccionados. / *No data for the selected filters.*")
    st.stop()

# ── Recoger todos los datos ───────────────────────────────────────────────────
# Estructura: {barco: {anio: {salida: metricas}}}
datos_flota = defaultdict(lambda: defaultdict(dict))
total_vendidas_global = 0
total_reservas_global = 0
total_cabinas_global  = 0
total_pax_global      = 0
n_salidas_global      = 0

progress = st.progress(0.0, text="Cargando datos de ocupación…")
total_crms = len(crms_filtrados)

for idx_crm, crm in enumerate(crms_filtrados):
    salidas = leer_salidas_crm(crm["id"])
    for sal in salidas:
        metricas = ocupacion_salida(crm["id"], sal)
        if metricas.get("error"):
            continue
        pct = metricas["pct_vend"]
        if pct < umbral_pct:
            continue
        datos_flota[crm["barco"]][crm["anio"]][sal] = metricas
        total_vendidas_global += metricas["vendidas"]
        total_reservas_global += metricas["reservas"]
        total_cabinas_global  += metricas["total"]
        total_pax_global      += metricas["pax"]
        n_salidas_global      += 1
    progress.progress((idx_crm + 1) / total_crms,
                      text=f"Procesando {crm['barco']} {crm['anio']}…")

progress.empty()

pct_global = round(total_vendidas_global / total_cabinas_global * 100, 1) if total_cabinas_global else 0

# ── KPIs globales ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="kpi-row">
    <div class="kpi-card">
        <div class="kpi-val">{pct_global}%</div>
        <div class="kpi-lbl">Ocupación Global<div class="kpi-lbl-en">Global Occupancy</div></div>
    </div>
    <div class="kpi-card">
        <div class="kpi-val">{total_vendidas_global:,}</div>
        <div class="kpi-lbl">Cabinas Vendidas<div class="kpi-lbl-en">Sold Cabins</div></div>
    </div>
    <div class="kpi-card">
        <div class="kpi-val">{total_reservas_global:,}</div>
        <div class="kpi-lbl">En Reserva<div class="kpi-lbl-en">On Hold</div></div>
    </div>
    <div class="kpi-card">
        <div class="kpi-val">{total_pax_global:,}</div>
        <div class="kpi-lbl">Pax Confirmados<div class="kpi-lbl-en">Confirmed Pax</div></div>
    </div>
    <div class="kpi-card">
        <div class="kpi-val">{n_salidas_global}</div>
        <div class="kpi-lbl">Salidas Activas<div class="kpi-lbl-en">Active Departures</div></div>
    </div>
    <div class="kpi-card">
        <div class="kpi-val">{len(crms_filtrados)}</div>
        <div class="kpi-lbl">Barcos<div class="kpi-lbl-en">Ships</div></div>
    </div>
</div>
<hr class="section-divider">
""", unsafe_allow_html=True)

# ── Helpers visualización ─────────────────────────────────────────────────────
def _color_barra(pct: float) -> str:
    if pct >= 90: return "#EF4444"
    if pct >= 70: return "#F97316"
    if pct >= 40: return "#EAB308"
    return "#22C55E"

def _clase_card(pct: float) -> str:
    if pct >= 90: return "full"
    if pct >= 70: return "high"
    if pct >= 40: return "mid"
    if pct > 0:   return "low"
    return "empty"

def _render_dep_card(sal: str, m: dict) -> str:
    pct      = m["pct_vend"]
    pct_res  = m["pct_res"]
    color    = _color_barra(pct)
    clase    = _clase_card(pct)
    pct_txt  = f'<span style="color:{color};">{pct}%</span>'
    barra    = (
        f'<div class="occ-bar-wrap">'
        f'<div class="occ-bar-fill" style="width:{pct}%;background:{color};"></div>'
        f'</div>'
    )
    res_tag  = (
        f'<span class="dep-res-tag">+{pct_res}% RVA</span>'
        if pct_res > 0 else ""
    )
    return f"""
    <div class="dep-card {clase}">
        <div class="dep-date">📅 {sal}</div>
        <div class="dep-pct-big">{pct_txt}</div>
        {barra}
        {res_tag}
        <div class="dep-metrics">
            <div class="dep-metric">
                <span class="dep-metric-val" style="color:#991B1B;">{m['vendidas']}</span>
                <span class="dep-metric-lbl">Vend.<span class="dep-metric-lbl-en">Sold</span></span>
            </div>
            <div class="dep-metric">
                <span class="dep-metric-val" style="color:#92400E;">{m['reservas']}</span>
                <span class="dep-metric-lbl">Res.<span class="dep-metric-lbl-en">Hold</span></span>
            </div>
            <div class="dep-metric">
                <span class="dep-metric-val" style="color:#6B7280;">{m['libres']}</span>
                <span class="dep-metric-lbl">Lib.<span class="dep-metric-lbl-en">Free</span></span>
            </div>
            <div class="dep-metric">
                <span class="dep-metric-val" style="color:#1E3A8A;">{m['pax']}</span>
                <span class="dep-metric-lbl">Pax</span>
            </div>
        </div>
    </div>
    """

# ── Render por barco ──────────────────────────────────────────────────────────
if not datos_flota:
    st.markdown(
        '<div class="empty-state">📭 Sin salidas que superen el umbral configurado.<br>'
        '<span style="font-size:0.8rem;font-style:italic;">No departures above the configured threshold.</span></div>',
        unsafe_allow_html=True
    )
    st.stop()

for barco in sorted(datos_flota.keys()):
    for anio in sorted(datos_flota[barco].keys(), reverse=True):
        salidas_barco = datos_flota[barco][anio]
        if not salidas_barco:
            continue

        # Métricas resumen del barco
        tot_v   = sum(m["vendidas"] for m in salidas_barco.values())
        tot_t   = sum(m["total"]    for m in salidas_barco.values())
        tot_r   = sum(m["reservas"] for m in salidas_barco.values())
        tot_p   = sum(m["pax"]      for m in salidas_barco.values())
        pct_b   = round(tot_v / tot_t * 100, 1) if tot_t else 0
        n_sal   = len(salidas_barco)
        color_b = _color_barra(pct_b)

        # Tarjetas de salida HTML
        cards_html = '<div class="departures-grid">'
        for sal in sorted(salidas_barco.keys()):
            cards_html += _render_dep_card(sal, salidas_barco[sal])
        cards_html += '</div>'

        st.markdown(f"""
        <div class="ship-card">
            <div class="ship-card-header">
                <div>
                    <div class="ship-name">
                        🚢 {barco}
                        <span class="ship-year">{anio}</span>
                    </div>
                    <div class="ship-summary">
                        {n_sal} salida{"s" if n_sal != 1 else ""} ·
                        {tot_v} vendidas · {tot_r} reservas · {tot_p} pax
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:1.6rem;font-weight:900;color:{color_b};">{pct_b}%</div>
                    <div style="font-size:0.65rem;color:#94A3B8;font-weight:700;text-transform:uppercase;">
                        Ocup. media · Avg. occ.
                    </div>
                </div>
            </div>
            {cards_html}
        </div>
        """, unsafe_allow_html=True)

# ── Leyenda ───────────────────────────────────────────────────────────────────
st.markdown("""
<hr class="section-divider">
<div style="display:flex;gap:1.5rem;flex-wrap:wrap;align-items:center;font-size:0.72rem;font-weight:700;color:#64748B;">
    <span>Leyenda / Legend:</span>
    <span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#22C55E;margin-right:4px;"></span>&lt;40% Baja / Low</span>
    <span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#EAB308;margin-right:4px;"></span>40-69% Media / Mid</span>
    <span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#F97316;margin-right:4px;"></span>70-89% Alta / High</span>
    <span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#EF4444;margin-right:4px;"></span>≥90% Completa / Full</span>
    <span style="margin-left:auto;font-size:0.65rem;color:#CBD5E1;">Crucemundo Hub · Ocupación Global</span>
</div>
""", unsafe_allow_html=True)
