# ============================================================
# BLOQUE 1: CONFIG — Constantes, mapeos, estado por defecto
# ============================================================

import streamlit as st

# ── IDs de Google Drive / Sheets ──────────────────────────
FOLDERSESIONESID     = "1MxMdeBlUG6v5n2upobsjNbQNQ8F_C_sO"
FOLDERID             = "1MxMdeBlUG6v5n2upobsjNbQNQ8F_C_sO"
LOGOID               = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGOURL              = f"https://lh3.googleusercontent.com/d/{LOGOID}"
TEMPLATEIDES         = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
TEMPLATEIDGRUPOS     = "1Z7ktX3PhVkMibWpzdrDDqAT4aPsmjzSJPf1SgZcL5-w"
TEMPLATEIDCRUCERO    = "1zSJPi6St_Z5Jw1c6eieVnKI4NyEdP7E9n3WTZ9yy3C0"
EXCURSIONESSHEETID   = "1ojMHeoosUyel8BA2XTmDsmyDJf_vvJrrJNOyxn2u1jg"
AGENCYSHEETID        = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
AGENCYSHEETNAME      = "Datos"
DRIVEROOTID          = "11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm"
GROUPSROOTID         = "1MMNH3y1E3jJIp6uUnxbwV0toAtdr2F2M"
BOATREGISTRYSHEETID  = "1pvDAEPGkb1DmvbauY-eKk3ymljDvEBvDivijVDUHmGA"
BOATREGISTRYSHEETNAME = "TICKETS, RESULTADO, ENVIADO TICKET"

# ── Usuarios válidos ──────────────────────────────────────
VALIDUSERS = {
    "support@crucemundo.com":      "Albina",
    "sales@crucemundo.com":        "Kristina",
    "cruise@crucemundo.com":       "Malvina",
    "tania@crucemundo.com":        "Tania Bondar",
    "incoming@crucemundo.com":     "Tatiana",
    "operations@crucemundo.com":   "Anton",
    "reservations@crucemundo.com": "Serge",
    "marketing@crucemundo.com":    "Asel",
    "alexei@crucemundo.com":       "Alexei",
    "anton@crucemundo.com":        "Anton",
    "finance@crucemundo.com":      "Aleksandr",
    "edarmm@gmail.com":            "Esteban",
}
VALIDPASSWORD = st.secrets.get("apppassword", "")

# ── Campos de agencia ─────────────────────────────────────
AGENCYFIELDS = [
    "Nombre",
    "CODIGO",
    "Grupo Gest",
    "Telefono",
    "Email",
    "Direccion",
    "COMISION AGENCIA",
    "COMISION AGENCIA CON OFERTA ",
    "COMISION AGENCIA OFERTA 2X1 ",
    "IVA",
    "IVA SERVICIO OPCIONAL",
]

# ── Mapeo código barco ↔ nombre ───────────────────────────
SHIPCODEMAP = {
    "MS_ALBERTINA":     "ALB",
    "MS_ARENA":         "ARN",
    "MS_CRUCEVITA":     "CV",
    "MS_DOURO_CRUISER": "DC",
    "MS_FIDELIO":       "FID",
    "MS_LEONORA":       "LEO",
    "MS_RIVER_DIAMOND": "RDA",
    "MS_RIVER_SAPPHIRE":"RSA",
    "MS_SWISS_SPLENDOR":"SPL",
    "MS_VISTA_GRACIA":  "VGR",
    "MS_VISTAMILLA":    "VMI",
    "MS_VISTA_RIO":     "VRI",
}
SHIPCODETONAME = {v: k for k, v in SHIPCODEMAP.items()}

# ── Estado por defecto de la sesión ──────────────────────
STATEDEFAULTS = {
    "authenticated":              False,
    "useremail":                  "",
    "displayname":                "",
    "confirmstate":               "idle",
    "historial":                  "",
    "sessiontype":                "",
    "activepanel":                None,
    "sessionid":                  "",
    "sessionstart":               None,

    "opensalidaform":             False,
    "opencruceroform":            False,
    "opennuevaagenciaform":       False,
    "openbuscaragenciaform":      False,
    "opencvcfitform":             False,
    "opencvcagenciasform":        False,
    "openirconfirmacionform":     False,
    "openinformebarcoform":       False,
    "opennuevobarcoform":         False,

    "salidayear":                 None,
    "salidaboat":                 None,
    "salidaname":                 None,

    "cruceroyear":                None,
    "cruceroboat":                None,

    "agencymatches":              [],
    "agencyselectedidx":          None,

    "cvcfitlocator":              "",
    "cvcfitresult":               None,
    "cvcfitlog":                  [],

    "cvcagenciaslocator":         "",
    "cvcagenciasresult":          None,
    "cvcagenciaslog":             [],

    "irconfirmacionlocator":      "",
    "irconfirmacionresult":       None,
    "irconfirmacionlog":          [],

    "informetype":                None,
    "informeyear":                None,
    "informeboat":                None,
    "informesalida":              None,
    "informeresult":              None,

    "nombrecopia":                "",
    "copyurl":                    "",
    "processtitle":               "",
    "processresult":              None,

    "nuevobarconombre":           "",
    "nuevobarcolocalizador":      "",
    "nuevobarcocabina1":          "",
    "nuevobarcocategoria1":       "",
    "nuevobarcocabina2":          "",
    "nuevobarcocategoria2":       "",
    "nuevobarcocabina3":          "",
    "nuevobarcocategoria3":       "",
    "nuevobarcocabina4":          "",
    "nuevobarcocategoria4":       "",
    "nuevobarcocabina5":          "",
    "nuevobarcocategoria5":       "",
}

