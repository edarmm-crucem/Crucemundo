#### BLOQUE 1: PAGE CONFIG
import streamlit as st
import pytz
import re
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from collections import defaultdict

st.set_page_config(page_title="MS VISTA RIO", page_icon="favicon1.png", layout="wide", initial_sidebar_state="collapsed")

#### BLOQUE 2: AUTH
if not st.session_state.get("authenticated"):
    st.markdown("""
        <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .auth-warn { background: #FEF3C7; border: 1.5px solid #FCD34D; border-radius: 12px; padding: 1rem 1.2rem; margin: 2rem auto; max-width: 480px; font-family: sans-serif; }
        .auth-warn-title { font-size: 1rem; font-weight: 800; color: #92400E; margin-bottom: 0.3rem; }
        .auth-warn-sub { font-size: 0.82rem; color: #78350F; }
        </style>
        <div class="auth-warn">
            <div class="auth-warn-title">⚠️ Acceso restringido / Restricted access</div>
            <div class="auth-warn-sub">No tienes acceso. Inicia sesión desde el menú principal.<br>
            <em>You don't have access. Please log in from the main menu.</em></div>
        </div>""", unsafe_allow_html=True)
    st.stop()

#### BLOQUE 3: CONSTANTES
BARCO = "MS_VISTA_RIO"
ANIO = "2026"
CRMBARCO_NAME = f"{BARCO}_{ANIO}_CRM"
MASTERCABINASID = "1K-Tn_E3QEhCplOP-IFHbKZc-vtKAxFEUBbZVK14EjJI"
CRMBARCO = "1ApNv3qK-_2ANOVwSZoOchAdwWaeQg0Evz-n54s6T2cE"
LOGOID = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGOURL = f"https://lh3.googleusercontent.com/d/{LOGOID}"
ROOT_GROUPS = "1MMNH3y1E3jJIp6uUnxbwV0toAtdr2F2M"
NOMBRE_BARCO_LIMPIO = BARCO.replace("_", " ")
ESTADOS_VALIDOS = ["LIBRE", "RESERVA", "VENDIDA"]

#### BLOQUE 4: UTILIDADES
TIMEZONE = pytz.timezone("Europe/Madrid")

def now():
    return datetime.now(pytz.utc).astimezone(TIMEZONE).replace(tzinfo=None)

def getsaludo(lang="es"):
    hour = now().hour
    if 6 <= hour < 14: return "Buenos días" if lang == "es" else "Good morning"
    if 14 <= hour < 21: return "Buenas tardes" if lang == "es" else "Good afternoon"
    return "Buenas noches" if lang == "es" else "Good evening"

DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Sin usuario / Unknown user"
SALUDO = getsaludo("es")
SALUDOEN = getsaludo("en")

#### BLOQUE 5: GOOGLE SERVICES
@st.cache_resource
def getgooglecreds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcpserviceaccount"],
        scopes=["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"],
    )

def getsheetsservice():
    return build("sheets", "v4", credentials=getgooglecreds())

def getdriveservice():
    return build("drive", "v3", credentials=getgooglecreds())

#### BLOQUE 6: BÚSQUEDA FIT EN DRIVE
def buscar_archivo_conf(ddmm):
    drive_service = getdriveservice()
    aa = ANIO[2:]; mm = ddmm[2:4]; dd = ddmm[0:2]
    nombre = f"{BARCO}_{aa}{mm}{dd}"
    try:
        q = f"name = '{nombre}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
        res = drive_service.files().list(q=q, fields="files(id, name)", supportsAllDrives=True, includeItemsFromAllDrives=True, pageSize=1).execute()
        archivos = res.get("files", [])
        if archivos:
            return archivos[0]["id"], f"✅ Archivo FIT localizado: `{archivos[0]['name']}`"
        return None, f"🔎 No se encontró `{nombre}`. / *File `{nombre}` not found.*"
    except Exception as e:
        return None, f"💥 Error con Google Drive API: {str(e)}"

@st.cache_data(ttl=60)
def extraer_datos_archivo_conf(spreadsheet_id):
    sheets_service = getsheetsservice()
    try:
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        hojas = [s["properties"]["title"] for s in spreadsheet.get("sheets", [])]
    except Exception:
        return {}
    datos = defaultdict(lambda: {"sold_por_cat": defaultdict(int), "localizadores": set(), "notes": set()})
    for hoja in hojas:
        try:
            result = sheets_service.spreadsheets().values().batchGet(
                spreadsheetId=spreadsheet_id,
                ranges=[f"'{hoja}'!B2", f"'{hoja}'!P5", f"'{hoja}'!G11", f"'{hoja}'!G24:G50", f"'{hoja}'!Q24:Q50"]
            ).execute()
            vr = result.get("valueRanges", [])
            if len(vr) < 5:
                continue
            b2 = vr[0].get("values", [])
            b2_val = b2[0][0].strip().upper() if b2 and b2[0] else ""
            if not any(k in b2_val for k in ["BOOKING", "PROFORMA"]):
                continue
            p5 = vr[1].get("values", [])
            agencia_cod = p5[0][0].strip() if p5 and p5[0] else ""
            if not agencia_cod:
                continue
            g11 = vr[2].get("values", [])
            loc_raw = g11[0][0].strip() if g11 and g11[0] else ""
            loc = "".join(re.findall(r'\d+$', loc_raw)) or loc_raw
            if loc:
                datos[agencia_cod]["localizadores"].add(loc)
            if agencia_cod == "CONF":
                datos[agencia_cod]["notes"].add(f"Hoja: {hoja}")
            pax_c = vr[3].get("values", [])
            cat_c = vr[4].get("values", [])
            if pax_c and pax_c[0]:
                lista_pax = [p for p in pax_c[0][0].strip().split('\n') if p.strip()]
                cat_val = "Sin Categoría"
                if cat_c and cat_c[0]:
                    raw_cat = cat_c[0][0].strip()
                    cat_val = raw_cat.split("/")[-1].strip() if "/" in raw_cat else raw_cat
                datos[agencia_cod]["sold_por_cat"][cat_val] += len(lista_pax)
        except Exception:
            continue
    return {ag: {"sold_por_cat": dict(info["sold_por_cat"]), "localizadores": list(info["localizadores"]), "notes": list(info["notes"])} for ag, info in datos.items()}

