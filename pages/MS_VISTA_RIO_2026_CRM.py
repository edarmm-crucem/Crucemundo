import streamlit as st
import pandas as pd
import pytz
import re
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from collections import defaultdict

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="MS VISTA RIO",
    page_icon="favicon1",
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
# CONSTANTES Y DETECCIÓN DE ENTORNO
# ============================================================
BARCO = "MS_VISTA_RIO"
ANIO = "2026"  # Extraído del contexto de la base de datos CRM del barco
CRMBARCO_NAME = f"{BARCO}_{ANIO}_CRM"

MASTERCABINASID = "1K-Tn_E3QEhCplOP-IFHbKZc-vtKAxFEUBbZVK14EjJI"
CRMBARCO = "1ApNv3qK-_2ANOVwSZoOchAdwWaeQg0Evz-n54s6T2cE"
LOGOID = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGOURL = f"https://lh3.googleusercontent.com/d/{LOGOID}"
DRIVE_RAIZ_FOLDER = "11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm"

NOMBRE_BARCO_LIMPIO = BARCO.replace("_", " ")
ESTADOS_VALIDOS = ["LIBRE", "RESERVA", "VENDIDA"]

# ============================================================
# UTILIDADES
# ============================================================
TIMEZONE = pytz.timezone("Europe/Madrid")

def now():
    return datetime.now(pytz.utc).astimezone(TIMEZONE).replace(tzinfo=None)

def getsaludo(lang="es"):
    hour = now().hour
    if 6 <= hour < 14: return "Buenos días" if lang == "es" else "Good morning"
    if 14 <= hour < 21: return "Buenas tardes" if lang == "es" else "Good afternoon"
    return "Buenas noches" if lang == "es" else "Good evening"

DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Sin usuario"
SALUDO = getsaludo("es")
SALUDOEN = getsaludo("en")

# ============================================================
# GOOGLE SERVICES API
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

def getdriveservice():
    return build("drive", "v3", credentials=getgooglecreds())

# ============================================================
# LÓGICA DE BÚSQUEDA Y EXTRACCIÓN EN DRIVE (OTRO SHEET - CONF)
# ============================================================
def buscar_archivo_conf(ddmm):
    """Navega por el árbol de carpetas de Drive para encontrar el archivo BARCO_AAMMDD.ddmm"""
    drive_service = getdriveservice()
    
    # Formatear la fecha esperada del archivo BARCO_AAMMDD (Ej: MS_VISTA_RIO_260527)
    aa = ANIO[2:]
    mm = ddmm[2:4]
    dd = ddmm[0:2]
    nombre_archivo_esperado = f"{BARCO}_{aa}{mm}{dd}"
    
    try:
        # 1. Buscar carpeta del Año dentro de la Raíz
        q_anio = f"'{DRIVE_RAIZ_FOLDER}' in parents and name = '{ANIO}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res_anio = drive_service.files().list(q=q_anio, fields="files(id)").execute()
        carpetas_anio = res_anio.get("files", [])
        if not carpetas_anio: return None
        folder_anio_id = carpetas_anio[0]["id"]
        
        # 2. Buscar carpeta del Barco dentro de la carpeta del Año
        q_barco = f"'{folder_anio_id}' in parents and name = '{BARCO}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res_barco = drive_service.files().list(q=q_barco, fields="files(id)").execute()
        carpetas_barco = res_barco.get("files", [])
        if not carpetas_barco: return None
        folder_barco_id = carpetas_barco[0]["id"]
        
        # 3. Buscar el archivo específico dentro de la carpeta del Barco
        q_file = f"'{folder_barco_id}' in parents and name = '{nombre_archivo_esperado}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
        res_file = drive_service.files().list(q=q_file, fields="files(id)").execute()
        archivos = res_file.get("files", [])
        if archivos:
            return archivos[0]["id"]
    except Exception:
        pass
    return None