# ── Grupos de estado por panel ────────────────────────────
STATEGROUPS = {
    "salida": [
        "salidayear", "salidaboat", "salidaname",
        "salidayearwidget", "salidaboatwidget", "salidanamewidget",
    ],
    "crucero": [
        "cruceroyear", "cruceroboat",
        "cruceroyearwidget", "cruceroboatwidget",
    ],
    "agencia": [
        "agencymatches", "agencyselectedidx", "agencysearchquery",
        "agnombre", "agcodigo", "aggrupogest", "agtelefono", "agemail", "agdireccion",
        "agcomision", "agcomisionoferta", "agcomision2x1", "agiva", "agivaservicioopcional",
    ],
    "cvcfit": [
        "cvcfitlocator", "cvcfitresult", "cvcfitlocatorwidget", "cvcfitlog",
    ],
    "cvcagencias": [
        "cvcagenciaslocator", "cvcagenciasresult", "cvcagenciaslocatorwidget", "cvcagenciaslog",
    ],
    "irconfirmacion": [
        "irconfirmacionlocator", "irconfirmacionresult", "irconfirmacionlocatorwidget", "irconfirmacionlog",
    ],
    "informebarco": [
        "informetype", "informeyear", "informeboat", "informesalida", "informeresult",
        "informetypewidget", "informeyearwidget", "informeboatwidget", "informesalidawidget",
    ],
    "nuevobarco": [
        "nuevobarconombre", "nuevobarcolocalizador",
        "nuevobarcocabina1", "nuevobarcocategoria1",
        "nuevobarcocabina2", "nuevobarcocategoria2",
        "nuevobarcocabina3", "nuevobarcocategoria3",
        "nuevobarcocabina4", "nuevobarcocategoria4",
        "nuevobarcocabina5", "nuevobarcocategoria5",
    ],
    "process": [
        "nombrecopia", "copyurl", "processtitle", "confirmstate", "sessiontype", "processresult",
    ],
}

# ── Flags de apertura por panel ───────────────────────────
PANELFLAGS = {
    "salida":          "opensalidaform",
    "crucero":         "opencruceroform",
    "nuevaagencia":    "opennuevaagenciaform",
    "buscaragencia":   "openbuscaragenciaform",
    "cvcfit":          "opencvcfitform",
    "cvcagencias":     "opencvcagenciasform",
    "irconfirmacion":  "openirconfirmacionform",
    "informebarco":    "openinformebarcoform",
    "nuevobarco":      "opennuevobarcoform",
}



# ============================================================
# BLOQUE 2: UTILS — Funciones auxiliares puras
#   (sin Google API, sin widgets de Streamlit)
# ============================================================

import re
from datetime import datetime


def getsaludo(lang="es"):
    hour = datetime.now().hour
    if lang == "en":
        if 6 <= hour < 14:
            return "Good morning"
        if 14 <= hour < 21:
            return "Good afternoon"
        return "Good evening"
    if 6 <= hour < 14:
        return "Buenos días"
    if 14 <= hour < 21:
        return "Buenas tardes"
    return "Buenas noches"


def normalizetext(value):
    return "" if value is None else str(value).strip().lower()


def normalizephone(value):
    return "" if value is None else re.sub(r"\D", "", str(value))


def percenttosheetdecimal(value):
    return "" if value is None else round(float(value) / 100, 4)


def safefilename(text):
    text = re.sub(r'[\\/:*?"<>|]+', "", str(text))
    return re.sub(r"\s+", " ", text).strip()


def firstline(value):
    return "" if value is None else str(value).splitlines()[0].strip()


def parsenumericvalue(value):
    text = str(value or "").strip()
    if not text:
        return 0.0
    text = text.replace("€", "").replace("EUR", "").replace("PAX", "").strip()
    text = text.replace(".", "").replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return 0.0
    try:
        return float(m.group(0))
    except Exception:
        return 0.0


def parseintfromtext(value):
    text = str(value or "").strip().upper().replace("PAX", "").strip()
    m = re.search(r"\d+", text)
    return int(m.group(0)) if m else 0


