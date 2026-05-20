import streamlit as st
import pytz
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="MS VISTA RIO",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# AUTH
# ============================================================
if not st.session_state.get("authenticated"):
    st.warning("No tienes acceso. Vuelve al inicio.")
    st.stop()

# ============================================================
# CONSTANTES
# ============================================================
BARCO = "MS_VISTA_RIO"
MASTERCABINASID = "1K-Tn_E3QEhCplOP-IFHbKZc-vtKAxFEUBbZVK14EjJI"
CRMBARCO = "1ApNv3qK-_2ANOVwSZoOchAdwWaeQg0Evz-n54s6T2cE"
LOGOID = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGOURL = f"https://lh3.googleusercontent.com/d/{LOGOID}"

# ============================================================
# UTILIDADES
# ============================================================
TIMEZONE = pytz.timezone("Europe/Madrid")
def now():
    return datetime.now(pytz.utc).astimezone(TIMEZONE).replace(tzinfo=None)
def getsaludo(lang="es"):
    hour = now().hour
    if lang == "en":
        if 6 <= hour < 14: return "Good morning"
        if 14 <= hour < 21: return "Good afternoon"
        return "Good evening"
    if 6 <= hour < 14: return "Buenos días"
    if 14 <= hour < 21: return "Buenas tardes"
    return "Buenas noches"

DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Sin usuario"
SALUDO = getsaludo("es")
SALUDOEN = getsaludo("en")

# ============================================================
# GOOGLE SHEETS SERVICE
# ============================================================
@st.cache_resource
def getgooglecreds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcpserviceaccount"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )

def getsheetsservice():
    return build("sheets", "v4", credentials=getgooglecreds())

# ============================================================
# FUNCIONES SHEETS
# ============================================================
@st.cache_data(ttl=60)
def getcabinas():
    service = getsheetsservice()
    result = service.spreadsheets().values().get(
        spreadsheetId=MASTERCABINASID,
        range="Hoja 1!A:D"
    ).execute()
    rows = result.get("values", [])
    return [r for r in rows if len(r) >= 4 and r[0] == BARCO]

@st.cache_data(ttl=60)
def getagencias():
    service = getsheetsservice()
    result = service.spreadsheets().values().get(
        spreadsheetId=MASTERCABINASID,
        range="AGENCIAS!A:B"
    ).execute()
    rows = result.get("values", [])
    agencias = {}
    for r in rows:
        if len(r) >= 2:
            agencias[r[0].strip()] = r[1].strip()
    return agencias

@st.cache_data(ttl=30)
def getsalidas():
    service = getsheetsservice()
    spreadsheet = service.spreadsheets().get(spreadsheetId=CRMBARCO).execute()
    return [s["properties"]["title"] for s in spreadsheet.get("sheets", [])]

def crearsalida(ddmm, cabinas, agencias_cupo):
    service = getsheetsservice()
    # Crear hoja
    service.spreadsheets().batchUpdate(
        spreadsheetId=CRMBARCO,
        body={"requests": [{"addSheet": {"properties": {"title": ddmm}}}]}
    ).execute()
    # Cabecera
    header = [["cabina", "categoria", "estado", "agencia", "pax", "localizador", "notas"]]
    # Filas por cabina
    rows = []
    for c in cabinas:
        rows.append([c[1], c[3], "LIBRE", "", "", "", ""])
    service.spreadsheets().values().update(
        spreadsheetId=CRMBARCO,
        range=f"{ddmm}!A1",
        valueInputOption="RAW",
        body={"values": header + rows}
    ).execute()

@st.cache_data(ttl=30)
def getdatossalida(ddmm):
    service = getsheetsservice()
    result = service.spreadsheets().values().get(
        spreadsheetId=CRMBARCO,
        range=f"{ddmm}!A:G"
    ).execute()
    rows = result.get("values", [])
    if len(rows) < 2:
        return []
    header = rows[0]
    return [dict(zip(header, r + [""] * len(header))) for r in rows[1:]]