@st.cache_data(ttl=60)
def extraer_datos_archivo_conf(spreadsheet_id):
    """Procesa el contenido de las pestañas del archivo CONF en Drive"""
    sheets_service = getsheetsservice()
    try:
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        hojas = [s["properties"]["title"] for s in spreadsheet.get("sheets", [])]
    except Exception:
        return {}

    datos_conf_agencia = defaultdict(lambda: {"sold_por_cat": defaultdict(int), "localizadores": set(), "notes": set()})

    for hoja in hojas:
        try:
            # Traer los rangos clave de una sola vez para optimizar llamadas
            result = sheets_service.spreadsheets().values().batchGet(
                spreadsheetId=spreadsheet_id,
                ranges=[f"'{hoja}'!B2", f"'{hoja}'!P5", f"'{hoja}'!G11", f"'{hoja}'!G24:G50", f"'{hoja}'!Q24:Q50"]
            ).execute()
            
            value_ranges = result.get("valueRanges", [])
            b2_val = value_ranges[0].get("values", [[""]])[0][0].strip().upper()
            
            # Validar si cumple con el criterio de tipo de hoja
            if b2_val not in ["BOOKING", "PROFORMA"]:
                continue
                
            agencia_cod = value_ranges[1].get("values", [[""]])[0][0].strip()
            loc_original = value_ranges[2].get("values", [[""]])[0][0].strip()
            
            # Limpiar localizador quedándose solo con los dígitos finales
            loc_limpio = "".join(re.findall(r'\d+$', loc_original)) or loc_original

            if not agencia_cod:
                continue

            if loc_limpio:
                datos_conf_agencia[agencia_cod]["localizadores"].add(loc_limpio)
            datos_conf_agencia[agencia_cod]["notes"].add(f"Hoja: {hoja}")

            # Procesar listado de pasajeros (G24:G50) y Categorías (Q24:Q50)
            pax_rows = value_ranges[3].get("values", [])
            cat_rows = value_ranges[4].get("values", [])

            for idx, r_pax in enumerate(pax_rows):
                if r_pax and r_pax[0].strip():  # Si hay nombre de pasajero válido en la fila
                    cat_val = ""
                    if idx < len(cat_rows) and cat_rows[idx]:
                        # Extraer categoría del formato: XXXX / CAT -> Quedarse con "CAT"
                        raw_cat = cat_rows[idx][0]
                        if "/" in raw_cat:
                            cat_val = raw_cat.split("/")[-1].strip()
                        else:
                            cat_val = raw_cat.strip()
                    
                    if cat_val:
                        datos_conf_agencia[agencia_cod]["sold_por_cat"][cat_val] += 1

        except Exception:
            continue

    return datos_conf_agencia

