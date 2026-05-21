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
# CONSTANTES Y ENTORNO
# ============================================================
BARCO = "MS_VISTA_RIO"
ANIO = "2026"  
CRMBARCO_NAME = f"{BARCO}_{ANIO}_CRM"

MASTERCABINASID = "1K-Tn_E3QEhCplOP-IFHbKZc-vtKAxFEUBbZVK14EjJI"
CRMBARCO = "1ApNv3qK-_2ANOVwSZoOchAdwWaeQg0Evz-n54s6T2cE"
LOGOID = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGOURL = f"https://lh3.googleusercontent.com/d/{LOGOID}"

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
# LÓGICA DE BÚSQUEDA Y EXTRACCIÓN EN DRIVE DIRECTA
# ============================================================
def buscar_archivo_conf(ddmm):
    drive_service = getdriveservice()
    aa = ANIO[2:]
    mm = ddmm[2:4]
    dd = ddmm[0:2]
    nombre_archivo_esperado = f"{BARCO}_{aa}{mm}{dd}"
    
    try:
        q = f"name = '{nombre_archivo_esperado}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
        res = drive_service.files().list(
            q=q, 
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=1
        ).execute()
        
        archivos = res.get("files", [])
        if archivos:
            return archivos[0]["id"], f"✅ Archivo CONF localizado y vinculado directamente: `{archivos[0]['name']}`"
        else:
            return None, f"🔎 No se encontró ningún archivo con el nombre exacto `{nombre_archivo_esperado}` al que la cuenta de servicio tenga acceso."
    except Exception as e:
        return None, f"💥 Error de comunicación con la API de Google Drive: {str(e)}"

@st.cache_data(ttl=60)
def extraer_datos_archivo_conf(spreadsheet_id):
    """Procesa el contenido de las pestañas del archivo CONF analizando rigurosamente B2 antes de agrupar por P5"""
    sheets_service = getsheetsservice()
    try:
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        hojas = [s["properties"]["title"] for s in spreadsheet.get("sheets", [])]
    except Exception:
        return {}

    # Diccionario temporal para ir agrupando los datos por código de agencia (P5)
    datos_conf_agencia = defaultdict(lambda: {"sold_por_cat": defaultdict(int), "localizadores": set(), "notes": set()})

    # 1. Ir hoja por hoja
    for hoja in hojas:
        try:
            # Traemos en bloque las celdas clave de la hoja actual
            result = sheets_service.spreadsheets().values().batchGet(
                spreadsheetId=spreadsheet_id,
                ranges=[f"'{hoja}'!B2", f"'{hoja}'!P5", f"'{hoja}'!G11", f"'{hoja}'!G24:G50", f"'{hoja}'!Q24:Q50"]
            ).execute()
            
            value_ranges = result.get("valueRanges", [])
            if len(value_ranges) < 5:
                continue
                
            # 2. Comprobar rigurosamente si la celda B2 contiene BOOKING o PROFORMA
            b2_rows = value_ranges[0].get("values", [])
            b2_val = b2_rows[0][0].strip().upper() if b2_rows and b2_rows[0] else ""
            
            if not any(x in b2_val for x in ["BOOKING", "PROFORMA"]):
                continue  # Si no coincide, salta por completo esta hoja sin procesar nada más
            
            # 3. Leer código de la agencia (P5) para agruparlo posteriormente
            p5_rows = value_ranges[1].get("values", [])
            agencia_cod = p5_rows[0][0].strip() if p5_rows and p5_rows[0] else ""
            
            if not agencia_cod:
                continue # Si la hoja es válida pero no tiene agencia asignada, se descarta
                
            # 4. Procesar y extraer la información restante de la hoja confirmada
            g11_rows = value_ranges[2].get("values", [])
            loc_original = g11_rows[0][0].strip() if g11_rows and g11_rows[0] else ""
            loc_limpio = "".join(re.findall(r'\d+$', loc_original)) or loc_original

            if loc_limpio:
                datos_conf_agencia[agencia_cod]["localizadores"].add(loc_limpio)
            datos_conf_agencia[agencia_cod]["notes"].add(f"Hoja: {hoja}")

            # Conteo de pax y mapeo por categorías
            pax_rows = value_ranges[3].get("values", [])
            cat_rows = value_ranges[4].get("values", [])

    max_filas = max(len(pax_rows), len(cat_rows))
    
    for idx in range(max_filas):
    
        pax_count = 0
        cat_val = ""
    
        # -------------------------------------------------
        # CONTAR PAX REALES DENTRO DE LA CELDA Gxx
        # -------------------------------------------------
        if idx < len(pax_rows) and pax_rows[idx]:
    
            texto_pax = pax_rows[idx][0].strip()
    
            if texto_pax:
    
                # separa por saltos de línea
                lineas_pax = [
                    x.strip()
                    for x in texto_pax.split("\n")
                    if x.strip()
                ]
    
                pax_count = len(lineas_pax)
    
        # -------------------------------------------------
        # LEER CATEGORÍA Qxx
        # -------------------------------------------------
        if idx < len(cat_rows) and cat_rows[idx]:
    
            raw_cat = cat_rows[idx][0].strip()
    
            if raw_cat:
                cat_val = raw_cat.split("/")[-1].strip() if "/" in raw_cat else raw_cat
    
        # -------------------------------------------------
        # SUMAR PAX A LA CATEGORÍA
        # -------------------------------------------------
        if cat_val and pax_count > 0:
            datos_conf_agencia[agencia_cod]["sold_por_cat"][cat_val] += pax_count

        except Exception:
            continue

    # Conversión limpia a tipos nativos para que Streamlit guarde en caché correctamente
    resultado_serializable = {}
    for agencia, info in datos_conf_agencia.items():
        resultado_serializable[agencia] = {
            "sold_por_cat": dict(info["sold_por_cat"]),
            "localizadores": list(info["localizadores"]),
            "notes": list(info["notes"])
        }

    return resultado_serializable