def formatestadobadge(value):
    v = str(value or "").strip().upper()
    if v == "CONFIRMADO":
        return '<span class="status-pill status-confirmado">CONFIRMADO</span>'
    if v == "NO CONFIRMADO":
        return '<span class="status-pill status-no-confirmado">NO CONFIRMADO</span>'
    if v == "CANCELADO":
        return '<span class="status-pill status-cancelado">CANCELADO</span>'
    return f'<span class="status-pill">{value or ""}</span>'


def formatestadopagobadge(value):
    v = str(value or "").strip().upper()
    if v == "PTE PAGO":
        return '<span class="status-pill status-pte-pago">PTE PAGO</span>'
    if v == "DEPOSITO":
        return '<span class="status-pill status-deposito">DEPOSITO</span>'
    if v == "CREDITO":
        return '<span class="status-pill status-credito">CREDITO</span>'
    if v == "PAGADO":
        return '<span class="status-pill status-pagado">PAGADO</span>'
    return f'<span class="status-pill">{value or ""}</span>'








# ============================================================
# BLOQUE 3: STATE — Gestión del estado de sesión y navegación
# ============================================================

import streamlit as st
from datetime import datetime

from config import STATEDEFAULTS, STATEGROUPS, PANELFLAGS


# ── Inicialización ────────────────────────────────────────
def init_state():
    for key, value in STATEDEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ── Helpers de duración ───────────────────────────────────
def getsessiondurationseconds():
    started = st.session_state.get("sessionstart")
    if not started:
        return 0
    try:
        return int((datetime.now() - started).total_seconds())
    except Exception:
        return 0


# ── Limpieza de grupos de estado ─────────────────────────
def clearstategroup(groupname):
    for key in STATEGROUPS.get(groupname, []):
        st.session_state.pop(key, None)


def closeallpanels():
    for flag in PANELFLAGS.values():
        st.session_state[flag] = False


def cleartransientui():
    for groupname in STATEGROUPS.keys():
        clearstategroup(groupname)
    closeallpanels()
    st.session_state.activepanel  = None
    st.session_state.confirmstate = "idle"
    st.session_state.sessiontype  = ""
    st.session_state.processresult = None


# ── Apertura / cierre de paneles ─────────────────────────
def openpanel(panelname):
    from audit import safeaudit   # import local para evitar circular
    cleartransientui()
    flag = PANELFLAGS.get(panelname)
    if flag:
        st.session_state[flag]    = True
        st.session_state.activepanel = panelname
        safeaudit("open_panel", f"Apertura de panel {panelname}",
                  panel=panelname, extra={"request_type": "open_panel"})


def closecurrentpanel():
    cleartransientui()
    st.rerun()


# ── Resets en cascada ────────────────────────────────────
def resetsalidadownstream(level):
    if level == "year":
        st.session_state.salidaboat = None
        st.session_state.salidaname = None
        st.session_state.pop("salidaboatwidget", None)
        st.session_state.pop("salidanamewidget", None)
    elif level == "boat":
        st.session_state.salidaname = None
        st.session_state.pop("salidanamewidget", None)


def resetcrucerodownstream(level):
    if level == "year":
        st.session_state.cruceroboat = None
        st.session_state.pop("cruceroboatwidget", None)


def resetinformedownstream(level):
    if level == "type":
        st.session_state.informeyear   = None
        st.session_state.informeboat   = None
        st.session_state.informesalida = None
        st.session_state.informeresult = None
        st.session_state.pop("informeyearwidget",  None)
        st.session_state.pop("informeboatwidget",  None)
        st.session_state.pop("informesalidawidget", None)
    elif level == "year":
        st.session_state.informeboat   = None
        st.session_state.informesalida = None
        st.session_state.informeresult = None
        st.session_state.pop("informeboatwidget",  None)
        st.session_state.pop("informesalidawidget", None)
    elif level == "boat":
        st.session_state.informesalida = None
        st.session_state.informeresult = None
        st.session_state.pop("informesalidawidget", None)


# ── Callbacks de widgets (on_change) ─────────────────────
def onyearchange():
    st.session_state.salidayear = st.session_state.get("salidayearwidget")
    resetsalidadownstream("year")


def onboatchange():
    st.session_state.salidaboat = st.session_state.get("salidaboatwidget")
    resetsalidadownstream("boat")


def onsalidachange():
    st.session_state.salidaname = st.session_state.get("salidanamewidget")


def oncruceroyearchange():
    st.session_state.cruceroyear = st.session_state.get("cruceroyearwidget")
    resetcrucerodownstream("year")


def oncruceroboatchange():
    st.session_state.cruceroboat = st.session_state.get("cruceroboatwidget")


def oninformetypechange():
    st.session_state.informetype = st.session_state.get("informetypewidget")
    resetinformedownstream("type")


def oninformeyearchange():
    st.session_state.informeyear = st.session_state.get("informeyearwidget")
    resetinformedownstream("year")


def oninformeboatchange():
    st.session_state.informeboat = st.session_state.get("informeboatwidget")
    resetinformedownstream("boat")


def oninformesalidachange():
    st.session_state.informesalida = st.session_state.get("informesalidawidget")