# ============================================================
# FUNCIONES INTERNAS SHEETS CRM
# ============================================================
@st.cache_data(ttl=60)
def getcabinas():
    service = getsheetsservice()
    result = service.spreadsheets().values().get(
        spreadsheetId=MASTERCABINASID,
        range="Hoja 1!A:F"
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

def crearsalida(ddmm, cabinas):
    service = getsheetsservice()
    service.spreadsheets().batchUpdate(
        spreadsheetId=CRMBARCO,
        body={"requests": [{"addSheet": {"properties": {"title": ddmm}}}]}
    ).execute()

    header = [["cabina", "categoria", "estado", "agencia", "pax", "localizador", "notes", "cupo_agencia", "cupo_maximo"]]
    rows = []
    for c in cabinas:
        rows.append([c[1], c[3], "LIBRE", "", "", "", "", "", ""])

    service.spreadsheets().values().update(
        spreadsheetId=CRMBARCO,
        range=f"{ddmm}!A1",
        valueInputOption="RAW",
        body={"values": header + rows}
    ).execute()

@st.cache_data(ttl=5)
def getdatossalida(ddmm):
    service = getsheetsservice()
    result = service.spreadsheets().values().get(
        spreadsheetId=CRMBARCO,
        range=f"{ddmm}!A:I"
    ).execute()
    rows = result.get("values", [])
    if len(rows) < 2:
        return []
    header = rows[0]
    return [dict(zip(header, r + [""] * (len(header) - len(r)))) for r in rows[1:]]

def guardarcabina(ddmm, rowindex, agencia, pax, localizador, notas, estado):
    service = getsheetsservice()
    fila = rowindex + 2
    service.spreadsheets().values().update(
        spreadsheetId=CRMBARCO,
        range=f"{ddmm}!C{fila}:G{fila}",
        valueInputOption="RAW",
        body={"values": [[estado, agencia, str(pax), localizador, notas]]}
    ).execute()

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

    service.spreadsheets().values().update(
        spreadsheetId=CRMBARCO,
        range=f"{ddmm}!H{fila_destino}:I{fila_destino}",
        valueInputOption="RAW",
        body={"values": [[clave_cupo, limites_str]]}
    ).execute()

# ============================================================
# CSS ESTILOS TRADICIONALES
# ============================================================
st.markdown(
    '''
    <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .portal-header { padding: 0.1rem 0 0.55rem 0; display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 0.55rem; }
        .portal-header-left { display: flex; align-items: center; gap: 1.2rem; }
        .portal-logo { height: 50px; width: auto; object-fit: contain; display: block; }
        .portal-title, .portal-title-en { font-size: 0.96rem; font-weight: 500; color: #4B5563; line-height: 1.2; }
        .portal-title strong, .portal-title-en strong { color: #111827; }
        .portal-title-en { margin-top: 0.12rem; font-style: italic; color: #6B7280; }
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
        .cabina-reserva { border-color: #F59E0B !important; border-width: 2px !important; border-style: dashed !important; }
        .cabina-vendida { border-color: #1F2937 !important; border-width: 3px !important; border-style: solid !important; }
        .categoria-label { font-size: 0.95rem; font-weight: 800; color: #1E3A8A; margin: 1rem 0 0.6rem 0; background: #EFF6FF; padding: 0.4rem 0.8rem; border-radius: 6px; display: inline-block; border-left: 4px solid #3B82F6; }
        .leyenda-estados { display: flex; gap: 1.2rem; align-items: center; margin-bottom: 0.8rem; flex-wrap: wrap; }
        .leyenda-item { display: flex; align-items: center; gap: 0.4rem; font-size: 0.75rem; font-weight: 600; color: #4B5563; }
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
    </style>
    ''',
    unsafe_allow_html=True,
)

# ============================================================
# CARGA DE DATOS BASE
# ============================================================
cabinas = getcabinas()
agencias = getagencias()
salidas = getsalidas()

if not cabinas:
    st.error(f"No se encontraron cabinas para {BARCO} en el master.")
    st.stop()

try:
    capacidad_total = cabinas[0][5].strip() if len(cabinas[0]) >= 6 else "No definida"
except Exception:
    capacidad_total = "No definida"

todas_categorias = sorted(list(set([c[3] for c in cabinas])))

# ============================================================
# CABECERA VISUAL
# ============================================================
st.markdown(
    f'''
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
            <div class="ship-subtitle">Panel de Control / Control Panel — Año {ANIO}</div>
            <div class="ship-capacity">👥 Capacidad Máx: {capacidad_total} Pax</div>
        </div>
    </div>
    ''',
    unsafe_allow_html=True,
)

st.markdown("---")

# ============================================================
# SELECTOR DE MODO
# ============================================================
opciones_modo = ["Mapa de cabinas", "Ver Cupos", "Configurar Cupos", "Informe", "Nueva salida", "Inicio"]
modo = st.radio("¿Qué quieres hacer?", opciones_modo, index=5, horizontal=True)

# ------------------------------------------------------------
# MODO: INICIO
# ------------------------------------------------------------
if modo == "Inicio":
    st.markdown(f"### 👋 Bienvenido al Panel del {NOMBRE_BARCO_LIMPIO}")
    st.markdown(
        f"""
        Has iniciado sesión correctamente como **{DISPLAYUSER}**.
        Desde este panel centralizado puedes gestionar de forma ágil la ocupación del buque.
        Utiliza el menú superior para navegar entre las herramientas disponibles:

        * **🚢 Mapa de cabinas:** Visualiza planos con validación cruzada estricta por categoría (Cabinas y Personas asignadas).
        * **📊 Ver Cupos:** Cuadro analítico de disponibilidad segmentado por Agencia, Categoría de Cabina y Pasajeros.
        * **⚙️ Configurar Cupos:** Ajusta las limitaciones comerciales de cabinas y personas por cada categoría del buque.
        * **📈 Informe:** Cuadro ejecutivo avanzado que cruza colores corporativos, límites de cupo, ventas consolidadas de CRM y datos dinámicos de Confirmaciones (CONF).
        * **📅 Nueva salida:** Genera la estructura inicial para una nueva fecha operativa del barco en la base de datos ({ANIO}).
        """
    )
    st.markdown("---")
    st.page_link("app.py", label=" Volver al Menú Principal (Selección de Barcos)", icon="🏠")

# ------------------------------------------------------------
# MODO: NUEVA SALIDA
# ------------------------------------------------------------
elif modo == "Nueva salida":
    st.markdown("#### Crear una nueva salida")
    ddmm = st.text_input("Fecha de salida (DDMM)", max_chars=4, placeholder="2705")
    if ddmm and len(ddmm) == 4:
        if ddmm in salidas:
            st.warning(f"La salida {ddmm} ya existe.")
        else:
            if st.button("✅ Crear salida"):
                with st.spinner("Creando salida..."):
                    crearsalida(ddmm, cabinas)
                    st.cache_data.clear()
                    st.success(f"Salida {ddmm} creada correctamente en el entorno {ANIO}.")
                    st.rerun()

# ------------------------------------------------------------
# MODOS INTERACTIVOS (SALIDAS EXISTENTES)
# ------------------------------------------------------------
else:
    if not salidas:
        st.info("No hay salidas creadas todavía.")
        st.stop()

    ddmm_sel = st.selectbox("Selecciona salida para operar", salidas)

    if ddmm_sel:
        datos = getdatossalida(ddmm_sel)

        if not datos:
            st.warning("La salida seleccionada no contiene datos.")
            st.stop()

        # Conteo e integraciones globales
        cabinas_por_ag_cat = defaultdict(int)
        pax_por_ag_cat = defaultdict(int)
        sold_por_ag_cat = defaultdict(int) 
        
        localizadores_por_agencia = defaultdict(list)
        notas_por_agencia = defaultdict(list)
        agencias_activas = set()
        cupos_config = {}

        for d in datos:
            cabina_id = d.get("cabina", "").strip()
            ag_en_fila = d.get("agencia", "").strip()
            estado_en_fila = d.get("estado", "LIBRE").strip()
            loc_en_fila = d.get("localizador", "").strip()
            notes_en_fila = d.get("notes", "").strip()
            
            cat_en_fila = next((c[3] for c in cabinas if c[1] == cabina_id), "").strip()

            if ag_en_fila and cat_en_fila:
                agencias_activas.add(ag_en_fila)
                cabinas_por_ag_cat[(ag_en_fila, cat_en_fila)] += 1
                
                if estado_en_fila == "VENDIDA":
                    sold_por_ag_cat[(ag_en_fila, cat_en_fila)] += 1
                   
                try:
                    pax_cabina = int(d.get("pax", 0) or 0)
                    pax_por_ag_cat[(ag_en_fila, cat_en_fila)] += pax_cabina
                except ValueError:
                    pass

                if loc_en_fila and loc_en_fila not in localizadores_por_agencia[ag_en_fila]:
                    localizadores_por_agencia[ag_en_fila].append(loc_en_fila)
                if notes_en_fila and notes_en_fila not in notas_por_agencia[ag_en_fila]:
                    notas_por_agencia[ag_en_fila].append(notes_en_fila)

            c_ag = d.get("cupo_agencia", "").strip()
            c_max = d.get("cupo_maximo", "").strip()

            if c_ag and "|" in c_ag and c_max and "," in c_max:
                try:
                    ag_cupo, cat_cupo = c_ag.split("|")
                    max_cab, max_px = c_max.split(",")
                    ag_cupo_strip = ag_cupo.strip()
                    cat_cupo_strip = cat_cupo.strip()
                    
                    cupos_config[(ag_cupo_strip, cat_cupo_strip)] = {
                        "cabinas": int(max_cab),
                        "pax": int(max_px)
                    }
                    agencias_activas.add(ag_cupo_strip)
                except ValueError:
                    pass

        # ------------------------------------------------------------
        # MODO: INFORME (CONEXIÓN CRM + DRIVE CONF)
        # ------------------------------------------------------------
        if modo == "Informe":
            st.markdown(f"### 📈 Informe de Estado Consolidado Cruzado — Salida {ddmm_sel}")
            st.markdown(f"Este informe dinámico unifica el **CRM ({CRMBARCO_NAME})** y los ficheros de reservas externas **CONF** de Drive.")

            # Búsqueda externa en Drive en segundo plano
            with st.spinner("Buscando ficheros de confirmaciones (CONF) en Google Drive..."):
                archivo_conf_id = buscar_archivo_conf(ddmm_sel)
                if archivo_conf_id:
                    datos_externos_conf = extraer_datos_archivo_conf(archivo_conf_id)
                    st.caption(f"✨ Conectado exitosamente al archivo externo de Drive ID: `{archivo_conf_id}`")
                else:
                    datos_externos_conf = {}
                    st.caption("ℹ️ No se localizó un archivo CONF equivalente para esta salida en Google Drive.")

            # Consolidar todas las agencias tanto de CRM como del fichero CONF
            todas_las_agencias_informe = agencias_activas.union(set(datos_externos_conf.keys()))

            if not todas_las_agencias_informe:
                st.info("No se registra actividad en ninguna base de datos para esta salida.")
            else:
                html_tabla = '<table class="informe-tabla"><thead><tr>'
                html_tabla += '<th>Origen</th>'
                html_tabla += '<th>Color</th>'
                html_tabla += '<th>Código Agencia</th>'
                
                for cat in todas_categorias:
                    html_tabla += f'<th>{cat} (Cupo)</th>'
                    html_tabla += f'<th>{cat} PAX</th>'
                    html_tabla += f'<th class="th-sold">{cat} SOLD</th>'
                    
                html_tabla += '<th>Localizador</th>'
                html_tabla += '<th>Notes</th>'
                html_tabla += '</tr></thead><tbody>'

                for ag_codigo in sorted(list(todas_las_agencias_informe)):
                    color_hex = agencias.get(ag_codigo, "#F3F4F6")
                    
                    # --- FILA ORIGEN: CRM ---
                    if ag_codigo in agencias_activas:
                        html_tabla += '<tr>'
                        html_tabla += '<td style="font-weight:bold; color:#1E3A8A; background:#F0F4FF;">CRM</td>'
                        html_tabla += f'<td><span class="color-block" style="background-color: {color_hex};"></span></td>'
                        html_tabla += f'<td style="font-weight: 700; text-align: left;">{ag_codigo}</td>'
                        
                        for cat in todas_categorias:
                            limites = cupos_config.get((ag_codigo, cat), {"cabinas": 0, "pax": 0})
                            cab_cupo = limites["cabinas"]
                            pax_cupo = limites["pax"]
                            cab_sold = sold_por_ag_cat.get((ag_codigo, cat), 0)
                            
                            val_cupo = cab_cupo if cab_cupo > 0 else "-"
                            val_pax = pax_cupo if pax_cupo > 0 else "-"
                            val_sold = cab_sold if cab_sold > 0 else "0"
                            
                            html_tabla += f'<td>{val_cupo}</td>'
                            html_tabla += f'<td>{val_pax}</td>'
                            html_tabla += f'<td class="td-sold">{val_sold}</td>'
                            
                        locs_str = ", ".join(localizadores_por_agencia[ag_codigo]) if localizadores_por_agencia[ag_codigo] else "-"
                        notes_str = " | ".join(notas_por_agencia[ag_codigo]) if notas_por_agencia[ag_codigo] else "-"
                        
                        html_tabla += f'<td style="text-align: left; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{locs_str}">{locs_str}</td>'
                        html_tabla += f'<td style="text-align: left; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{notes_str}">{notes_str}</td>'
                        html_tabla += '</tr>'

                    # --- FILA ORIGEN: CONF (SI EXISTE EN DRIVE) ---
                    if ag_codigo in datos_externos_conf:
                        conf_node = datos_externos_conf[ag_codigo]
                        html_tabla += '<tr>'
                        html_tabla += '<td style="font-weight:bold; color:#15803D; background:#F0FDF4;">CONF</td>'
                        html_tabla += f'<td><span class="color-block" style="background-color: {color_hex};"></span></td>'
                        html_tabla += f'<td style="font-weight: 700; text-align: left; color:#15803D;">{ag_codigo}</td>'
                        
                        for cat in todas_categorias:
                            # CONF no maneja cupos ni pax previstos en las hojas de confirmación directamente
                            val_cupo_conf = "-"
                            val_pax_conf = "-"
                            val_sold_conf = conf_node["sold_por_cat"].get(cat,