# ============================================================
# FUNCIONES INTERNAS CRM SHEETS
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
# CSS INTERFAZ NATIVA ORIGINAL
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
        # MODO: INFORME
        # ------------------------------------------------------------
        if modo == "Informe":
            st.markdown(f"### 📈 Informe de Estado Consolidado Cruzado — Salida {ddmm_sel}")
            st.markdown(f"Este informe dinámico unifica el **CRM ({CRMBARCO_NAME})** y los ficheros de reservas externas **CONF** de Drive.")

            with st.spinner("Buscando ficheros de confirmaciones (CONF) en Google Drive..."):
                archivo_conf_id, mensaje_rastreo = buscar_archivo_conf(ddmm_sel)
                
                if archivo_conf_id:
                    st.success(mensaje_rastreo)
                    datos_externos_conf = extraer_datos_archivo_conf(archivo_conf_id)
                else:
                    st.error(mensaje_rastreo)
                    datos_externos_conf = {}

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
                    
                    # --- CRM FILA ---
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
                            html_tabla += f'<th class="td-sold">{val_sold}</th>'
                            
                        locs_str = ", ".join(localizadores_por_agencia[ag_codigo]) if localizadores_por_agencia[ag_codigo] else "-"
                        notes_str = " | ".join(notas_por_agencia[ag_codigo]) if notas_por_agencia[ag_codigo] else "-"
                        
                        html_tabla += f'<td style="text-align: left; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{locs_str}">{locs_str}</td>'
                        html_tabla += f'<td style="text-align: left; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{notes_str}">{notes_str}</td>'
                        html_tabla += '</tr>'

                    # --- CONF FILA ---
                    if ag_codigo in datos_externos_conf:
                        conf_node = datos_externos_conf[ag_codigo]
                        html_tabla += '<tr>'
                        html_tabla += '<td style="font-weight:bold; color:#15803D; background:#F0FDF4;">CONF</td>'
                        html_tabla += f'<td><span class="color-block" style="background-color: {color_hex};"></span></td>'
                        html_tabla += f'<td style="font-weight: 700; text-align: left; color:#15803D;">{ag_codigo}</td>'
                        
                        for cat in todas_categorias:
                            val_cupo_conf = "-"
                            val_pax_conf = "-"
                            val_sold_conf = conf_node["sold_por_cat"].get(cat, 0)
                            
                            html_tabla += f'<td style="color:#6B7280;">{val_cupo_conf}</td>'
                            html_tabla += f'<td style="color:#6B7280;">{val_pax_conf}</td>'
                            html_tabla += f'<td class="td-sold" style="background-color:#F0FDF4; color:#166534;">{val_sold_conf}</td>'
                            
                        locs_conf_str = ", ".join(conf_node["localizadores"]) if conf_node["localizadores"] else "-"
                        notes_conf_str = " | ".join(conf_node["notes"]) if conf_node["notes"] else "-"
                        
                        html_tabla += f'<td style="text-align: left; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{locs_conf_str}">{locs_conf_str}</td>'
                        html_tabla += f'<td style="text-align: left; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{notes_conf_str}">{notes_conf_str}</td>'
                        html_tabla += '</tr>'
                        
                html_tabla += '</tbody></table>'
                st.markdown(html_tabla, unsafe_allow_html=True)

        # ------------------------------------------------------------
        # OPCIÓN: VER CUPOS
        # ------------------------------------------------------------
        elif modo == "Ver Cupos":
            st.markdown(f"### 📊 Cuadro de Mandos de Cupos — Salida {ddmm_sel}")
            if not cupos_config:
                st.info("No hay cupos configurados para esta salida. Configúralos en la pestaña 'Configurar Cupos'.")
            else:
                tabla_cupos = []
                for (ag, cat), lims in cupos_config.items():
                    cab_lim = lims["cabinas"]
                    pax_lim = lims["pax"]
                    cab_usadas = cabinas_por_ag_cat[(ag, cat)]
                    pax_usados = pax_por_ag_cat[(ag, cat)]
                    cab_disp = cab_lim - cab_usadas
                    pax_disp = pax_lim - pax_usados
                    status = "✅ OK"
                    if cab_disp < 0 or pax_disp < 0:
                        status = "🚨 Excedido"

                    tabla_cupos.append({
                        "Agencia": ag,
                        "Categoría": cat,
                        "Cupo Cabinas": cab_lim,
                        "Cabinas Ocupadas": cab_usadas,
                        "Cabinas Disp.": cab_disp,
                        "Cupo Pax (Personas)": pax_lim,
                        "Pax Registrados": pax_usados,
                        "Pax Disp.": pax_disp,
                        "Estado": status
                    })

                if tabla_cupos:
                    st.table(tabla_cupos)

        # ------------------------------------------------------------
        # OPCIÓN: CONFIGURAR CUPOS
        # ------------------------------------------------------------
        elif modo == "Configurar Cupos":
            st.markdown(f"### ⚙️ Definir Límites por Categoría — Salida {ddmm_sel}")
            col_a, col_b = st.columns(2)
            with col_a:
                agencia_cupo = st.selectbox("1. Selecciona la Agencia", list(agencias.keys()))
            with col_b:
                categoria_cupo = st.selectbox("2. Selecciona la Categoría del Buque", todas_categorias)

            valores_actuales = cupos_config.get((agencia_cupo, categoria_cupo), {"cabinas": 0, "pax": 0})

            st.markdown("---")
            c_l1, c_l2 = st.columns(2)
            with c_l1:
                limite_cabinas = st.number_input("Número MÁXIMO de Cabinas autorizadas", min_value=0, max_value=50, value=valores_actuales["cabinas"])
            with c_l2:
                limite_pax = st.number_input("Número MÁXIMO de Personas (Pax) autorizadas", min_value=0, max_value=150, value=valores_actuales["pax"])

            if st.button("💾 Guardar Límites de Cupo"):
                with st.spinner("Sincronizando con base de datos..."):
                    clave_compuesta = f"{agencia_cupo}|{categoria_cupo}"
                    datos_limites_str = f"{limite_cabinas},{limite_pax}"
                    guardar_cupo_sheets(ddmm_sel, datos, clave_compuesta, datos_limites_str)
                    st.cache_data.clear()
                    st.success(f"Límites guardados para {agencia_cupo} en {categoria_cupo} ({limite_cabinas} Cabinas / {limite_pax} Pax).")
                    st.rerun()

        # ------------------------------------------------------------
        # OPCIÓN: MAPA DE CABINAS
        # ------------------------------------------------------------
        elif modo == "Mapa de cabinas":
            estadocabina = {d.get("cabina", ""): d for d in datos}
            porcategoria = defaultdict(list)
            for c in cabinas:
                porcategoria[c[3]].append(c[1])

            if cupos_config:
                with st.expander("📊 Vista Rápida de Alertas de Cupos Avanzados (Categorías)", expanded=True):
                    c_cups = st.columns(min(len(cupos_config), 4))
                    for idx, ((ag, cat), lims) in enumerate(cupos_config.items()):
                        c_max = lims["cabinas"]
                        p_max = lims["pax"]
                        c_act = cabinas_por_ag_cat[(ag, cat)]
                        p_act = pax_por_ag_cat[(ag, cat)]

                        with c_cups[idx % len(c_cups)]:
                            excedido = (c_act > c_max) or (p_act > p_max)
                            label_tarjeta = f"{'🚨' if excedido else '💼'} {ag} ({cat})"
                            val_tarjeta = f"Cab: {c_act}/{c_max} | Pax: {p_act}/{p_max}"
                            st.metric(label=label_tarjeta, value=val_tarjeta)

            st.markdown(f"### 🚢 Distribución de Cubiertas — Salida {ddmm_sel}")
            st.caption("◀ Conteo desde la Derecha hacia la Izquierda en ambas filas")

            st.markdown(
                '''
                <div class="leyenda-estados">
                    <div class="leyenda-item">
                        <span class="leyenda-box leyenda-libre"></span> Libre
                    </div>
                    <div class="leyenda-item">
                        <span class="leyenda-box leyenda-reserva"></span> Reserva (RVA)
                    </div>
                    <div class="leyenda-item">
                        <span class="leyenda-box leyenda-vendida"></span> Vendida (SOLD)
                    </div>
                </div>
                ''',
                unsafe_allow_html=True,
            )

            for categoria, nums in porcategoria.items():
                st.markdown(f'<div class="categoria-label">📍 {categoria}</div>', unsafe_allow_html=True)

                impares = []
                pares = []

                for num in nums:
                    try:
                        num_limpio = ''.join(filter(str.isdigit, num))
                        val = int(num_limpio)
                        if val % 2 != 0:
                            impares.append((val, num))
                        else:
                            pares.append((val, num))
                    except ValueError:
                        pares.append((999, num))

                impares_ordenados = [item[1] for item in sorted(impares, key=lambda x: x[0], reverse=True)]
                pares_ordenados = [item[1] for item in sorted(pares, key=lambda x: x[0], reverse=True)]

                def render_cabina(num):
                    info = estadocabina.get(num, {})
                    agencia = info.get("agencia", "").strip()
                    estado = info.get("estado", "LIBRE").strip()
                    cant_pax = info.get("pax", "")
                    pax_txt = f" ({cant_pax}p)" if cant_pax and str(cant_pax).isdigit() and int(cant_pax) > 0 else ""

                    color = agencias.get(agencia, "#F3F4F6") if agencia else "#F3F4F6"
                    textcolor = "#1F2937" if agencia else "#9CA3AF"

                    if estado == "VENDIDA":
                        border_color = "#1F2937"
                        border_width = "3px"
                        border_style = "solid"
                        css_class = "cabina-box cabina-vendida"
                    elif estado == "RESERVA":
                        border_color = "#F59E0B"
                        border_width = "2px"
                        border_style = "dashed"
                        css_class = "cabina-box cabina-reserva"
                    else:
                        border_color = "#D1D5DB"
                        border_width = "2px"
                        border_style = "solid"
                        css_class = "cabina-box cabina-libre"

                    sublabel = f"{agencia}{pax_txt}" if agencia else ""

                    return f'''
                    <div class="{css_class}"
                         style="background:{color};border-color:{border_color};border-width:{border_width};border-style:{border_style};color:{textcolor};"
                         onclick="window.parent.postMessage({{type:'streamlit:setComponentValue', value:'{num}'}}, '*')">
                        <span class="cabina-num-destacado">{num}</span>
                        <span style="font-size:0.58rem; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:72px; text-align:center; margin-top:2px;">{sublabel}</span>
                    </div>'''

                html = '<div class="deck-layout">'
                html += '<div class="deck-row deck-row-style">'
                for num in impares_ordenados:
                    html += render_cabina(num)
                html += '</div>'
                html += '<div class="horizontal-corridor">Pasillo Central de Cubierta</div>'
                html += '<div class="deck-row deck-row-style">'
                for num in pares_ordenados:
                    html += render_cabina(num)
                html += '</div>'
                html += '</div>'
                st.markdown(html, unsafe_allow_html=True)

            # Panel individual de guardado
            st.markdown("---")
            st.markdown("#### ✏️ Asignar cabina")

            col1, col2 = st.columns([1, 2])
            with col1:
                nums_disponibles = [c[1] for c in cabinas]
                cabina_input = st.selectbox("Cabina", sorted(nums_disponibles))

            if cabina_input:
                info = estadocabina.get(cabina_input, {})
                agencia_actual_cabina = info.get("agencia", "").strip()
                pax_actual_cabina = int(info.get("pax", 0) or 0)
                estado_actual_cabina = info.get("estado", "LIBRE").strip()
                if estado_actual_cabina not in ESTADOS_VALIDOS:
                    estado_actual_cabina = "LIBRE"

                cat_cabina_actual = next((c[3] for c in cabinas if c[1] == cabina_input), "").strip()

                permitir_guardado = True
                if agencia_actual_cabina:
                    estado_badge = "🟡 RESERVA" if estado_actual_cabina == "RESERVA" else "🔴 VENDIDA"
                    st.error(f"⚠️ **¡Atención!** La cabina {cabina_input} ({cat_cabina_actual}) ya está asignada a **{agencia_actual_cabina}** en estado **{estado_badge}**.")
                    confirmar_sustitucion = st.checkbox(f"¿Quieres sustituir la asignación de {agencia_actual_cabina}?", value=False)
                    if not confirmar_sustitucion:
                        permitir_guardado = False

                with col2:
                    agencia_sel = st.selectbox(
                        "Agencia",
                        [""] + list(agencias.keys()),
                        index=list(agencias.keys()).index(info.get("agencia", "")) + 1 if info.get("agencia") in agencias else 0,
                        disabled=not permitir_guardado
                    )

                estado_sel = st.selectbox(
                    "Estado de la reserva",
                    ESTADOS_VALIDOS,
                    index=ESTADOS_VALIDOS.index(estado_actual_cabina),
                    format_func=lambda x: {
                        "LIBRE": "⬜ LIBRE — Sin asignar",
                        "RESERVA": "🟡 RESERVA (RVA) — Bloqueada para agencia, pendiente de confirmar",
                        "VENDIDA": "🔴 VENDIDA (SOLD) — Confirmada y cerrada"
                    }.get(x, x),
                    disabled=not permitir_guardado
                )

                c1, c2, c3 = st.columns(3)
                with c1:
                    pax_input = st.number_input("Pax", min_value=0, max_value=10, value=int(info.get("pax", 0) or 0), disabled=not permitir_guardado)
                with c2:
                    loc_input = st.text_input("Localizador", value=info.get("localizador", ""), disabled=not permitir_guardado)
                with c3:
                    notas_input = st.text_input("Notas", value=info.get("notes", ""), disabled=not permitir_guardado)

                if agencia_sel and (agencia_sel, cat_cabina_actual) in cupos_config:
                    limites = cupos_config[(agencia_sel, cat_cabina_actual)]
                    max_cabs_autorizadas = limites["cabinas"]
                    max_pax_autorizados = limites["pax"]

                    cabs_actuales_en_cat = cabinas_por_ag_cat[(agencia_sel, cat_cabina_actual)]
                    pax_actuales_en_cat = pax_por_ag_cat[(agencia_sel, cat_cabina_actual)]

                    if agencia_sel == agencia_actual_cabina:
                        cabs_actuales_en_cat -= 1
                        pax_actuales_en_cat -= pax_actual_cabina

                    impacto_cabs = cabs_actuales_en_cat + 1
                    impacto_pax = pax_actuales_en_cat + pax_input

                    if impacto_cabs > max_cabs_autorizadas:
                        st.error(f"🚫 **Cupo de Cabinas Superado en {cat_cabina_actual}:** {agencia_sel} tiene asignadas {cabs_actuales_en_cat} de {max_cabs_autorizadas} cabinas autorizadas.")

                    if impacto_pax > max_pax_autorizados:
                        st.error(f"🚫 **Cupo de Pasajeros Superado en {cat_cabina_actual}:** Agregar {pax_input} personas llevaría el total a {impacto_pax} pax de los {max_pax_autorizados} permitidos.")

                if st.button("💾 Guardar", disabled=not permitir_guardado):
                    rowindex = next((i for i, d in enumerate(datos) if d.get("cabina") == cabina_input), None)
                    if rowindex is not None:
                        estado_final = estado_sel if agencia_sel else "LIBRE"
                        with st.spinner("Guardando..."):
                            guardarcabina(ddmm_sel, rowindex, agencia_sel, pax_input, loc_input, notas_input, estado_final)
                            st.cache_data.clear()
                            st.success(f"Cabina {cabina_input} guardada como **{estado_final}**.")
                            st.rerun()

# ============================================================
# PIE DE PÁGINA
# ============================================================
st.markdown("---")
st.page_link("app.py", label=" Volver al Menú Principal (Selección de Barcos)", icon="🏠")