def guardarcabina(ddmm, rowindex, agencia, pax, localizador, notas):
    service = getsheetsservice()
    # rowindex es 0-based desde datos, +2 por header y base 1
    fila = rowindex + 2
    service.spreadsheets().values().update(
        spreadsheetId=CRMBARCO,
        range=f"{ddmm}!C{fila}:G{fila}",
        valueInputOption="RAW",
        body={"values": [["VENDIDA" if agencia else "LIBRE", agencia, pax, localizador, notas]]}
    ).execute()

# ============================================================
# CSS
# ============================================================
st.markdown(
    '''
    <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .portal-header { padding: 0.1rem 0 0.55rem 0; display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 0.55rem; }
        .portal-header-left { display: flex; align-items: center; gap: 0.9rem; }
        .portal-logo { height: 42px; width: auto; object-fit: contain; display: block; }
        .portal-title, .portal-title-en { font-size: 0.96rem; font-weight: 800; color: #1F2937; line-height: 1.15; }
        .portal-title-en { margin-top: 0.12rem; }
        .portal-subtitle, .portal-subtitle-en { font-size: 0.72rem; color: #667085; line-height: 1.2; }
        .portal-subtitle { margin-top: 0.12rem; }
        .portal-subtitle-en { margin-top: 0.08rem; }
        .user-top { font-size: 0.72rem; color: #566079; white-space: nowrap; }
        section[data-testid="stMain"] > div:first-child { padding-top: 1rem !important; }
        .cabina-grid { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 1rem; }
        .cabina-box {
            width: 64px; height: 48px; border-radius: 6px; border: 2px solid transparent;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            font-size: 0.7rem; font-weight: 700; cursor: pointer; transition: all 0.15s;
        }
        .cabina-libre { background: #F3F4F6; border-color: #D1D5DB; color: #6B7280; }
        .cabina-vendida { border-color: #1F2937 !important; border-width: 3px !important; }
        .categoria-label { font-size: 0.85rem; font-weight: 700; color: #374151; margin: 0.75rem 0 0.35rem 0; }
    </style>
    ''',
    unsafe_allow_html=True,
)

# ============================================================
# CABECERA
# ============================================================
st.markdown(
    f'''
    <div class="portal-header">
        <div class="portal-header-left">
            <img class="portal-logo" src="{LOGOURL}" alt="Logo">
            <div>
                <div class="portal-title">{SALUDO}, {DISPLAYUSER}. ¿Qué hacemos hoy?</div>
                <div class="portal-title-en">{SALUDOEN}, {DISPLAYUSER}. What are we doing today?</div>
                <div class="portal-subtitle">MS Vista Rio · Gestión de Cabinas</div>
                <div class="portal-subtitle-en">MS Vista Rio · Cabin Management</div>
            </div>
        </div>
        <div class="user-top">{DISPLAYUSER}</div>
    </div>
    ''',
    unsafe_allow_html=True,
)

st.markdown("---")

# ============================================================
# CARGA DE DATOS BASE
# ============================================================
cabinas = getcabinas()
agencias = getagencias()
salidas = getsalidas()

if not cabinas:
    st.error("No se encontraron cabinas para MS_VISTA_RIO en el master.")
    st.stop()

# ============================================================
# SELECTOR: NUEVA SALIDA O EXISTENTE
# ============================================================
modo = st.radio("¿Qué quieres hacer?", ["Salida existente", "Nueva salida"], horizontal=True)