# ============================================================
# BLOQUE 4: GOOGLE_API — Llamadas a Google Drive y Sheets
# ============================================================

import re
import urllib.parse
from datetime import datetime

import requests
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import (
    DRIVEROOTID, GROUPSROOTID, FOLDERSESIONESID,
    FOLDERID, TEMPLATEIDCRUCERO,
    AGENCYSHEETID, AGENCYSHEETNAME, AGENCYFIELDS,
    BOATREGISTRYSHEETID, SHIPCODEMAP, SHIPCODETONAME,
)
from utils import (
    safefilename, firstline, normalizetext, normalizephone,
    parsenumericvalue, parseintfromtext,
)


# ── Credenciales y servicios (cacheados) ──────────────────
@st.cache_resource
def getgooglecreds():
    if "gcpserviceaccount" not in st.secrets:
        raise Exception("Falta gcpserviceaccount en secrets.")
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcpserviceaccount"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )


@st.cache_resource
def getdriveservice():
    return build("drive", "v3", credentials=getgooglecreds())


@st.cache_resource
def getsheetsservice():
    return build("sheets", "v4", credentials=getgooglecreds())


# ── Drive: listado y búsqueda de archivos ─────────────────
def listfolderitems(parentid, foldersonly=False):
    service = getdriveservice()
    query = f"'{parentid}' in parents and trashed=false"
    if foldersonly:
        query += " and mimeType='application/vnd.google-apps.folder'"
    results, pagetoken = [], None
    while True:
        response = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, webViewLink, description, createdTime, modifiedTime)",
            supportsAllDrives=True, includeItemsFromAllDrives=True,
            corpora="allDrives", pageToken=pagetoken, pageSize=1000,
            orderBy="modifiedTime desc",
        ).execute()
        results.extend(response.get("files", []))
        pagetoken = response.get("nextPageToken")
        if not pagetoken:
            break
    return results


def listspreadsheetsinfolderrecentfirst(folderid):
    service = getdriveservice()
    query = (
        f"'{folderid}' in parents and trashed=false "
        f"and mimeType='application/vnd.google-apps.spreadsheet'"
    )
    results, pagetoken = [], None
    while True:
        response = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, webViewLink, createdTime, modifiedTime)",
            supportsAllDrives=True, includeItemsFromAllDrives=True,
            corpora="allDrives", pageToken=pagetoken, pageSize=1000,
            orderBy="modifiedTime desc",
        ).execute()
        results.extend(response.get("files", []))
        pagetoken = response.get("nextPageToken")
        if not pagetoken:
            break
    return results


def findchildfolder(parentid, foldername):
    for item in listfolderitems(parentid, foldersonly=True):
        if item["name"].strip() == foldername.strip():
            return item
    return None


def createfolder(parentid, foldername):
    service = getdriveservice()
    body = {
        "name": foldername,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parentid],
    }
    return service.files().create(body=body, fields="id, name", supportsAllDrives=True).execute()


def getorcreatefolder(parentid, foldername):
    return findchildfolder(parentid, foldername) or createfolder(parentid, foldername)


def findfilebyname(parentid, filename):
    for item in listfolderitems(parentid, foldersonly=False):
        if item["name"].strip() == filename.strip():
            return item
    return None


def copyfiletofolder(fileid, newname, parent, description=None):
    service = getdriveservice()
    body = {"name": newname, "parents": [parent]}
    if description:
        body["description"] = description
    return service.files().copy(
        fileId=fileid, body=body,
        fields="id, name, webViewLink", supportsAllDrives=True,
    ).execute()


# ── Drive: años, barcos, salidas (cacheados) ──────────────
@st.cache_data(ttl=300)
def getyears():
    folders = listfolderitems(DRIVEROOTID, foldersonly=True)
    years = [f["name"].strip() for f in folders if re.fullmatch(r"\d{4}", f["name"].strip())]
    return sorted(years, reverse=True)


@st.cache_data(ttl=300)
def getyearfolderid(yearname):
    folder = findchildfolder(DRIVEROOTID, yearname)
    return folder["id"] if folder else None


@st.cache_data(ttl=300)
def getboats(yearname):
    yearfolderid = getyearfolderid(yearname)
    if not yearfolderid:
        return []
    folders = listfolderitems(yearfolderid, foldersonly=True)
    return sorted(f["name"].strip() for f in folders if f["name"].strip())


@st.cache_data(ttl=300)
def getdepartures(yearname, boatname):
    yearfolderid = getyearfolderid(yearname)
    if not yearfolderid:
        return []
    boatfolder = findchildfolder(yearfolderid, boatname)
    if not boatfolder:
        return []
    files = listfolderitems(boatfolder["id"], foldersonly=False)
    pattern = re.compile(rf"^{re.escape(boatname)}_?\d{{6}}")
    departures = []
    for file in files:
        name = file["name"].strip()
        if pattern.match(name):
            departures.append({
                "nombre": name,
                "id": file["id"],
                "url": file.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{file['id']}/edit",
            })
    departures.sort(key=lambda x: x["nombre"])
    return departures


