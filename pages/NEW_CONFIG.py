# ============================================================
# NEW_CONFIG.py — Formulario compacto estilo spreadsheet
# ============================================================

import re
import streamlit as st
from datetime import date, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.set_page_config(
    page_title="Nueva Confirmación",
    page_icon="favicon1.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# CSS GLOBAL - FUENTE CENTURY GOTHIC
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Century+Gothic&display=swap');
    
    html, body, [class*="css"], .stTextInput, .stSelectbox, .stDateInput, .stNumberInput {
        font-family: 'Century Gothic', sans-serif !important;
    }
    
    .sheet-wrap { background: #fff; border: 1.5px solid #94A3B8; border-radius: 6px; overflow: hidden; padding: 0; }
    .sh-group-hdr { background: #1E3A8A; color: #BFDBFE; font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; padding: 5px 10px; border-bottom: 2px solid #2563EB; }
    .sh-lbl { background: #EFF6FF; border-right: 1px solid #CBD5E1; color: #1E40AF; font-size: 0.65rem; font-weight: 700; padding: 0 8px; display: flex; align-items: center; }
    .sh-val-info { background: #F8FAFF; border-right: 1px solid #CBD5E1; color: #1E3A8A; font-size: 0.75rem; font-weight: 600; padding: 0 8px; display: flex; align-items: center; }
    .sh-val-code { background: #DBEAFE; border-right: 1px solid #CBD5E1; color: #1D4ED8; font-family: monospace; font-size: 0.80rem; font-weight: 800; padding: 0 10px; display: flex; align-items: center; justify-content: center; }
    .sh-rownum { background: #F1F5F9; border-right: 1.5px solid #94A3B8; color: #94A3B8; font-family: monospace; font-size: 0.60rem; width: 26px; display: flex; align-items: center; justify-content: center; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# AUTH CHECK
# ============================================================
if not st.session_state.get("authenticated"):
    st.markdown('<div class="auth-warn">Acceso restringido</div>', unsafe_allow_html=True)
    st.stop()

# ============================================================
# CONSTANTES Y GOOGLE SERVICES
# ============================================================
LOGOID = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGOURL = f"https://lh3.googleusercontent.com/d/{LOGOID}"
AGENCYSHEETID = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
BARCOS_SHEET_ID = "1K-Tn_E3QEhCplOP-IFHbKZc-vtKAxFEUBbZVK14EjJI"
AGENCYFIELDS = ["Nombre", "CODIGO", "Grupo Gest", "Telefono", "Email", "Direccion", "COMISION AGENCIA", "COMISION AGENCIA CON OFERTA ", "COMISION AGENCIA OFERTA 2X1 ", "IVA", "IVA SERVICIO OPCIONAL"]
DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Usuario"

@st.cache_resource
def getsheetsservice():
    return build("sheets", "v4", credentials=service_account.Credentials.from_service_account_info(
        st.secrets["gcpserviceaccount"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]))

@st.cache_data(ttl=600)
def get_barcos_list():
    res = getsheetsservice().spreadsheets().values().get(spreadsheetId=BARCOS_SHEET_ID, range="A2:A").execute()
    return sorted(list(set([v[0] for v in res.get("values", []) if v])))

@st.cache_data(ttl=300)
def getagencias():
    service = getsheetsservice()
    response = service.spreadsheets().values().get(spreadsheetId=AGENCYSHEETID, range="Datos!A:K").execute()
    rows = response.get("values", [])
    agencies = []
    for idx, row in enumerate(rows, start=1):
        row = row + [""] * (11 - len(row))
        data = {"rownumber": idx}
        for i, field in enumerate(AGENCYFIELDS): data[field] = row[i]
        data["searchblob"] = " ".join(str(data.get(f, "") or "").strip().lower() for f in ["Nombre", "CODIGO", "Grupo Gest", "Telefono", "Email"])
        agencies.append(data)
    return agencies

def searchagencias(query):
    q = str(query or "").strip().lower()
    return [a for a in getagencias() if q in a["searchblob"]] if len(q) >= 2 else []

# ============================================================
# CABECERA Y UI
# ============================================================
st.markdown(f'<div class="doc-header">📋 PROFORMA · CONFIRMACIÓN</div>', unsafe_allow_html=True)
st.markdown('<div class="sheet-wrap">', unsafe_allow_html=True)


# ============================================================
# PARTE 2: LÓGICA DE UI Y BLOQUES
# ============================================================

# 1. TIPO DE CONFIRMACIÓN
if "nc_tipo" not in st.session_state: st.session_state.nc_tipo = None
st.markdown('<div class="sh-group-hdr">TIPO DE CONFIRMACIÓN / TYPE</div>', unsafe_allow_html=True)
# (Aquí iría tu lógica de botones si la tenías antes)

# 2. SECCIÓN AGENCIA
st.markdown('<div class="sh-group-hdr">AGENCIA / AGENCY</div>', unsafe_allow_html=True)
# --- [Tu lógica original de buscador de agencias aquí] ---

# 3. NUEVO BLOQUE: BARCO / FECHAS
st.markdown('<div class="sh-group-hdr">BARCO / FECHAS</div>', unsafe_allow_html=True)
c = st.columns([0.3, 1, 3, 1, 2, 0.5, 1, 0.5, 2], gap="small")

with c[0]: st.markdown('<div class="sh-rownum" style="height:35px;">7</div>', unsafe_allow_html=True)
with c[1]: st.markdown('<div class="sh-lbl" style="height:35px;">Barco</div>', unsafe_allow_html=True)
with c[2]: barco = st.selectbox("b", options=[""] + get_barcos_list(), key="nc_barco_widget")
with c[3]: st.markdown('<div class="sh-lbl" style="height:35px;">F. Salida</div>', unsafe_allow_html=True)
with c[4]: f_salida = st.date_input("fs", value=date.today(), format="DD/MM/YY")
with c[5]: st.markdown('<div class="sh-lbl" style="height:35px;">Días</div>', unsafe_allow_html=True)
with c[6]: dias = st.number_input("d", min_value=1, value=7, key="nc_dias_widget")
with c[7]: st.markdown('<div class="sh-lbl" style="height:35px;">Llegada</div>', unsafe_allow_html=True)
with c[8]:
    f_llegada = f_salida + timedelta(days=dias-1)
    st.markdown(f'<div class="sh-val-info" style="height:35px;">{f_llegada.strftime("%d/%m/%y")}</div>', unsafe_allow_html=True)

# 4. SECCIÓN LOCALIZADOR (Final)
st.markdown('<div class="sh-group-hdr">LOCALIZADOR CRUCEMUNDO</div>', unsafe_allow_html=True)
LOCALIZADOR_REMOTE_ID = "1c1oiBTLDRtDAAKQp8hE7uA1FfStp4DJAYhwa7F_yCNQ"

# --- [Pega aquí tu lógica original de 'generar_localizador'] ---

# --- [Cierre de la hoja] ---
st.markdown('</div>', unsafe_allow_html=True)

# --- [Tu código restante de pie de página o futuras filas] ---
st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
st.info("🚧 Próximas filas: Cabinas, Pax, Fechas de crucero, Observaciones...")


