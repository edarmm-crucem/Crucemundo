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
            <div class="auth-warn-title">⚠️ Acceso restringido <span style="font-size:0.8em;font-style:italic;color:#B45309;">/ Restricted access</span></div>
            <div class="auth-warn-sub">No tienes acceso. Inicia sesión desde el menú principal.<br>
            <em>You don't have access. Please log in from the main menu.</em></div>
        </div>""", unsafe_allow_html=True)
    st.stop()

#### BLOQUE 3: CONSTANTES
BARCO = "MS_VISTA_RIO"                                                    # ← CAMBIAR POR BARCO
ANIO = "2026"                                                             # ← CAMBIAR AÑO
CRMBARCO_NAME = f"{BARCO}_{ANIO}_CRM"
MASTERCABINASID = "1K-Tn_E3QEhCplOP-IFHbKZc-vtKAxFEUBbZVK14EjJI"
CRMBARCO = "1ApNv3qK-_2ANOVwSZoOchAdwWaeQg0Evz-n54s6T2cE"                   # ← CAMBIAR ID CRM
LOGOURL = "favicon1.png"
ROOT_GROUPS = "1MMNH3y1E3jJIp6uUnxbwV0toAtdr2F2M"
NOMBRE_BARCO_LIMPIO = BARCO.replace("_", " ")
ESTADOS_VALIDOS = ["LIBRE", "RESERVA", "VENDIDA"]

#### BLOQUE 4: UTILIDADES
TIMEZONE = pytz.timezone("Europe/Madrid")

import base64

def getlogobase64():
    try:
        with open("favicon1.png", "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""

LOGOURL = getlogobase64()


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

# ── Helpers multi-agencia ──────────────────────────────────────────────────────

def split_pipe(val: str) -> list:
    """Divide un campo separado por | en lista de strings limpios."""
    if val and "|" in val:
        return [v.strip() for v in val.split("|")]
    return [val.strip()] if val and val.strip() else []

def join_pipe(lst: list) -> str:
    return "|".join(str(v) for v in lst)

def agregar_agencia_a_cabina(datos_cabina: dict, nueva_ag: str, nuevo_pax,
                              nuevo_loc: str, nuevas_notas: str,
                              nuevo_estado: str) -> tuple:
    """
    Añade una agencia a los campos multi-valor de una cabina.
    Si la agencia ya existe actualiza sus datos.
    Devuelve (estado, agencia_str, pax_str, loc_str, notas_str).
    """
    ags   = split_pipe(datos_cabina.get("agencia", ""))
    paxs  = split_pipe(datos_cabina.get("pax", ""))
    locs  = split_pipe(datos_cabina.get("localizador", ""))
    notas = split_pipe(datos_cabina.get("notes", ""))

    # Alinear longitudes
    while len(paxs)  < len(ags): paxs.append("")
    while len(locs)  < len(ags): locs.append("")
    while len(notas) < len(ags): notas.append("")

    if nueva_ag in ags:
        idx = ags.index(nueva_ag)
        paxs[idx]  = str(nuevo_pax)
        locs[idx]  = nuevo_loc
        notas[idx] = nuevas_notas
    else:
        ags.append(nueva_ag)
        paxs.append(str(nuevo_pax))
        locs.append(nuevo_loc)
        notas.append(nuevas_notas)

    return (
        nuevo_estado,
        join_pipe(ags),
        join_pipe(paxs),
        join_pipe(locs),
        join_pipe(notas),
    )

def quitar_agencia_de_cabina(datos_cabina: dict, ag_borrar: str) -> tuple:
    """Elimina una agencia de los campos multi-valor."""
    ags   = split_pipe(datos_cabina.get("agencia", ""))
    paxs  = split_pipe(datos_cabina.get("pax", ""))
    locs  = split_pipe(datos_cabina.get("localizador", ""))
    notas = split_pipe(datos_cabina.get("notes", ""))

    while len(paxs)  < len(ags): paxs.append("")
    while len(locs)  < len(ags): locs.append("")
    while len(notas) < len(ags): notas.append("")

    indices = [i for i, a in enumerate(ags) if a != ag_borrar]
    ags_n   = [ags[i]   for i in indices]
    paxs_n  = [paxs[i]  for i in indices]
    locs_n  = [locs[i]  for i in indices]
    notas_n = [notas[i] for i in indices]

    estado_final = "LIBRE" if not ags_n else "RESERVA"
    return (
        estado_final,
        join_pipe(ags_n),
        join_pipe(paxs_n),
        join_pipe(locs_n),
        join_pipe(notas_n),
        )

def color_cabina_html(agencias_dict: dict, ags_lista: list) -> str:
    """
    Genera el CSS background para una cabina multi-agencia.
    1 agencia  → color sólido
    2-4 agencias → franjas iguales izquierda→derecha
    """
    colores = [agencias_dict.get(a, "#F3F4F6") for a in ags_lista]
    n = len(colores)
    if n == 0:
        return "#F3F4F6"
    if n == 1:
        return colores[0]
    stops = []
    for i, c in enumerate(colores):
        pct_ini = round(i * 100 / n)
        pct_fin = round((i + 1) * 100 / n)
        stops.append(f"{c} {pct_ini}%")
        stops.append(f"{c} {pct_fin}%")
    return f"linear-gradient(90deg, {', '.join(stops)})"

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
            loc = loc_raw
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
@st.cache_data(ttl=30)
def getdescripcionessalidas():
    service = getsheetsservice()
    spreadsheet = service.spreadsheets().get(spreadsheetId=CRMBARCO).execute()
    titulos = [s["properties"]["title"] for s in spreadsheet.get("sheets", [])]
    descripciones = {}
    if not titulos:
        return descripciones
    ranges = [f"'{t}'!K1" for t in titulos]
    result = service.spreadsheets().values().batchGet(spreadsheetId=CRMBARCO, ranges=ranges).execute()
    for t, vr in zip(titulos, result.get("valueRanges", [])):
        vals = vr.get("values", [])
        descripciones[t] = vals[0][0].strip() if vals and vals[0] else ""
    return descripciones
def crearsalida(ddmm, cabinas, descripcion=""):
    service = getsheetsservice()
    service.spreadsheets().batchUpdate(spreadsheetId=CRMBARCO, body={"requests": [{"addSheet": {"properties": {"title": ddmm}}}]}).execute()
    header = [["cabina", "categoria", "estado", "agencia", "pax", "localizador", "notes", "cupo_agencia", "cupo_maximo"]]
    rows = [[c[1], c[3], "LIBRE", "", "", "", "", "", ""] for c in cabinas]
    service.spreadsheets().values().update(spreadsheetId=CRMBARCO, range=f"{ddmm}!A1", valueInputOption="RAW", body={"values": header + rows}).execute()
    # Guardar descripción en K1
    if descripcion.strip():
        service.spreadsheets().values().update(
            spreadsheetId=CRMBARCO, range=f"{ddmm}!K1",
            valueInputOption="RAW", body={"values": [[descripcion.strip()]]}
        ).execute()

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
    .en-inline { font-size: 0.78em; font-style: italic; color: #9CA3AF; }
    .th-bilingual { display: flex; flex-direction: column; align-items: center; gap: 1px; }
    .th-es { font-size: 0.82rem; font-weight: 700; }
    .th-en { font-size: 0.66rem; font-style: italic; color: #9CA3AF; }
    .td-total-cab { background-color: #EFF6FF; color: #1E40AF; font-weight: 700; }
    .th-total-cab { background-color: #DBEAFE !important; color: #1E40AF !important; }
    .section-en { font-size: 0.55em; font-style: italic; color: #9CA3AF; font-weight: 400; margin-left: 0.5em; }
    .cabina-multi { border-color: #6366F1 !important; border-width: 3px !important; border-style: solid !important; }
    .leyenda-multi { background: linear-gradient(90deg, #60A5FA 50%, #F87171 50%); border: 3px solid #6366F1; }
    .ag-badge { display:inline-block; padding:1px 7px; border-radius:99px; font-size:0.72rem;
                font-weight:700; margin:1px 2px; color:#1F2937; border:1px solid rgba(0,0,0,0.15); }
    .cabina-box { overflow: hidden; }
</style>
''', unsafe_allow_html=True)

#### BLOQUE 10: CARGA DE DATOS BASE
cabinas = getcabinas()
agencias = getagencias()
salidas = getsalidas()
descripciones_salidas = getdescripcionessalidas()

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
        <div class="ship-subtitle">Panel de Control <span class="en-inline">/ Control Panel</span> — {ANIO}</div>
        <div class="ship-capacity">👥 Cap. Máx <span class="en-inline">/ Max Cap</span>: {capacidad_total} Pax</div>
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
    "🔄 Sincronizar Cabinas FIT / GROUP → CRM → FIT / GROUP",
    "📅 Nueva salida / New Departure",
    "🏠 Inicio / Home",
]
modo = st.radio(
    "¿Qué quieres hacer? / *What would you like to do?*",
    opciones_modo, index=8, horizontal=True
)

def _modo(key):
    return key in modo

#### BLOQUE 13: MODO INICIO
if _modo("Inicio"):
    st.markdown(
        f"### 👋 Bienvenido al Panel del {NOMBRE_BARCO_LIMPIO} "
        f"<span class='section-en'>Welcome to the {NOMBRE_BARCO_LIMPIO} Dashboard</span>",
        unsafe_allow_html=True
    )
    st.markdown(f"""
        Has iniciado sesión como **{DISPLAYUSER}**.
        <span class='en'>You are logged in as **{DISPLAYUSER}**.</span>

        Desde este panel puedes gestionar la ocupación del buque.
        <span class='en'>From this panel you can manage the ship's occupancy.</span>

        ---
        * **🗺️ Mapa de cabinas** / *Cabin Map*
          &nbsp;&nbsp;&nbsp;&nbsp;Visualiza el plano de cubiertas con el estado de cada cabina en tiempo real (libre, reserva, vendida) y permite asignar agencia, pax, localizador y notas directamente sobre el mapa.
          <span class='en'>&nbsp;&nbsp;&nbsp;&nbsp;Shows the deck plan with real-time cabin status (free, on hold, sold) and lets you assign agency, pax, booking ref and notes directly on the map.</span>

        * **📊 Ver Cupos** / *View Quotas*
          &nbsp;&nbsp;&nbsp;&nbsp;Cuadro de mandos de cupos por agencia y categoría: muestra el límite autorizado de cabinas y pax, las unidades ya usadas y las disponibles, con alerta visual si se supera el cupo.
          <span class='en'>&nbsp;&nbsp;&nbsp;&nbsp;Quota dashboard by agency and category: shows authorised cabin and pax limits, units used and remaining, with a visual alert if the quota is exceeded.</span>

        * **⚙️ Configurar Cupos** / *Configure Quotas*
          &nbsp;&nbsp;&nbsp;&nbsp;Define los límites comerciales máximos de cabinas y pasajeros por agencia y categoría para cada salida. Los límites se guardan directamente en el CRM.
          <span class='en'>&nbsp;&nbsp;&nbsp;&nbsp;Set the maximum commercial limits of cabins and passengers per agency and category for each departure. Limits are saved directly to the CRM.</span>

        * **📈 Informe** / *Report*
          &nbsp;&nbsp;&nbsp;&nbsp;Informe consolidado que cruza los datos del CRM con los archivos FIT y GROUP de Drive, mostrando en una sola tabla las cabinas vendidas, cupos, localizadores y notas por agencia y categoría.
          <span class='en'>&nbsp;&nbsp;&nbsp;&nbsp;Consolidated report crossing CRM data with FIT and GROUP files from Drive, showing sold cabins, quotas, booking refs and notes per agency and category in a single table.</span>

        * **🛏️ Informe Cabinas** / *Cabin Report*
          &nbsp;&nbsp;&nbsp;&nbsp;Lista detallada de todas las cabinas de la salida filtrable por estado (todas, vendidas, reservas o libres), con agencia, pax, localizador y notas de cada una.
          <span class='en'>&nbsp;&nbsp;&nbsp;&nbsp;Detailed cabin list for the departure, filterable by status (all, sold, on hold or free), showing agency, pax, booking ref and notes for each cabin.</span>

        * **🛳️ Ocupación** / *Occupancy*
          &nbsp;&nbsp;&nbsp;&nbsp;Panel de ocupación del buque con métricas globales (cabinas vendidas, reservas, libres y pax totales) y tabla por categoría con barra de progreso visual del porcentaje de ocupación.
          <span class='en'>&nbsp;&nbsp;&nbsp;&nbsp;Ship occupancy dashboard with global metrics (sold cabins, on hold, free and total pax) and a per-category table with a visual progress bar showing occupancy percentage.</span>

        * **🔄 Sincronizar CRM → FIT**
          &nbsp;&nbsp;&nbsp;&nbsp;Módulo planificado que cruzará automáticamente las cabinas asignadas en el CRM con las confirmaciones FIT en Drive usando el localizador como clave, y pegará las cabinas en las hojas correspondientes. Las filas con conflicto quedarán marcadas para revisión manual.
          <span class='en'>&nbsp;&nbsp;&nbsp;&nbsp;Planned module that will automatically cross CRM cabin assignments with FIT confirmation files in Drive using the booking ref as key, and paste cabins into the corresponding sheets. Conflicting rows will be flagged for manual review.</span>

        * **📅 Nueva salida** / *New Departure*
          &nbsp;&nbsp;&nbsp;&nbsp;Crea una nueva fecha operativa para {ANIO} en el CRM, inicializando todas las cabinas del buque en estado LIBRE listas para asignar.
          <span class='en'>&nbsp;&nbsp;&nbsp;&nbsp;Creates a new operational date for {ANIO} in the CRM, initialising all ship cabins as FREE and ready to assign.</span>
    """, unsafe_allow_html=True)

#### BLOQUE 14: MODO NUEVA SALIDA
elif _modo("Nueva salida"):
    st.markdown(
        "#### 📅 Crear una nueva salida "
        "<span class='section-en'>Create a new departure</span>",
        unsafe_allow_html=True
    )
    col1, col2 = st.columns([1, 2])
    with col1:
        ddmm = st.text_input(
            "Fecha de salida (DDMM) / *Departure date (DDMM)*",
            max_chars=4, placeholder="2705"
        )
    with col2:
        descripcion = st.text_input(
            "Descripción / *Description*",
            placeholder="Ej: Crucero Especial Semana Santa"
        )

    if ddmm and len(ddmm) == 4:
        if ddmm in salidas:
            st.warning(f"La salida **{ddmm}** ya existe. / *Departure {ddmm} already exists.*")
        else:
            if st.button("✅ Crear salida / *Create departure*"):
                with st.spinner("Creando salida… / *Creating departure…*"):
                    crearsalida(ddmm, cabinas, descripcion)
                    st.cache_data.clear()
                    st.success(f"Salida **{ddmm}** creada en {ANIO}. / *Departure {ddmm} created for {ANIO}.*")
                    st.rerun()

#### BLOQUE 15: GUARD + SELECTOR DE SALIDA + CÁLCULO DE AGREGADOS
else:
    if not salidas:
        st.info("No hay salidas creadas todavía. / *No departures have been created yet.*")
        st.stop()

    ddmm_sel = st.selectbox(
        "Selecciona salida / *Select departure*",
        salidas,
        format_func=lambda x: f"{x} — {descripciones_salidas.get(x, '')}" if descripciones_salidas.get(x) else x
    )

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
            ag_raw    = d.get("agencia", "").strip()
            estado    = d.get("estado", "LIBRE").strip()
            loc_raw   = d.get("localizador", "").strip()
            notes_raw = d.get("notes", "").strip()
            pax_raw   = d.get("pax", "").strip()
            cat = next((c[3] for c in cabinas if c[1] == cabina_id), "").strip()

            ags_list  = split_pipe(ag_raw)
            locs_list = split_pipe(loc_raw)
            nts_list  = split_pipe(notes_raw)
            paxs_list = split_pipe(pax_raw)

            for idx, ag in enumerate(ags_list):
                if not ag or not cat:
                    continue
                agencias_activas.add(ag)
                cabinas_por_ag_cat[(ag, cat)] += 1
                if estado == "VENDIDA":
                    sold_por_ag_cat[(ag, cat)] += 1
                try:
                    pax_val = int(paxs_list[idx]) if idx < len(paxs_list) else 0
                    pax_por_ag_cat[(ag, cat)] += pax_val
                except ValueError:
                    pass
                loc_val = locs_list[idx] if idx < len(locs_list) else ""
                nt_val  = nts_list[idx]  if idx < len(nts_list)  else ""
                if loc_val and loc_val not in localizadores_por_agencia[ag]:
                    localizadores_por_agencia[ag].append(loc_val)
                if nt_val and nt_val not in notas_por_agencia[ag]:
                    notas_por_agencia[ag].append(nt_val)

            c_ag  = d.get("cupo_agencia", "").strip()
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
            st.markdown(
                f"### 📈 Informe Consolidado — Salida {ddmm_sel} "
                f"<span class='section-en'>Consolidated Report — Departure {ddmm_sel}</span>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"Cruza **CRM ({CRMBARCO_NAME})** + **FIT** + **GROUP**. "
                f"<span class='en-inline'>Crosses CRM + FIT + GROUP files from Drive.</span>",
                unsafe_allow_html=True
            )

            with st.spinner("Buscando FIT en Drive… / *Searching FIT files…*"):
                archivo_conf_id, msg = buscar_archivo_conf(ddmm_sel)
                if archivo_conf_id:
                    st.success(msg)
                    datos_externos_conf = extraer_datos_archivo_conf(archivo_conf_id)
                else:
                    st.error(msg)
                    datos_externos_conf = {}

            with st.spinner("Buscando GROUP en Drive… / *Searching GROUP files…*"):
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
                    st.success(f"✅ {len(archivos_group)} archivo(s) GROUP encontrado(s). / *{len(archivos_group)} GROUP file(s) found.*")
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
                f"<span class='section-en'>Cabin Report — Departure {ddmm_sel}</span>",
                unsafe_allow_html=True
            )
            tipo_informe = st.selectbox(
                "Selecciona el tipo de informe / *Select report type*",
                [
                    "Todas las cabinas / All cabins",
                    "Solo VENDIDAS / Sold only",
                    "Solo RESERVAS / On Hold only",
                    "Solo LIBRES / Free only",
                ]
            )
            datos_filtrados = [
                d for d in datos if
                ("Todas" in tipo_informe) or
                ("VENDIDAS" in tipo_informe and d.get("estado") == "VENDIDA") or
                ("RESERVAS" in tipo_informe and d.get("estado") == "RESERVA") or
                ("LIBRES" in tipo_informe and d.get("estado") == "LIBRE")
            ]

            def th(es, en):
                return f'<th><div class="th-bilingual"><span class="th-es">{es}</span><span class="th-en">{en}</span></div></th>'

            t = '<table class="informe-tabla"><thead><tr>'
            t += th("Cabina", "Cabin") + th("Estado", "Status") + th("Agencias", "Agencies")
            t += th("PAX", "PAX") + th("Localizador(es)", "Ref(s)") + th("Notas", "Notes")
            t += '</tr></thead><tbody>'

            for d in sorted(datos_filtrados, key=lambda x: int(re.sub(r"[^0-9]", "", x.get("cabina", "0")) or 0)):
                ag_raw   = d.get("agencia", "").strip()
                ags_lst  = split_pipe(ag_raw)
                locs_lst = split_pipe(d.get("localizador", "").strip())
                paxs_lst = split_pipe(d.get("pax", "").strip())
                nts_lst  = split_pipe(d.get("notes", "").strip())
                estado   = d.get("estado", "LIBRE")

                # Badges de agencias con su color
                ag_badges = ""
                for ag in ags_lst:
                    if not ag: continue
                    col = agencias.get(ag, "#E5E7EB")
                    ag_badges += f'<span class="ag-badge" style="background:{col};">{ag}</span>'

                pax_str = " | ".join(p for p in paxs_lst if p) or "-"
                loc_str = " | ".join(l for l in locs_lst if l) or "-"
                nt_str  = " | ".join(n for n in nts_lst  if n) or "-"

                estado_cell = {
                    "VENDIDA": '<span style="color:#991B1B;font-weight:700;">🔴 VENDIDA</span>',
                    "RESERVA": '<span style="color:#92400E;font-weight:700;">🟡 RESERVA</span>',
                    "LIBRE":   '<span style="color:#6B7280;">⬜ LIBRE</span>',
                }.get(estado, estado)

                row_bg = ""
                if len(ags_lst) > 1:
                    row_bg = ' style="background:#F5F3FF;"'
                elif estado == "VENDIDA":
                    row_bg = ' style="background:#FEF2F2;"'

                t += f'<tr{row_bg}>'
                t += f'<td style="font-weight:700;">{d.get("cabina", "")}</td>'
                t += f'<td>{estado_cell}</td>'
                t += f'<td style="text-align:left;">{ag_badges if ag_badges else "-"}</td>'
                t += f'<td>{pax_str}</td>'
                t += f'<td style="text-align:left;font-size:0.78rem;">{loc_str}</td>'
                t += f'<td style="text-align:left;font-size:0.78rem;">{nt_str}</td>'
                t += '</tr>'
            t += '</tbody></table>'
            st.markdown(t, unsafe_allow_html=True)
#### BLOQUE 18: MODO OCUPACIÓN
        elif modo == "🛳️ Ocupación / Occupancy":
            st.markdown(
                f"### 🛳️ Ocupación del Buque — Salida {ddmm_sel} "
                f"<span class='section-en'>Ship Occupancy — Departure {ddmm_sel}</span>",
                unsafe_allow_html=True
            )
            total_cabinas = len(datos)
            cab_vendidas  = sum(1 for d in datos if d.get("estado") == "VENDIDA")
            cab_fisicas_reserva = sum(1 for d in datos if d.get("estado") == "RESERVA")
            cab_reservas = sum(
                len([a for a in split_pipe(d.get("agencia", "")) if a])
                for d in datos if d.get("estado") == "RESERVA"
            )
            cab_libres    = sum(1 for d in datos if d.get("estado") == "LIBRE")
            total_pax = sum(int(d.get("pax", 0) or 0) for d in datos if d.get("estado") == "VENDIDA")
            try:
                cap_max = int(''.join(filter(str.isdigit, capacidad_total.split()[0])))
            except Exception:
                cap_max = 0
            pct_cab = round(cab_vendidas / total_cabinas * 100, 1) if total_cabinas else 0
            pct_pax = round(total_pax / cap_max * 100, 1) if cap_max else 0
            pct_res = round(cab_reservas / cab_fisicas_reserva * 100, 1) if cab_fisicas_reserva else 0
            alerta_res = "⚠️ Overbooking" if pct_res > 100 else ""
            barra_sold = min(pct_cab, 100)
            barra_res  = min(pct_res, 100)

            if barra_sold < 40:   color_sold = "#22C55E"
            elif barra_sold < 70: color_sold = "#EAB308"
            elif barra_sold < 90: color_sold = "#F97316"
            else:                 color_sold = "#EF4444"

            if barra_res < 40:   color_res = "#22C55E"
            elif barra_res < 70: color_res = "#EAB308"
            elif barra_res < 90: color_res = "#F97316"
            else:                color_res = "#EF4444"

            c1, c2, c3, c4 = st.columns(4)

            c1.metric("🔴 Vendidas / Sold", f"{cab_vendidas}", f"{pct_cab}% del total / of total")
            partes_sold = []
            partes_sold.append("<div style=\"margin-top:0.3rem;\">")
            partes_sold.append("<div style=\"background:#E5E7EB;border-radius:4px;height:8px;width:100%;margin-bottom:3px;\">")
            partes_sold.append("<div style=\"background:" + color_sold + ";width:" + str(barra_sold) + "%;height:8px;border-radius:4px;\"></div></div>")
            partes_sold.append("<div style=\"font-size:0.72rem;font-weight:700;color:" + color_sold + ";\">" + str(pct_cab) + "% ocupación</div>")
            partes_sold.append("</div>")
            c1.markdown("".join(partes_sold), unsafe_allow_html=True)

            c2.metric("🟡 Reservas / On Hold", f"{cab_reservas}", f"{pct_res}% ratio reserva / booking ratio")
            partes_res = []
            partes_res.append("<div style=\"margin-top:0.3rem;\">")
            partes_res.append("<div style=\"background:#E5E7EB;border-radius:4px;height:8px;width:100%;margin-bottom:3px;\">")
            partes_res.append("<div style=\"background:" + color_res + ";width:" + str(barra_res) + "%;height:8px;border-radius:4px;\"></div></div>")
            partes_res.append("<div style=\"font-size:0.72rem;font-weight:700;color:" + color_res + ";\">" + str(pct_res) + "% ratio" + (" — " + alerta_res if alerta_res else "") + "</div>")
            partes_res.append("</div>")
            c2.markdown("".join(partes_res), unsafe_allow_html=True)

            c3.metric("⬜ Libres / Free", f"{cab_libres}")
            c4.metric("👥 Pax SOLD", f"{total_pax}", f"{pct_pax}% cap. máx / max cap" if cap_max else "")
            st.markdown("---")

            def th(es, en):
                return f'<th><div class="th-bilingual"><span class="th-es">{es}</span><span class="th-en">{en}</span></div></th>'

            stats_cat = {}
            for cat in todas_categorias:
                cabinas_cat = [c[1] for c in cabinas if c[3] == cat]
                n_total    = len(cabinas_cat)
                n_vendidas = sum(1 for d in datos if d.get("cabina") in cabinas_cat and d.get("estado") == "VENDIDA")
                n_fisicas_reserva = sum(1 for d in datos if d.get("cabina") in cabinas_cat and d.get("estado") == "RESERVA")
                n_reservas = sum(
                    len([a for a in split_pipe(d.get("agencia", "")) if a])
                    for d in datos if d.get("cabina") in cabinas_cat and d.get("estado") == "RESERVA"
                )
                n_libres   = sum(1 for d in datos if d.get("cabina") in cabinas_cat and d.get("estado") == "LIBRE")
                pax_cat    = sum(int(d.get("pax", 0) or 0) for d in datos if d.get("cabina") in cabinas_cat and d.get("estado") == "VENDIDA")
                pct        = round(n_vendidas / n_total * 100, 1) if n_total else 0
                pct_r      = round(n_reservas / n_fisicas_reserva * 100, 1) if n_fisicas_reserva else 0
                stats_cat[cat] = {"total": n_total, "vendidas": n_vendidas, "reservas": n_reservas, "fisicas_reserva": n_fisicas_reserva, "libres": n_libres, "pax": pax_cat, "pct": pct, "pct_r": pct_r}

            t = '<table class="informe-tabla"><thead><tr>'
            t += th("Categoría", "Category")
            t += '<th class="th-total-cab"><div class="th-bilingual"><span class="th-es">Total Cabinas</span><span class="th-en">Total Cabins</span></div></th>'
            t += th("Vendidas", "Sold") + th("% Ocup.", "% Occup.") + th("Reservas", "On Hold") + th("% Ratio Reserva", "% Booking Ratio") + th("Libres", "Free") + th("Pax SOLD", "Pax Sold")
            t += '</tr></thead><tbody>'

            for cat, s in stats_cat.items():
                pct   = s["pct"]
                pct_r = s["pct_r"]

                if pct < 40:   grad = "linear-gradient(90deg, #22C55E, #86EFAC)"
                elif pct < 70: grad = "linear-gradient(90deg, #22C55E, #EAB308)"
                elif pct < 90: grad = "linear-gradient(90deg, #EAB308, #F97316)"
                else:          grad = "linear-gradient(90deg, #F97316, #EF4444)"

                if pct_r < 100:  grad_r = "linear-gradient(90deg, #22C55E, #86EFAC)"
                elif pct_r < 150: grad_r = "linear-gradient(90deg, #EAB308, #F97316)"
                else:             grad_r = "linear-gradient(90deg, #F97316, #EF4444)"

                barra_v = (
                    "<div style=\"background:#E5E7EB;border-radius:4px;height:10px;width:100%;margin-bottom:4px;\">"
                    "<div style=\"background:" + grad + ";width:" + str(pct) + "%;height:10px;border-radius:4px;\"></div></div>"
                    "<span style=\"font-size:0.78rem;font-weight:700;\">" + str(pct) + "%</span>"
                )
                barra_r = (
                    "<div style=\"background:#E5E7EB;border-radius:4px;height:10px;width:100%;margin-bottom:4px;\">"
                    "<div style=\"background:" + grad_r + ";width:" + str(min(pct_r, 100)) + "%;height:10px;border-radius:4px;\"></div></div>"
                    "<span style=\"font-size:0.78rem;font-weight:700;\">" + str(pct_r) + "%</span>"
                )

                t += (
                    "<tr>"
                    "<td style=\"font-weight:700;text-align:left;\">" + cat + "</td>"
                    "<td class=\"td-total-cab\">" + str(s["total"]) + "</td>"
                    "<td class=\"td-sold\">" + str(s["vendidas"]) + "</td>"
                    "<td style=\"min-width:120px;\">" + barra_v + "</td>"
                    "<td style=\"color:#92400E;font-weight:700;\">" + str(s["reservas"]) + "</td>"
                    "<td style=\"min-width:120px;\">" + barra_r + "</td>"
                    "<td>" + str(s["libres"]) + "</td>"
                    "<td>" + str(s["pax"]) + "</td>"
                    "</tr>"
                )

            tot_v   = sum(s["vendidas"] for s in stats_cat.values())
            tot_r   = sum(s["reservas"] for s in stats_cat.values())
            tot_fr  = sum(s["fisicas_reserva"] for s in stats_cat.values())
            tot_l   = sum(s["libres"]   for s in stats_cat.values())
            tot_t   = sum(s["total"]    for s in stats_cat.values())
            tot_p   = sum(s["pax"]      for s in stats_cat.values())
            tot_pct = round(tot_v / tot_t * 100, 1) if tot_t else 0
            tot_pct_r = round(tot_r / tot_fr * 100, 1) if tot_fr else 0

            if tot_pct < 40:   grad_tot = "linear-gradient(90deg, #22C55E, #86EFAC)"
            elif tot_pct < 70: grad_tot = "linear-gradient(90deg, #22C55E, #EAB308)"
            elif tot_pct < 90: grad_tot = "linear-gradient(90deg, #EAB308, #F97316)"
            else:              grad_tot = "linear-gradient(90deg, #F97316, #EF4444)"

            if tot_pct_r < 100:  grad_tot_r = "linear-gradient(90deg, #22C55E, #86EFAC)"
            elif tot_pct_r < 150: grad_tot_r = "linear-gradient(90deg, #EAB308, #F97316)"
            else:                 grad_tot_r = "linear-gradient(90deg, #F97316, #EF4444)"

            barra_tot = (
                "<div style=\"background:#E5E7EB;border-radius:4px;height:10px;width:100%;margin-bottom:4px;\">"
                "<div style=\"background:" + grad_tot + ";width:" + str(tot_pct) + "%;height:10px;border-radius:4px;\"></div></div>"
                "<strong style=\"font-size:0.78rem;\">" + str(tot_pct) + "%</strong>"
            )
            barra_tot_r = (
                "<div style=\"background:#E5E7EB;border-radius:4px;height:10px;width:100%;margin-bottom:4px;\">"
                "<div style=\"background:" + grad_tot_r + ";width:" + str(min(tot_pct_r, 100)) + "%;height:10px;border-radius:4px;\"></div></div>"
                "<strong style=\"font-size:0.78rem;\">" + str(tot_pct_r) + "%</strong>"
            )

            t += (
                "<tr style=\"background:#F3F4F6;font-weight:800;border-top:2px solid #D1D5DB;\">"
                "<td style=\"text-align:left;\">TOTAL</td>"
                "<td class=\"td-total-cab\">" + str(tot_t) + "</td>"
                "<td class=\"td-sold\">" + str(tot_v) + "</td>"
                "<td style=\"min-width:120px;\">" + barra_tot + "</td>"
                "<td style=\"color:#92400E;font-weight:700;\">" + str(tot_r) + "</td>"
                "<td style=\"min-width:120px;\">" + barra_tot_r + "</td>"
                "<td>" + str(tot_l) + "</td>"
                "<td>" + str(tot_p) + "</td>"
                "</tr>"
            )
            t += '</tbody></table>'
            st.markdown(t, unsafe_allow_html=True)
        
#### BLOQUE 19: MODO VER CUPOS
        elif modo == "📊 Ver Cupos / View Quotas":
            st.markdown(
                f"### 📊 Cuadro de Mandos de Cupos — Salida {ddmm_sel} "
                f"<span class='section-en'>Quota Dashboard — Departure {ddmm_sel}</span>",
                unsafe_allow_html=True
            )
            if not cupos_config:
                st.info("No hay cupos configurados. Ve a **Configurar Cupos** para añadirlos. / *No quotas configured. Go to **Configure Quotas** to add them.*")
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

                def th(es, en):
                    return f'<th><div class="th-bilingual"><span class="th-es">{es}</span><span class="th-en">{en}</span></div></th>'
                
                t = '<table class="cupos-tabla"><thead><tr>'
                t += th("Agencia", "Agency") + th("Categoría", "Category")
                t += '<th class="th-cupo-cab"><div class="th-bilingual"><span class="th-es">Cupo Cabinas</span><span class="th-en">Cabin Quota</span></div></th>'
                t += th("Cab. Usadas", "Used") + th("Cab. Fuera Cupo", "Cabins Outside Quota")
                t += th("Cabinas Categoría", "Category Cabins")
                t += '<th class="th-cupo-pax"><div class="th-bilingual"><span class="th-es">Cupo Pax</span><span class="th-en">Pax Quota</span></div></th>'
                t += th("Pax Registrados", "Registered") + th("Pax Disp.", "Avail.")
                t += th("Estado", "Status") + '</tr></thead><tbody>'
                
                for (ag, cat), lims in cupos_config.items():
                    cab_lim = lims["cabinas"]; pax_lim = lims["pax"]
                    cab_usadas = cabinas_por_ag_cat[(ag, cat)]; pax_usados = pax_por_ag_cat[(ag, cat)]
                    cab_disp = cab_lim - cab_usadas; pax_disp = pax_lim - pax_usados
                
                    total_cabinas_cat = len([c for c in cabinas if c[3] == cat])
                    cupo_supera_capacidad = cab_lim > total_cabinas_cat
                
                    excedido = cab_disp < 0 or pax_disp < 0 or cupo_supera_capacidad
                    if cupo_supera_capacidad:
                        status_html = (
                            f'<span class="td-exc">⚠️ Cupo &gt; capacidad '
                            f'<span style="font-size:0.8em;font-style:italic;">/ Quota &gt; capacity</span></span>'
                        )
                    elif excedido:
                        status_html = (
                            '<span class="td-exc">🚨 Excedido <span style="font-size:0.8em;font-style:italic;">/ Exceeded</span></span>'
                        )
                    else:
                        status_html = '<span class="td-ok">✅ OK</span>'
                
                    cat_cell_style = ' style="color:#991B1B;font-weight:700;"' if cupo_supera_capacidad else ''
                
                    t += (f'<tr><td style="font-weight:700;text-align:left;">{ag}</td><td>{cat}</td>'
                          f'<td class="td-cupo-cab">{cab_lim}</td><td>{cab_usadas}</td>'
                          f'<td>{"🔴 " if cab_disp < 0 else ""}{cab_disp}</td>'
                          f'<td{cat_cell_style}>{total_cabinas_cat}</td>'
                          f'<td class="td-cupo-pax">{pax_lim}</td><td>{pax_usados}</td>'
                          f'<td>{"🔴 " if pax_disp < 0 else ""}{pax_disp}</td>'
                          f'<td>{status_html}</td></tr>')
                t += '</tbody></table>'
                st.markdown(t, unsafe_allow_html=True)

        elif modo == "⚙️ Configurar Cupos / Configure Quotas":

            def _cabina_disponible_para_cupo(d: dict, cat: str, agencia_cupo: str) -> bool:
                if next((c[3] for c in cabinas if c[1] == d.get("cabina", "")), "") != cat:
                    return False
                estado = d.get("estado", "LIBRE")
                if estado == "VENDIDA":
                    return False
                ags_act = [a for a in split_pipe(d.get("agencia", "")) if a]
                if estado == "LIBRE" and not ags_act:
                    return True
                if estado == "RESERVA" and agencia_cupo not in ags_act and len(ags_act) < 4:
                    return True
                return False

            st.markdown(
                f"### ⚙️ Gestión de Cupos — Salida {ddmm_sel} "
                f"<span class='section-en'>Quota Management — Departure {ddmm_sel}</span>",
                unsafe_allow_html=True
            )

            subtab = st.radio(
                "Acción / *Action*",
                ["➕ Configurar / New or Edit", "✏️ Modificar o Borrar / Modify or Delete"],
                horizontal=True
            )

            if "Configurar" in subtab:
                col_a, col_b = st.columns(2)
                with col_a:
                    agencia_cupo = st.selectbox("1. Selecciona la Agencia / *Select Agency*", list(agencias.keys()))
                with col_b:
                    categoria_cupo = st.selectbox("2. Selecciona la Categoría / *Select Category*", todas_categorias)
                valores_actuales = cupos_config.get((agencia_cupo, categoria_cupo), {"cabinas": 0, "pax": 0})

                cab_ya_asignadas = cabinas_por_ag_cat.get((agencia_cupo, categoria_cupo), 0)
                cab_libres_cat = [
                    d for d in datos
                    if _cabina_disponible_para_cupo(d, categoria_cupo, agencia_cupo)
                ]

                st.markdown("---")

                c_l1, c_l2 = st.columns(2)
                with c_l1:
                    limite_cabinas = st.number_input(
                        "Nº MÁXIMO de Cabinas / *Max authorised Cabins*",
                        min_value=0, max_value=50, value=valores_actuales["cabinas"]
                    )
                with c_l2:
                    limite_pax = st.number_input(
                        "Nº MÁXIMO de Personas (Pax) / *Max authorised Passengers*",
                        min_value=0, max_value=150, value=valores_actuales["pax"]
                    )

                a_bloquear = max(0, limite_cabinas - cab_ya_asignadas)
                disponibles_para_bloqueo = len(cab_libres_cat)
                reales_a_bloquear = min(a_bloquear, disponibles_para_bloqueo)

                if limite_cabinas > 0:
                    col_inf1, col_inf2, col_inf3 = st.columns(3)
                    col_inf1.metric("Ya asignadas / Assigned", cab_ya_asignadas)
                    col_inf2.metric("A bloquear / To reserve", reales_a_bloquear)
                    col_inf3.metric("Libres disponibles / Free available", disponibles_para_bloqueo)
                
                    if a_bloquear > disponibles_para_bloqueo:
                        st.warning(
                            f"⚠️ Para cubrir el cupo de **{limite_cabinas}** cabinas faltarían "
                            f"**{a_bloquear}**, pero solo hay **{disponibles_para_bloqueo}** "
                            f"cabina(s) libres en esta categoría. "
                            f"Se bloquearán **{reales_a_bloquear}** y el cupo quedará incompleto "
                            f"({cab_ya_asignadas + reales_a_bloquear} de {limite_cabinas}). "
                            f"/ *Not enough free cabins to fully cover this quota — "
                            f"only {disponibles_para_bloqueo} available, "
                            f"{reales_a_bloquear} will be reserved "
                            f"({cab_ya_asignadas + reales_a_bloquear} of {limite_cabinas} covered).*"
                        )
                    elif reales_a_bloquear > 0:
                        st.info(
                            f"ℹ️ Al guardar se pondrán **{reales_a_bloquear}** cabina(s) en **RESERVA** "
                            f"para **{agencia_cupo}** / **{categoria_cupo}**. "
                            f"/ *{reales_a_bloquear} free cabin(s) will be set to RESERVA on save.*"
                        )
                    else:
                        st.success(
                            f"✅ El cupo ya está cubierto con las {cab_ya_asignadas} cabinas existentes. "
                            f"No se bloqueará ninguna adicional. "
                            f"/ *Quota already met — no new cabins will be reserved.*"
                        )

                if st.button("💾 Guardar Límites / *Save Limits*"):
                    with st.spinner("Sincronizando… / *Syncing…*"):
                        guardar_cupo_sheets(
                            ddmm_sel, datos,
                            f"{agencia_cupo}|{categoria_cupo}",
                            f"{limite_cabinas},{limite_pax}"
                        )

                        cabinas_bloqueadas = []
                        if reales_a_bloquear > 0:
                            cabinas_libres_ord = sorted(
                                cab_libres_cat,
                                key=lambda d: int(''.join(filter(str.isdigit, d.get("cabina", "0"))) or 0)
                            )
                            for d in cabinas_libres_ord[:reales_a_bloquear]:
                                cab_num  = d.get("cabina", "")
                                rowindex = next(
                                    (i for i, x in enumerate(datos) if x.get("cabina") == cab_num),
                                    None
                                )
                                if rowindex is None:
                                    continue
                                estado_f, ag_f, pax_f, loc_f, nt_f = agregar_agencia_a_cabina(
                                    d, agencia_cupo, "",
                                    f"CUPO:{agencia_cupo}",
                                    "Auto-reserva por cupo",
                                    "RESERVA"
                                )
                                guardarcabina(ddmm_sel, rowindex, ag_f, pax_f, loc_f, nt_f, estado_f)
                                cabinas_bloqueadas.append(cab_num)

                        st.cache_data.clear()
                        if cabinas_bloqueadas:
                            st.success(
                                f"✅ Límites guardados y **{len(cabinas_bloqueadas)}** cabina(s) bloqueadas: "
                                f"{', '.join(cabinas_bloqueadas)}. / *Limits saved and cabins reserved.*"
                            )
                        else:
                            st.success(
                                f"✅ Límites guardados: **{agencia_cupo}** / **{categoria_cupo}** — "
                                f"{limite_cabinas} Cab · {limite_pax} Pax. "
                                f"/ *Limits saved. No new auto-reservations.*"
                            )
                        st.rerun()

            # ── SUBTAB 2: MODIFICAR O BORRAR ──────────────────────────────────
            else:
                if not cupos_config:
                    st.info("No hay cupos configurados todavía. / *No quotas configured yet.*")
                else:
                    st.markdown(
                        "Selecciona un cupo existente para modificar sus límites o eliminarlo. "
                        "Al eliminar, las cabinas auto-reservadas con localizador `CUPO:agencia` "
                        "quedarán libres automáticamente. "
                        "<span class='en-inline'>/ Select an existing quota to edit or delete it. "
                        "Auto-reserved cabins will be released on deletion.</span>",
                        unsafe_allow_html=True
                    )

                    # Selector de cupo existente
                    opciones_cupo = [f"{ag} — {cat}" for (ag, cat) in sorted(cupos_config.keys())]
                    cupo_sel_str = st.selectbox(
                        "Cupo a gestionar / *Quota to manage*",
                        opciones_cupo
                    )
                    ag_sel, cat_sel = [x.strip() for x in cupo_sel_str.split("—")]
                    lims_sel = cupos_config[(ag_sel, cat_sel)]

                    # Cabinas auto-reservadas para este cupo (localizador CUPO:agencia)
                    cabinas_auto = [
                        d for d in datos
                        if ag_sel in split_pipe(d.get("agencia", ""))
                        and f"CUPO:{ag_sel}" in split_pipe(d.get("localizador", ""))
                        and next((c[3] for c in cabinas if c[1] == d.get("cabina", "")), "") == cat_sel
                    ]

                    col_info1, col_info2, col_info3 = st.columns(3)
                    col_info1.metric("Cupo cabinas / Cabin quota", lims_sel["cabinas"])
                    col_info2.metric("Cupo pax / Pax quota", lims_sel["pax"])
                    col_info3.metric(
                        "Auto-reservadas / Auto-reserved",
                        len(cabinas_auto),
                        help="Cabinas bloqueadas automáticamente al configurar el cupo"
                    )

                    if cabinas_auto:
                        st.info(
                            f"Cabinas auto-reservadas: **{', '.join(d['cabina'] for d in cabinas_auto)}**"
                        )

                    st.markdown("---")

                    # ── Modificar límites ──────────────────────────────────────
                    with st.expander("✏️ Modificar límites / *Edit limits*", expanded=False):
                        c_m1, c_m2 = st.columns(2)
                        with c_m1:
                            nuevo_lim_cab = st.number_input(
                                "Nuevo límite de Cabinas / *New cabin limit*",
                                min_value=0, max_value=50,
                                value=lims_sel["cabinas"],
                                key="mod_cab"
                            )
                        with c_m2:
                            nuevo_lim_pax = st.number_input(
                                "Nuevo límite de Pax / *New pax limit*",
                                min_value=0, max_value=150,
                                value=lims_sel["pax"],
                                key="mod_pax"
                            )

                        cab_asignadas_ahora = cabinas_por_ag_cat.get((ag_sel, cat_sel), 0)
                        diff = nuevo_lim_cab - lims_sel["cabinas"]

                        if diff > 0:
                            cab_libres_mod = [
                                d for d in datos
                                if _cabina_disponible_para_cupo(d, cat_sel, ag_sel)
                            ]
                       
                            extra_a_bloquear = min(diff, len(cab_libres_mod))
                            if extra_a_bloquear > 0:
                                st.info(
                                    f"ℹ️ Se bloquearán **{extra_a_bloquear}** cabina(s) adicionales. "
                                    f"/ *{extra_a_bloquear} additional cabin(s) will be reserved.*"
                                )
                        elif diff < 0:
                            a_liberar = min(abs(diff), len(cabinas_auto))
                            if a_liberar > 0:
                                st.info(
                                    f"ℹ️ Se liberarán **{a_liberar}** cabina(s) auto-reservadas. "
                                    f"/ *{a_liberar} auto-reserved cabin(s) will be released.*"
                                )

                        if st.button("💾 Actualizar límites / *Update limits*", key="btn_mod"):
                            with st.spinner("Actualizando… / *Updating…*"):
                                guardar_cupo_sheets(
                                    ddmm_sel, datos,
                                    f"{ag_sel}|{cat_sel}",
                                    f"{nuevo_lim_cab},{nuevo_lim_pax}"
                                )

                                # Ajustar cabinas auto-reservadas al nuevo límite
                                if diff > 0:
                                    # Bloquear más cabinas
                                    cab_libres_mod = sorted([
                                        d for d in datos
                                        if _cabina_disponible_para_cupo(d, cat_sel, ag_sel)
                                    ], key=lambda d: int(''.join(filter(str.isdigit, d.get("cabina", "0"))) or 0))
                                    for d in cab_libres_mod[:diff]:
                                        rowindex = next((i for i, x in enumerate(datos) if x.get("cabina") == d.get("cabina")), None)
                                        if rowindex is None: continue
                                        estado_f, ag_f, pax_f, loc_f, nt_f = agregar_agencia_a_cabina(
                                            d, ag_sel, "", f"CUPO:{ag_sel}", "Auto-reserva por cupo", "RESERVA"
                                        )
                                        guardarcabina(ddmm_sel, rowindex, ag_f, pax_f, loc_f, nt_f, estado_f)

                                elif diff < 0:
                                    # Liberar cabinas auto-reservadas sobrantes
                                    for d in cabinas_auto[:abs(diff)]:
                                        rowindex = next((i for i, x in enumerate(datos) if x.get("cabina") == d.get("cabina")), None)
                                        if rowindex is None: continue
                                        estado_f, ag_f, pax_f, loc_f, nt_f = quitar_agencia_de_cabina(d, ag_sel)
                                        guardarcabina(ddmm_sel, rowindex, ag_f, pax_f, loc_f, nt_f, estado_f)

                                st.cache_data.clear()
                                st.success(
                                    f"✅ Límites actualizados: **{ag_sel}** / **{cat_sel}** — "
                                    f"{nuevo_lim_cab} Cab · {nuevo_lim_pax} Pax. / *Limits updated.*"
                                )
                                st.rerun()

                    # ── Eliminar cupo ──────────────────────────────────────────
                    with st.expander("🗑️ Eliminar cupo / *Delete quota*", expanded=False):
                        st.warning(
                            f"Se eliminará el cupo de **{ag_sel}** / **{cat_sel}** "
                            f"y se liberarán **{len(cabinas_auto)}** cabina(s) auto-reservadas. "
                            f"Las cabinas con agencia asignada manualmente **no** se modifican. "
                            f"/ *The quota for {ag_sel} / {cat_sel} will be deleted and "
                            f"{len(cabinas_auto)} auto-reserved cabin(s) will be released. "
                            f"Manually assigned cabins are not affected.*"
                        )
                        confirmar = st.checkbox(
                            "Confirmo que quiero eliminar este cupo / *I confirm I want to delete this quota*",
                            key="confirm_del"
                        )
                        if st.button("🗑️ Eliminar cupo / *Delete quota*", disabled=not confirmar, key="btn_del"):
                            with st.spinner("Eliminando… / *Deleting…*"):
                                # 1. Liberar cabinas auto-reservadas
                                for d in cabinas_auto:
                                    rowindex = next((i for i, x in enumerate(datos) if x.get("cabina") == d.get("cabina")), None)
                                    if rowindex is None: continue
                                    estado_f, ag_f, pax_f, loc_f, nt_f = quitar_agencia_de_cabina(d, ag_sel)
                                    guardarcabina(ddmm_sel, rowindex, ag_f, pax_f, loc_f, nt_f, estado_f)

                                # 2. Borrar la fila del cupo en Sheets (escribir celdas vacías)
                                service = getsheetsservice()
                                for i, d in enumerate(datos):
                                    if d.get("cupo_agencia", "").strip() == f"{ag_sel}|{cat_sel}":
                                        fila = i + 2
                                        service.spreadsheets().values().update(
                                            spreadsheetId=CRMBARCO,
                                            range=f"{ddmm_sel}!H{fila}:I{fila}",
                                            valueInputOption="RAW",
                                            body={"values": [["", ""]]}
                                        ).execute()
                                        break

                                st.cache_data.clear()
                                st.success(
                                    f"✅ Cupo eliminado y {len(cabinas_auto)} cabina(s) liberadas. "
                                    f"/ *Quota deleted and cabins released.*"
                                )
                                st.rerun()

#### BLOQUE 21: MODO MAPA DE CABINAS
        elif modo == "🗺️ Mapa de cabinas / Cabin Map":
            estadocabina = {d.get("cabina", ""): d for d in datos}
            porcategoria = defaultdict(list)
            for c in cabinas:
                porcategoria[c[3]].append(c[1])

            st.markdown(
                f"### 🚢 Distribución de Cubiertas — Salida {ddmm_sel} "
                f"<span class='section-en'>Deck Layout — Departure {ddmm_sel}</span>",
                unsafe_allow_html=True
            )
            st.markdown('''
                <div class="leyenda-estados">
                    <div class="leyenda-item"><span class="leyenda-box leyenda-libre"></span>Libre <span class="leyenda-sub">/ Free</span></div>
                    <div class="leyenda-item"><span class="leyenda-box leyenda-reserva"></span>Reserva (RVA) <span class="leyenda-sub">/ On Hold</span></div>
                    <div class="leyenda-item"><span class="leyenda-box leyenda-vendida"></span>Vendida (SOLD) <span class="leyenda-sub">/ Sold</span></div>
                    <div class="leyenda-item"><span class="leyenda-box leyenda-multi"></span>Compartida <span class="leyenda-sub">/ Shared</span></div>
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
                    info    = estadocabina.get(num, {})
                    ag_raw  = info.get("agencia", "").strip()
                    est     = info.get("estado", "LIBRE").strip()
                    pax_raw = info.get("pax", "")
                    ags_lst = split_pipe(ag_raw)
                    n_ags   = len([a for a in ags_lst if a])

                    if est == "VENDIDA":
                        border_css = "border-color:#1F2937;border-width:3px;border-style:solid;"
                    elif est == "RESERVA":
                        border_css = "border-color:#1F2937;border-width:3px;border-style:dashed;"
                    else:
                        border_css = "border-color:#D1D5DB;border-width:2px;border-style:solid;"

                    if n_ags == 0:
                        bg_css    = "#F3F4F6"
                        textcolor = "#9CA3AF"
                        sublabel  = ""
                    elif n_ags == 1:
                        bg_css    = agencias.get(ags_lst[0], "#F3F4F6")
                        textcolor = "#1F2937"
                        pax_lst = split_pipe(pax_raw)
                        pax_txt = f" ({pax_lst[0]}p)" if pax_lst and pax_lst[0].isdigit() and int(pax_lst[0]) > 0 else ""
                        sublabel = f"{ags_lst[0]}{pax_txt}"
                    else:
                        ags_validas = [a for a in ags_lst if a]
                        bg_css     = color_cabina_html(agencias, ags_validas)
                        textcolor  = "#1F2937"
                        sublabel   = "+".join(ags_validas[:4])

                    return (
                        f'<div class="cabina-box" '
                        f'style="background:{bg_css};{border_css}color:{textcolor};" '
                        f'onclick="window.parent.postMessage({{type:\'streamlit:setComponentValue\',value:\'{num}\'}},\'*\')">'
                        f'<span class="cabina-num-destacado">{num}</span>'
                        f'<span style="font-size:0.52rem;font-weight:700;white-space:nowrap;overflow:hidden;'
                        f'text-overflow:ellipsis;max-width:72px;text-align:center;margin-top:2px;">{sublabel}</span>'
                        f'</div>'
                    )

                LABEL_PROA = ('<div style="min-width:32px;display:flex;align-items:center;justify-content:center;">'
                              '<div style="width:0;height:0;border-top:30px solid transparent;'
                              'border-bottom:30px solid transparent;border-left:18px solid #D1D5DB;"></div>'
                              '</div>')

                html = '<div class="deck-layout">'
                html += '<div style="display:flex;align-items:stretch;">'
                html += '<div style="flex:1;"><div class="deck-row deck-row-style">'
                for num in impares_ord:
                    html += render_cabina(num)
                html += (
                    '</div>'
                    '<div class="horizontal-corridor">Pasillo Central '
                    '<span style="font-style:italic;font-size:0.85em;opacity:0.7;">/ Central Corridor</span></div>'
                    '<div class="deck-row deck-row-style">'
                )
                for num in pares_ord:
                    html += render_cabina(num)
                html += '</div></div>'
                html += LABEL_PROA
                html += '</div></div>'
                st.markdown(html, unsafe_allow_html=True)

            #### BLOQUE 22: PANEL ASIGNAR CABINA (multi-agencia)
            st.markdown("---")
            st.markdown(
                "#### ✏️ Asignar cabina "
                "<span class='section-en'>Assign cabin</span>",
                unsafe_allow_html=True
            )

            todas_cabinas_ord = sorted([c[1] for c in cabinas])

            col1, col2 = st.columns([2, 1])
            with col1:
                cabinas_sel = st.multiselect(
                    "Cabinas / *Cabins*",
                    todas_cabinas_ord,
                    placeholder="Selecciona una o varias…"
                )
            with col2:
                # DESPUÉS
                rango = st.text_input("O rango / *Or range*", placeholder="101-105", key="rango_map")
                if rango and "-" in rango:
                    try:
                        ini, fin = rango.split("-")
                        nums_rango = set(range(int(ini.strip()), int(fin.strip()) + 1))
                        extras = [c for c in todas_cabinas_ord
                                  if int(''.join(filter(str.isdigit, c)) or 0) in nums_rango
                                  and c not in cabinas_sel]
                        cabinas_sel = cabinas_sel + extras
                    except ValueError:
                        st.warning("Rango no válido. Usa formato 101-105.")

            if cabinas_sel:
                # Mostrar agencias ya asignadas en las cabinas seleccionadas
                cabinas_con_ags = []
                for cab in cabinas_sel:
                    info = estadocabina.get(cab, {})
                    ags_act = [a for a in split_pipe(info.get("agencia", "").strip()) if a]
                    if ags_act:
                        cabinas_con_ags.append(f"**{cab}** → {', '.join(ags_act)}")
                if cabinas_con_ags:
                    st.info(
                        "ℹ️ Cabinas ya asignadas — la nueva agencia se **añadirá** sin sobreescribir:\n" +
                        " · ".join(cabinas_con_ags) +
                        "\n\n*Cabins already assigned — new agency will be **added**, not overwritten.*"
                    )

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    agencia_sel = st.selectbox("Agencia / *Agency*", [""] + list(agencias.keys()))
                with col_b:
                    estado_sel = st.selectbox(
                        "Estado / *Status*",
                        ESTADOS_VALIDOS,
                        format_func=lambda x: {
                            "LIBRE":   "⬜ LIBRE — Sin asignar",
                            "RESERVA": "🟡 RESERVA — Bloqueada",
                            "VENDIDA": "🔴 VENDIDA — Confirmada",
                        }.get(x, x)
                    )
                with col_c:
                    pax_input = st.number_input("Pax / *Pax*", min_value=0, max_value=10, value=2)

                col_d, col_e = st.columns(2)
                with col_d:
                    loc_input   = st.text_input("Localizador / *Booking Ref*", value="")
                with col_e:
                    notas_input = st.text_input("Notas / *Notes*", value="")

                # Avisos límite 4 agencias
                for cab in cabinas_sel:
                    info = estadocabina.get(cab, {})
                    ags_act = [a for a in split_pipe(info.get("agencia", "")) if a]
                    if agencia_sel and agencia_sel not in ags_act and len(ags_act) >= 4:
                        st.warning(f"⚠️ Cabina **{cab}** ya tiene 4 agencias (máximo). / *Cabin {cab} already at 4-agency limit.*")

                if st.button("💾 Añadir agencia / *Add agency*"):
                    with st.spinner("Guardando… / *Saving…*"):
                        guardadas, omitidas = [], []
                        for cab in cabinas_sel:
                            rowindex = next((i for i, d in enumerate(datos) if d.get("cabina") == cab), None)
                            if rowindex is None:
                                continue
                            info    = estadocabina.get(cab, {})
                            ags_act = [a for a in split_pipe(info.get("agencia", "")) if a]

                            if not agencia_sel:
                                # Sin agencia → limpiar cabina
                                guardarcabina(ddmm_sel, rowindex, "", "", "", "", "LIBRE")
                                guardadas.append(cab)
                                continue

                            if agencia_sel not in ags_act and len(ags_act) >= 4:
                                omitidas.append(cab)
                                continue

                            estado_f, ag_f, pax_f, loc_f, nt_f = agregar_agencia_a_cabina(
                                info, agencia_sel, pax_input, loc_input, notas_input, estado_sel
                            )
                            guardarcabina(ddmm_sel, rowindex, ag_f, pax_f, loc_f, nt_f, estado_f)
                            guardadas.append(cab)

                        st.cache_data.clear()
                        if guardadas:
                            st.success(f"✅ {len(guardadas)} cabina(s) actualizadas: {', '.join(guardadas)}")
                        if omitidas:
                            st.warning(f"⚠️ {len(omitidas)} omitidas por límite de 4 agencias: {', '.join(omitidas)}")
                        st.rerun()

                # ── Quitar agencia ────────────────────────────────────────────
                st.markdown("---")
                st.markdown(
                    "**🗑️ Quitar agencia de cabina(s)** "
                    "<span class='section-en'>Remove agency from cabin(s)</span>",
                    unsafe_allow_html=True
                )
                ags_en_seleccion = set()
                for cab in cabinas_sel:
                    for ag in split_pipe(estadocabina.get(cab, {}).get("agencia", "")):
                        if ag: ags_en_seleccion.add(ag)

                col_rm1, col_rm2 = st.columns([2, 1])
                with col_rm1:
                    ag_a_quitar = st.selectbox(
                        "Agencia a eliminar / *Agency to remove*",
                        ["—"] + sorted(list(ags_en_seleccion))
                    )
                with col_rm2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    btn_quitar = st.button("🗑️ Quitar / *Remove*", key="btn_quitar_ag")

                if btn_quitar and ag_a_quitar != "—":
                    with st.spinner("Quitando… / *Removing…*"):
                        for cab in cabinas_sel:
                            rowindex = next((i for i, d in enumerate(datos) if d.get("cabina") == cab), None)
                            if rowindex is None:
                                continue
                            info = estadocabina.get(cab, {})
                            if ag_a_quitar not in split_pipe(info.get("agencia", "")):
                                continue
                            estado_f, ag_f, pax_f, loc_f, nt_f = quitar_agencia_de_cabina(info, ag_a_quitar)
                            guardarcabina(ddmm_sel, rowindex, ag_f, pax_f, loc_f, nt_f, estado_f)
                        st.cache_data.clear()
                        st.success(f"✅ Agencia **{ag_a_quitar}** eliminada. / *Agency removed.*")
                        st.rerun()
           
#### BLOQUE 21-SYNC: MODO SINCRONIZAR CABINAS FIT/GROUP → CRM → FIT/GROUP
        elif modo == "🔄 Sincronizar Cabinas FIT / GROUP → CRM → FIT / GROUP":
            st.markdown(
                f"### 🔄 Sincronizar Cabinas FIT/GROUP ↔ CRM — Salida {ddmm_sel} "
                f"<span class='section-en'>Sync FIT/GROUP Cabins ↔ CRM — Departure {ddmm_sel}</span>",
                unsafe_allow_html=True
            )

            # ── Helpers internos ──────────────────────────────────────────────

            def _es_group(localizador: str) -> bool:
                """El localizador termina en GROUP → estado RESERVA."""
                return localizador.upper().endswith("GROUP")

            def _cabinas_libres_de_categoria(cat: str, datos_crm: list) -> list:
                """Cabinas LIBRES de una categoría (sin agencia asignada)."""
                cabinas_cat = {c[1] for c in cabinas if c[3] == cat}
                return [
                    d["cabina"] for d in datos_crm
                    if d.get("cabina") in cabinas_cat
                    and d.get("estado", "LIBRE") == "LIBRE"
                    and not d.get("agencia", "").strip()
                ]
            
            def _cabinas_reserva_desplazables_de_categoria(cat: str, datos_crm: list) -> list:
                """
                Cabinas en RESERVA de una categoría que pueden cederse a una VENDIDA.
                Prioriza las auto-reservadas por cupo (localizador CUPO:agencia),
                porque son bloqueos "blandos" sin pax real.
                Devuelve lista de cabinas ordenada: primero auto-reserva por cupo,
                luego otras reservas.
                """
                cabinas_cat = {c[1] for c in cabinas if c[3] == cat}
                candidatas_cupo = []
                candidatas_otras = []
                for d in datos_crm:
                    if d.get("cabina") not in cabinas_cat:
                        continue
                    if d.get("estado") != "RESERVA":
                        continue
                    locs = split_pipe(d.get("localizador", ""))
                    if any(l.startswith("CUPO:") for l in locs):
                        candidatas_cupo.append(d["cabina"])
                    else:
                        candidatas_otras.append(d["cabina"])
                return candidatas_cupo + candidatas_otras

            def _liberar_reserva_para_venta(cab_num: str, datos_crm: list, ddmm_sel: str) -> bool:
                """
                Libera una cabina en RESERVA (quita todas sus agencias) para dejarla
                disponible y poder asignarla como VENDIDA. Devuelve True si se liberó.
                """
                rowindex = next((i for i, d in enumerate(datos_crm) if d.get("cabina") == cab_num), None)
                if rowindex is None:
                    return False
                d_crm = datos_crm[rowindex]
                ags = [a for a in split_pipe(d_crm.get("agencia", "")) if a]
                estado_f, ag_f, pax_f, loc_f, nt_f = "LIBRE", "", "", "", ""
                for ag in ags:
                    estado_f, ag_f, pax_f, loc_f, nt_f = quitar_agencia_de_cabina(d_crm, ag)
                    d_crm.update({"agencia": ag_f, "estado": estado_f, "pax": pax_f,
                                   "localizador": loc_f, "notes": nt_f})
                guardarcabina(ddmm_sel, rowindex, ag_f, pax_f, loc_f, nt_f, estado_f)
                datos_crm[rowindex].update({"agencia": "", "pax": "", "localizador": "",
                                             "notes": "", "estado": "LIBRE"})
                return True
            
            def _obtener_cabinas_disponibles_con_prioridad(cat: str, n_necesarias: int,
                                                            datos_crm: list, estado_dst: str,
                                                            excluidas: list, warnings: list) -> list:
                """
                Devuelve hasta n_necesarias cabinas disponibles de la categoría 'cat'.
                1) Usa primero las LIBRES.
                2) Si faltan y estado_dst es VENDIDA, libera RESERVAS (con prioridad
                   para las auto-reservadas por cupo) y avisa al usuario.
                """
                libres = [c for c in _cabinas_libres_de_categoria(cat, datos_crm) if c not in excluidas]
                if len(libres) >= n_necesarias or estado_dst != "VENDIDA":
                    return libres[:n_necesarias]
            
                faltan = n_necesarias - len(libres)
                desplazables = [c for c in _cabinas_reserva_desplazables_de_categoria(cat, datos_crm)
                                 if c not in excluidas and c not in libres]
            
                liberadas = []
                for cab in desplazables:
                    if faltan <= 0:
                        break
                    if _liberar_reserva_para_venta(cab, datos_crm, ddmm_sel):
                        liberadas.append(cab)
                        faltan -= 1
            
                if liberadas:
                    warnings.append(
                        f"🔄 Categoría {cat}: no había suficientes cabinas LIBRES para la VENTA. "
                        f"Se liberaron {len(liberadas)} cabina(s) en RESERVA "
                        f"({', '.join(liberadas)}) para dar prioridad a la venta confirmada. "
                        f"/ Not enough FREE cabins for the SALE — released {len(liberadas)} "
                        f"cabin(s) previously on HOLD: {', '.join(liberadas)} (sold has priority)."
                    )
            
                return (libres + liberadas)[:n_necesarias]

            def _extraer_pax_q24(raw_q24: str) -> list:
                """
                Parsea el contenido de Q24 (multilínea) con formato  XXX / YYYY
                donde YYYY es la categoría. Devuelve lista de (categoria, n_pax).
                Cada LÍNEA es 1 persona salvo DSU en G24 (1 cabina/persona).
                """
                lineas = [l.strip() for l in raw_q24.strip().splitlines() if l.strip()]
                por_cat = defaultdict(int)
                for l in lineas:
                    if "/" in l:
                        partes = l.split("/")
                        cat_raw = partes[-1].strip()
                        cat_raw = cat_raw.split()[0] if cat_raw else cat_raw
                        por_cat[cat_raw] += 1
                return list(por_cat.items())   # [(cat, n_pax), ...]

            def _cabinas_por_categoria_fit(raw_q24: str, es_dsu: bool) -> list:
                """
                Convierte las líneas de Q24 a cabinas necesarias por categoría.
                - Normal:  1 cabina cada 2 personas de la misma categoría
                - DSU:     1 cabina por persona
                Devuelve lista de dict {cat, n_cabinas, n_pax}
                """
                pax_por_cat = _extraer_pax_q24(raw_q24)
                resultado = []
                for cat, n_pax in pax_por_cat:
                    if es_dsu:
                        n_cab = n_pax
                    else:
                        n_cab = max(1, round(n_pax / 2))
                    resultado.append({"cat": cat, "n_cab": n_cab, "n_pax": n_pax})
                return resultado

            # ── 1. Cargar archivo FIT del Drive ───────────────────────────────
            with st.spinner("Buscando archivo FIT en Drive… / *Looking for FIT file…*"):
                archivo_conf_id, msg_fit = buscar_archivo_conf(ddmm_sel)

            if not archivo_conf_id:
                st.error(msg_fit)
                st.stop()

            st.success(msg_fit)

            # ── 2. Leer todas las hojas relevantes del FIT ────────────────────
            @st.cache_data(ttl=30)
            @st.cache_data(ttl=30)
            def _leer_hojas_fit(spreadsheet_id: str) -> list:
                svc = getsheetsservice()
                CAT_MAP = {"PRINCIPAL": "MAIN", "INTERMEDIA": "MID", "SUPERIOR": "UPP"}
                COLS_GROUP = ["G", "K", "N", "O"]
                try:
                    meta = svc.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                    hojas = [s["properties"]["title"] for s in meta.get("sheets", [])]
                except Exception:
                    return []

                resultado = []
                for hoja in hojas:
                    try:
                        vr = svc.spreadsheets().values().batchGet(
                            spreadsheetId=spreadsheet_id,
                            ranges=[
                                f"'{hoja}'!B2",   # 0 tipo doc
                                f"'{hoja}'!P5",   # 1 agencia
                                f"'{hoja}'!G11",  # 2 localizador
                                f"'{hoja}'!G56",  # 3 cabina asignada
                                f"'{hoja}'!Q24",  # 4 lista pax/categoría (FIT)
                                f"'{hoja}'!G24",  # 5 primer campo pax DSU (FIT)
                                # GROUP filas 20/21/22 por columna
                                f"'{hoja}'!G20", f"'{hoja}'!G21", f"'{hoja}'!G22",  # 6,7,8
                                f"'{hoja}'!K20", f"'{hoja}'!K21", f"'{hoja}'!K22",  # 9,10,11
                                f"'{hoja}'!N20", f"'{hoja}'!N21", f"'{hoja}'!N22",  # 12,13,14
                                f"'{hoja}'!O20", f"'{hoja}'!O21", f"'{hoja}'!O22",  # 15,16,17
                            ]
                        ).execute().get("valueRanges", [])

                        def cv(i):
                            rows = vr[i].get("values", []) if i < len(vr) else []
                            return rows[0][0].strip() if rows and rows[0] else ""

                        b2 = cv(0).upper()
                        if not any(k in b2 for k in ["BOOKING", "PROFORMA"]):
                            continue

                        loc      = cv(2)
                        es_group = loc.upper().endswith("GROUP")
                        cab_g56  = cv(3)

                        # Construir preview GROUP desde filas 20-22
                        group_preview = []
                        group_cats    = []   # lista de {cat, n_cab, n_pax} para ejecución
                        if es_group:
                            for i, col in enumerate(COLS_GROUP):
                                base    = 6 + i * 3
                                raw_cab = cv(base)
                                raw_cat = cv(base + 1).upper()
                                raw_pax = cv(base + 2)
                                if not raw_cab or not raw_cat:
                                    continue
                                m_cab = re.match(r"(\d+)", raw_cab)
                                m_pax = re.match(r"(\d+)", raw_pax) if raw_pax else None
                                if not m_cab:
                                    continue
                                cat   = CAT_MAP.get(raw_cat, raw_cat)
                                n_cab = int(m_cab.group(1))
                                n_pax = int(m_pax.group(1)) if m_pax else 0
                                group_preview.append(f"{n_cab} cab × {cat} ({n_pax} pax)")
                                group_cats.append({"cat": cat, "n_cab": n_cab, "n_pax": n_pax})

                        resultado.append({
                            "hoja":          hoja,
                            "agencia":       cv(1),
                            "localizador":   loc,
                            "cabina_g56":    cab_g56,
                            "q24_raw":       vr[4].get("values", [[""]])[0][0].strip() if len(vr) > 4 and vr[4].get("values") else "",
                            "es_dsu":        "DSU" in cv(5).upper(),
                            "es_group":      es_group,
                            "group_preview": group_preview,
                            "group_cats":    group_cats,
                        })
                    except Exception:
                        continue
                return resultado
            hojas_fit = _leer_hojas_fit(archivo_conf_id)

            if not hojas_fit:
                st.warning("No se encontraron hojas con BOOKING/PROFORMA en B2. / *No BOOKING/PROFORMA sheets found.*")
                st.stop()

            # ── 3. Valoración inicial ─────────────────────────────────────────
            st.markdown(
                "#### 🔍 Valoración inicial "
                "<span class='section-en'>Initial assessment</span>",
                unsafe_allow_html=True
            )
            st.markdown(
                "Revisión de cada confirmación antes de ejecutar cambios. "
                "<span class='en-inline'>/ Review of each confirmation before applying any changes.</span>",
                unsafe_allow_html=True
            )

            def th(es, en=""):
                inner = (f'<div class="th-bilingual"><span class="th-es">{es}</span>'
                         f'<span class="th-en">{en}</span></div>') if en else es
                return f"<th>{inner}</th>"

            filas_valoracion = []
            datos_crm_live = getdatossalida(ddmm_sel)

            def _normalizar_loc(loc: str) -> str:
                """Extrae la parte final tras el último guión, quitando ceros a la izquierda."""
                loc = loc.strip()
                if "-" in loc:
                    loc = loc.rsplit("-", 1)[-1]
                return loc.lstrip("0") or loc  # evita que "000" quede vacío
            
            crm_por_loc = {}
            for d in datos_crm_live:
                loc_crm = d.get("localizador", "").strip()
                if loc_crm:
                    key = _normalizar_loc(loc_crm)
                    crm_por_loc.setdefault(key, []).append(d)

            for hf in hojas_fit:
                hoja       = hf["hoja"]
                agencia    = hf["agencia"]
                loc        = hf["localizador"]
                cab_g56    = hf["cabina_g56"]
                q24_raw    = hf["q24_raw"]
                es_dsu     = hf["es_dsu"]
                es_group   = hf.get("es_group", False)
                estado_destino = "RESERVA" if es_group else "VENDIDA"

                crm_entries = crm_por_loc.get(_normalizar_loc(loc), [])
                crm_cabinas = [e["cabina"] for e in crm_entries]

                # ── Descripción origen ─────────────────────────────────────
                if es_group:
                    preview_parts = hf.get("group_preview", [])
                    desc_cabinas  = ", ".join(preview_parts) if preview_parts else "⚠️ Sin datos en filas 20-22"
                    g56_txt       = f" · G56: {cab_g56}" if cab_g56 else " · G56: —"
                    descripcion_origen  = f"{desc_cabinas}{g56_txt}"
                    tipo_asignacion     = "group"
                    cabinas_solicitadas = hf.get("group_cats", [])

                elif cab_g56:
                    numeros_g56 = re.findall(r'\d+', cab_g56)
                    descripcion_origen  = f"G56: cabina(s) {cab_g56}"
                    cabinas_solicitadas = [{"cat": None, "n_cab": len(numeros_g56),
                                            "n_pax": None, "numeros": numeros_g56}]
                    tipo_asignacion     = "g56"

                else:
                    if not q24_raw:
                        filas_valoracion.append({
                            "hoja": hoja, "agencia": agencia, "loc": loc,
                            "estado_destino": estado_destino,
                            "descripcion_origen": "Sin datos en G56 ni Q24",
                            "cabinas_solicitadas": [],
                            "crm_cabinas": crm_cabinas,
                            "tipo_asignacion": "sin_datos",
                            "alerta": "⚠️ Sin info de cabinas en FIT",
                        })
                        continue
                    cab_por_cat = _cabinas_por_categoria_fit(q24_raw, es_dsu)
                    dsu_txt = " (DSU: 1 cab/pax)" if es_dsu else ""
                    partes  = ", ".join(f"{x['n_cab']} cab × {x['cat']} ({x['n_pax']} pax)" for x in cab_por_cat)
                    descripcion_origen  = f"Q24{dsu_txt}: {partes}"
                    cabinas_solicitadas = cab_por_cat
                    tipo_asignacion     = "q24"

                # ── Estado sync ────────────────────────────────────────────
                if crm_cabinas and cab_g56 and any(c in crm_cabinas for c in re.findall(r'\d+', cab_g56)):
                    sync_status = "sincronizado"
                elif crm_cabinas:
                    sync_status = "parcial"
                else:
                    sync_status = "pendiente"

                filas_valoracion.append({
                    "hoja": hoja, "agencia": agencia, "loc": loc,
                    "estado_destino": estado_destino,
                    "descripcion_origen": descripcion_origen,
                    "cabinas_solicitadas": cabinas_solicitadas,
                    "crm_cabinas": crm_cabinas,
                    "tipo_asignacion": tipo_asignacion,
                    "cab_g56": cab_g56,
                    "q24_raw": q24_raw,
                    "es_dsu": es_dsu,
                    "es_group": es_group,
                    "group_cats": hf.get("group_cats", []),
                    "sync_status": sync_status,
                    "alerta": "",
                })

            # Render tabla valoración
            t = '<table class="informe-tabla"><thead><tr>'
            t += th("Hoja / Localizador", "Sheet / Ref")
            t += th("Agencia", "Agency")
            t += th("Tipo", "Type")
            t += th("Cabinas solicitadas (FIT)", "Requested cabins (FIT)")
            t += th("CRM actual", "Current CRM")
            t += th("Estado destino", "Target status")
            t += th("Acción", "Action")
            t += '</tr></thead><tbody>'

            for fv in filas_valoracion:
                ss     = fv.get("sync_status", "error")
                alerta = fv.get("alerta", "")

                if alerta:
                    badge   = f'<span style="background:#FEF3C7;color:#92400E;padding:2px 8px;border-radius:5px;font-size:0.75rem;font-weight:700;">{alerta}</span>'
                    row_bg  = ' style="background:#FFFBEB;"'
                elif ss == "sincronizado":
                    badge   = '<span style="background:#D1FAE5;color:#065F46;padding:2px 8px;border-radius:5px;font-size:0.75rem;font-weight:700;">✅ Sincronizado</span>'
                    row_bg  = ' style="background:#F0FDF4;"'
                elif ss == "parcial":
                    badge   = '<span style="background:#FEF3C7;color:#92400E;padding:2px 8px;border-radius:5px;font-size:0.75rem;font-weight:700;">⚠️ Parcial / revisión</span>'
                    row_bg  = ' style="background:#FFFBEB;"'
                else:
                    badge   = '<span style="background:#DBEAFE;color:#1E3A8A;padding:2px 8px;border-radius:5px;font-size:0.75rem;font-weight:700;">🔵 Listo para asignar</span>'
                    row_bg  = ""

                tipo_txt = "GROUP 🟡" if fv.get("estado_destino") == "RESERVA" else "FIT 🔴"
                crm_txt  = ", ".join(fv.get("crm_cabinas", [])) or "—"
                estado_dst_html = (
                    '<span style="color:#92400E;font-weight:700;">🟡 RESERVA</span>'
                    if fv.get("estado_destino") == "RESERVA"
                    else '<span style="color:#991B1B;font-weight:700;">🔴 VENDIDA</span>'
                )

                t += f'<tr{row_bg}>'
                t += (f'<td style="font-family:monospace;font-size:0.78rem;text-align:left;">'
                      f'{fv["hoja"]}<br>'
                      f'<span style="color:#6B7280;font-size:0.72rem;">{fv["loc"]}</span>'
                      f'</td>')
                t += f'<td style="font-weight:700;text-align:left;">{fv["agencia"]}</td>'
                t += f'<td style="font-size:0.78rem;">{tipo_txt}</td>'
                t += f'<td style="text-align:left;font-size:0.78rem;">{fv["descripcion_origen"]}</td>'
                t += f'<td style="font-weight:700;color:#1E3A8A;">{crm_txt}</td>'
                t += f'<td>{estado_dst_html}</td>'
                t += f'<td>{badge}</td>'
                t += '</tr>'

            t += '</tbody></table>'
            st.markdown(t, unsafe_allow_html=True)

            # ── 4. Botones de ejecución ───────────────────────────────────────
            st.markdown("---")
            st.markdown(
                "#### ⚡ Ejecutar sincronización "
                "<span class='section-en'>Run synchronisation</span>",
                unsafe_allow_html=True
            )

            pendientes = [fv for fv in filas_valoracion
                          if fv.get("sync_status") == "pendiente" and not fv.get("alerta")]
            n_pendientes = len(pendientes)
            n_total      = len(filas_valoracion)

            col_info, col_btn = st.columns([3, 1])
            with col_info:
                st.markdown(
                    f"**{n_pendientes}** de **{n_total}** confirmaciones listas para asignar. "
                    f"<span class='en-inline'>/ {n_pendientes} of {n_total} confirmations ready to assign.</span>",
                    unsafe_allow_html=True
                )
            with col_btn:
                ejecutar_todo = st.button(
                    f"🚀 Asignar todas ({n_pendientes}) / *Assign all*",
                    disabled=(n_pendientes == 0),
                    key="btn_sync_all"
                )

            st.markdown(
                "O procesa una a una: "
                "<span class='en-inline'>/ Or process one by one:</span>",
                unsafe_allow_html=True
            )

            ejecutar_individual = {}
            for fv in filas_valoracion:
                if fv.get("sync_status") == "pendiente" and not fv.get("alerta"):
                    col_label, col_boton = st.columns([4, 1])
                    with col_label:
                        st.markdown(
                            f"📄 **{fv['hoja']}** — {fv['agencia']} — `{fv['loc']}` — {fv['descripcion_origen']}"
                        )
                    with col_boton:
                        ejecutar_individual[fv["hoja"]] = st.button(
                            "▶ Asignar",
                            key=f"btn_sync_{fv['hoja']}"
                        )

            # ── 5. Lógica de ejecución ────────────────────────────────────────

            def _asignar_confirmacion(fv: dict, datos_crm: list) -> dict:
                svc_sheets = getsheetsservice()
                agencia    = fv["agencia"]
                loc        = fv["loc"]
                estado_dst = fv["estado_destino"]
                tipo       = fv["tipo_asignacion"]
                cab_g56    = fv.get("cab_g56", "")
                q24_raw    = fv.get("q24_raw", "")
                es_dsu     = fv.get("es_dsu", False)
                es_group   = fv.get("es_group", False)

                cabinas_asignadas = []
                errores   = []
                warnings  = []

                # ── CASO GROUP ────────────────────────────────────────────────
                if es_group:
                    cab_por_cat = fv.get("group_cats", [])
                    if not cab_por_cat:
                        errores.append("No se encontraron datos de cabinas en filas 20-22.")
                        return {"ok": False, "cabinas_asignadas": [], "errores": errores, "warnings": warnings}

                    todas_asignadas_en_vuelta = []
                    for item in cab_por_cat:
                        cat        = item["cat"]
                        n_cab      = item["n_cab"]
                        n_pax_item = item["n_pax"]
                        libres = _obtener_cabinas_disponibles_con_prioridad(
                            cat, n_cab, datos_crm, estado_dst, todas_asignadas_en_vuelta, warnings
                        )
                        libres     = [c for c in libres if c not in todas_asignadas_en_vuelta]
                        if len(libres) < n_cab:
                            errores.append(
                                f"Categoría {cat}: se necesitan {n_cab} cabinas libres, "
                                f"solo hay {len(libres)}."
                            )
                            continue
                        asignadas_cat = libres[:n_cab]
                        pax_por_cab   = max(1, round(n_pax_item / n_cab)) if n_pax_item else ""
                        for cab_num in asignadas_cat:
                            rowindex = next((i for i, d in enumerate(datos_crm) if d.get("cabina") == cab_num), None)
                            if rowindex is None:
                                errores.append(f"No se encontró fila CRM para cabina {cab_num}.")
                                continue
                            d_crm = datos_crm[rowindex]
                            estado_f, ag_f, pax_f, loc_f, nt_f = agregar_agencia_a_cabina(
                                d_crm, agencia, pax_por_cab, loc, "", estado_dst
                            )
                            guardarcabina(ddmm_sel, rowindex, ag_f, pax_f, loc_f, nt_f, estado_f)
                            cabinas_asignadas.append(cab_num)
                            todas_asignadas_en_vuelta.append(cab_num)
                            datos_crm[rowindex].update({"agencia": ag_f, "estado": estado_f, "localizador": loc_f})

                    return {
                        "ok": len(cabinas_asignadas) > 0 and not errores,
                        "cabinas_asignadas": cabinas_asignadas,
                        "errores": errores,
                        "warnings": warnings,
                    }

                # ── CASO FIT G56 ──────────────────────────────────────────────
                if tipo == "g56":
                    numeros_g56 = re.findall(r'\d+', cab_g56)
                    if len(numeros_g56) > 1:
                        warnings.append(
                            f"G56 contiene {len(numeros_g56)} cabinas ({cab_g56}). "
                            f"Solo se asignará la primera; el resto deben hacerse manualmente."
                        )
                    num_cab = numeros_g56[0] if numeros_g56 else None
                    if not num_cab:
                        errores.append("No se pudo extraer número de cabina de G56.")
                        return {"ok": False, "cabinas_asignadas": [], "errores": errores, "warnings": warnings}

                    rowindex = next((i for i, d in enumerate(datos_crm) if d.get("cabina") == num_cab), None)
                    if rowindex is None:
                        errores.append(f"Cabina {num_cab} de G56 no existe en CRM.")
                        return {"ok": False, "cabinas_asignadas": [], "errores": errores, "warnings": warnings}

                    d_crm   = datos_crm[rowindex]
                    ags_act = [a for a in split_pipe(d_crm.get("agencia", "")) if a]
                    if len(ags_act) >= 4 and agencia not in ags_act:
                        warnings.append(f"Cabina {num_cab} ya tiene 4 agencias — no se añade más.")
                    else:
                        estado_f, ag_f, pax_f, loc_f, nt_f = agregar_agencia_a_cabina(
                            d_crm, agencia, "", loc, "", estado_dst
                        )
                        guardarcabina(ddmm_sel, rowindex, ag_f, pax_f, loc_f, nt_f, estado_f)
                        cabinas_asignadas.append(num_cab)
                        datos_crm[rowindex].update({"agencia": ag_f, "estado": estado_f, "localizador": loc_f})

                    for extra in numeros_g56[1:]:
                        warnings.append(f"⚠️ Cabina adicional en G56: {extra} — asignación manual necesaria.")

                # ── CASO FIT Q24 ──────────────────────────────────────────────
                elif tipo == "q24":
                    cab_por_cat = _cabinas_por_categoria_fit(q24_raw, es_dsu)
                    todas_asignadas_en_vuelta = []
                    for item in cab_por_cat:
                        cat        = item["cat"]
                        n_cab      = item["n_cab"]
                        n_pax_item = item["n_pax"]
                        libres = _obtener_cabinas_disponibles_con_prioridad(
                            cat, n_cab, datos_crm, estado_dst, todas_asignadas_en_vuelta, warnings
                        )
                        libres     = [c for c in libres if c not in todas_asignadas_en_vuelta]
                        if len(libres) < n_cab:
                            errores.append(
                                f"Categoría {cat}: se necesitan {n_cab} cabinas libres, "
                                f"solo hay {len(libres)}."
                            )
                            continue
                        asignadas_cat = libres[:n_cab]
                        pax_por_cab   = max(1, round(n_pax_item / n_cab)) if n_pax_item else ""
                        for cab_num in asignadas_cat:
                            rowindex = next((i for i, d in enumerate(datos_crm) if d.get("cabina") == cab_num), None)
                            if rowindex is None:
                                errores.append(f"No se encontró fila CRM para cabina {cab_num}.")
                                continue
                            d_crm = datos_crm[rowindex]
                            estado_f, ag_f, pax_f, loc_f, nt_f = agregar_agencia_a_cabina(
                                d_crm, agencia, pax_por_cab, loc, "", estado_dst
                            )
                            guardarcabina(ddmm_sel, rowindex, ag_f, pax_f, loc_f, nt_f, estado_f)
                            cabinas_asignadas.append(cab_num)
                            todas_asignadas_en_vuelta.append(cab_num)
                            datos_crm[rowindex].update({"agencia": ag_f, "estado": estado_f, "localizador": loc_f})

                    if cabinas_asignadas:
                        cabinas_str = " / ".join(cabinas_asignadas)
                        try:
                            svc_sheets.spreadsheets().values().update(
                                spreadsheetId=archivo_conf_id,
                                range=f"'{fv['hoja']}'!G56",
                                valueInputOption="USER_ENTERED",
                                body={"values": [[cabinas_str]]}
                            ).execute()
                        except Exception as e_write:
                            warnings.append(f"No se pudo escribir G56 en FIT: {str(e_write)}")

                else:
                    errores.append("Sin datos de cabinas (G56 vacío y Q24 vacío).")

                ok = len(cabinas_asignadas) > 0 and not errores
                return {"ok": ok, "cabinas_asignadas": cabinas_asignadas,
                        "errores": errores, "warnings": warnings}

            # ── Determinar qué ejecutar ───────────────────────────────────────
            hojas_a_ejecutar = []
            if ejecutar_todo:
                hojas_a_ejecutar = [fv["hoja"] for fv in filas_valoracion
                                    if fv.get("sync_status") == "pendiente" and not fv.get("alerta")]
            else:
                for hoja_key, clicked in ejecutar_individual.items():
                    if clicked:
                        hojas_a_ejecutar.append(hoja_key)

            if hojas_a_ejecutar:
                st.markdown("---")
                st.markdown(
                    "#### 📋 Informe de ejecución "
                    "<span class='section-en'>Execution report</span>",
                    unsafe_allow_html=True
                )

                st.cache_data.clear()
                datos_crm_exec = getdatossalida(ddmm_sel)
                resultados_ejecucion = []

                for hoja_exec in hojas_a_ejecutar:
                    fv_exec = next((fv for fv in filas_valoracion if fv["hoja"] == hoja_exec), None)
                    if not fv_exec:
                        continue
                    with st.spinner(f"Procesando {hoja_exec}… / *Processing {hoja_exec}…*"):
                        res = _asignar_confirmacion(fv_exec, datos_crm_exec)
                    resultados_ejecucion.append({**fv_exec, **res})

                t2 = '<table class="informe-tabla"><thead><tr>'
                t2 += th("Hoja / Localizador", "Sheet / Ref")
                t2 += th("Agencia", "Agency")
                t2 += th("Cabinas asignadas", "Assigned cabins")
                t2 += th("Estado", "Status")
                t2 += th("Avisos / Errores", "Warnings / Errors")
                t2 += '</tr></thead><tbody>'

                for r in resultados_ejecucion:
                    cab_txt   = ", ".join(r.get("cabinas_asignadas", [])) or "—"
                    errores_r = r.get("errores", [])
                    warnings_r = r.get("warnings", [])
                    if r.get("ok"):
                        badge2  = '<span style="background:#D1FAE5;color:#065F46;padding:2px 8px;border-radius:5px;font-size:0.75rem;font-weight:700;">✅ Asignado</span>'
                        row_bg2 = ' style="background:#F0FDF4;"'
                    elif errores_r:
                        badge2  = '<span style="background:#FEE2E2;color:#991B1B;padding:2px 8px;border-radius:5px;font-size:0.75rem;font-weight:700;">❌ Error</span>'
                        row_bg2 = ' style="background:#FEF2F2;"'
                    else:
                        badge2  = '<span style="background:#FEF3C7;color:#92400E;padding:2px 8px;border-radius:5px;font-size:0.75rem;font-weight:700;">⚠️ Parcial</span>'
                        row_bg2 = ' style="background:#FFFBEB;"'

                    msgs = []
                    for e in errores_r:
                        msgs.append(f'<span style="color:#991B1B;">❌ {e}</span>')
                    for w in warnings_r:
                        msgs.append(f'<span style="color:#92400E;">⚠️ {w}</span>')
                    msgs_html = "<br>".join(msgs) if msgs else "—"

                    t2 += f'<tr{row_bg2}>'
                    t2 += (f'<td style="font-family:monospace;font-size:0.78rem;text-align:left;">'
                           f'{r["hoja"]}<br>'
                           f'<span style="color:#6B7280;font-size:0.72rem;">{r["loc"]}</span>'
                           f'</td>')
                    t2 += f'<td style="font-weight:700;text-align:left;">{r["agencia"]}</td>'
                    t2 += f'<td style="font-weight:700;color:#1E3A8A;">{cab_txt}</td>'
                    t2 += f'<td>{badge2}</td>'
                    t2 += f'<td style="text-align:left;font-size:0.78rem;">{msgs_html}</td>'
                    t2 += '</tr>'

                t2 += '</tbody></table>'
                st.markdown(t2, unsafe_allow_html=True)

                st.cache_data.clear()
                st.success(
                    "✅ Sincronización completada. / *Synchronisation complete.* "
                    "Recarga la página para ver el CRM actualizado."
                )

#### BLOQUE 23: PIE DE PÁGINA
st.markdown("---")
st.page_link("app.py", label="🏠 Volver al Menú Principal / Back to Main Menu", icon="🏠")