def getyearsbyroot(rootid):
    folders = listfolderitems(rootid, foldersonly=True)
    if rootid == DRIVEROOTID:
        years = [f["name"].strip() for f in folders if re.fullmatch(r"\d{4}", f["name"].strip())]
    else:
        years = [f["name"].strip() for f in folders if re.fullmatch(r"\d{4}_GROUP", f["name"].strip())]
    return sorted(years, reverse=True)


def getyearfolderidbyroot(rootid, yearname):
    folder = findchildfolder(rootid, yearname)
    return folder["id"] if folder else None


def getboatsbyroot(rootid, yearname):
    yearfolderid = getyearfolderidbyroot(rootid, yearname)
    if not yearfolderid:
        return []
    folders = listfolderitems(yearfolderid, foldersonly=True)
    return sorted(f["name"].strip() for f in folders if f["name"].strip())


@st.cache_data(ttl=300)
def getdeparturesbyroot(rootid, yearname, boatname):
    yearfolderid = getyearfolderidbyroot(rootid, yearname)
    if not yearfolderid:
        return []
    boatfolder = findchildfolder(yearfolderid, boatname)
    if not boatfolder:
        return []
    files = listfolderitems(boatfolder["id"], foldersonly=False)
    if rootid == DRIVEROOTID:
        pattern = re.compile(rf"^{re.escape(boatname)}_\d{{6}}$")
    else:
        pattern = re.compile(rf"^{re.escape(boatname)}_\d{{6}}_GROUP$")
    departures = []
    for file in files:
        name = file["name"].strip()
        if pattern.match(name):
            departures.append({
                "nombre": name,
                "id": file["id"],
                "url": file.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{file['id']}/edit",
            })
    departures.sort(key=lambda x: x["nombre"])
    return departures


# ── Sheets: lectura ───────────────────────────────────────
def getsheettitleswithids(spreadsheetid):
    sheetsservice = getsheetsservice()
    spreadsheet = sheetsservice.spreadsheets().get(spreadsheetId=spreadsheetid).execute()
    return [
        {"title": s.get("properties", {}).get("title", ""), "sheetId": s.get("properties", {}).get("sheetId")}
        for s in spreadsheet.get("sheets", [])
    ]


def getsinglecell(spreadsheetid, sheettitle, a1):
    sheetsservice = getsheetsservice()
    values = sheetsservice.spreadsheets().values().get(
        spreadsheetId=spreadsheetid,
        range=f"{sheettitle}!{a1}",
        majorDimension="ROWS",
    ).execute().get("values", [])
    return values[0][0] if values and values[0] else ""


def getsheetcellsbatch(spreadsheetid, sheettitle, a1list):
    sheetsservice = getsheetsservice()
    ranges = [f"{sheettitle}!{a1}" for a1 in a1list]
    response = sheetsservice.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheetid, ranges=ranges, majorDimension="ROWS",
    ).execute()
    out = {}
    for a1, vr in zip(a1list, response.get("valueRanges", [])):
        vals = vr.get("values", [])
        out[a1] = vals[0][0] if vals and vals[0] else ""
    return out


def getsheettitleb2(spreadsheetid, sheettitle):
    return getsinglecell(spreadsheetid, sheettitle, "B2")


# ── Sheets: escritura ─────────────────────────────────────
def appendagencyrow(agencydata):
    sheetsservice = getsheetsservice()
    values = [[agencydata.get(field, "") for field in AGENCYFIELDS]]
    sheetsservice.spreadsheets().values().append(
        spreadsheetId=AGENCYSHEETID,
        range=f"{AGENCYSHEETNAME}!A:K",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()


def updatecrucerosheet(spreadsheetid, barco):
    sheetsservice = getsheetsservice()
    spreadsheet = sheetsservice.spreadsheets().get(spreadsheetId=spreadsheetid).execute()
    sheets = spreadsheet.get("sheets", [])
    if not sheets:
        raise Exception("El spreadsheet no contiene hojas.")
    firstsheet    = sheets[0]
    firstsheetid  = firstsheet["properties"]["sheetId"]
    firstsheettitle = firstsheet["properties"]["title"]
    sheetsservice.spreadsheets().values().update(
        spreadsheetId=spreadsheetid,
        range=f"{firstsheettitle}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": [[barco]]},
    ).execute()
    sheetsservice.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheetid,
        body={"requests": [{"updateSheetProperties": {
            "properties": {"sheetId": firstsheetid, "title": barco},
            "fields": "title",
        }}]},
    ).execute()


