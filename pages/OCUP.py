# ============================================================
# PÁGINA: OCUP
# Panel global de ocupación por barco, salida y categoría
# ============================================================

import streamlit as st
import pytz
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from collections import defaultdict
import re

st.set_page_config(
    page_title="OCUP – Crucemundo Hub",
    page_icon="favicon1.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Auth guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("authenticated"):
    st.warning("Debes iniciar sesión primero. / Please log in first.")
    if st.button("← Volver al Hub"):
        st.switch_page("app.py")
    st.stop()

# ── Constantes ────────────────────────────────────────────────────────────────
LOGOID          = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGOURL         = f"https://lh3.googleusercontent.com/d/{LOGOID}"
FOLDER_CRM_ROOT = "1aPckLqAn_sKHaMJPBdA0hnW2jegT1rT-"
TIMEZONE        = pytz.timezone("Europe/Madrid")

# ── Helpers ───────────────────────────────────────────────────────────────────
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

# ── Descubrir CRMs ────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def descubrir_crms() -> list:
    svc = drive_svc()
    crms = []

    def _list(parent_id):
        items, token = [], None
        while True:
            res = svc.files().list(
                q=f"'{parent_id}' in parents and trashed=false",
                fields="nextPageToken, files(id,name,mimeType)",
                supportsAllDrives=True, includeItemsFromAllDrives=True,
                pageSize=200, pageToken=token,
            ).execute()
            items.extend(res.get("files", []))
            token = res.get("nextPageToken")
            if not token:
                break
        return items

    for item in _list(FOLDER_CRM_ROOT):
        if item["mimeType"] == "application/vnd.google-apps.spreadsheet":
            _parse(item, crms)
        elif item["mimeType"] == "application/vnd.google-apps.folder":
            for sub in _list(item["id"]):
                if sub["mimeType"] == "application/vnd.google-apps.spreadsheet":
                    _parse(sub, crms)

    return sorted(crms, key=lambda x: (x["barco"], x["anio"]))

def _parse(item, out):
    name = item["name"].strip()
    m = re.search(r"_(\d{4})_CRM$", name, re.IGNORECASE)
    if not m:
        return
    anio  = m.group(1)
    barco = name[:m.start()].replace("_", " ").strip()
    out.append({"id": item["id"], "name": name, "barco": barco, "anio": anio})

# ── Leer salidas de un CRM ────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def leer_salidas_crm(crm_id: str) -> list:
    try:
        ss = sheets_svc().spreadsheets().get(spreadsheetId=crm_id).execute()
        return [s["properties"]["title"] for s in ss.get("sheets", [])]
    except Exception:
        return []

# ── Ocupación por categoría de una salida ────────────────────────────────────
@st.cache_data(ttl=60)
def ocupacion_por_categoria(crm_id: str, salida: str) -> dict:
    """
    Lee la hoja y devuelve:
    {cat: {vendidas, reservas, libres, total}}
    Columnas: cabina(A) categoria(B) estado(C)
    """
    try:
        result = sheets_svc().spreadsheets().values().get(
            spreadsheetId=crm_id,
            range=f"'{salida}'!A:C"
        ).execute()
        rows = result.get("values", [])
    except Exception:
        return {}

    if len(rows) < 2:
        return {}

    header = [h.lower().strip() for h in rows[0]]
    try:
        idx_cat = header.index("categoria")
        idx_est = header.index("estado")
    except ValueError:
        return {}

    por_cat = defaultdict(lambda: {"vendidas": 0, "reservas": 0, "libres": 0, "total": 0})

    for r in rows[1:]:
        if not r:
            continue
        cabina_val = r[0].strip() if r else ""
        # Ignorar filas vacías o de configuración de cupos
        if not cabina_val or cabina_val.lower() in ("cabina", "cupo_agencia", ""):
            continue
        cat    = r[idx_cat].strip() if idx_cat < len(r) else ""
        estado = r[idx_est].strip().upper() if idx_est < len(r) else "LIBRE"
        if not cat:
            continue
        por_cat[cat]["total"] += 1
        if estado == "VENDIDA":
            por_cat[cat]["vendidas"] += 1
        elif estado == "RESERVA":
            por_cat[cat]["reservas"] += 1
        else:
            por_cat[cat]["libres"] += 1

    return dict(por_cat)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800;900&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: "DM Sans", sans-serif; background: #F8FAFC !important; }
[data-testid="stAppViewContainer"] { background: #F8FAFC !important; }
[data-testid="stHeader"]           { background: transparent !important; }
[data-testid="stSidebarNav"]       { display: none !important; }
section[data-testid="stSidebar"]   { display: none !important; }
.block-container, [data-testid="stMainBlockContainer"] {
    padding-top: 0 !important; padding-bottom: 2rem !important;
    padding-left: 1.5rem !important; padding-right: 1.5rem !important;
    max-width: 1800px !important; margin: 0 auto !important;
}

/* Header */
.glob-header { padding: 0.8rem 0 0.5rem; display: flex; align-items: center;
    justify-content: space-between; gap: 1rem; margin-bottom: 0.3rem; }
.glob-header-left { display: flex; align-items: center; gap: 1rem; }
.glob-logo   { height: 40px; width: auto; object-fit: contain; }
.glob-title  { font-size: 0.92rem; font-weight: 700; color: #1F2937; line-height: 1.2; }
.glob-sub    { font-size: 0.7rem; color: #6B7280; margin-top: 0.1rem; }
.glob-badge  { font-size: 1rem; font-weight: 900; color: #1E3A8A; }

/* Divider */
.hr { border: none; border-top: 1.5px solid #E2E8F0; margin: 0.5rem 0 1.2rem; }

/* Tarjeta barco */
.ship-card {
    background: #fff; border: 1px solid #E2E8F0; border-radius: 18px;
    padding: 1.1rem 1.3rem 1rem; margin-bottom: 2rem;
    box-shadow: 0 1px 4px rgba(15,23,42,0.06);
}
.ship-name {
    font-size: 1rem; font-weight: 900; color: #0F172A;
    display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.9rem;
}
.ship-year {
    font-size: 0.67rem; font-weight: 700; color: #64748B;
    background: #F1F5F9; border: 1px solid #CBD5E1;
    padding: 0.14rem 0.5rem; border-radius: 999px;
}

/* Grid salidas */
.departures-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 0.9rem;
}

/* Tarjeta salida */
.dep-card {
    border-radius: 14px; border: 1.5px solid #E2E8F0;
    padding: 0.9rem 1rem 0.8rem; background: #FAFAFA;
    position: relative; overflow: hidden;
    transition: box-shadow 0.15s;
}
.dep-card:hover { box-shadow: 0 4px 18px rgba(15,23,42,0.09); }

/* Franja lateral */
.dep-card::before {
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
    border-radius: 14px 0 0 14px;
}
.dep-card.full::before  { background: #EF4444; }
.dep-card.high::before  { background: #F97316; }
.dep-card.mid::before   { background: #EAB308; }
.dep-card.low::before   { background: #22C55E; }
.dep-card.empty::before { background: #CBD5E1; }

.dep-date {
    font-size: 0.8rem; font-weight: 800; color: #1F2937;
    letter-spacing: 0.03em; margin-bottom: 0.7rem;
}

/* Tabla de categorías dentro de la tarjeta */
.cat-table { width: 100%; border-collapse: collapse; font-size: 0.72rem; }
.cat-table th {
    color: #94A3B8; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.06em; padding: 0 0 0.3rem 0; text-align: right;
    font-size: 0.62rem;
}
.cat-table th:first-child { text-align: left; }
.cat-table td {
    padding: 0.22rem 0; border-top: 1px solid #F1F5F9;
    font-weight: 700; text-align: right; color: #1F2937;
    white-space: nowrap;
}
.cat-table td:first-child { text-align: left; color: #374151; font-weight: 800; }
.cat-table td.sold  { color: #991B1B; }
.cat-table td.hold  { color: #92400E; }
.cat-table td.free  { color: #6B7280; }
.cat-table td .pct  { font-weight: 600; color: #94A3B8; font-size: 0.62rem; }

/* % global salida */
.dep-pct {
    font-size: 1.3rem; font-weight: 900; line-height: 1;
    margin-bottom: 0.6rem;
}

div.stButton > button {
    border-radius: 999px !important; padding: 0 1rem !important;
    font-size: 0.78rem !important; font-weight: 800 !important;
    border: 2px solid transparent !important;
    background: linear-gradient(180deg, #2F6DF6 0%, #245FE0 100%) !important;
    color: #fff !important;
    box-shadow: 0 4px 14px rgba(37,99,235,0.2) !important;
    font-family: "DM Sans", sans-serif !important;
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
            <div class="glob-sub">Ocupación Global · Global Occupancy</div>
        </div>
    </div>
    <div class="glob-badge">🌍 Flota · {datetime.now().year}</div>
</div>
<hr class="hr">
""", unsafe_allow_html=True)

# ── Botones ───────────────────────────────────────────────────────────────────
col_back, col_ref, _ = st.columns([1, 1, 8])
with col_back:
    if st.button("← Hub"):
        st.switch_page("app.py")
with col_ref:
    if st.button("🔄 Actualizar"):
        st.cache_data.clear()
        st.rerun()

# ── Cargar CRMs ───────────────────────────────────────────────────────────────
with st.spinner("Descubriendo barcos… / *Discovering ships…*"):
    crms = descubrir_crms()

if not crms:
    st.info("No se encontraron CRMs en la carpeta configurada.")
    st.stop()

# ── Helpers de color ──────────────────────────────────────────────────────────
def _color(pct: float) -> str:
    if pct >= 90: return "#EF4444"
    if pct >= 70: return "#F97316"
    if pct >= 40: return "#EAB308"
    return "#22C55E"

def _clase(pct: float) -> str:
    if pct >= 90: return "full"
    if pct >= 70: return "high"
    if pct >= 40: return "mid"
    if pct > 0:   return "low"
    return "empty"

# ── Render tarjeta de salida ──────────────────────────────────────────────────
def _render_salida(sal: str, por_cat: dict) -> str:
    if not por_cat:
        return f"""
        <div class="dep-card empty">
            <div class="dep-date">📅 {sal}</div>
            <div style="font-size:0.72rem;color:#94A3B8;font-style:italic;">Sin datos / No data</div>
        </div>"""

    total_v = sum(v["vendidas"] for v in por_cat.values())
    total_t = sum(v["total"]   for v in por_cat.values())
    total_r = sum(v["reservas"] for v in por_cat.values())
    total_l = sum(v["libres"]  for v in por_cat.values())
    pct_v   = round(total_v / total_t * 100, 1) if total_t else 0
    color   = _color(pct_v)
    clase   = _clase(pct_v)

    # Tabla de categorías
    filas = ""
    for cat, m in sorted(por_cat.items()):
        t   = m["total"]
        v   = m["vendidas"]
        r   = m["reservas"]
        l   = m["libres"]
        pct_v_cat = round(v / t * 100) if t else 0
        pct_r_cat = round(r / t * 100) if t else 0
        pct_l_cat = round(l / t * 100) if t else 0
        filas += f"""
        <tr>
            <td>{cat}</td>
            <td>{t}</td>
            <td class="sold">{v} <span class="pct">({pct_v_cat}%)</span></td>
            <td class="hold">{r} <span class="pct">({pct_r_cat}%)</span></td>
            <td class="free">{l} <span class="pct">({pct_l_cat}%)</span></td>
        </tr>"""

    return f"""
    <div class="dep-card {clase}">
        <div class="dep-date">📅 {sal}</div>
        <div class="dep-pct" style="color:{color};">{pct_v}%
            <span style="font-size:0.65rem;color:#94A3B8;font-weight:600;margin-left:4px;">
                {total_v}V · {total_r}R · {total_l}L
            </span>
        </div>
        <table class="cat-table">
            <thead><tr>
                <th>Cat.</th>
                <th># Cab.</th>
                <th># Vend.</th>
                <th># Res.</th>
                <th># Lib.</th>
            </tr></thead>
            <tbody>{filas}</tbody>
        </table>
    </div>"""

# ── Render por barco ──────────────────────────────────────────────────────────
progress = st.progress(0.0, text="Cargando datos…")
total_crms = len(crms)

for idx_crm, crm in enumerate(crms):
    salidas = leer_salidas_crm(crm["id"])
    if not salidas:
        progress.progress((idx_crm + 1) / total_crms)
        continue

    cards_html = '<div class="departures-grid">'
    hay_datos = False

    for sal in sorted(salidas):
        por_cat = ocupacion_por_categoria(crm["id"], sal)
        cards_html += _render_salida(sal, por_cat)
        if por_cat:
            hay_datos = True

    cards_html += "</div>"

    if hay_datos:
        st.markdown(f"""
        <div class="ship-card">
            <div class="ship-name">
                🚢 {crm["barco"]}
                <span class="ship-year">{crm["anio"]}</span>
            </div>
            {cards_html}
        </div>
        """, unsafe_allow_html=True)

    progress.progress((idx_crm + 1) / total_crms,
                      text=f"Procesando {crm['barco']} {crm['anio']}…")

progress.empty()

# ── Leyenda ───────────────────────────────────────────────────────────────────
st.markdown("""
<hr class="hr">
<div style="display:flex;gap:1.5rem;flex-wrap:wrap;align-items:center;
            font-size:0.72rem;font-weight:700;color:#64748B;">
    <span>Leyenda:</span>
    <span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;
        background:#22C55E;margin-right:4px;"></span>&lt;40% Baja</span>
    <span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;
        background:#EAB308;margin-right:4px;"></span>40–69% Media</span>
    <span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;
        background:#F97316;margin-right:4px;"></span>70–89% Alta</span>
    <span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;
        background:#EF4444;margin-right:4px;"></span>≥90% Completa</span>
    <span style="margin-left:auto;font-size:0.65rem;color:#CBD5E1;">
        🔴 Vendidas · 🟡 Reservas · ⬜ Libres
    </span>
</div>
""", unsafe_allow_html=True)