#### BLOQUE 7: BÚSQUEDA GROUP EN DRIVE
def buscar_archivos_group(ddmm):
    drive_service = getdriveservice()
    aa = ANIO[2:]; mm = ddmm[2:4]; dd = ddmm[0:2]
    nombre_buscado = f"MS_FIDELIO_{aa}{mm}{dd}_GROUP"
    year_folder_name = f"{ANIO}_GROUP"
    encontrados = []
    try:
        q1 = f"'{ROOT_GROUPS}' in parents and name = '{year_folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res1 = drive_service.files().list(q=q1, fields="files(id, name)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        for yf in res1.get("files", []):
            q2 = f"'{yf['id']}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            res2 = drive_service.files().list(q=q2, fields="files(id, name)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
            for sf in res2.get("files", []):
                q3 = f"'{sf['id']}' in parents and name = '{nombre_buscado}' and trashed = false"
                res3 = drive_service.files().list(q=q3, fields="files(id, name)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
                for f in res3.get("files", []):
                    encontrados.append({"id": f["id"], "name": f["name"], "ship": sf["name"]})
    except Exception as e:
        st.warning(f"⚠️ Error buscando archivos GROUP / *Error searching GROUP files*: {str(e)}")
    return encontrados

CATEGORY_MAP_GROUP = {"PRINCIPAL": "MAIN", "INTERMEDIA": "MID", "SUPERIOR": "UPP"}

@st.cache_data(ttl=60)
def extraer_datos_archivo_group(spreadsheet_id):
    sheets_service = getsheetsservice()
    PAX_COLS = ["G", "K", "N", "P"]
    CAT_ROW, PAX_ROW = 21, 22
    try:
        result = sheets_service.spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id,
            ranges=["B2"] + [f"{col}{CAT_ROW}" for col in PAX_COLS] + [f"{col}{PAX_ROW}" for col in PAX_COLS]
        ).execute()
        vr = result.get("valueRanges", [])
    except Exception:
        return {}
    def cell(i):
        rows = vr[i].get("values", []) if i < len(vr) else []
        return rows[0][0].strip() if rows and rows[0] else ""
    agencia = cell(0)
    if not agencia:
        return {}
    datos_group = defaultdict(lambda: {"sold_por_cat": defaultdict(int), "localizadores": [], "notes": []})
    for i in range(len(PAX_COLS)):
        raw_cat = cell(1 + i)
        raw_pax = cell(1 + len(PAX_COLS) + i)
        if not raw_cat or not raw_pax:
            continue
        category = CATEGORY_MAP_GROUP.get(raw_cat.upper(), raw_cat.upper())
        m = re.match(r"(\d+)", raw_pax)
        if not m:
            continue
        datos_group[agencia]["sold_por_cat"][category] += int(m.group(1))
    return {ag: {"sold_por_cat": dict(info["sold_por_cat"]), "localizadores": [], "notes": []} for ag, info in datos_group.items()}

#### BLOQUE 8: FUNCIONES CRM SHEETS
@st.cache_data(ttl=60)
def getcabinas():
    service = getsheetsservice()
    result = service.spreadsheets().values().get(spreadsheetId=MASTERCABINASID, range="Hoja 1!A:F").execute()
    return [r for r in result.get("values", []) if len(r) >= 4 and r[0] == BARCO]

@st.cache_data(ttl=60)
def getagencias():
    service = getsheetsservice()
    result = service.spreadsheets().values().get(spreadsheetId=MASTERCABINASID, range="AGENCIAS!A:B").execute()
    agencias = {}
    for r in result.get("values", []):
        if len(r) >= 2:
            agencias[r[0].strip()] = r[1].strip()
    return agencias

@st.cache_data(ttl=30)
def getsalidas():
    service = getsheetsservice()
    spreadsheet = service.spreadsheets().get(spreadsheetId=CRMBARCO).execute()
    return [s["properties"]["title"] for s in spreadsheet.get("sheets", [])]

def crearsalida(ddmm, cabinas):
    service = getsheetsservice()
    service.spreadsheets().batchUpdate(spreadsheetId=CRMBARCO, body={"requests": [{"addSheet": {"properties": {"title": ddmm}}}]}).execute()
    header = [["cabina", "categoria", "estado", "agencia", "pax", "localizador", "notes", "cupo_agencia", "cupo_maximo"]]
    rows = [[c[1], c[3], "LIBRE", "", "", "", "", "", ""] for c in cabinas]
    service.spreadsheets().values().update(spreadsheetId=CRMBARCO, range=f"{ddmm}!A1", valueInputOption="RAW", body={"values": header + rows}).execute()

@st.cache_data(ttl=5)
def getdatossalida(ddmm):
    service = getsheetsservice()
    result = service.spreadsheets().values().get(spreadsheetId=CRMBARCO, range=f"{ddmm}!A:I").execute()
    rows = result.get("values", [])
    if len(rows) < 2:
        return []
    header = rows[0]
    return [dict(zip(header, r + [""] * (len(header) - len(r)))) for r in rows[1:]]

def guardarcabina(ddmm, rowindex, agencia, pax, localizador, notas, estado):
    service = getsheetsservice()
    fila = rowindex + 2
    service.spreadsheets().values().update(spreadsheetId=CRMBARCO, range=f"{ddmm}!C{fila}:G{fila}", valueInputOption="RAW", body={"values": [[estado, agencia, str(pax), localizador, notas]]}).execute()

def guardar_cupo_sheets(ddmm, datos_completos, clave_cupo, limites_str):
    service = getsheetsservice()
    fila_destino = None
    for i, d in enumerate(datos_completos):
        if d.get("cupo_agencia", "").strip() == clave_cupo:
            fila_destino = i + 2
            break
    if fila_destino is None:
        for i, d in enumerate(datos_completos):
            if not d.get("cupo_agencia", "").strip():
                fila_destino = i + 2
                break
    if fila_destino is None:
        fila_destino = len(datos_completos) + 2
    service.spreadsheets().values().update(spreadsheetId=CRMBARCO, range=f"{ddmm}!H{fila_destino}:I{fila_destino}", valueInputOption="RAW", body={"values": [[clave_cupo, limites_str]]}).execute()

