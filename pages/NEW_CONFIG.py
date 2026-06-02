# ============================================================
# NEW_CONFIG.py — Formulario compacto estilo spreadsheet
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
        </style>
        <div style="padding:1rem;background:#FEF3C7;border:1px solid #FCD34D;border-radius:10px;">
            ⚠️ Acceso restringido
        </div>
    """, unsafe_allow_html=True)
    st.stop()

# ============================================================
# CONSTANTES (mínimas por ahora)
# ============================================================
DISPLAYUSER = st.session_state.get("displayname", "Usuario")

# ============================================================
# CSS BASE (vacío inicial controlado)
# ============================================================
st.markdown("""
<style>
.cell-label {
    background: #f5f5f5;
    padding: 6px 8px;
    border: 1px solid #d0d0d0;
    font-weight: 600;
    height: 38px;
    display:flex;
    align-items:center;
}

.cell-value {
    background: #fff;
    padding: 6px 8px;
    border: 1px solid #d0d0d0;
    height: 38px;
    display:flex;
    align-items:center;
}

.sheet-row {
    margin-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER (SALUDO + USUARIO + LOGO)
# ============================================================
st.markdown(f"""
<div style="
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:6px 0 10px 0;
    border-bottom:1px solid #e5e7eb;
    margin-bottom:10px;
">

    <!-- IZQUIERDA -->
    <div style="display:flex;align-items:center;gap:12px;">
        <img src="https://lh3.googleusercontent.com/d/1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8" style="height:42px;">
        <div>
            <div style="font-size:15px;font-weight:700;color:#111827;">
                {SALUDO}, {DISPLAYUSER}
            </div>
            <div style="font-size:11px;color:#6b7280;">
                Nueva Confirmación / New Confirmation
            </div>
        </div>
    </div>

    <!-- DERECHA -->
    <div style="text-align:right;">
        <div style="font-size:18px;font-weight:800;color:#1f2937;">
            CRUCEMUNDO
        </div>
        <div style="font-size:11px;color:#6b7280;">
            Control Panel
        </div>
    </div>

</div>
""", unsafe_allow_html=True)


# ============================================================
# HEADER SIMPLE
# ============================================================
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
        <h4>📋 Nueva Confirmación</h4>
        <small>{DISPLAYUSER}</small>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# ESTADO INICIAL
# ============================================================
if "nc_tipo" not in st.session_state:
    st.session_state.nc_tipo = None

# ============================================================
# FILA 1 — TIPO DE CONFIRMACIÓN
# ============================================================
st.markdown("### Tipo de Confirmación / Confirmation Type")

row = st.columns([0.5, 2, 2, 2, 2, 3])

with row[0]:
    st.markdown('<div class="cell-label">1</div>', unsafe_allow_html=True)

with row[1]:
    st.markdown('<div class="cell-label">Tipo</div>', unsafe_allow_html=True)

with row[2]:
    if st.button("📘 FIT ES"):
        st.session_state.nc_tipo = "FIT_ES"

with row[3]:
    if st.button("📗 FIT EN"):
        st.session_state.nc_tipo = "FIT_EN"

with row[4]:
    if st.button("👥 GRUPOS"):
        st.session_state.nc_tipo = "GROUPS"

with row[5]:
    tipo = st.session_state.nc_tipo

    if tipo == "FIT_ES":
        st.markdown("📘 FIT ESPAÑOL seleccionado")
    elif tipo == "FIT_EN":
        st.markdown("📗 FIT ENGLISH selected")
    elif tipo == "GROUPS":
        st.markdown("👥 GRUPOS seleccionado")
    else:
        st.markdown("— sin seleccionar —")