if modo == "Nueva salida":
    st.markdown("#### Nueva salida")
    ddmm = st.text_input("Fecha de salida (DDMM)", max_chars=4, placeholder="2705")
    if ddmm and len(ddmm) == 4:
        if ddmm in salidas:
            st.warning(f"La salida {ddmm} ya existe.")
        else:
            st.markdown("**Cupo por agencia (opcional)**")
            cupos = {}
            cols = st.columns(4)
            for i, (cod, color) in enumerate(agencias.items()):
                with cols[i % 4]:
                    cupo = st.number_input(cod, min_value=0, max_value=200, value=0, key=f"cupo_{cod}")
                    if cupo > 0:
                        cupos[cod] = cupo
            if st.button("✅ Crear salida"):
                with st.spinner("Creando salida..."):
                    crearsalida(ddmm, cabinas, cupos)
                    st.cache_data.clear()
                    st.success(f"Salida {ddmm} creada con {len(cabinas)} cabinas.")
                    st.rerun()

else:
    if not salidas:
        st.info("No hay salidas creadas todavía.")
        st.stop()

    ddmm_sel = st.selectbox("Selecciona salida", salidas)

    if ddmm_sel:
        datos = getdatossalida(ddmm_sel)
        if not datos:
            st.warning("La salida no tiene datos.")
            st.stop()

        # Mapa de estado por cabina
        estadocabina = {d.get("cabina", ""): d for d in datos}

        # Agrupar cabinas por categoría
        from collections import defaultdict
        porcategoria = defaultdict(list)
        for c in cabinas:
            porcategoria[c[3]].append(c[1])  # c[3]=categoria, c[1]=numero cabina

        # ============================================================
        # MAPA DE CABINAS
        # ============================================================
        st.markdown(f"### 🚢 Mapa de cabinas — Salida {ddmm_sel}")

        cabina_seleccionada = st.session_state.get("cabina_sel")

        for categoria, nums in porcategoria.items():
            st.markdown(f'<div class="categoria-label">📦 {categoria}</div>', unsafe_allow_html=True)
            html = '<div class="cabina-grid">'
            for num in sorted(nums):
                info = estadocabina.get(num, {})
                agencia = info.get("agencia", "")
                estado = info.get("estado", "LIBRE")
                color = agencias.get(agencia, "#F3F4F6") if agencia else "#F3F4F6"
                border = "#1F2937" if estado == "VENDIDA" else "#D1D5DB"
                textcolor = "#1F2937" if agencia else "#9CA3AF"
                html += f'''
                <div class="cabina-box" style="background:{color};border-color:{border};color:{textcolor};"
                     onclick="window.parent.postMessage({{type:'streamlit:setComponentValue', value:'{num}'}}, '*')">
                    <span>{num}</span>
                    <span style="font-size:0.6rem">{agencia or "libre"}</span>
                </div>'''
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

        # ============================================================
        # PANEL ASIGNACIÓN
        # ============================================================
        st.markdown("---")
        st.markdown("#### ✏️ Asignar cabina")

        col1, col2 = st.columns([1, 2])
        with col1:
            nums_disponibles = [c[1] for c in cabinas]
            cabina_input = st.selectbox("Cabina", sorted(nums_disponibles))

        if cabina_input:
            info = estadocabina.get(cabina_input, {})
            with col2:
                agencia_sel = st.selectbox(
                    "Agencia",
                    [""] + list(agencias.keys()),
                    index=list(agencias.keys()).index(info.get("agencia", "")) + 1
                    if info.get("agencia") in agencias else 0
                )
            c1, c2, c3 = st.columns(3)
            with c1:
                pax_input = st.number_input("Pax", min_value=0, max_value=10, value=int(info.get("pax", 0) or 0))
            with c2:
                loc_input = st.text_input("Localizador", value=info.get("localizador", ""))
            with c3:
                notas_input = st.text_input("Notas", value=info.get("notas", ""))

            if st.button("💾 Guardar"):
                rowindex = next((i for i, d in enumerate(datos) if d.get("cabina") == cabina_input), None)
                if rowindex is not None:
                    with st.spinner("Guardando..."):
                        guardarcabina(ddmm_sel, rowindex, agencia_sel, pax_input, loc_input, notas_input)
                        st.cache_data.clear()
                        st.success(f"Cabina {cabina_input} actualizada.")
                        st.rerun()