#### BLOQUE 9: CSS
st.markdown('''
<style>
    [data-testid="stSidebarNav"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    .portal-header { padding: 0.1rem 0 0.55rem 0; display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 0.55rem; }
    .portal-header-left { display: flex; align-items: center; gap: 1.2rem; }
    .portal-logo { height: 50px; width: auto; object-fit: contain; display: block; }
    .portal-title { font-size: 0.96rem; font-weight: 500; color: #4B5563; line-height: 1.2; }
    .portal-title strong { color: #111827; }
    .portal-title-en { margin-top: 0.12rem; font-style: italic; color: #6B7280; font-size: 0.82rem; }
    .ship-badge-container { display: flex; flex-direction: column; align-items: flex-end; text-align: right; }
    .ship-title { font-size: 1.5rem; font-weight: 900; color: #1E3A8A; letter-spacing: 0.05em; line-height: 1; }
    .ship-subtitle { font-size: 0.75rem; font-weight: 600; color: #4B5563; text-transform: uppercase; margin-top: 0.2rem; letter-spacing: 0.1em; }
    .ship-capacity { margin-top: 0.35rem; background-color: #EFF6FF; color: #1E3A8A; border: 1px solid #BFDBFE; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.72rem; font-weight: 700; display: inline-block; text-transform: uppercase; letter-spacing: 0.05em; }
    section[data-testid="stMain"] > div:first-child { padding-top: 1rem !important; }
    .deck-layout { background: #FFFFFF; padding: 1.2rem; border-radius: 12px; border: 1px solid #E5E7EB; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 1.5rem; }
    .deck-row { display: flex; flex-wrap: nowrap; gap: 0.5rem; overflow-x: auto; padding: 0.2rem 0; }
    .deck-row-style { justify-content: flex-start; }
    .horizontal-corridor { height: 18px; margin: 0.4rem 0; background-image: linear-gradient(to right, #E5E7EB 50%, rgba(255,255,255,0) 0%); background-position: bottom; background-size: 15px 2px; background-repeat: repeat-x; display: flex; align-items: center; padding-left: 0.5rem; font-size: 0.6rem; font-weight: 700; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.15em; }
    .cabina-box { min-width: 76px; max-width: 76px; height: 54px; border-radius: 6px; border: 2px solid transparent; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; transition: all 0.15s; box-sizing: border-box; }
    .cabina-num-destacado { font-size: 1.15rem; font-weight: 800; line-height: 1.1; }
    .cabina-libre { background: #F3F4F6; border-color: #D1D5DB; color: #6B7280; border-style: solid; }
    .cabina-reserva { border-color: #1F2937 !important; border-width: 3px !important; border-style: dashed !important; }
    .cabina-vendida { border-color: #1F2937 !important; border-width: 3px !important; border-style: solid !important; }
    .categoria-label { font-size: 0.95rem; font-weight: 800; color: #1E3A8A; margin: 1rem 0 0.6rem 0; background: #EFF6FF; padding: 0.4rem 0.8rem; border-radius: 6px; display: inline-block; border-left: 4px solid #3B82F6; }
    .leyenda-estados { display: flex; gap: 1.2rem; align-items: center; margin-bottom: 0.8rem; flex-wrap: wrap; }
    .leyenda-item { display: flex; align-items: center; gap: 0.4rem; font-size: 0.75rem; font-weight: 600; color: #4B5563; }
    .leyenda-sub { font-size: 0.65rem; font-style: italic; color: #9CA3AF; }
    .leyenda-box { width: 22px; height: 16px; border-radius: 3px; display: inline-block; }
    .leyenda-libre { background: #F3F4F6; border: 2px solid #D1D5DB; }
    .leyenda-reserva { background: #FFFBEB; border: 2px dashed #F59E0B; }
    .leyenda-vendida { background: #F9FAFB; border: 3px solid #1F2937; }
    .informe-tabla { width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.85rem; }
    .informe-tabla th { background-color: #F3F4F6; color: #374151; font-weight: 700; padding: 10px; border: 1px solid #E5E7EB; text-align: center; }
    .informe-tabla td { padding: 8px 10px; border: 1px solid #E5E7EB; text-align: center; vertical-align: middle; }
    .informe-tabla tr:hover { background-color: #F9FAFB; }
    .color-block { width: 24px; height: 24px; border-radius: 4px; display: inline-block; border: 1px solid #D1D5DB; }
    .th-sold { background-color: #FEE2E2 !important; color: #991B1B !important; }
    .td-sold { background-color: #FEF2F2; font-weight: bold; color: #B91C1C; }
    .en { font-size: 0.70em; font-style: italic; color: #9CA3AF; display: block; line-height: 1.2; margin-top: 1px; }
    .th-bilingual { display: flex; flex-direction: column; align-items: center; gap: 1px; }
    .th-es { font-size: 0.82rem; font-weight: 700; }
    .th-en { font-size: 0.66rem; font-style: italic; color: #9CA3AF; }
    .td-total-cab { background-color: #EFF6FF; color: #1E40AF; font-weight: 700; }
    .th-total-cab { background-color: #DBEAFE !important; color: #1E40AF !important; }
</style>
''', unsafe_allow_html=True)

#### BLOQUE 10: CARGA DE DATOS BASE
cabinas = getcabinas()
agencias = getagencias()
salidas = getsalidas()

if not cabinas:
    st.error(f"No se encontraron cabinas para {BARCO}. / *No cabins found for {BARCO}.*")
    st.stop()

try:
    capacidad_total = cabinas[0][5].strip() if len(cabinas[0]) >= 6 else "No definida / Undefined"
except Exception:
    capacidad_total = "No definida / Undefined"

todas_categorias = sorted(list(set([c[3] for c in cabinas])))

#### BLOQUE 11: CABECERA VISUAL
st.markdown(f'''
<div class="portal-header">
    <div class="portal-header-left">
        <img class="portal-logo" src="{LOGOURL}" alt="Logo">
        <div>
            <div class="portal-title">{SALUDO}, <strong>{DISPLAYUSER}</strong>. ¿Qué hacemos hoy?</div>
            <div class="portal-title-en">{SALUDOEN}, <strong>{DISPLAYUSER}</strong>. What are we doing today?</div>
        </div>
    </div>
    <div class="ship-badge-container">
        <div class="ship-title">🚢 {NOMBRE_BARCO_LIMPIO}</div>
        <div class="ship-subtitle">Panel de Control / Control Panel — {ANIO}</div>
        <div class="ship-capacity">👥 Cap. Máx / Max Cap: {capacidad_total} Pax</div>
    </div>
</div>
''', unsafe_allow_html=True)

st.markdown("---")

#### BLOQUE 12: SELECTOR DE MODO
opciones_modo = [
    "🗺️ Mapa de cabinas / Cabin Map",
    "📊 Ver Cupos / View Quotas",
    "⚙️ Configurar Cupos / Configure Quotas",
    "📈 Informe / Report",
    "🛏️ Informe Cabinas / Cabin Report",
    "🛳️ Ocupación / Occupancy",
    "📅 Nueva salida / New Departure",
    "🏠 Inicio / Home",
]
modo = st.radio("¿Qué quieres hacer? / *What would you like to do?*", opciones_modo, index=5, horizontal=True)

def _modo(key):
    return key in modo