# ── Sheets: registro de barcos ────────────────────────────
def ensure_sheet_headers():
    sheetsservice = getsheetsservice()
    spreadsheet = sheetsservice.spreadsheets().get(spreadsheetId=BOATREGISTRYSHEETID).execute()
    sheets = spreadsheet.get("sheets", [])
    if len(sheets) < 2:
        raise Exception("El spreadsheet debe tener al menos 2 hojas.")

    log_title    = sheets[0]["properties"]["title"]
    ticket_title = sheets[1]["properties"]["title"]

    audit_headers = [[
        "timestamp", "useremail", "displayname", "sessionid",
        "action", "detail", "panel", "duration_seconds",
        "metadata", "requested_by", "request_date",
    ]]
    ticket_headers = [[
        "timestamp", "useremail", "displayname", "sessionid",
        "barco", "localizador", "linea", "cabina",
        "categoria_normalizada", "requested_by", "request_date",
    ]]

    log_values = sheetsservice.spreadsheets().values().get(
        spreadsheetId=BOATREGISTRYSHEETID, range=f"{log_title}!A1:K1",
    ).execute().get("values", [])
    if not log_values or not any(str(v).strip() for v in log_values[0]):
        sheetsservice.spreadsheets().values().update(
            spreadsheetId=BOATREGISTRYSHEETID, range=f"{log_title}!A1:K1",
            valueInputOption="USER_ENTERED", body={"values": audit_headers},
        ).execute()

    ticket_values = sheetsservice.spreadsheets().values().get(
        spreadsheetId=BOATREGISTRYSHEETID, range=f"{ticket_title}!A1:K1",
    ).execute().get("values", [])
    if not ticket_values or not any(str(v).strip() for v in ticket_values[0]):
        sheetsservice.spreadsheets().values().update(
            spreadsheetId=BOATREGISTRYSHEETID, range=f"{ticket_title}!A1:K1",
            valueInputOption="USER_ENTERED", body={"values": ticket_headers},
        ).execute()


