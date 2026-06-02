# ============================================================
# NEW_CONFIG.py — VERSION COMPLETA LIMPIA
# ============================================================

import re
import streamlit as st
from datetime import date, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.set_page_config(
    page_title="Nueva Confirmación",
    layout="wide",
)

# ============================================================
# CSS LIMPIO TIPO EXCEL
# ============================================================

st.markdown("""
<style>

html, body, [class*="css"] {
    font-family: Arial, sans-serif;
    font-size: 13px;
}

/* etiqueta */
.cell-label {
    background: #f2f2f2;
    border: 1px solid #d0d0d0;
    padding: 6px;
    font-weight: 600;
}

/* valor */
.cell-value {
    background: #ffffff;
    border: 1px solid #d0d0d0;
    padding: 6px;
}

/* input */
.cell-input {
    background: #fffdf2;
    border: 2px solid #e6b800;
    padding: 4px;
    border-radius: 4px;
}

.block {
    margin-top: 10px;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================

today_str = date.today().strftime("%d/%m/%Y")
st.markdown(f"### 📋 PROFORMA · CONFIRMACIÓN — {today_str}")

# ============================================================
# GOOGLE
# ============================================================

@st.cache_resource
def get_creds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

@st.cache_resource
def get_service():
    return build("sheets", "v4", credentials=get_creds())

# ============================================================
# BLOQUE FECHAS (NUEVO)
# ============================================================

st.markdown('<div class="block">', unsafe_allow_html=True)

c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([1,2,1,2,1,2,1,2])

with c1:
    st.markdown('<div class="cell-label">Fecha salida</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="cell-input">', unsafe_allow_html=True)
    fecha_salida = st.date_input("fecha_salida", value=date.today(), label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown('<div class="cell-label">Noches</div>', unsafe_allow_html=True)

with c4:
    st.markdown('<div class="cell-input">', unsafe_allow_html=True)
    noches = st.number_input("noches", min_value=1, value=7, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

fecha_llegada = fecha_salida + timedelta(days=int(noches))
dias = int(noches) + 1

with c5:
    st.markdown('<div class="cell-label">Fecha llegada</div>', unsafe_allow_html=True)

with c6:
    st.markdown(f'<div class="cell-value">{fecha_llegada.strftime("%d/%m/%Y")}</div>', unsafe_allow_html=True)

with c7:
    st.markdown('<div class="cell-label">Días</div>', unsafe_allow_html=True)

with c8:
    st.markdown(f'<div class="cell-value">{dias}</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# ITINERARIO
# ============================================================

st.markdown('<div class="block">', unsafe_allow_html=True)

c9, c10 = st.columns([1,7])

with c9:
    st.markdown('<div class="cell-label">Itinerario</div>', unsafe_allow_html=True)

with c10:
    st.markdown('<div class="cell-input">', unsafe_allow_html=True)
    itinerario = st.text_area("itinerario", height=100, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# LOCALIZADOR (TU LOGICA SIMPLIFICADA VISUALMENTE)
# ============================================================

st.markdown('<div class="block">', unsafe_allow_html=True)

c11, c12, c13, c14 = st.columns([1,2,3,2])

with c11:
    st.markdown('<div class="cell-label">Localizador</div>', unsafe_allow_html=True)

with c12:
    if st.button("⚡ Generar"):
        codigo = f"CM-{fecha_salida.strftime('%y%m%d')}-{int(noches):03d}"
        st.session_state["loc"] = codigo

with c13:
    loc = st.session_state.get("loc", "")
    st.markdown(f'<div class="cell-value">{loc if loc else "Pendiente"}</div>', unsafe_allow_html=True)

with c14:
    if loc:
        if st.button("Reset"):
            st.session_state["loc"] = ""

st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# FIN
# ============================================================

st.success("✅ Formulario listo y estable")