#### BLOQUE 13: MODO INICIO
if _modo("Inicio"):
    st.markdown(f"### 👋 Bienvenido al Panel del {NOMBRE_BARCO_LIMPIO} <span style='font-size:0.6em;font-style:italic;color:#9CA3AF;'>Welcome to the {NOMBRE_BARCO_LIMPIO} Dashboard</span>", unsafe_allow_html=True)
    st.markdown(f"""
        Has iniciado sesión como **{DISPLAYUSER}**.
        <span class='en'>You are logged in as **{DISPLAYUSER}**.</span>

        Desde este panel puedes gestionar la ocupación del buque.
        <span class='en'>From this panel you can manage the ship's occupancy.</span>

        ---
        * **🗺️ Mapa de cabinas / Cabin Map** — Visualiza planos  <span class='en'>Deck plans</span>
        * **📊 Ver Cupos / View Quotas** — por Agencia y Categoría. <span class='en'>Availability by Agency, Category and Passengers.</span>
        * **⚙️ Configurar Cupos / Configure Quotas** — Límites comerciales por categoría. <span class='en'>Commercial limits per cabin category.</span>
        * **📈 Informe / Report** — Cruce CRM + FIT + GROUP. <span class='en'>Cross-data from CRM + FIT + GROUP files.</span>
        * **🛏️ Informe Cabinas / Cabin Report** — Lista detallada de cabinas por estado. <span class='en'>Detailed cabin list filtered by status.</span>
        * **📅 Nueva salida / New Departure** — Nueva fecha operativa {ANIO}. <span class='en'>Create a new operational date for {ANIO}.</span>
    """, unsafe_allow_html=True)

#### BLOQUE 14: MODO NUEVA SALIDA
elif _modo("Nueva salida"):
    st.markdown("#### 📅 Crear una nueva salida <span style='font-size:0.65em;font-style:italic;color:#9CA3AF;'>Create a new departure</span>", unsafe_allow_html=True)
    ddmm = st.text_input("Fecha de salida (DDMM) / *Departure date (DDMM)*", max_chars=4, placeholder="2705")
    if ddmm and len(ddmm) == 4:
        if ddmm in salidas:
            st.warning(f"La salida {ddmm} ya existe. / *Departure {ddmm} already exists.*")
        else:
            if st.button("✅ Crear salida / *Create departure*"):
                with st.spinner("Creando salida... / *Creating departure...*"):
                    crearsalida(ddmm, cabinas)
                    st.cache_data.clear()
                    st.success(f"Salida {ddmm} creada en {ANIO}. / *Departure {ddmm} created for {ANIO}.*")
                    st.rerun()