def save_new_boat_registry(barconombre, localizador, cabin_pairs):
    ensure_sheet_headers()
    sheetsservice = getsheetsservice()
    spreadsheet = sheetsservice.spreadsheets().get(spreadsheetId=BOATREGISTRYSHEETID).execute()
    sheets = spreadsheet.get("sheets", [])
    if len(sheets) < 2:
        raise Exception("El spreadsheet debe tener al menos 2 hojas.")
    ticket_title = sheets[1]["properties"]["title"]

    timestamp    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    useremail    = st.session_state.get("useremail", "")
    displayname  = st.session_state.get("displayname", "")
    sessionid    = st.session_state.get("sessionid", "")
    requested_by = displayname.strip() or useremail
    request_date = timestamp

    values = []
    for idx, (cabina, categoria) in enumerate(cabin_pairs, start=1):
        cabina   = str(cabina).strip()
        categoria = str(categoria).strip().upper()
        if not cabina and not categoria:
            continue
        values.append([
            timestamp, useremail, displayname, sessionid,
            barconombre.strip(), localizador.strip().upper(), idx,
            cabina, categoria, requested_by, request_date,
        ])

    if not values:
        raise Exception("Debes informar al menos una cabina y/o una categoría.")

    sheetsservice.spreadsheets().values().append(
        spreadsheetId=BOATREGISTRYSHEETID,
        range=f"{ticket_title}!A:K",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()
    return len(values)


# ── PDF export desde Sheets ───────────────────────────────
def exportsheetpdfbytes(spreadsheetid, gid):
    creds = getgooglecreds().with_scopes([
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
    ])
    creds.refresh(Request())
    exporturl = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheetid}/export"
        f"?format=pdf&gid={gid}&size=A4&portrait=true&fitw=true&fith=false"
        f"&sheetnames=false&scale=2&printtitle=false&pagenumbers=false"
        f"&gridlines=false&fzr=false&top_margin=0.50&bottom_margin=0.50"
        f"&left_margin=0.50&right_margin=0.50"
    )
    response = requests.get(
        exporturl,
        headers={"Authorization": f"Bearer {creds.token}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.content


# ── Agencias ──────────────────────────────────────────────
def getagencies():
    sheetsservice = getsheetsservice()
    response = sheetsservice.spreadsheets().values().get(
        spreadsheetId=AGENCYSHEETID,
        range=f"{AGENCYSHEETNAME}!A:K",
    ).execute()
    rows = response.get("values", [])
    agencies = []
    for idx, row in enumerate(rows, start=1):
        row = row + [""] * (11 - len(row))
        data = {"rownumber": idx}
        for i, field in enumerate(AGENCYFIELDS):
            data[field] = row[i]
        data["searchblob"] = " ".join(
            normalizetext(data[field])
            for field in ["Nombre", "CODIGO", "Grupo Gest", "Telefono", "Email", "Direccion"]
        )
        data["phonenorm"] = normalizephone(data["Telefono"])
        agencies.append(data)
    return agencies


def searchagencies(query):
    agencies = getagencies()
    q      = normalizetext(query)
    qphone = normalizephone(query)
    if not q and not qphone:
        return []
    matches = []
    for agency in agencies:
        if q and q in agency["searchblob"]:
            matches.append(agency)
            continue
        if qphone and qphone in agency["phonenorm"]:
            matches.append(agency)
    return matches


# ── Creación de archivos de crucero ───────────────────────
def createcrucerofile(barco, fechaobj):
    if not barco or not fechaobj:
        raise Exception("Faltan datos de barco o fecha.")
    anio       = str(fechaobj.year)
    nombrenuevo = f"{barco}_{fechaobj.strftime('%y%m%d')}"
    fechaes    = fechaobj.strftime("%d/%m/%Y")

    carpetaanio  = getorcreatefolder(DRIVEROOTID, anio)
    carpetabarco = getorcreatefolder(carpetaanio["id"], barco)

    duplicado = findfilebyname(carpetabarco["id"], nombrenuevo)
    if duplicado:
        return {
            "status": "duplicate",
            "name": nombrenuevo,
            "url": duplicado.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{duplicado['id']}/edit",
        }

    descripcion = (
        f"Barco: {barco}\nSalida: {fechaes}\n"
        f"Creado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"Los archivos de sesión deben borrarse a los 30 días."
    )
    copia = copyfiletofolder(TEMPLATEIDCRUCERO, nombrenuevo, carpetabarco["id"], descripcion)
    updatecrucerosheet(copia["id"], barco)
    getyears.clear()
    getboats.clear()
    getdepartures.clear()

    return {
        "status": "created",
        "name": nombrenuevo,
        "url": copia.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{copia['id']}/edit",
        "year": anio,
        "boat": barco,
    }


# ── Informe por barco ─────────────────────────────────────
def buildsheettaburl(spreadsheetid, sheetgid):
    return f"https://docs.google.com/spreadsheets/d/{spreadsheetid}/edit#gid={sheetgid}"


def extractinformeporbarco(spreadsheetid, spreadsheetname):
    sheets = getsheettitleswithids(spreadsheetid)
    rows   = []
    for sheet in sheets:
        sheettitle = sheet["title"]
        try:
            b2 = str(getsheettitleb2(spreadsheetid, sheettitle) or "").upper()
            if "CONFIR" not in b2 and "PROFORMA" not in b2:
                continue
            cells = getsheetcellsbatch(
                spreadsheetid, sheettitle,
                ["G10","G11","G5","G57","P57","Q55","G22","K22","N22","P22","G20","K20","N20","P20","G19","G18"],
            )
            pax      = sum(parseintfromtext(cells.get(a1)) for a1 in ["G22","K22","N22","P22"])
            cabinas  = sum(int(parsenumericvalue(cells.get(a1))) for a1 in ["G20","K20","N20","P20"])
            deposito = parsenumericvalue(cells.get("P57"))
            total    = parsenumericvalue(cells.get("Q55"))
            duracion = int(parsenumericvalue(cells.get("G18")))
            rows.append({
                "Localizador":       str(cells.get("G11","")).strip(),
                "Agencia":           str(cells.get("G5","")).strip(),
                "Estado":            str(cells.get("G10","")).strip(),
                "Estado Pago":       str(cells.get("G57","")).strip(),
                "Cantidad Deposito": deposito,
                "Total":             total,
                "PAX":               pax,
                "Cabinas":           cabinas,
                "Itinerario":        str(cells.get("G19","")).strip(),
                "Duracion":          f"{duracion} Dias" if duracion else "",
                "SheetId":           sheet["sheetId"],
                "SheetUrl":          buildsheettaburl(spreadsheetid, sheet["sheetId"]),
            })
        except Exception:
            continue
    return {
        "spreadsheetid":   spreadsheetid,
        "spreadsheetname": spreadsheetname,
        "rows":            rows,
        "totalpax":        sum(r["PAX"] for r in rows),
    }


# ── Búsqueda de localizador para IR A CONFIRMACIÓN ───────
def parselocatorinput(locatorraw):
    locator  = str(locatorraw or "").strip().upper()
    if not locator:
        raise Exception("Debes introducir un localizador.")
    isgroup  = locator.endswith("_GROUP")
    core     = locator[:-6] if isgroup else locator
    m = re.fullmatch(r"([A-Z]{2,3})(\d{6})-(\d{3})", core)
    if not m:
        raise Exception("Formato de localizador no válido. Debe ser CODIGOBARCOAAMMDD-999 o terminar en _GROUP.")
    shipcode, yymmdd, sequence = m.groups()
    boatname = SHIPCODETONAME.get(shipcode)
    if not boatname:
        raise Exception(f"Código de barco no reconocido: {shipcode}")
    yearfull = f"20{yymmdd[:2]}"
    filebase = f"{boatname}_{yymmdd}"
    return {
        "original":       locator,
        "isgroup":        isgroup,
        "core":           core,
        "shipcode":       shipcode,
        "boatname":       boatname,
        "yymmdd":         yymmdd,
        "sequence":       sequence,
        "yearfull":       yearfull,
        "yearfoldername": f"{yearfull}_GROUP" if isgroup else yearfull,
        "filename":       f"{filebase}_GROUP" if isgroup else filebase,
        "sheetname":      f"{core}_GROUP" if isgroup else core,
        "rootid":         GROUPSROOTID if isgroup else DRIVEROOTID,
    }


def findlocatorconfirmation(locatorraw):
    parsed   = parselocatorinput(locatorraw)
    loglines = []
    yearfolder = findchildfolder(parsed["rootid"], parsed["yearfoldername"])
    if not yearfolder:
        loglines.append(f"No existe la carpeta de año {parsed['yearfoldername']}")
        return {"status": "missingyear", "parsed": parsed, "log": loglines}
    loglines.append(f"Carpeta de año encontrada: {parsed['yearfoldername']}")
    boatfolder = findchildfolder(yearfolder["id"], parsed["boatname"])
    if not boatfolder:
        loglines.append(f"No existe la carpeta del barco {parsed['boatname']}")
        return {"status": "missingboat", "parsed": parsed, "log": loglines}
    loglines.append(f"Carpeta de barco encontrada: {parsed['boatname']}")
    fileobj = findfilebyname(boatfolder["id"], parsed["filename"])
    if not fileobj:
        loglines.append(f"No existe el archivo {parsed['filename']}")
        return {"status": "missingfile", "parsed": parsed, "file": fileobj, "log": loglines}
    loglines.append(f"Archivo encontrado: {parsed['filename']}")
    sheets = getsheettitleswithids(fileobj["id"])
    targetsheet = next((s for s in sheets if s["title"].strip() == parsed["sheetname"].strip()), None)
    if not targetsheet:
        loglines.append(f"No existe la pestaña {parsed['sheetname']}")
        return {"status": "missinglocator", "parsed": parsed, "file": fileobj, "log": loglines}
    finalurl = buildsheettaburl(fileobj["id"], targetsheet["sheetId"])
    loglines.append(f"Pestaña encontrada: {parsed['sheetname']}")
    return {
        "status": "found",
        "parsed": parsed,
        "file":   fileobj,
        "sheet":  targetsheet,
        "url":    finalurl,
        "log":    loglines,
    }


# ── Generación de PDF CVC ─────────────────────────────────
def buildcvcpdffromlocator(locator, targetsheet, pdfprefix):
    locatorclean = str(locator).strip()
    if not locatorclean:
        raise Exception("Debes introducir un localizador.")

    yield {"type": "status", "msg": "Listando spreadsheets en el CVC Fit..."}
    spreadsheets = listspreadsheetsinfolderrecentfirst(FOLDERID)
    if not spreadsheets:
        raise Exception("No se han encontrado Google Sheets en el indicado.")
    total = len(spreadsheets)
    yield {"type": "status", "msg": f"Encontrados {total} spreadsheets. Iniciando búsqueda del localizador {locatorclean}..."}

    for idx, file in enumerate(spreadsheets, start=1):
        spreadsheetid   = file["id"]
        spreadsheetname = file["name"]
        yield {"type": "progress", "current": idx, "total": total, "file": spreadsheetname,
               "msg": f"Revisando {idx}/{total}: {spreadsheetname}"}
        try:
            titles = {s["title"]: s["sheetId"] for s in getsheettitleswithids(spreadsheetid)}
            if "Booking ES" not in titles:
                yield {"type": "skip", "msg": f"Sin hoja Booking ES: {spreadsheetname}"}
                continue
            if targetsheet not in titles:
                yield {"type": "skip", "msg": f"Sin hoja {targetsheet}: {spreadsheetname}"}
                continue
            g11value = firstline(getsinglecell(spreadsheetid, "Booking ES", "G11"))
            if str(g11value).strip() != locatorclean:
                yield {"type": "skip", "msg": f"G11 '{g11value}' no coincide en {spreadsheetname}"}
                continue
            yield {"type": "status", "msg": f"Coincidencia encontrada en {spreadsheetname}. Leyendo nombre..."}
            nombre    = firstline(getsinglecell(spreadsheetid, "Booking ES", "G24"))
            nombresafe = safefilename(nombre if nombre else "Sin nombre")
            pdfname   = safefilename(f"{pdfprefix} {nombresafe} {locatorclean}.pdf")
            yield {"type": "status", "msg": f"Generando PDF de la hoja {targetsheet}..."}
            pdfbytes  = exportsheetpdfbytes(spreadsheetid, titles[targetsheet])
            yield {
                "type": "done",
                "locator": locatorclean,
                "spreadsheetid":   spreadsheetid,
                "spreadsheetname": spreadsheetname,
                "spreadsheeturl":  file.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{spreadsheetid}/edit",
                "nombre":   nombre,
                "filename": pdfname,
                "pdfbytes": pdfbytes,
            }
            return
        except StopIteration:
            raise
        except Exception as exc:
            yield {"type": "error", "msg": f"Error en {spreadsheetname}: {str(exc)}"}

    raise Exception("No se ha encontrado el localizador en Booking ES!G11 de ningún Sheet del folder.")