#### BLOQUE 15: GUARD + SELECTOR DE SALIDA + CÁLCULO DE AGREGADOS
else:
    if not salidas:
        st.info("No hay salidas creadas todavía. / *No departures have been created yet.*")
        st.stop()

    ddmm_sel = st.selectbox("Selecciona salida / *Select departure*", salidas)

    if ddmm_sel:
        datos = getdatossalida(ddmm_sel)
        if not datos:
            st.warning("La salida no contiene datos. / *The departure contains no data.*")
            st.stop()

        cabinas_por_ag_cat = defaultdict(int)
        pax_por_ag_cat = defaultdict(int)
        sold_por_ag_cat = defaultdict(int)
        localizadores_por_agencia = defaultdict(list)
        notas_por_agencia = defaultdict(list)
        agencias_activas = set()
        cupos_config = {}

        for d in datos:
            cabina_id = d.get("cabina", "").strip()
            ag = d.get("agencia", "").strip()
            estado = d.get("estado", "LIBRE").strip()
            loc = d.get("localizador", "").strip()
            notes = d.get("notes", "").strip()
            cat = next((c[3] for c in cabinas if c[1] == cabina_id), "").strip()
            if ag and cat:
                agencias_activas.add(ag)
                cabinas_por_ag_cat[(ag, cat)] += 1
                if estado == "VENDIDA":
                    sold_por_ag_cat[(ag, cat)] += 1
                try:
                    pax_por_ag_cat[(ag, cat)] += int(d.get("pax", 0) or 0)
                except ValueError:
                    pass
                if loc and loc not in localizadores_por_agencia[ag]:
                    localizadores_por_agencia[ag].append(loc)
                if notes and notes not in notas_por_agencia[ag]:
                    notas_por_agencia[ag].append(notes)
            c_ag = d.get("cupo_agencia", "").strip()
            c_max = d.get("cupo_maximo", "").strip()
            if c_ag and "|" in c_ag and c_max and "," in c_max:
                try:
                    ag_cupo, cat_cupo = [x.strip() for x in c_ag.split("|")]
                    max_cab, max_px = c_max.split(",")
                    cupos_config[(ag_cupo, cat_cupo)] = {"cabinas": int(max_cab), "pax": int(max_px)}
                    agencias_activas.add(ag_cupo)
                except ValueError:
                    pass

        #### BLOQUE 16: MODO INFORME (CRM + FIT + GROUP)
        if modo == "📈 Informe / Report":
            st.markdown(f"### 📈 Informe Consolidado — Salida {ddmm_sel} <span style='font-size:0.6em;font-style:italic;color:#9CA3AF;'>Consolidated Report — Departure {ddmm_sel}</span>", unsafe_allow_html=True)
            st.markdown(f"Cruza **CRM ({CRMBARCO_NAME})** + **FIT** + **GROUP**. <span class='en'>Crosses CRM + FIT + GROUP files from Drive.</span>", unsafe_allow_html=True)

            with st.spinner("Buscando FIT en Drive... / *Searching FIT files...*"):
                archivo_conf_id, msg = buscar_archivo_conf(ddmm_sel)
                if archivo_conf_id:
                    st.success(msg)
                    datos_externos_conf = extraer_datos_archivo_conf(archivo_conf_id)
                else:
                    st.error(msg)
                    datos_externos_conf = {}

            with st.spinner("Buscando GROUP en Drive... / *Searching GROUP files...*"):
                archivos_group = buscar_archivos_group(ddmm_sel)
                datos_externos_group = {}
                for ag_file in archivos_group:
                    parcial = extraer_datos_archivo_group(ag_file["id"])
                    for ag_cod, ag_data in parcial.items():
                        if ag_cod not in datos_externos_group:
                            datos_externos_group[ag_cod] = {"sold_por_cat": defaultdict(int), "localizadores": [], "notes": []}
                        for cat, pax in ag_data["sold_por_cat"].items():
                            datos_externos_group[ag_cod]["sold_por_cat"][cat] += pax
                if archivos_group:
                    st.success(f"✅ {len(archivos_group)} archivo(s) GROUP. / *{len(archivos_group)} GROUP file(s) found.*")
                else:
                    st.info("🔎 No se encontraron archivos GROUP. / *No GROUP files found.*")

            todas = agencias_activas.union(set(datos_externos_conf.keys())).union(set(datos_externos_group.keys()))
            if not todas:
                st.info("No se registra actividad. / *No activity recorded.*")
            else:
                def th(es, en):
                    return f'<th><div class="th-bilingual"><span class="th-es">{es}</span><span class="th-en">{en}</span></div></th>'
                t = '<table class="informe-tabla"><thead><tr>'
                t += th("Origen", "Source") + th("Color", "Color") + th("Código Agencia", "Agency Code")
                for cat in todas_categorias:
                    t += th(f"{cat} Cupo", f"{cat} Quota") + th(f"{cat} PAX", f"{cat} PAX")
                    t += f'<th class="th-sold"><div class="th-bilingual"><span class="th-es">{cat} SOLD</span><span class="th-en">Sold</span></div></th>'
                t += th("Localizador", "Booking Ref") + th("Notes", "Notes") + '</tr></thead><tbody>'

                for ag_cod in sorted(list(todas)):
                    color_hex = agencias.get(ag_cod, "#F3F4F6")
                    if ag_cod in agencias_activas:
                        t += '<tr>'
                        t += '<td style="font-weight:bold;color:#1E3A8A;background:#F0F4FF;">CRM</td>'
                        t += f'<td><span class="color-block" style="background-color:{color_hex};"></span></td>'
                        t += f'<td style="font-weight:700;text-align:left;">{ag_cod}</td>'
                        for cat in todas_categorias:
                            lims = cupos_config.get((ag_cod, cat), {"cabinas": 0, "pax": 0})
                            v_c = lims["cabinas"] if lims["cabinas"] > 0 else "-"
                            v_p = lims["pax"] if lims["pax"] > 0 else "-"
                            v_s = sold_por_ag_cat.get((ag_cod, cat), 0)
                            t += f'<td>{v_c}</td><td>{v_p}</td><td class="td-sold">{v_s}</td>'
                        locs = ", ".join(localizadores_por_agencia[ag_cod]) or "-"
                        nts = " | ".join(notas_por_agencia[ag_cod]) or "-"
                        t += f'<td style="text-align:left;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{locs}">{locs}</td>'
                        t += f'<td style="text-align:left;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{nts}">{nts}</td></tr>'
                    if ag_cod in datos_externos_conf:
                        cn = datos_externos_conf[ag_cod]
                        t += '<tr><td style="font-weight:bold;color:#15803D;background:#F0FDF4;">FIT</td>'
                        t += f'<td><span class="color-block" style="background-color:{color_hex};"></span></td>'
                        t += f'<td style="font-weight:700;text-align:left;color:#15803D;">{ag_cod}</td>'
                        for cat in todas_categorias:
                            v_s = cn["sold_por_cat"].get(cat, 0)
                            t += f'<td style="color:#6B7280;">-</td><td style="color:#6B7280;">-</td><td class="td-sold" style="background:#F0FDF4;color:#166534;">{v_s}</td>'
                        locs_c = ", ".join(cn["localizadores"]) or "-"
                        nts_c = " | ".join(cn["notes"]) or "-"
                        t += f'<td style="text-align:left;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{locs_c}">{locs_c}</td>'
                        t += f'<td style="text-align:left;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{nts_c}">{nts_c}</td></tr>'
                    if ag_cod in datos_externos_group:
                        gn = datos_externos_group[ag_cod]
                        t += '<tr><td style="font-weight:bold;color:#7C3AED;background:#F5F3FF;">GROUPS</td>'
                        t += f'<td><span class="color-block" style="background-color:{color_hex};"></span></td>'
                        t += f'<td style="font-weight:700;text-align:left;color:#7C3AED;">{ag_cod}</td>'
                        for cat in todas_categorias:
                            v_s = gn["sold_por_cat"].get(cat, 0)
                            t += f'<td style="color:#6B7280;">-</td><td style="color:#6B7280;">-</td><td class="td-sold" style="background:#F5F3FF;color:#6D28D9;">{v_s if v_s else 0}</td>'
                        t += '<td style="text-align:left;">-</td><td style="text-align:left;">-</td></tr>'
                t += '</tbody></table>'
                st.markdown(t, unsafe_allow_html=True)

        #### BLOQUE 17: MODO INFORME CABINAS
        elif modo == "🛏️ Informe Cabinas / Cabin Report":
            st.markdown(
                f"### 🛏️ Informe de Cabinas — Salida {ddmm_sel} "
                "<span style='font-size:0.6em;font-style:italic;color:#9CA3AF;'>Cabin Report</span>",
                unsafe_allow_html=True
            )
            tipo_informe = st.selectbox("Selecciona el tipo de informe / *Select report type*",
                                        ["Todas las cabinas", "Solo VENDIDAS", "Solo RESERVAS", "Solo LIBRES"])
            datos_filtrados = [d for d in datos if (tipo_informe == "Todas las cabinas") or
                               (tipo_informe == "Solo VENDIDAS" and d.get("estado") == "VENDIDA") or
                               (tipo_informe == "Solo RESERVAS" and d.get("estado") == "RESERVA") or
                               (tipo_informe == "Solo LIBRES" and d.get("estado") == "LIBRE")]

            def th(es, en):
                return f'<th><div class="th-bilingual"><span class="th-es">{es}</span><span class="th-en">{en}</span></div></th>'

            t = '<table class="informe-tabla"><thead><tr>'
            t += th("Cabina", "Cabin") + th("Agencia", "Agency") + th("PAX", "PAX") + th("Localizador", "Ref") + th("Notas", "Notes")
            t += '</tr></thead><tbody>'
            for d in sorted(datos_filtrados, key=lambda x: int(re.sub(r"[^0-9]", "", x.get("cabina", "0")) or 0)):
                estado_class = "td-sold" if d.get("estado") == "VENDIDA" else ""
                t += f'<tr class="{estado_class}">'
                t += f'<td>{d.get("cabina", "")}</td>'
                t += f'<td>{d.get("agencia", "-")}</td>'
                t += f'<td>{d.get("pax", "-")}</td>'
                t += f'<td>{d.get("localizador", "-")}</td>'
                t += f'<td>{d.get("notes", "-")}</td>'
                t += '</tr>'
            t += '</tbody></table>'
            st.markdown(t, unsafe_allow_html=True)

        #### BLOQUE 18: MODO OCUPACIÓN
        elif modo == "🛳️ Ocupación / Occupancy":
            st.markdown(
                f"### 🛳️ Ocupación del Buque — Salida {ddmm_sel} "
                "<span style='font-size:0.6em;font-style:italic;color:#9CA3AF;'>Ship Occupancy</span>",
                unsafe_allow_html=True
            )
            total_cabinas = len(datos)
            cab_vendidas  = sum(1 for d in datos if d.get("estado") == "VENDIDA")
            cab_reservas  = sum(1 for d in datos if d.get("estado") == "RESERVA")
            cab_libres    = sum(1 for d in datos if d.get("estado") == "LIBRE")
            total_pax = sum(int(d.get("pax", 0) or 0) for d in datos if d.get("estado") == "VENDIDA")
            try:
                cap_max = int(''.join(filter(str.isdigit, capacidad_total.split()[0])))
            except Exception:
                cap_max = 0
            pct_cab = round(cab_vendidas / total_cabinas * 100, 1) if total_cabinas else 0
            pct_pax = round(total_pax / cap_max * 100, 1) if cap_max else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🔴 Vendidas / Sold",    f"{cab_vendidas}", f"{pct_cab}% del total")
            c2.metric("🟡 Reservas / On Hold",  f"{cab_reservas}")
            c3.metric("⬜ Libres / Free",       f"{cab_libres}")
            c4.metric("👥 Pax SOLD",            f"{total_pax}",   f"{pct_pax}% cap. máx" if cap_max else "")
            st.markdown("---")

            def th(es, en):
                return f'<th><div class="th-bilingual"><span class="th-es">{es}</span><span class="th-en">{en}</span></div></th>'

            stats_cat = {}
            for cat in todas_categorias:
                cabinas_cat = [c[1] for c in cabinas if c[3] == cat]
                n_total     = len(cabinas_cat)
                n_vendidas  = sum(1 for d in datos if d.get("cabina") in cabinas_cat and d.get("estado") == "VENDIDA")
                n_reservas  = sum(1 for d in datos if d.get("cabina") in cabinas_cat and d.get("estado") == "RESERVA")
                n_libres    = sum(1 for d in datos if d.get("cabina") in cabinas_cat and d.get("estado") == "LIBRE")
                pax_cat     = sum(int(d.get("pax", 0) or 0) for d in datos if d.get("cabina") in cabinas_cat and d.get("estado") == "VENDIDA")
                pct         = round(n_vendidas / n_total * 100, 1) if n_total else 0
                stats_cat[cat] = {"total": n_total, "vendidas": n_vendidas, "reservas": n_reservas, "libres": n_libres, "pax": pax_cat, "pct": pct}

            t = '<table class="informe-tabla"><thead><tr>'
            t += th("Categoría", "Category")
            t += '<th class="th-total-cab"><div class="th-bilingual"><span class="th-es">Total Cabinas</span><span class="th-en">Total Cabins</span></div></th>'
            t += th("Vendidas", "Sold") + th("Reservas", "On Hold") + th("Libres", "Free") + th("% Ocup.", "% Occup.") + th("Pax SOLD", "Pax Sold")
            t += '</tr></thead><tbody>'

            for cat, s in stats_cat.items():
                pct = s["pct"]
                if pct < 40:   grad = "linear-gradient(90deg, #22C55E, #86EFAC)"
                elif pct < 70: grad = "linear-gradient(90deg, #22C55E, #EAB308)"
                elif pct < 90: grad = "linear-gradient(90deg, #EAB308, #F97316)"
                else:          grad = "linear-gradient(90deg, #F97316, #EF4444)"
                barra = (f'<div style="background:#E5E7EB;border-radius:4px;height:10px;width:100%;margin-bottom:4px;">'
                         f'<div style="background:{grad};width:{pct}%;height:10px;border-radius:4px;"></div></div>'
                         f'<span style="font-size:0.78rem;font-weight:700;">{pct}%</span>')
                t += (f'<tr><td style="font-weight:700;text-align:left;">{cat}</td>'
                      f'<td class="td-total-cab">{s["total"]}</td>'
                      f'<td class="td-sold">{s["vendidas"]}</td>'
                      f'<td style="color:#92400E;font-weight:700;">{s["reservas"]}</td>'
                      f'<td>{s["libres"]}</td>'
                      f'<td style="min-width:120px;">{barra}</td>'
                      f'<td>{s["pax"]}</td></tr>')

            tot_v = sum(s["vendidas"] for s in stats_cat.values())
            tot_r = sum(s["reservas"] for s in stats_cat.values())
            tot_l = sum(s["libres"]   for s in stats_cat.values())
            tot_t = sum(s["total"]    for s in stats_cat.values())
            tot_p = sum(s["pax"]      for s in stats_cat.values())
            tot_pct = round(tot_v / tot_t * 100, 1) if tot_t else 0
            if tot_pct < 40:   grad_tot = "linear-gradient(90deg, #22C55E, #86EFAC)"
            elif tot_pct < 70: grad_tot = "linear-gradient(90deg, #22C55E, #EAB308)"
            elif tot_pct < 90: grad_tot = "linear-gradient(90deg, #EAB308, #F97316)"
            else:              grad_tot = "linear-gradient(90deg, #F97316, #EF4444)"
            barra_tot = (f'<div style="background:#E5E7EB;border-radius:4px;height:10px;width:100%;margin-bottom:4px;">'
                         f'<div style="background:{grad_tot};width:{tot_pct}%;height:10px;border-radius:4px;"></div></div>'
                         f'<strong style="font-size:0.78rem;">{tot_pct}%</strong>')
            t += (f'<tr style="background:#F3F4F6;font-weight:800;border-top:2px solid #D1D5DB;">'
                  f'<td style="text-align:left;">TOTAL</td>'
                  f'<td class="td-total-cab">{tot_t}</td>'
                  f'<td class="td-sold">{tot_v}</td>'
                  f'<td style="color:#92400E;font-weight:700;">{tot_r}</td>'
                  f'<td>{tot_l}</td>'
                  f'<td style="min-width:120px;">{barra_tot}</td>'
                  f'<td>{tot_p}</td></tr>')
            t += '</tbody></table>'
            st.markdown(t, unsafe_allow_html=True)

        #### BLOQUE 19: MODO VER CUPOS
        elif modo == "📊 Ver Cupos / View Quotas":
            st.markdown(f"### 📊 Cuadro de Mandos de Cupos — Salida {ddmm_sel} <span style='font-size:0.6em;font-style:italic;color:#9CA3AF;'>Quota Dashboard — Departure {ddmm_sel}</span>", unsafe_allow_html=True)
            if not cupos_config:
                st.info("No hay cupos configurados. Ve a 'Configurar Cupos'. / *No quotas configured. Go to 'Configure Quotas'.*")
            else:
                st.markdown("""
                <style>
                .cupos-tabla { width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.85rem; }
                .cupos-tabla th { background-color: #F3F4F6; color: #374151; font-weight: 700; padding: 10px; border: 1px solid #E5E7EB; text-align: center; }
                .cupos-tabla td { padding: 8px 10px; border: 1px solid #E5E7EB; text-align: center; vertical-align: middle; }
                .cupos-tabla tr:hover { background-color: #F9FAFB; }
                .td-cupo-cab { background-color: #EFF6FF; color: #1E40AF; font-weight: 700; }
                .td-cupo-pax { background-color: #F0FDF4; color: #166534; font-weight: 700; }
                .th-cupo-cab { background-color: #DBEAFE !important; color: #1E40AF !important; }
                .th-cupo-pax { background-color: #DCFCE7 !important; color: #166534 !important; }
                .td-ok { color: #166534; font-weight: 700; }
                .td-exc { color: #991B1B; font-weight: 700; }
                </style>
                """, unsafe_allow_html=True)
                t = '<table class="cupos-tabla"><thead><tr>'
                t += '<th>Agencia / Agency</th><th>Categoría / Category</th>'
                t += '<th class="th-cupo-cab">Cupo Cabinas / Cabin Quota</th>'
                t += '<th>Cabinas Usadas / Used</th><th>Cabinas Disp. / Avail.</th>'
                t += '<th class="th-cupo-pax">Cupo Pax / Pax Quota</th>'
                t += '<th>Pax Registrados / Registered</th><th>Pax Disp. / Avail.</th>'
                t += '<th>Estado / Status</th></tr></thead><tbody>'
                for (ag, cat), lims in cupos_config.items():
                    cab_lim = lims["cabinas"]; pax_lim = lims["pax"]
                    cab_usadas = cabinas_por_ag_cat[(ag, cat)]; pax_usados = pax_por_ag_cat[(ag, cat)]
                    cab_disp = cab_lim - cab_usadas; pax_disp = pax_lim - pax_usados
                    excedido = cab_disp < 0 or pax_disp < 0
                    status_html = '<span class="td-exc">🚨 Excedido / Exceeded</span>' if excedido else '<span class="td-ok">✅ OK</span>'
                    t += (f'<tr><td style="font-weight:700;text-align:left;">{ag}</td><td>{cat}</td>'
                          f'<td class="td-cupo-cab">{cab_lim}</td><td>{cab_usadas}</td>'
                          f'<td>{"🔴 " if cab_disp < 0 else ""}{cab_disp}</td>'
                          f'<td class="td-cupo-pax">{pax_lim}</td><td>{pax_usados}</td>'
                          f'<td>{"🔴 " if pax_disp < 0 else ""}{pax_disp}</td>'
                          f'<td>{status_html}</td></tr>')
                t += '</tbody></table>'
                st.markdown(t, unsafe_allow_html=True)

        #### BLOQUE 20: MODO CONFIGURAR CUPOS
        elif modo == "⚙️ Configurar Cupos / Configure Quotas":
            st.markdown(f"### ⚙️ Definir Límites por Categoría — Salida {ddmm_sel} <span style='font-size:0.6em;font-style:italic;color:#9CA3AF;'>Set Limits by Category — Departure {ddmm_sel}</span>", unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            with col_a:
                agencia_cupo = st.selectbox("1. Selecciona la Agencia / *Select Agency*", list(agencias.keys()))
            with col_b:
                categoria_cupo = st.selectbox("2. Selecciona la Categoría / *Select Category*", todas_categorias)
            valores_actuales = cupos_config.get((agencia_cupo, categoria_cupo), {"cabinas": 0, "pax": 0})
            st.markdown("---")
            c_l1, c_l2 = st.columns(2)
            with c_l1:
                limite_cabinas = st.number_input("Nº MÁXIMO de Cabinas / *Max authorised Cabins*", min_value=0, max_value=50, value=valores_actuales["cabinas"])
            with c_l2:
                limite_pax = st.number_input("Nº MÁXIMO de Personas (Pax) / *Max authorised Passengers*", min_value=0, max_value=150, value=valores_actuales["pax"])
            if st.button("💾 Guardar Límites / *Save Limits*"):
                with st.spinner("Sincronizando... / *Syncing...*"):
                    guardar_cupo_sheets(ddmm_sel, datos, f"{agencia_cupo}|{categoria_cupo}", f"{limite_cabinas},{limite_pax}")
                    st.cache_data.clear()
                    st.success(f"Límites guardados: {agencia_cupo} / {categoria_cupo} — {limite_cabinas} Cab · {limite_pax} Pax. / *Limits saved.*")
                    st.rerun()

        #### BLOQUE 21: MODO MAPA DE CABINAS
        elif modo == "🗺️ Mapa de cabinas / Cabin Map":
            estadocabina = {d.get("cabina", ""): d for d in datos}
            porcategoria = defaultdict(list)
            for c in cabinas:
                porcategoria[c[3]].append(c[1])

            ####if cupos_config:
               #### with st.expander("📊 Vista Rápida de Alertas de Cupos / *Quick Quota Alert View*", expanded=True):
                   #### c_cups = st.columns(min(len(cupos_config), 4))
                    ####for idx, ((ag, cat), lims) in enumerate(cupos_config.items()):
                        ####c_act = cabinas_por_ag_cat[(ag, cat)]; p_act = pax_por_ag_cat[(ag, cat)]
                        ####with c_cups[idx % len(c_cups)]:
                            ####excedido = (c_act > lims["cabinas"]) or (p_act > lims["pax"])
                            ####st.metric(label=f"{'🚨' if excedido else '💼'} {ag} ({cat})", value=f"Cab: {c_act}/{lims['cabinas']} | Pax: {p_act}/{lims['pax']}")

            st.markdown(f"### 🚢 Distribución de Cubiertas — Salida {ddmm_sel} <span style='font-size:0.6em;font-style:italic;color:#9CA3AF;'>Deck Layout — Departure {ddmm_sel}</span>", unsafe_allow_html=True)
            st.markdown('''
                <div class="leyenda-estados">
                    <div class="leyenda-item"><span class="leyenda-box leyenda-libre"></span>Libre <span class="leyenda-sub">/ Free</span></div>
                    <div class="leyenda-item"><span class="leyenda-box leyenda-reserva"></span>Reserva (RVA) <span class="leyenda-sub">/ On Hold</span></div>
                    <div class="leyenda-item"><span class="leyenda-box leyenda-vendida"></span>Vendida (SOLD) <span class="leyenda-sub">/ Sold</span></div>
                </div>''', unsafe_allow_html=True)

            for categoria, nums in porcategoria.items():
                st.markdown(f'<div class="categoria-label">📍 {categoria}</div>', unsafe_allow_html=True)
                impares, pares = [], []
                for num in nums:
                    try:
                        val = int(''.join(filter(str.isdigit, num)))
                        (impares if val % 2 != 0 else pares).append((val, num))
                    except ValueError:
                        pares.append((999, num))
                impares_ord = [x[1] for x in sorted(impares, key=lambda x: x[0], reverse=True)]
                pares_ord   = [x[1] for x in sorted(pares,   key=lambda x: x[0], reverse=True)]

                def render_cabina(num):
                    info = estadocabina.get(num, {})
                    ag = info.get("agencia", "").strip()
                    est = info.get("estado", "LIBRE").strip()
                    cant_pax = info.get("pax", "")
                    pax_txt = (f" ({cant_pax}p)" if cant_pax and str(cant_pax).isdigit() and int(cant_pax) > 0 else "")
                    color = agencias.get(ag, "#F3F4F6") if ag else "#F3F4F6"
                    textcolor = "#1F2937" if ag else "#9CA3AF"
                    if est == "VENDIDA":
                        bc, bw, bs, css = "#1F2937", "3px", "solid", "cabina-box cabina-vendida"
                    elif est == "RESERVA":
                        bc, bw, bs, css = "#F59E0B", "2px", "dashed", "cabina-box cabina-reserva"
                    else:
                        bc, bw, bs, css = "#D1D5DB", "2px", "solid", "cabina-box cabina-libre"
                    sublabel = f"{ag}{pax_txt}" if ag else ""
                    return (f'<div class="{css}" style="background:{color};border-color:{bc};border-width:{bw};border-style:{bs};color:{textcolor};"'
                            f'onclick="window.parent.postMessage({{type:\'streamlit:setComponentValue\',value:\'{num}\'}},\'*\')">'
                            f'<span class="cabina-num-destacado">{num}</span>'
                            f'<span style="font-size:0.58rem;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:72px;text-align:center;margin-top:2px;">{sublabel}</span>'
                            f'</div>')

            LABEL_POPA = '<div style="min-width:48px;display:flex;align-items:center;justify-content:center;font-size:0.6rem;font-weight:800;color:#9CA3AF;letter-spacing:0.1em;writing-mode:vertical-rl;text-orientation:mixed;">◀ POPA</div>'
            LABEL_PROA = '<div style="min-width:48px;display:flex;align-items:center;justify-content:center;font-size:0.6rem;font-weight:800;color:#9CA3AF;letter-spacing:0.1em;writing-mode:vertical-rl;text-orientation:mixed;">PROA ▶</div>'
            
            html = '<div class="deck-layout">'
            html += '<div style="display:flex;align-items:stretch;">'
            html += LABEL_POPA
            html += '<div style="flex:1;"><div class="deck-row deck-row-style">'
            for num in impares_ord:
            html += render_cabina(num)
            html += '</div><div class="horizontal-corridor">Pasillo Central / Central Corridor</div><div class="deck-row deck-row-style">'
            for num in pares_ord:
            html += render_cabina(num)
            html += '</div></div>'
            html += LABEL_PROA
            html += '</div></div>'
                st.markdown(html, unsafe_allow_html=True)

            #### BLOQUE 22: PANEL ASIGNAR CABINA
            st.markdown("---")
            st.markdown("#### ✏️ Asignar cabina <span style='font-size:0.65em;font-style:italic;color:#9CA3AF;'>Assign cabin</span>", unsafe_allow_html=True)
            col1, col2 = st.columns([1, 2])
            with col1:
                cabina_input = st.selectbox("Cabina / *Cabin*", sorted([c[1] for c in cabinas]))

            if cabina_input:
                info = estadocabina.get(cabina_input, {})
                agencia_actual = info.get("agencia", "").strip()
                pax_actual = int(info.get("pax", 0) or 0)
                estado_actual = info.get("estado", "LIBRE").strip()
                if estado_actual not in ESTADOS_VALIDOS:
                    estado_actual = "LIBRE"
                cat_actual = next((c[3] for c in cabinas if c[1] == cabina_input), "").strip()

                permitir_guardado = True
                if agencia_actual:
                    estado_badge = "🟡 RESERVA / Hold" if estado_actual == "RESERVA" else "🔴 VENDIDA / Sold"
                    st.error(f"⚠️ **¡Atención! / Warning!** La cabina {cabina_input} ({cat_actual}) ya está asignada a **{agencia_actual}** — {estado_badge}.")
                    if not st.checkbox(f"¿Sustituir la asignación de {agencia_actual}? / *Replace assignment for {agencia_actual}?*", value=False):
                        permitir_guardado = False

                with col2:
                    agencia_sel = st.selectbox("Agencia / *Agency*", [""] + list(agencias.keys()),
                        index=(list(agencias.keys()).index(info.get("agencia", "")) + 1 if info.get("agencia") in agencias else 0),
                        disabled=not permitir_guardado)

                estado_sel = st.selectbox("Estado de la reserva / *Booking status*", ESTADOS_VALIDOS,
                    index=ESTADOS_VALIDOS.index(estado_actual),
                    format_func=lambda x: {
                        "LIBRE":   "⬜ LIBRE — Sin asignar / Unassigned",
                        "RESERVA": "🟡 RESERVA (RVA) — Bloqueada / On hold, pending confirmation",
                        "VENDIDA": "🔴 VENDIDA (SOLD) — Confirmada / Confirmed and closed",
                    }.get(x, x),
                    disabled=not permitir_guardado)

                c1, c2, c3 = st.columns(3)
                with c1:
                    pax_input = st.number_input("Pax", min_value=0, max_value=10, value=int(info.get("pax", 0) or 0), disabled=not permitir_guardado)
                with c2:
                    loc_input = st.text_input("Localizador / *Booking Ref*", value=info.get("localizador", ""), disabled=not permitir_guardado)
                with c3:
                    notas_input = st.text_input("Notas / *Notes*", value=info.get("notes", ""), disabled=not permitir_guardado)

                if agencia_sel and (agencia_sel, cat_actual) in cupos_config:
                    lims = cupos_config[(agencia_sel, cat_actual)]
                    cabs_act = cabinas_por_ag_cat[(agencia_sel, cat_actual)]
                    pax_act = pax_por_ag_cat[(agencia_sel, cat_actual)]
                    if agencia_sel == agencia_actual:
                        cabs_act -= 1; pax_act -= pax_actual
                    if cabs_act + 1 > lims["cabinas"]:
                        st.error(f"🚫 **Cupo Cabinas Superado / Cabin Quota Exceeded** — {cat_actual}: {cabs_act}/{lims['cabinas']}. / *{agencia_sel} has {cabs_act} of {lims['cabinas']} authorised cabins.*")
                    if pax_act + pax_input > lims["pax"]:
                        st.error(f"🚫 **Cupo Pax Superado / Pax Quota Exceeded** — {cat_actual}: {pax_act + pax_input}/{lims['pax']}. / *Adding {pax_input} pax would exceed the limit of {lims['pax']}.*")

                if st.button("💾 Guardar / *Save*", disabled=not permitir_guardado):
                    rowindex = next((i for i, d in enumerate(datos) if d.get("cabina") == cabina_input), None)
                    if rowindex is not None:
                        estado_final = estado_sel if agencia_sel else "LIBRE"
                        with st.spinner("Guardando... / *Saving...*"):
                            guardarcabina(ddmm_sel, rowindex, agencia_sel, pax_input, loc_input, notas_input, estado_final)
                            st.cache_data.clear()
                            st.success(f"Cabina {cabina_input} guardada como **{estado_final}**. / *Cabin {cabina_input} saved as **{estado_final}**.*")
                            st.rerun()

#### BLOQUE 23: PIE DE PÁGINA
st.markdown("---")
st.page_link("app.py", label="🏠 Volver al Menú Principal / Back to Main Menu", icon="🏠")
