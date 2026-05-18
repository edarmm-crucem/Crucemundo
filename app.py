import re
import urllib.parse
from datetime import date, datetime
import uuid

import requests
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.set_page_config(
    page_title="Crucemundo Hub",
    page_icon="favicon1.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

FOLDERSESIONESID = "1MxMdeBlUG6v5n2upobsjNbQNQ8F_C_sO"
FOLDERID = "1MxMdeBlUG6v5n2upobsjNbQNQ8F_C_sO"
LOGOID = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGOURL = f"https://lh3.googleusercontent.com/d/{LOGOID}"
TEMPLATEIDES = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
TEMPLATEIDGRUPOS = "1Z7ktX3PhVkMibWpzdrDDqAT4aPsmjzSJPf1SgZcL5-w"
TEMPLATEIDCRUCERO = "1zSJPi6St_Z5Jw1c6eieVnKI4NyEdP7E9n3WTZ9yy3C0"
EXCURSIONESSHEETID = "1ojMHeoosUyel8BA2XTmDsmyDJf_vvJrrJNOyxn2u1jg"
AGENCYSHEETID = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
AGENCYSHEETNAME = "Datos"
DRIVEROOTID = "11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm"
GROUPSROOTID = "1MMNH3y1E3jJIp6uUnxbwV0toAtdr2F2M"
BOATREGISTRYSHEETID = "1pvDAEPGkb1DmvbauY-eKk3ymljDvEBvDivijVDUHmGA"
BOATREGISTRYSHEETNAME = "TICKETS, RESULTADO, ENVIADO TICKET"
MASTERCLIENTESSHEETID = "1Z4sZolu-F44_WfMV7ZiYlelSU3SLU6JVO1MmqLeIZ0k"  # ← NUEVO

VALIDUSERS = {
    "support@crucemundo.com": "Albina",
    "sales@crucemundo.com": "Kristina",
    "cruise@crucemundo.com": "Malvina",
    "tania@crucemundo.com": "Tania Bondar",
    "incoming@crucemundo.com": "Tatiana",
    "operations@crucemundo.com": "Anton",
    "reservations@crucemundo.com": "Serge",
    "marketing@crucemundo.com": "Asel",
    "alexei@crucemundo.com": "Alexei",
    "anton@crucemundo.com": "Anton",
    "finance@crucemundo.com": "Aleksandr",
    "edarmm@gmail.com": "Esteban",
}
VALIDPASSWORD = st.secrets.get("apppassword", "")

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

CLIENTFIELDS = ["Nombre", "Apellidos", "Documento", "Region", "Localizador"]  # ← NUEVO

SHIPCODEMAP = {
    "MS_ALBERTINA": "ALB",
    "MS_ARENA": "ARN",
    "MS_CRUCEVITA": "CV",
    "MS_DOURO_CRUISER": "DC",
    "MS_FIDELIO": "FID",
    "MS_LEONORA": "LEO",
    "MS_RIVER_DIAMOND": "RDA",
    "MS_RIVER_SAPPHIRE": "RSA",
    "MS_SWISS_SPLENDOR": "SPL",
    "MS_VISTA_GRACIA": "VGR",
    "MS_VISTAMILLA": "VMI",
    "MS_VISTA_RIO": "VRI",
}
SHIPCODETONAME = {v: k for k, v in SHIPCODEMAP.items()}



STATEDEFAULTS = {
    "authenticated": False,
    "useremail": "",
    "displayname": "",
    "confirmstate": "idle",
    "historial": "",
    "sessiontype": "",
    "activepanel": None,
    "sessionid": "",
    "sessionstart": None,

    "opensalidaform": False,
    "opencruceroform": False,
    "opennuevaagenciaform": False,
    "openbuscaragenciaform": False,
    "opencvcfitform": False,
    "opencvcagenciasform": False,
    "openirconfirmacionform": False,
    "openinformebarcoform": False,
    "opennuevobarcoform": False,
    "openbuscarclientesform": False,  # ← NUEVO

    "salidayear": None,
    "salidaboat": None,
    "salidaname": None,

    "cruceroyear": None,
    "cruceroboat": None,

    "agencymatches": [],
    "agencyselectedidx": None,

    "cvcfitlocator": "",
    "cvcfitresult": None,
    "cvcfitlog": [],

    "cvcagenciaslocator": "",
    "cvcagenciasresult": None,
    "cvcagenciaslog": [],

    "irconfirmacionlocator": "",
    "irconfirmacionresult": None,
    "irconfirmacionlog": [],

    "informetype": None,
    "informeyear": None,
    "informeboat": None,
    "informesalida": None,
    "informeresult": None,

    "nombrecopia": "",
    "copyurl": "",
    "processtitle": "",
    "processresult": None,

    "nuevobarconombre": "",
    "nuevobarcolocalizador": "",
    "nuevobarcocabina1": "",
    "nuevobarcocategoria1": "",
    "nuevobarcocabina2": "",
    "nuevobarcocategoria2": "",
    "nuevobarcocabina3": "",
    "nuevobarcocategoria3": "",
    "nuevobarcocabina4": "",
    "nuevobarcocategoria4": "",
    "nuevobarcocabina5": "",
    "nuevobarcocategoria5": "",

    # ← NUEVO
    "buscarclientes_query": "",
    "buscarclientes_matches": [],
    "buscarclientes_lastmodified": None,
}

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
    # ← NUEVO
    "buscarclientes": [
        "buscarclientes_query", "buscarclientes_matches",
        "buscarclientes_lastmodified", "buscarclientes_querywidget",
    ],
}

PANELFLAGS = {
    "salida": "opensalidaform",
    "crucero": "opencruceroform",
    "nuevaagencia": "opennuevaagenciaform",
    "buscaragencia": "openbuscaragenciaform",
    "cvcfit": "opencvcfitform",
    "cvcagencias": "opencvcagenciasform",
    "irconfirmacion": "openirconfirmacionform",
    "informebarco": "openinformebarcoform",
    "nuevobarco": "opennuevobarcoform",
    "buscarclientes": "openbuscarlientesform",  # ← NUEVO
}

for key, value in STATEDEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


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
    st.session_state.activepanel = None
    st.session_state.confirmstate = "idle"
    st.session_state.sessiontype = ""
    st.session_state.processresult = None


def openpanel(panelname):
    cleartransientui()
    flag = PANELFLAGS.get(panelname)
    if flag:
        st.session_state[flag] = True
        st.session_state.activepanel = panelname
        safeaudit("open_panel", f"Apertura de panel {panelname}", panel=panelname, extra={"request_type": "open_panel"})


def closecurrentpanel():
    cleartransientui()
    st.rerun()


def getsessiondurationseconds():
    started = st.session_state.get("sessionstart")
    if not started:
        return 0
    try:
        return int((datetime.now() - started).total_seconds())
    except Exception:
        return 0


def renderkeyvaluegrid(cssprefix, fields):
    st.markdown(f'<div class="{cssprefix}-card"><div class="{cssprefix}-grid">', unsafe_allow_html=True)
    for label, value in fields:
        safevalue = value if value not in (None, "") else "-"
        st.markdown(
            f'''
            <div>
                <div class="{cssprefix}-item-label">{label}</div>
                <div class="{cssprefix}-item-value">{safevalue}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    st.markdown("</div></div>", unsafe_allow_html=True)


def panelheader(title, closekey):
    headcol1, headcol2 = st.columns([12, 1])
    with headcol1:
        st.markdown(f"### {title}")
    with headcol2:
        if st.button("✕", key=closekey):
            closecurrentpanel()


def get_request_identity():
    requested_by = st.session_state.get("displayname", "").strip() or st.session_state.get("useremail", "")
    request_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return requested_by, request_date











def dologout():
    safeaudit("logout", "Cierre de sesión", panel=st.session_state.get("activepanel") or "app", extra={"request_type": "logout"})
    for key in list(st.session_state.keys()):
        st.session_state.pop(key, None)
    st.rerun()


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


def listfolderitems(parentid, foldersonly=False):
    service = getdriveservice()
    query = f"'{parentid}' in parents and trashed=false"
    if foldersonly:
        query += " and mimeType='application/vnd.google-apps.folder'"
    results = []
    pagetoken = None
    while True:
        response = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, webViewLink, description, createdTime, modifiedTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            pageToken=pagetoken,
            pageSize=1000,
            orderBy="modifiedTime desc",
        ).execute()
        results.extend(response.get("files", []))
        pagetoken = response.get("nextPageToken")
        if not pagetoken:
            break
    return results


def listspreadsheetsinfolderrecentfirst(folderid):
    service = getdriveservice()
    query = f"'{folderid}' in parents and trashed=false and mimeType='application/vnd.google-apps.spreadsheet'"
    results = []
    pagetoken = None
    while True:
        response = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, webViewLink, createdTime, modifiedTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            pageToken=pagetoken,
            pageSize=1000,
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
    return service.files().create(
        body=body, fields="id, name", supportsAllDrives=True
    ).execute()


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
        fileId=fileid,
        body=body,
        fields="id, name, webViewLink",
        supportsAllDrives=True,
    ).execute()


def ensure_sheet_headers():
    sheetsservice = getsheetsservice()
    spreadsheet = sheetsservice.spreadsheets().get(
        spreadsheetId=BOATREGISTRYSHEETID
    ).execute()
    sheets = spreadsheet.get("sheets", [])
    if len(sheets) < 2:
        raise Exception("El spreadsheet debe tener al menos 2 hojas.")
    log_title = sheets[0]["properties"]["title"]
    ticket_title = sheets[1]["properties"]["title"]
    audit_headers = [["timestamp","useremail","displayname","sessionid","action","detail","panel","duration_seconds","metadata","requested_by","request_date"]]
    ticket_headers = [["timestamp","useremail","displayname","sessionid","barco","localizador","linea","cabina","categoria_normalizada","requested_by","request_date"]]
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


def appendauditrow(action, detail="", panel="", extra=None):
    ensure_sheet_headers()
    sheetsservice = getsheetsservice()
    spreadsheet = sheetsservice.spreadsheets().get(spreadsheetId=BOATREGISTRYSHEETID).execute()
    sheets = spreadsheet.get("sheets", [])
    if len(sheets) < 2:
        raise Exception("El spreadsheet debe tener al menos 2 hojas.")
    log_title = sheets[0]["properties"]["title"]
    metadata = extra or {}
    requested_by, request_date = get_request_identity()
    values = [[
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        st.session_state.get("useremail", ""),
        st.session_state.get("displayname", ""),
        st.session_state.get("sessionid", ""),
        action, detail,
        panel or st.session_state.get("activepanel") or "",
        getsessiondurationseconds(),
        str(metadata), requested_by, request_date,
    ]]
    sheetsservice.spreadsheets().values().append(
        spreadsheetId=BOATREGISTRYSHEETID, range=f"{log_title}!A:K",
        valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()


def safeaudit(action, detail="", panel="", extra=None):
    try:
        appendauditrow(action, detail, panel, extra)
    except Exception:
        pass


def save_new_boat_registry(barconombre, localizador, cabin_pairs):
    ensure_sheet_headers()
    sheetsservice = getsheetsservice()
    spreadsheet = sheetsservice.spreadsheets().get(spreadsheetId=BOATREGISTRYSHEETID).execute()
    sheets = spreadsheet.get("sheets", [])
    if len(sheets) < 2:
        raise Exception("El spreadsheet debe tener al menos 2 hojas.")
    ticket_title = sheets[1]["properties"]["title"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    useremail = st.session_state.get("useremail", "")
    displayname = st.session_state.get("displayname", "")
    sessionid = st.session_state.get("sessionid", "")
    requested_by, request_date = get_request_identity()
    values = []
    for idx, (cabina, categoria) in enumerate(cabin_pairs, start=1):
        cabina = str(cabina).strip()
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
        spreadsheetId=BOATREGISTRYSHEETID, range=f"{ticket_title}!A:K",
        valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()
    return len(values)


def updatecrucerosheet(spreadsheetid, barco):
    sheetsservice = getsheetsservice()
    spreadsheet = sheetsservice.spreadsheets().get(spreadsheetId=spreadsheetid).execute()
    sheets = spreadsheet.get("sheets", [])
    if not sheets:
        raise Exception("El spreadsheet no contiene hojas.")
    firstsheet = sheets[0]
    firstsheetid = firstsheet["properties"]["sheetId"]
    firstsheettitle = firstsheet["properties"]["title"]
    sheetsservice.spreadsheets().values().update(
        spreadsheetId=spreadsheetid, range=f"{firstsheettitle}!A1",
        valueInputOption="USER_ENTERED", body={"values": [[barco]]},
    ).execute()
    sheetsservice.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheetid,
        body={"requests": [{"updateSheetProperties": {"properties": {"sheetId": firstsheetid, "title": barco}, "fields": "title"}}]},
    ).execute()


def appendagencyrow(agencydata):
    sheetsservice = getsheetsservice()
    values = [[agencydata.get(field, "") for field in AGENCYFIELDS]]
    sheetsservice.spreadsheets().values().append(
        spreadsheetId=AGENCYSHEETID, range=f"{AGENCYSHEETNAME}!A:K",
        valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()


def getagencies():
    sheetsservice = getsheetsservice()
    response = sheetsservice.spreadsheets().values().get(
        spreadsheetId=AGENCYSHEETID, range=f"{AGENCYSHEETNAME}!A:K",
    ).execute()
    rows = response.get("values", [])
    agencies = []
    for idx, row in enumerate(rows, start=1):
        row = row + [""] * (11 - len(row))
        data = {"rownumber": idx}
        for i, field in enumerate(AGENCYFIELDS):
            data[field] = row[i]
        data["searchblob"] = " ".join(normalizetext(data[field]) for field in ["Nombre", "CODIGO", "Grupo Gest", "Telefono", "Email", "Direccion"])
        data["phonenorm"] = normalizephone(data["Telefono"])
        agencies.append(data)
    return agencies


def searchagencies(query):
    agencies = getagencies()
    q = normalizetext(query)
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




def getmasterclienteslastmodified():
    """Devuelve la fecha de última modificación del archivo MASTER CLIENTES en Drive."""
    try:
        service = getdriveservice()
        file = service.files().get(
            fileId=MASTERCLIENTESSHEETID,
            fields="modifiedTime, name",
            supportsAllDrives=True,
        ).execute()
        modtime = file.get("modifiedTime", "")
        if modtime:
            dt = datetime.strptime(modtime, "%Y-%m-%dT%H:%M:%S.%fZ")
            return dt.strftime("%d/%m/%Y %H:%M")
        return None
    except Exception:
        return None


def getclientes():
    """Lee el índice 0 del MASTER_CLIENTES: col A Nombre, B Apellidos, C Documento, D Region, E Localizador."""
    sheetsservice = getsheetsservice()
    spreadsheet = sheetsservice.spreadsheets().get(
        spreadsheetId=MASTERCLIENTESSHEETID
    ).execute()
    sheets = spreadsheet.get("sheets", [])
    if not sheets:
        raise Exception("El archivo MASTER CLIENTES no tiene hojas.")
    firsttitle = sheets[0]["properties"]["title"]
    response = sheetsservice.spreadsheets().values().get(
        spreadsheetId=MASTERCLIENTESSHEETID,
        range=f"{firsttitle}!A:E",
    ).execute()
    rows = response.get("values", [])
    clientes = []
    for idx, row in enumerate(rows, start=1):
        if idx == 1:
            continue  # saltar cabecera si la hay
        row = row + [""] * (5 - len(row))
        data = {
            "rownumber": idx,
            "Nombre": row[0],
            "Apellidos": row[1],
            "Documento": row[2],
            "Region": row[3],
            "Localizador": row[4],
        }
        data["searchblob"] = " ".join(
            normalizetext(data[field]) for field in CLIENTFIELDS
        )
        clientes.append(data)
    return clientes


def searchclientes(query):
    clientes = getclientes()
    q = normalizetext(query)
    if not q:
        return []
    return [c for c in clientes if q in c["searchblob"]]




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


def createcrucerofile(barco, fechaobj):
    if not barco or not fechaobj:
        raise Exception("Faltan datos de barco o fecha.")
    anio = str(fechaobj.year)
    nombrenuevo = f"{barco}_{fechaobj.strftime('%y%m%d')}"
    fechaes = fechaobj.strftime("%d/%m/%Y")
    carpetaanio = getorcreatefolder(DRIVEROOTID, anio)
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


def getsheettitleswithids(spreadsheetid):
    sheetsservice = getsheetsservice()
    spreadsheet = sheetsservice.spreadsheets().get(spreadsheetId=spreadsheetid).execute()
    return [
        {"title": sheet.get("properties", {}).get("title", ""), "sheetId": sheet.get("properties", {}).get("sheetId")}
        for sheet in spreadsheet.get("sheets", [])
    ]


def getsinglecell(spreadsheetid, sheettitle, a1):
    sheetsservice = getsheetsservice()
    values = sheetsservice.spreadsheets().values().get(
        spreadsheetId=spreadsheetid, range=f"{sheettitle}!{a1}", majorDimension="ROWS",
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
    response = requests.get(exporturl, headers={"Authorization": f"Bearer {creds.token}"}, timeout=60)
    response.raise_for_status()
    return response.content



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
        spreadsheetid = file["id"]
        spreadsheetname = file["name"]
        yield {"type": "progress", "current": idx, "total": total, "file": spreadsheetname, "msg": f"Revisando {idx}/{total}: {spreadsheetname}"}
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
            yield {"type": "status", "msg": f"Coincidencia encontrada en {spreadsheetname}. Leyendo nombre del pasajero..."}
            nombre = firstline(getsinglecell(spreadsheetid, "Booking ES", "G24"))
            nombresafe = safefilename(nombre if nombre else "Sin nombre")
            pdfname = safefilename(f"{pdfprefix} {nombresafe} {locatorclean}.pdf")
            yield {"type": "status", "msg": f"Generando PDF de la hoja {targetsheet}..."}
            pdfbytes = exportsheetpdfbytes(spreadsheetid, titles[targetsheet])
            yield {
                "type": "done",
                "locator": locatorclean, "spreadsheetid": spreadsheetid,
                "spreadsheetname": spreadsheetname,
                "spreadsheeturl": file.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{spreadsheetid}/edit",
                "nombre": nombre, "filename": pdfname, "pdfbytes": pdfbytes,
            }
            return
        except StopIteration:
            raise
        except Exception as exc:
            yield {"type": "error", "msg": f"Error en {spreadsheetname}: {str(exc)}"}
    raise Exception("No se ha encontrado el localizador en Booking ES!G11 de ningún Sheet del folder.")


def runcvcsearch(locator, targetsheet, pdfprefix, statekey):
    st.session_state[f"{statekey}result"] = None
    st.session_state[f"{statekey}log"] = []
    progressbar = st.progress(0.0, text="Iniciando...")
    statusbox = st.empty()
    logbox = st.empty()
    loglines = []
    try:
        result = None
        for event in buildcvcpdffromlocator(locator, targetsheet, pdfprefix):
            etype = event.get("type")
            if etype == "progress":
                pct = event["current"] / event["total"]
                progressbar.progress(pct, text=f"Revisando {event['current']}/{event['total']}: {event['file']}")
                statusbox.markdown(f'<div class="{statekey}-log-line">{event["msg"]}</div>', unsafe_allow_html=True)
            elif etype == "status":
                loglines.append(event["msg"])
            elif etype == "skip":
                loglines.append(f'<span style="color:#9BA5B7">{event["msg"]}</span>')
            elif etype == "error":
                loglines.append(f'<span style="color:#D97706">{event["msg"]}</span>')
            elif etype == "done":
                result = event
                progressbar.progress(1.0, text="PDF generado correctamente")
                statusbox.empty()
        if loglines:
            logbox.markdown(
                "<br>".join(f'<div class="{statekey}-log-line">{line}</div>' for line in loglines[-12:]),
                unsafe_allow_html=True,
            )
        if result:
            st.session_state[f"{statekey}result"] = result
            st.session_state[f"{statekey}log"] = loglines
        else:
            st.error("Búsqueda finalizada sin coincidencias.")
    except Exception as exc:
        progressbar.empty()
        statusbox.empty()
        st.error(f"Error: {exc}")
        st.session_state[f"{statekey}result"] = None


def parselocatorinput(locatorraw):
    locator = str(locatorraw or "").strip().upper()
    if not locator:
        raise Exception("Debes introducir un localizador.")
    isgroup = locator.endswith("_GROUP")
    core = locator[:-6] if isgroup else locator
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
        "original": locator, "isgroup": isgroup, "core": core,
        "shipcode": shipcode, "boatname": boatname, "yymmdd": yymmdd,
        "sequence": sequence, "yearfull": yearfull,
        "yearfoldername": f"{yearfull}_GROUP" if isgroup else yearfull,
        "filename": f"{filebase}_GROUP" if isgroup else filebase,
        "sheetname": f"{core}_GROUP" if isgroup else core,
        "rootid": GROUPSROOTID if isgroup else DRIVEROOTID,
    }


def buildsheettaburl(spreadsheetid, sheetgid):
    return f"https://docs.google.com/spreadsheets/d/{spreadsheetid}/edit#gid={sheetgid}"


def findlocatorconfirmation(locatorraw):
    parsed = parselocatorinput(locatorraw)
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
    return {"status": "found", "parsed": parsed, "file": fileobj, "sheet": targetsheet, "url": finalurl, "log": loglines}


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
                "nombre": name, "id": file["id"],
                "url": file.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{file['id']}/edit",
            })
    departures.sort(key=lambda x: x["nombre"])
    return departures


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


def extractinformeporbarco(spreadsheetid, spreadsheetname):
    sheets = getsheettitleswithids(spreadsheetid)
    rows = []
    for sheet in sheets:
        sheettitle = sheet["title"]
        try:
            b2 = str(getsinglecell(spreadsheetid, sheettitle, "B2") or "").upper()
            if "CONFIR" not in b2 and "PROFORMA" not in b2:
                continue
            cells = getsheetcellsbatch(spreadsheetid, sheettitle,
                ["G10","G11","G5","G57","P57","Q55","G22","K22","N22","P22","G20","K20","N20","P20","G19","G18"])
            pax = sum(parseintfromtext(cells.get(a1)) for a1 in ["G22","K22","N22","P22"])
            cabinas = sum(int(parsenumericvalue(cells.get(a1))) for a1 in ["G20","K20","N20","P20"])
            deposito = parsenumericvalue(cells.get("P57"))
            total = parsenumericvalue(cells.get("Q55"))
            duracionnum = int(parsenumericvalue(cells.get("G18")))
            rows.append({
                "Localizador": str(cells.get("G11", "")).strip(),
                "Agencia": str(cells.get("G5", "")).strip(),
                "Estado": str(cells.get("G10", "")).strip(),
                "Estado Pago": str(cells.get("G57", "")).strip(),
                "Cantidad Deposito": deposito, "Total": total,
                "PAX": pax, "Cabinas": cabinas,
                "Itinerario": str(cells.get("G19", "")).strip(),
                "Duracion": f"{duracionnum} Dias" if duracionnum else "",
                "SheetId": sheet["sheetId"],
                "SheetUrl": buildsheettaburl(spreadsheetid, sheet["sheetId"]),
            })
        except Exception:
            continue
    totalpax = sum(r["PAX"] for r in rows)
    return {"spreadsheetid": spreadsheetid, "spreadsheetname": spreadsheetname, "rows": rows, "totalpax": totalpax}


def formatestadobadge(value):
    v = str(value or "").strip().upper()
    if v == "CONFIRMADO": return '<span class="status-pill status-confirmado">CONFIRMADO</span>'
    if v == "NO CONFIRMADO": return '<span class="status-pill status-no-confirmado">NO CONFIRMADO</span>'
    if v == "CANCELADO": return '<span class="status-pill status-cancelado">CANCELADO</span>'
    return f'<span class="status-pill">{value or ""}</span>'


def formatestadopagobadge(value):
    v = str(value or "").strip().upper()
    if v == "PTE PAGO": return '<span class="status-pill status-pte-pago">PTE PAGO</span>'
    if v == "DEPOSITO": return '<span class="status-pill status-deposito">DEPOSITO</span>'
    if v == "CREDITO": return '<span class="status-pill status-credito">CREDITO</span>'
    if v == "PAGADO": return '<span class="status-pill status-pagado">PAGADO</span>'
    return f'<span class="status-pill">{value or ""}</span>'



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
        st.session_state.informeyear = None
        st.session_state.informeboat = None
        st.session_state.informesalida = None
        st.session_state.informeresult = None
        st.session_state.pop("informeyearwidget", None)
        st.session_state.pop("informeboatwidget", None)
        st.session_state.pop("informesalidawidget", None)
    elif level == "year":
        st.session_state.informeboat = None
        st.session_state.informesalida = None
        st.session_state.informeresult = None
        st.session_state.pop("informeboatwidget", None)
        st.session_state.pop("informesalidawidget", None)
    elif level == "boat":
        st.session_state.informesalida = None
        st.session_state.informeresult = None
        st.session_state.pop("informesalidawidget", None)


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


def iniciarproceso(sessiontype, templateid, prefixname, processtitle):
    try:
        cleartransientui()
        fechastr = datetime.now().strftime("%Y%m%d-%H%M")
        displayuser = st.session_state.get("displayname", "").strip() or "Sin usuario"
        nombrecopia = f"SESION - {displayuser} - {prefixname} - {fechastr}"
        copyurl = (
            f"https://docs.google.com/spreadsheets/d/{templateid}/copy"
            f"?copyDestination={FOLDERSESIONESID}"
            f"&title={urllib.parse.quote(nombrecopia)}"
        )
        safeaudit("request_create_session", f"Petición crear sesión: {prefixname}", panel="process", extra={"request_type": "create_session"})
        st.session_state.confirmstate = "step1"
        st.session_state.sessiontype = sessiontype
        st.session_state.nombrecopia = nombrecopia
        st.session_state.copyurl = copyurl
        st.session_state.processtitle = processtitle
        st.session_state.activepanel = "process"
        st.rerun()
    except Exception as e:
        st.error(str(e))



st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');

    * { box-sizing: border-box; }
    html, body, [class*="css"] { font-family: "DM Sans", sans-serif; background: #FFFFFF !important; }
    [data-testid="stAppViewContainer"] { background: #FFFFFF !important; }
    [data-testid="stHeader"] { background: transparent !important; }
    section[data-testid="stSidebar"] { display: none !important; }

    .block-container, section.stMain .block-container, .stMainBlockContainer, [data-testid="stMainBlockContainer"] {
        padding-top: 0rem !important; padding-bottom: 1rem !important;
        padding-left: 1rem !important; padding-right: 1rem !important;
        max-width: 1900px !important; margin: 0 auto !important;
    }

    .login-page { min-height: auto; display: flex; align-items: flex-start; justify-content: center; padding: 0.2rem 1rem 1rem; }
    .login-shell { width: 100%; max-width: 390px; margin: 0 auto; }
    .login-head { text-align: center; margin-bottom: 0.55rem; }
    .login-logo { height: 56px; width: auto; margin: 0 auto 0.65rem auto; display: block; }
    .login-title { font-size: 1.08rem; font-weight: 800; color: #1F2937; }
    .login-subtitle { font-size: 0.78rem; color: #667085; margin-top: 0.28rem; }
    .login-form-box { background: transparent !important; border: none !important; padding: 0 !important; }
    .login-note { margin-top: 0.65rem; text-align: center; font-size: 0.72rem; color: #8A93A5; }

    div[data-testid="stTextInput"] label,
    div[data-testid="stSelectbox"] label,
    div[data-testid="stDateInput"] label,
    div[data-testid="stNumberInput"] label {
        color: #334155 !important; font-size: 0.80rem !important;
        font-weight: 700 !important; letter-spacing: 0.01em !important;
    }

    div[data-testid="stTextInput"] input,
    div[data-testid="stDateInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background: #FFFFFF !important; border: 1.6px solid #CBD5E1 !important;
        border-radius: 14px !important; color: #1F2937 !important;
        min-height: 46px !important; box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05) !important;
        font-family: "DM Sans", sans-serif !important; font-size: 0.90rem !important;
        font-weight: 600 !important; transition: all 0.18s ease !important;
    }

    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stDateInput"] input:focus,
    div[data-testid="stNumberInput"] input:focus,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within {
        border-color: #2563EB !important;
        box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.14), 0 8px 18px rgba(37, 99, 235, 0.10) !important;
        background: #FFFFFF !important;
    }

    div.stButton { width: fit-content !important; }
    div.stButton button,
    div[data-testid="stFormSubmitButton"] button,
    .logout-btn div button, .download-btn button, .stDownloadButton button {
        border-radius: 999px !important; min-height: 42px !important;
        padding: 0 1.15rem !important; font-size: 0.83rem !important;
        font-weight: 800 !important; box-shadow: 0 3px 10px rgba(15, 23, 42, 0.08) !important;
        font-family: "DM Sans", sans-serif !important; letter-spacing: 0.01em !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease !important;
        border: 1.5px solid transparent !important;
    }

    div.stButton button:hover, div[data-testid="stFormSubmitButton"] button:hover,
    .download-btn button:hover, .stDownloadButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12) !important;
        filter: saturate(1.04);
    }

    .portal-header { padding: 0.1rem 0 0.55rem 0; display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 0.55rem; }
    .portal-header-left { display: flex; align-items: center; gap: 0.9rem; }
    .portal-logo { height: 42px; width: auto; object-fit: contain; display: block; }
    .portal-title, .portal-title-en { font-size: 0.96rem; font-weight: 800; color: #1F2937; line-height: 1.15; }
    .portal-title-en { margin-top: 0.12rem; }
    .portal-subtitle, .portal-subtitle-en { font-size: 0.72rem; color: #667085; line-height: 1.2; }
    .portal-subtitle { margin-top: 0.12rem; }
    .portal-subtitle-en { margin-top: 0.08rem; }
    .user-top { font-size: 0.72rem; color: #566079; white-space: nowrap; }

    .main-content { padding: 0; }
    .section-head-row, .section-head-row-green {
        display: flex; align-items: center; justify-content: flex-start; gap: 0.55rem;
        margin-bottom: 0.75rem; flex-wrap: wrap;
    }
    .section-head-row-green { margin-top: -0.15rem; }

    .section-eyebrow {
        display: inline-flex; align-items: center; padding: 0.34rem 0.74rem; border-radius: 999px;
        background: #E0ECFF; border: 1px solid #BFD4FF; color: #1E4FBF; font-size: 0.66rem;
        font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0 !important;
    }

    .web-chip, .web-chip-green {
        display: inline-flex; align-items: center; justify-content: center;
        padding: 0.38rem 0.82rem; border-radius: 999px; font-size: 0.71rem; font-weight: 800;
        line-height: 1; text-decoration: none; white-space: nowrap; box-shadow: 0 2px 8px rgba(15,23,42,0.06);
    }
    .web-chip { background: #FFE69A; border: 1px solid #F2C94C; color: #7A5900 !important; }
    .web-chip-green { background: #DDF7E6; border: 1px solid #9FDEB4; color: #17663B !important; }

    .user-pill {
        display: inline-flex; align-items: center; gap: 0.4rem; margin: 0.02rem 0 1rem;
        padding: 0.42rem 0.78rem; border-radius: 999px; background: #fff; border: 1px solid #D9E2EC;
        font-size: 0.73rem; font-weight: 700; color: #4B5565; max-width: 100%; word-break: break-word;
        box-shadow: 0 2px 8px rgba(15,23,42,0.04);
    }

    .panel-inline {
        background: linear-gradient(180deg, #FFFFFF 0%, #FAFBFD 100%);
        border: 1px solid #DCE5F0; border-radius: 22px;
        padding: 1rem 1rem 1.1rem 1rem; margin-top: 0.95rem;
        box-shadow: 0 8px 28px rgba(15,23,42,0.05);
    }

    .action-box {
        width: 100%; min-height: 20px; border-radius: 22px;
        padding: 0.72rem 0.85rem 0.78rem 0.85rem; margin-bottom: 0.70rem;
        display: flex; flex-direction: column; justify-content: space-between;
        gap: 0.42rem; border: 1px solid transparent;
        box-shadow: 0 6px 18px rgba(15,23,42,0.05);
    }

    .card-es { background: #EAF3FF; border-color: #BFD7FF; --card-btn-bg:#CFE3FF; --card-btn-border:#94BEFF; --card-btn-text:#1E4E93; --card-btn-shadow:rgba(30,78,147,0.16); }
    .card-grupos { background: #EAF8EE; border-color: #BDE3C7; --card-btn-bg:#CDEFD7; --card-btn-border:#93D0A7; --card-btn-text:#1F6A3A; --card-btn-shadow:rgba(31,106,58,0.15); }
    .card-salida { background: #FFF2E3; border-color: #F1CFA9; --card-btn-bg:#FFDDB8; --card-btn-border:#F1B97B; --card-btn-text:#8A5318; --card-btn-shadow:rgba(138,83,24,0.16); }
    .card-crucero { background: #F0EAFE; border-color: #D3C4FA; --card-btn-bg:#DDD0FF; --card-btn-border:#B9A0F8; --card-btn-text:#5A3E9E; --card-btn-shadow:rgba(90,62,158,0.16); }
    .card-nueva-agencia { background: #EAF8EF; border-color: #BEE3C9; --card-btn-bg:#D0EFDA; --card-btn-border:#98D0AA; --card-btn-text:#256245; --card-btn-shadow:rgba(37,98,69,0.16); }
    .card-buscar-agencia { background: #FFF1E5; border-color: #F1D1B0; --card-btn-bg:#FFDDBF; --card-btn-border:#F0B77E; --card-btn-text:#8B5620; --card-btn-shadow:rgba(139,86,32,0.16); }
    .card-cvcfit { background: #FDECF3; border-color: #F1C3D6; --card-btn-bg:#F7D2E2; --card-btn-border:#E89BBB; --card-btn-text:#9B3A63; --card-btn-shadow:rgba(155,58,99,0.16); }
    .card-cvcagencias { background: #EBF8EF; border-color: #BFE1C9; --card-btn-bg:#D0EFD8; --card-btn-border:#97D0A9; --card-btn-text:#2C6A44; --card-btn-shadow:rgba(44,106,68,0.16); }
    .card-irconfirmacion { background: #F0F3F8; border-color: #CFD8E6; --card-btn-bg:#E0E7F1; --card-btn-border:#B8C6DC; --card-btn-text:#4A5874; --card-btn-shadow:rgba(74,88,116,0.16); }
    .card-informebarco { background: #EAF7FB; border-color: #BFDDE8; --card-btn-bg:#D2EDF6; --card-btn-border:#97CEE0; --card-btn-text:#2B6881; --card-btn-shadow:rgba(43,104,129,0.16); }
    .card-nuevobarco { background: #EEF6FF; border-color: #C7DCF9; --card-btn-bg:#DCEBFF; --card-btn-border:#A8C8F5; --card-btn-text:#27518A; --card-btn-shadow:rgba(39,81,138,0.16); }
    /* ← NUEVO */
    .card-buscarclientes { background: #F3EEFF; border-color: #D8C8F9; --card-btn-bg:#E5D8FF; --card-btn-border:#C3A8F6; --card-btn-text:#5230A0; --card-btn-shadow:rgba(82,48,160,0.16); }

    .action-top { display: flex; align-items: flex-start; gap: 0.65rem; }
    .action-icon {
        width: 38px; height: 38px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
        font-size: 1rem; flex-shrink: 0; background: rgba(255,255,255,0.42); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.35);
    }
    .action-text { display: flex; flex-direction: column; gap: 0.06rem; min-width: 0; }
    .action-title, .action-title-en {
        font-family: "DM Sans", sans-serif !important; line-height: 1.08; white-space: nowrap;
        overflow: hidden; text-overflow: ellipsis;
    }
    .action-title { font-size: 0.96rem; font-weight: 800; color: #1F2937; }
    .action-title-en { margin-top: 0.02rem; color: #41506B; font-size: 0.80rem; font-weight: 800; }
    .action-desc, .action-desc-en { display: none !important; }

    .action-button-wrap {
        display: flex !important; justify-content: flex-start !important; align-items: center !important;
        width: 100% !important; margin-top: 0.02rem;
    }

    .done-link {
        display: inline-flex; align-items: center; gap: 0.35rem; border-radius: 999px; padding: 0.48rem 0.96rem;
        font-size: 0.82rem; font-weight: 800; font-family: "DM Sans", sans-serif !important; text-decoration: none;
        white-space: nowrap; box-shadow: 0 5px 14px rgba(15,23,42,0.08);
        transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
    }
    .done-link:hover { transform: translateY(-1px); filter: saturate(1.04); }

    .action-box div.stButton button, .action-box .done-link {
        background: var(--card-btn-bg) !important; border: 1.5px solid var(--card-btn-border) !important;
        color: var(--card-btn-text) !important; box-shadow: 0 6px 14px var(--card-btn-shadow) !important;
    }

    .panel-inline div.stButton button,
    .panel-inline div[data-testid="stFormSubmitButton"] button,
    .panel-inline .download-btn button,
    .panel-inline .stDownloadButton button {
        background: linear-gradient(180deg, #2F6DF6 0%, #245FE0 100%) !important;
        color: #FFFFFF !important; border: 1.5px solid #1E4FC7 !important;
        box-shadow: 0 8px 20px rgba(37, 99, 235, 0.22) !important;
    }

    .agency-card, .cvcfit-card, .cvcfit-status-card, .cvcagencias-card, .cvcagencias-status-card,
    .process-card, .irconfirmacion-card, .informebarco-card, .buscarclientes-card {
        background: #FBFCFF; border: 1px solid #DCE5F0; border-radius: 18px; padding: 1rem; margin-top: 0.75rem;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
    }

    .agency-grid, .cvcfit-grid, .cvcagencias-grid, .process-grid,
    .irconfirmacion-grid, .informebarco-grid, .buscarclientes-grid {
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.85rem 1rem;
    }

    .agency-item-label, .cvcfit-item-label, .cvcagencias-item-label, .process-item-label,
    .irconfirmacion-item-label, .informebarco-item-label, .buscarclientes-item-label {
        font-size: 0.68rem; color: #64748B; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.16rem; font-weight: 700;
    }

    .agency-item-value, .cvcfit-item-value, .cvcagencias-item-value, .process-item-value,
    .irconfirmacion-item-value, .informebarco-item-value, .buscarclientes-item-value {
        font-size: 0.82rem; color: #1F2937; line-height: 1.35; word-break: break-word; font-weight: 600;
    }

    .cvcfit-log-line, .cvcagencias-log-line, .irconfirmacion-log-line {
        font-size: 0.74rem; color: #465066; line-height: 1.45; margin-bottom: 0.35rem; word-break: break-word;
    }

    .report-table-wrap { margin-top: 1rem; overflow-x: auto; }
    .report-table {
        width: 100%; border-collapse: collapse; background: #fff;
        border: 1px solid #DCE5F0; border-radius: 16px; overflow: hidden;
    }
    .report-table th, .report-table td {
        font-size: 0.76rem; padding: 0.65rem 0.7rem; border-bottom: 1px solid #EEF2F7;
        text-align: left; vertical-align: top;
    }
    .report-table th { background: #F5F8FC; color: #334155; font-weight: 800; white-space: nowrap; }
    .report-table td { color: #1F2937; font-weight: 500; }

    .status-pill { display:inline-flex; align-items:center; justify-content:center; padding:0.24rem 0.56rem; border-radius:999px; font-size:0.70rem; font-weight:800; line-height:1; white-space:nowrap; border:1px solid transparent; }
    .status-confirmado{ background:#DCFCE7; color:#166534; border-color:#86EFAC; }
    .status-no-confirmado{ background:#FEF3C7; color:#92400E; border-color:#FCD34D; }
    .status-cancelado{ background:#FEE2E2; color:#991B1B; border-color:#FCA5A5; }
    .status-pte-pago{ background:#FEF3C7; color:#92400E; border-color:#FCD34D; }
    .status-deposito{ background:#DBEAFE; color:#1D4ED8; border-color:#93C5FD; }
    .status-credito{ background:#F3E8FF; color:#7E22CE; border-color:#D8B4FE; }
    .status-pagado{ background:#DCFCE7; color:#166534; border-color:#86EFAC; }
    .report-link{ color:#1D4ED8; font-weight:700; text-decoration:none; }
    .report-link:hover{ text-decoration:underline; }

    .portal-footer {
        margin-top: 1rem; padding: 0.5rem 0 0 0; display: flex; justify-content: space-between;
        align-items: center; gap: 0.8rem; flex-wrap: wrap;
    }
    .footer-text { font-size: 0.71rem; color: #A2ABBD; }

    @media (max-width: 1600px) {
        .agency-grid, .cvcfit-grid, .cvcagencias-grid, .process-grid,
        .irconfirmacion-grid, .informebarco-grid, .buscarclientes-grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 1300px) {
        .portal-header, .portal-footer { flex-direction: column; align-items: flex-start; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)




if not st.session_state.authenticated:
    st.markdown('<div class="login-page"><div class="login-shell">', unsafe_allow_html=True)
    st.markdown(
        f'''
        <div class="login-head">
            <img class="login-logo" src="{LOGOURL}" alt="Logo">
            <div class="login-title">Acceso</div>
            <div class="login-subtitle">Access</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="login-form-box">', unsafe_allow_html=True)
    with st.form("loginform", clear_on_submit=False):
        email = st.text_input("Mail / Email", placeholder="support@crucemundo.com")
        password = st.text_input("Contraseña / Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Entrar / Login")
        if submitted:
            emailclean = email.strip().lower()
            if not emailclean or not password:
                st.error("Debes introducir mail y contraseña / Please enter email and password.")
            elif emailclean not in VALIDUSERS:
                st.error("Usuario no autorizado / Unauthorized user.")
            elif password.strip() != str(VALIDPASSWORD).strip():
                st.error("Contraseña incorrecta / Incorrect password.")
            else:
                st.session_state.authenticated = True
                st.session_state.useremail = emailclean
                st.session_state.displayname = VALIDUSERS[emailclean]
                st.session_state.sessionid = str(uuid.uuid4())
                st.session_state.sessionstart = datetime.now()
                safeaudit("login", "Inicio de sesión correcto", panel="login", extra={"request_type": "login"})
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="login-note">El mail valida el acceso y el alias se usará para nombrar la sesión / Email validates access and the alias will be used to name the session.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()



USEREMAIL = st.session_state.get("useremail", "").strip()
DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Sin usuario"
SALUDO = getsaludo("es")
SALUDOEN = getsaludo("en")

excursionesurl = f"https://docs.google.com/spreadsheets/d/{EXCURSIONESSHEETID}/edit"
driverooturl = f"https://drive.google.com/drive/folders/{DRIVEROOTID}"
groupsrooturl = f"https://drive.google.com/drive/folders/{GROUPSROOTID}"
cvcfitfolderurl = f"https://drive.google.com/drive/folders/{FOLDERID}"

st.markdown(
    f'''
    <div class="portal-header">
        <div class="portal-header-left">
            <img class="portal-logo" src="{LOGOURL}" alt="Logo">
            <div>
                <div class="portal-title">{SALUDO}, {DISPLAYUSER}. ¿Qué hacemos hoy?</div>
                <div class="portal-title-en">{SALUDOEN}, {DISPLAYUSER}. What are we doing today?</div>
                <div class="portal-subtitle">Herramientas y automatizaciones · Backend Google Drive</div>
                <div class="portal-subtitle-en">Tools and automations · Google Drive backend</div>
            </div>
        </div>
        <div class="user-top">{DISPLAYUSER}</div>
    </div>
    ''',
    unsafe_allow_html=True,
)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

st.markdown(
    '''
    <div class="section-head-row">
        <div class="section-eyebrow">ACCIONES RÁPIDAS · QUICK ACTIONS</div>
        <a class="web-chip" href="https://www.crucemundo.es" target="_blank" rel="noopener noreferrer">Ir a Crucemundo</a>
        <a class="web-chip" href="https://mail.google.com" target="_blank" rel="noopener noreferrer">Gmail</a>
    </div>
    ''',
    unsafe_allow_html=True,
)

st.markdown(
    f'''
    <div class="section-head-row-green">
        <a class="web-chip-green" href="{driverooturl}" target="_blank" rel="noopener noreferrer">Drive Root</a>
        <a class="web-chip-green" href="{groupsrooturl}" target="_blank" rel="noopener noreferrer">Drive Groups</a>
        <a class="web-chip-green" href="{cvcfitfolderurl}" target="_blank" rel="noopener noreferrer">Folder Sesiones</a>
        <a class="web-chip-green" href="https://docs.google.com/spreadsheets/d/1K-TnE3QEhCplOP-IFHbKZc-vtKAxFEUBbZVK14EjJI/edit?gid=0#gid=0" target="_blank" rel="noopener noreferrer">MASTERCABINAS</a>
        <a class="web-chip-green" href="https://docs.google.com/spreadsheets/d/1ojMHeoosUyel8BA2XTmDsmyDJf_vvJrrJNOyxn2u1jg/edit?gid=0#gid=0" target="_blank" rel="noopener noreferrer">EXCURSIONES</a>
        <a class="web-chip-green" href="https://docs.google.com/spreadsheets/d/1Z4sZolu-F44WfMV7ZiYlelSU3SLU6JVO1MmqLeIZ0k/edit?gid=0#gid=0" target="_blank" rel="noopener noreferrer">MASTER CLIENTES</a>
        <a class="web-chip-green" href="https://docs.google.com/spreadsheets/d/1mlUYqtwTzLCRHJr9TCD7VWrGI6nDhMtwi27cMJL1s/edit?gid=0#gid=0" target="_blank" rel="noopener noreferrer">Ventas FIT</a>
    </div>
    ''',
    unsafe_allow_html=True,
)

st.markdown(f'<div class="user-pill">{DISPLAYUSER} · {USEREMAIL}</div>', unsafe_allow_html=True)



def renderactioncard(col, config):
    with col:
        st.markdown(
            f'''
            <div class="action-box {config["cardclass"]}">
                <div class="action-top">
                    <div class="action-icon">{config["icon"]}</div>
                    <div class="action-text">
                        <div class="action-title">{config["titlees"]}</div>
                        <div class="action-title-en">{config["titleen"]}</div>
                    </div>
                </div>
                <div class="action-button-wrap">
            ''',
            unsafe_allow_html=True,
        )
        if config.get("link"):
            st.markdown(
                f'<a class="done-link" href="{config["link"]}" target="_blank" rel="noopener noreferrer">{config["buttonlabel"]}</a>',
                unsafe_allow_html=True,
            )
        else:
            disabled = config.get("disabled", False)
            if not disabled and st.button(config["buttonlabel"], key=config["key"]):
                action = config.get("action")
                if action:
                    action()
            elif disabled:
                st.button(config["buttonlabel"], key=config["key"], disabled=True)
        st.markdown("</div></div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# FILA 1: pos1 Nueva Confirmación ES | pos2 Nueva Confirmación GRUPOS
#         pos3 Ir a Salida | pos4 Ir a Confirmación
#         pos5 Buscar Agencia | pos6 Buscar Clientes  ← NUEVO ORDEN
# ──────────────────────────────────────────────
row1_cards = [
    {
        "cardclass": "card-es",
        "icon": "📘",
        "titlees": "Nueva Confirmación",
        "titleen": "New Confirmation",
        "buttonlabel": "Crear Sesión",
        "key": "btncreares",
        "action": lambda: iniciarproceso("es", TEMPLATEIDES, "MASTER", "Estado del Proceso / Process Status / Crear Sesión MASTERCONFIRMATION"),
    },
    {
        "cardclass": "card-grupos",
        "icon": "👥",
        "titlees": "Nueva Confirmación GRUPOS",
        "titleen": "New GROUPS Confirmation",
        "buttonlabel": "Crear Sesión GRUPOS",
        "key": "btncreargrupos",
        "action": lambda: iniciarproceso("grupos", TEMPLATEIDGRUPOS, "MASTER GRUPOS", "Estado del Proceso / Process Status / Crear Sesión MASTERGRUPOS"),
    },
    {
        "cardclass": "card-salida",
        "icon": "🧭",
        "titlees": "Ir a Salida",
        "titleen": "Go to Departure",
        "buttonlabel": "Buscar Salida",
        "key": "btnirsalida",
        "action": lambda: openpanel("salida"),
    },
    {
        "cardclass": "card-irconfirmacion",
        "icon": "📍",
        "titlees": "Ir a Confirmación",
        "titleen": "Go to Confirmation",
        "buttonlabel": "Buscar Localizador",
        "key": "btnirconfirmacionopen",
        "action": lambda: openpanel("irconfirmacion"),
    },
    {
        "cardclass": "card-buscar-agencia",
        "icon": "🔎",
        "titlees": "Buscar Agencia",
        "titleen": "Find Agency",
        "buttonlabel": "Buscar Agencia",
        "key": "btnbuscaragencia",
        "action": lambda: openpanel("buscaragencia"),
    },
    {
        "cardclass": "card-buscarclientes",
        "icon": "🙋",
        "titlees": "Buscar Cliente",
        "titleen": "Find Client",
        "buttonlabel": "Buscar Cliente",
        "key": "btnbuscarclientes",
        "action": lambda: openpanel("buscarclientes"),
    },
]

# ──────────────────────────────────────────────
# FILA 2: pos1 CVC Fit | pos2 CVC Agencias
#         pos3 Informe € por Barco | pos4 Crear Crucero
#         pos5 Añadir Agencia | pos6 Nuevo Barco  ← NUEVO ORDEN
# ──────────────────────────────────────────────
row2_cards = [
    {
        "cardclass": "card-cvcfit",
        "icon": "📄",
        "titlees": "CVC Fit",
        "titleen": "CVC Fit",
        "buttonlabel": "Abrir CVC Fit",
        "key": "btncvcfitopen",
        "action": lambda: openpanel("cvcfit"),
    },
    {
        "cardclass": "card-cvcagencias",
        "icon": "📑",
        "titlees": "CVC Agencias",
        "titleen": "CVC Agencies",
        "buttonlabel": "Abrir CVC Agencias",
        "key": "btncvcagenciasopen",
        "action": lambda: openpanel("cvcagencias"),
    },
    {
        "cardclass": "card-informebarco",
        "icon": "📊",
        "titlees": "Informe € por Barco",
        "titleen": "Report € by Ship",
        "buttonlabel": "Abrir Informe",
        "key": "btninformebarcoopen",
        "action": lambda: openpanel("informebarco"),
    },
    {
        "cardclass": "card-crucero",
        "icon": "🚢",
        "titlees": "Crear Crucero",
        "titleen": "Create Cruise",
        "buttonlabel": "Nuevo Crucero",
        "key": "btncrearcruceroopen",
        "action": lambda: openpanel("crucero"),
    },
    {
        "cardclass": "card-nueva-agencia",
        "icon": "🏢",
        "titlees": "Añadir Agencia",
        "titleen": "New Agency",
        "buttonlabel": "Añadir Agencia",
        "key": "btnnuevaagencia",
        "action": lambda: openpanel("nuevaagencia"),
    },
    {
        "cardclass": "card-nuevobarco",
        "icon": "🛳️",
        "titlees": "Nuevo Barco",
        "titleen": "New Ship",
        "buttonlabel": "Abrir Nuevo Barco",
        "key": "btnnuevobarcoopen",
        "action": lambda: openpanel("nuevobarco"),
    },
]

row1_cols = st.columns([1.1, 1.1, 1.1, 1.1, 1.1, 1.1], gap="medium")
for col, card in zip(row1_cols, row1_cards):
    renderactioncard(col, card)

row2_cols = st.columns([1.1, 1.1, 1.1, 1.1, 1.1, 1.1], gap="medium")
for col, card in zip(row2_cols, row2_cards):
    renderactioncard(col, card)



if st.session_state.get("confirmstate") == "step1":
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    panelheader("Crear sesión", "closeprocesspanel")
    st.markdown(
        f'<a class="done-link" href="{st.session_state.copyurl}" target="_blank" rel="noopener noreferrer">Crear copia en Drive</a>',
        unsafe_allow_html=True,
    )
    if st.button("Ya he creado la copia", key="btnconfirmcopydone"):
        st.session_state.confirmstate = "done"
        st.success("Sesión creada correctamente")
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.get("confirmstate") == "done":
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    panelheader("Crear sesión", "closeprocesspaneldone")
    st.success("Ok")
    renderkeyvaluegrid(
        "process",
        [
            ("Tipo de sesión", "MASTER CONFIRMATION" if st.session_state.get("sessiontype") == "es" else "MASTER GROUPS"),
            ("Nombre creado", st.session_state.get("nombrecopia")),
            ("Usuario", DISPLAYUSER),
            ("Estado", "Creada correctamente"),
        ],
    )
    if st.session_state.get("copyurl"):
        st.markdown(
            f'<a class="done-link" href="{st.session_state.copyurl}" target="_blank" rel="noopener noreferrer">Abrir sesión creada</a>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.get("opensalidaform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    panelheader("Seleccionar salida / Select departure", "closesalidapanel")
    try:
        years = getyears()
        currentyear = st.session_state.get("salidayear")
        if currentyear not in years:
            currentyear = None
        selectedyear = st.selectbox("AÑO / YEAR", options=years,
            index=years.index(currentyear) if currentyear in years else None,
            placeholder="Selecciona un año / Select a year",
            key="salidayearwidget", on_change=onyearchange)
        if selectedyear != st.session_state.get("salidayear"):
            st.session_state.salidayear = selectedyear
        boats = getboats(selectedyear) if selectedyear else []
        currentboat = st.session_state.get("salidaboat")
        if currentboat not in boats:
            currentboat = None
        selectedboat = st.selectbox("BARCO / SHIP", options=boats,
            index=boats.index(currentboat) if currentboat in boats else None,
            placeholder="Selecciona un barco / Select a ship",
            key="salidaboatwidget", on_change=onboatchange, disabled=not selectedyear)
        if selectedboat != st.session_state.get("salidaboat"):
            st.session_state.salidaboat = selectedboat
        departures = getdepartures(selectedyear, selectedboat) if selectedyear and selectedboat else []
        departurenames = [d["nombre"] for d in departures]
        currentdeparture = st.session_state.get("salidaname")
        if currentdeparture not in departurenames:
            currentdeparture = None
        selecteddeparture = st.selectbox("SALIDA / DEPARTURE", options=departurenames,
            index=departurenames.index(currentdeparture) if currentdeparture in departurenames else None,
            placeholder="Selecciona una salida / Select a departure",
            key="salidanamewidget", on_change=onsalidachange, disabled=not selectedboat)
        if selecteddeparture != st.session_state.get("salidaname"):
            st.session_state.salidaname = selecteddeparture
        if selecteddeparture:
            selectedobj = next((d for d in departures if d["nombre"] == selecteddeparture), None)
            if selectedobj:
                st.markdown(
                    f'<a class="done-link" href="{selectedobj["url"]}" target="_blank" rel="noopener noreferrer">Abrir salida / Open departure</a>',
                    unsafe_allow_html=True,
                )
    except Exception as exc:
        st.exception(exc)
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.get("opencruceroform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    panelheader("Crear crucero / Create cruise", "closecruceropanel")
    try:
        years = getyears()
        currentcyear = st.session_state.get("cruceroyear")
        if currentcyear not in years:
            currentcyear = None
        cruceroyear = st.selectbox("AÑO DESTINO / TARGET YEAR", options=years,
            index=years.index(currentcyear) if currentcyear in years else None,
            placeholder="Selecciona un año / Select a year",
            key="cruceroyearwidget", on_change=oncruceroyearchange)
        if cruceroyear != st.session_state.get("cruceroyear"):
            st.session_state.cruceroyear = cruceroyear
        cruceroboats = getboats(cruceroyear) if cruceroyear else []
        currentcboat = st.session_state.get("cruceroboat")
        if currentcboat not in cruceroboats:
            currentcboat = None
        cruceroboat = st.selectbox("BARCO / SHIP", options=cruceroboats,
            index=cruceroboats.index(currentcboat) if currentcboat in cruceroboats else None,
            placeholder="Selecciona un barco / Select a ship",
            key="cruceroboatwidget", on_change=oncruceroboatchange, disabled=not cruceroyear)
        if cruceroboat != st.session_state.get("cruceroboat"):
            st.session_state.cruceroboat = cruceroboat
        fechasalida = st.date_input("FECHA DE SALIDA / DEPARTURE DATE", value=date.today(), format="DD/MM/YYYY")
        if cruceroboat and fechasalida:
            previewname = f"{cruceroboat}{fechasalida.strftime('%y%m%d')}"
            st.caption(f"Nombre previsto / Expected name: {previewname}")
        if st.button("Crear Crucero", key="btncrearcruceroaction", disabled=not (cruceroyear and cruceroboat and fechasalida)):
            if int(cruceroyear) != fechasalida.year:
                st.error("El año seleccionado no coincide con el año de la fecha / Selected year does not match the date year.")
            else:
                safeaudit("request_create_cruise", f"Petición crear crucero: {cruceroboat} {fechasalida}", panel="crucero", extra={"request_type": "create_cruise"})
                result = createcrucerofile(cruceroboat, fechasalida)
                if result["status"] == "duplicate":
                    st.warning(f"Ya existe / Already exists: {result['name']}")
                    st.markdown(f'<a class="done-link" href="{result["url"]}" target="_blank" rel="noopener noreferrer">Abrir archivo existente / Open existing file</a>', unsafe_allow_html=True)
                else:
                    st.success(f"Archivo creado / File created: {result['name']}")
                    st.markdown(f'<a class="done-link" href="{result["url"]}" target="_blank" rel="noopener noreferrer">Abrir crucero / Open cruise</a>', unsafe_allow_html=True)
    except Exception as exc:
        st.exception(exc)
    st.markdown("</div>", unsafe_allow_html=True)




if st.session_state.get("opennuevaagenciaform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    panelheader("Nueva Agencia / New Agency", "closenuevaagenciapanel")
    with st.form("formnuevaagencia", clear_on_submit=False):
        rowa1, rowa2 = st.columns(2, gap="medium")
        with rowa1:
            agnombre = st.text_input("Nombre", key="agnombre")
        with rowa2:
            agcodigo = st.text_input("CODIGO", key="agcodigo")
        rowb1, rowb2 = st.columns(2, gap="medium")
        with rowb1:
            aggrupogest = st.text_input("Grupo Gest", key="aggrupogest")
        with rowb2:
            agtelefono = st.text_input("Telefono", key="agtelefono")
        rowc1, rowc2 = st.columns(2, gap="medium")
        with rowc1:
            agemail = st.text_input("Email", key="agemail")
        with rowc2:
            agdireccion = st.text_input("Direccion", key="agdireccion")
        st.markdown("#### Comisiones e IVA")
        rowd1, rowd2, rowd3 = st.columns(3, gap="medium")
        with rowd1:
            agcomision = st.number_input("COMISION AGENCIA %", min_value=0.0, max_value=100.0, value=0.0, step=0.5, format="%.2f", key="agcomision")
        with rowd2:
            agcomisionoferta = st.number_input("COMISION AGENCIA CON OFERTA %", min_value=0.0, max_value=100.0, value=0.0, step=0.5, format="%.2f", key="agcomisionoferta")
        with rowd3:
            agcomision2x1 = st.number_input("COMISION AGENCIA OFERTA 2X1 %", min_value=0.0, max_value=100.0, value=0.0, step=0.5, format="%.2f", key="agcomision2x1")
        rowe1, rowe2 = st.columns(2, gap="medium")
        with rowe1:
            agiva = st.number_input("IVA %", min_value=0.0, max_value=100.0, value=21.0, step=0.5, format="%.2f", key="agiva")
        with rowe2:
            agivaservicioopcional = st.number_input("IVA SERVICIO OPCIONAL %", min_value=0.0, max_value=100.0, value=21.0, step=0.5, format="%.2f", key="agivaservicioopcional")
        guardaragencia = st.form_submit_button("Guardar Agencia")
        if guardaragencia:
            if not agnombre.strip():
                st.error("El campo Nombre es obligatorio.")
            elif not agcodigo.strip():
                st.error("El campo CODIGO es obligatorio.")
            else:
                agencydata = {
                    "Nombre": agnombre.strip(), "CODIGO": agcodigo.strip(),
                    "Grupo Gest": aggrupogest.strip(), "Telefono": agtelefono.strip(),
                    "Email": agemail.strip(), "Direccion": agdireccion.strip(),
                    "COMISION AGENCIA": percenttosheetdecimal(agcomision),
                    "COMISION AGENCIA CON OFERTA ": percenttosheetdecimal(agcomisionoferta),
                    "COMISION AGENCIA OFERTA 2X1 ": percenttosheetdecimal(agcomision2x1),
                    "IVA": percenttosheetdecimal(agiva),
                    "IVA SERVICIO OPCIONAL": percenttosheetdecimal(agivaservicioopcional),
                }
                try:
                    appendagencyrow(agencydata)
                    st.success(f"Agencia guardada correctamente: {agencydata['Nombre']}")
                except Exception as exc:
                    st.exception(exc)
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.get("openbuscaragenciaform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    panelheader("Buscar Agencia / Find Agency", "closebuscaragenciapanel")
    searchquery = st.text_input(
        "Introduce lo que sepas: nombre, código, grupo, teléfono, email o dirección",
        key="agencysearchquery",
        placeholder="Ej: Viajes Pepe, AG123, 912345678, info@...",
    )
    if st.button("Buscar coincidencias", key="btnejecutarbusquedaagencia"):
        try:
            st.session_state.agencymatches = searchagencies(searchquery)
            st.session_state.agencyselectedidx = None
        except Exception as exc:
            st.exception(exc)
    matches = st.session_state.get("agencymatches", [])
    if searchquery and not matches:
        st.info("No hay coincidencias.")
    selectedagency = None
    if len(matches) == 1:
        st.success("Se ha encontrado 1 coincidencia.")
        selectedagency = matches[0]
    elif len(matches) > 1:
        st.warning(f"Hay {len(matches)} coincidencias. Selecciona la correcta.")
        options = [f"{i+1}. {ag['Nombre']} · {ag['CODIGO']} · {ag['Telefono']} · {ag['Email']}" for i, ag in enumerate(matches)]
        selectedlabel = st.selectbox("Elige la agencia correcta", options=options, index=None, placeholder="Selecciona una coincidencia")
        if selectedlabel:
            selectedagency = matches[options.index(selectedlabel)]
    if selectedagency:
        renderkeyvaluegrid("agency", [(field, selectedagency.get(field)) for field in AGENCYFIELDS])
    st.markdown("</div>", unsafe_allow_html=True)



if st.session_state.get("opencvcfitform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    panelheader("CVC Fit", "closecvcfitpanel")
    locator = st.text_input("Localizador", key="cvcfitlocatorwidget", placeholder="Introduce el localizador exacto de Booking ES!G11")
    if st.button("Generar PDF CVC Fit", key="btncvcfitaction", disabled=not locator):
        runcvcsearch(locator, "CVC Fit", "CVC Fit", "cvcfit")
    loglinessaved = st.session_state.get("cvcfitlog")
    if loglinessaved:
        st.markdown('<div class="cvcfit-status-card" style="margin-top:0.75rem;">', unsafe_allow_html=True)
        st.markdown("**Log de la búsqueda**")
        st.markdown("<br>".join(f'<div class="cvcfit-log-line">{line}</div>' for line in loglinessaved), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    result = st.session_state.get("cvcfitresult")
    if result:
        renderkeyvaluegrid("cvcfit", [
            ("Localizador", result.get("locator")),
            ("Nombre pasajero", result.get("nombre")),
            ("Spreadsheet", result.get("spreadsheetname")),
            ("Nombre del PDF", result.get("filename")),
        ])
        cola, colb = st.columns([1, 3], gap="small")
        with cola:
            st.download_button(label="Descargar PDF", data=result["pdfbytes"], file_name=result["filename"], mime="application/pdf", key="downloadcvcfitpdf")
        with colb:
            st.markdown(f'<a class="done-link" href="{result["spreadsheeturl"]}" target="_blank" rel="noopener noreferrer">Abrir spreadsheet</a>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.get("opencvcagenciasform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    panelheader("CVC Agencias", "closecvcagenciaspanel")
    locator = st.text_input("Localizador", key="cvcagenciaslocatorwidget", placeholder="Introduce el localizador exacto de Booking ES!G11")
    if st.button("Generar PDF CVC Agencias", key="btncvcagenciasaction", disabled=not locator):
        runcvcsearch(locator, "CVC Agencias", "CVC Agencias", "cvcagencias")
    loglinessaved = st.session_state.get("cvcagenciaslog")
    if loglinessaved:
        st.markdown('<div class="cvcagencias-status-card" style="margin-top:0.75rem;">', unsafe_allow_html=True)
        st.markdown("**Log de la búsqueda**")
        st.markdown("<br>".join(f'<div class="cvcagencias-log-line">{line}</div>' for line in loglinessaved), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    result = st.session_state.get("cvcagenciasresult")
    if result:
        renderkeyvaluegrid("cvcagencias", [
            ("Localizador", result.get("locator")),
            ("Nombre pasajero", result.get("nombre")),
            ("Spreadsheet", result.get("spreadsheetname")),
            ("Nombre del PDF", result.get("filename")),
        ])
        cola, colb = st.columns([1, 3], gap="small")
        with cola:
            st.download_button(label="Descargar PDF CVC Agencias", data=result["pdfbytes"], file_name=result["filename"], mime="application/pdf", key="downloadcvcagenciaspdf")
        with colb:
            st.markdown(f'<a class="done-link" href="{result["spreadsheeturl"]}" target="_blank" rel="noopener noreferrer">Abrir spreadsheet</a>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.get("openirconfirmacionform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    panelheader("Ir a Confirmación", "closeirconfirmacionpanel")
    locator = st.text_input("Localizador", key="irconfirmacionlocatorwidget", placeholder="Ej: ALB250601-001 o ALB250601-001_GROUP")
    if st.button("Buscar confirmación", key="btnirconfirmacionaction", disabled=not locator):
        try:
            result = findlocatorconfirmation(locator)
            st.session_state.irconfirmacionresult = result
            st.session_state.irconfirmacionlog = result.get("log", [])
        except Exception as exc:
            st.error(str(exc))
            st.session_state.irconfirmacionresult = None
            st.session_state.irconfirmacionlog = []
    loglinessaved = st.session_state.get("irconfirmacionlog")
    if loglinessaved:
        st.markdown('<div class="irconfirmacion-card" style="margin-top:0.75rem;">', unsafe_allow_html=True)
        st.markdown("**Resultado de la búsqueda**")
        st.markdown("<br>".join(f'<div class="irconfirmacion-log-line">{line}</div>' for line in loglinessaved), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    result = st.session_state.get("irconfirmacionresult")
    if result and result.get("status") == "found":
        parsed = result.get("parsed", {})
        renderkeyvaluegrid("irconfirmacion", [
            ("Localizador", parsed.get("original")),
            ("Barco", parsed.get("boatname")),
            ("Archivo", result.get("file", {}).get("name")),
            ("Pestaña", result.get("sheet", {}).get("title")),
        ])
        st.markdown(f'<a class="done-link" href="{result["url"]}" target="_blank" rel="noopener noreferrer">Abrir confirmación</a>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.get("openbuscarlientesform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    panelheader("Buscar Cliente / Find Client", "closebuscarlientespanel")

    masterclientesurl = f"https://docs.google.com/spreadsheets/d/{MASTERCLIENTESSHEETID}/edit"

    searchquery = st.text_input(
        "Busca por nombre, apellidos, documento o localizador",
        key="buscarclientes_querywidget",
        placeholder="Ej: García, 12345678A, ALB250601-001...",
    )

    if st.button("Buscar cliente", key="btnbuscarclientes_action", disabled=not searchquery):
        try:
            matches = searchclientes(searchquery)
            st.session_state.buscarclientes_matches = matches
            if not matches:
                lastmod = getmasterclienteslastmodified()
                st.session_state.buscarclientes_lastmodified = lastmod
            else:
                st.session_state.buscarclientes_lastmodified = None
        except Exception as exc:
            st.error(str(exc))
            st.session_state.buscarclientes_matches = []
            st.session_state.buscarclientes_lastmodified = None

    matches = st.session_state.get("buscarclientes_matches", [])
    lastmod = st.session_state.get("buscarclientes_lastmodified")

    if searchquery and not matches and lastmod is not None:
        st.warning(
            f"No se han encontrado resultados para «{searchquery}».\n\n"
            f"El archivo MASTER_CLIENTES fue modificado por última vez el **{lastmod}**. "
            f"Si los datos son recientes, es posible que el archivo no esté actualizado."
        )
        st.markdown(
            f'<a class="done-link" href="{masterclientesurl}" target="_blank" rel="noopener noreferrer">Abrir MASTER CLIENTES</a>',
            unsafe_allow_html=True,
        )
    elif searchquery and not matches and lastmod is None and st.session_state.get("buscarclientes_matches") == []:
        # la búsqueda ya se ejecutó pero no hay lastmod (error al obtenerlo)
        st.info("No se han encontrado resultados.")

    selectedclient = None
    if len(matches) == 1:
        st.success("Se ha encontrado 1 coincidencia.")
        selectedclient = matches[0]
    elif len(matches) > 1:
        st.warning(f"Hay {len(matches)} coincidencias. Selecciona la correcta.")
        options = [
            f"{i+1}. {c['Nombre']} {c['Apellidos']} · {c['Documento']} · {c['Localizador']}"
            for i, c in enumerate(matches)
        ]
        selectedlabel = st.selectbox(
            "Elige el cliente correcto",
            options=options,
            index=None,
            placeholder="Selecciona una coincidencia",
            key="buscarclientes_select",
        )
        if selectedlabel:
            selectedclient = matches[options.index(selectedlabel)]

    if selectedclient:
        renderkeyvaluegrid(
            "buscarclientes",
            [
                ("Nombre", selectedclient.get("Nombre")),
                ("Apellidos", selectedclient.get("Apellidos")),
                ("Documento", selectedclient.get("Documento")),
                ("Región", selectedclient.get("Region")),
                ("Localizador", selectedclient.get("Localizador")),
            ],
        )
        st.markdown(
            f'<a class="done-link" href="{masterclientesurl}" target="_blank" rel="noopener noreferrer">Abrir MASTER CLIENTES</a>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)



if st.session_state.get("opennuevobarcoform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    panelheader("Nuevo Barco / New Ship", "closenuevobarcopanel")
    with st.form("formnuevobarco", clear_on_submit=False):
        rownb1, rownb2 = st.columns(2, gap="medium")
        with rownb1:
            barconombre = st.text_input("Nombre de barco", key="nuevobarconombre", placeholder="Ej: MS FIDELIO")
        with rownb2:
            localizador = st.text_input("Localizador", key="nuevobarcolocalizador", placeholder="Ej: FID")
        st.markdown("#### Cabinas y categorías normalizadas")
        cabin_pairs = []
        for idx in range(1, 6):
            colcab, colcat = st.columns(2, gap="medium")
            with colcab:
                cabina = st.text_input(f"Categoria {idx}", key=f"nuevobarcocabina{idx}", placeholder="Ej: PRINCIPAL, SUPERIOR ...")
            with colcat:
                categoria = st.text_input(f"Categoría normalizada {idx}", key=f"nuevobarcocategoria{idx}", placeholder="Ej: UPP, MAIN, G UPP...")
            cabin_pairs.append((cabina, categoria))
        guardarnuevobarco = st.form_submit_button("Guardar Barco")
        if guardarnuevobarco:
            if not barconombre.strip():
                st.error("El campo Nombre de barco es obligatorio.")
            elif not localizador.strip():
                st.error("El campo Localizador es obligatorio.")
            else:
                try:
                    totalrows = save_new_boat_registry(barconombre, localizador, cabin_pairs)
                    safeaudit(
                        "save_new_boat",
                        f"Barco guardado: {barconombre.strip()} ({localizador.strip().upper()})",
                        panel="nuevobarco",
                        extra={"filas": totalrows, "requested_by": st.session_state.get("displayname", ""), "request_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                    )
                    st.success(f"Barco registrado con {totalrows} categorías. Enviado ticket para incorporacion al sistema.")
                except Exception as exc:
                    st.exception(exc)
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.get("openinformebarcoform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    panelheader("Informe por Barco", "closeinformebarcopanel")
    try:
        tipooptions = ["NORMAL", "GROUPS"]
        currenttipo = st.session_state.get("informetype")
        if currenttipo not in tipooptions:
            currenttipo = None
        st.selectbox("TIPO", options=tipooptions,
            index=tipooptions.index(currenttipo) if currenttipo in tipooptions else None,
            placeholder="Selecciona tipo", key="informetypewidget", on_change=oninformetypechange)
        selected_type = st.session_state.get("informetype")
        rootid = GROUPSROOTID if selected_type == "GROUPS" else DRIVEROOTID
        years = getyearsbyroot(rootid) if selected_type else []
        currentyear = st.session_state.get("informeyear")
        if currentyear not in years:
            currentyear = None
        st.selectbox("AÑO", options=years,
            index=years.index(currentyear) if currentyear in years else None,
            placeholder="Selecciona año", key="informeyearwidget", on_change=oninformeyearchange, disabled=not selected_type)
        selected_year = st.session_state.get("informeyear")
        boats = getboatsbyroot(rootid, selected_year) if selected_type and selected_year else []
        currentboat = st.session_state.get("informeboat")
        if currentboat not in boats:
            currentboat = None
        st.selectbox("BARCO", options=boats,
            index=boats.index(currentboat) if currentboat in boats else None,
            placeholder="Selecciona barco", key="informeboatwidget", on_change=oninformeboatchange, disabled=not selected_year)
        selected_boat = st.session_state.get("informeboat")
        departures = getdeparturesbyroot(rootid, selected_year, selected_boat) if selected_type and selected_year and selected_boat else []
        departurenames = [d["nombre"] for d in departures]
        currentdep = st.session_state.get("informesalida")
        if currentdep not in departurenames:
            currentdep = None
        st.selectbox("SALIDA", options=departurenames,
            index=departurenames.index(currentdep) if currentdep in departurenames else None,
            placeholder="Selecciona salida", key="informesalidawidget", on_change=oninformesalidachange, disabled=not selected_boat)
        selected_departure = st.session_state.get("informesalida")
        if st.button("Generar informe", key="btngenerarinforme", disabled=not selected_departure):
            try:
                selected = next((d for d in departures if d["nombre"] == selected_departure), None)
                if not selected:
                    st.error("No se ha encontrado la salida seleccionada.")
                else:
                    st.session_state.informeresult = extractinformeporbarco(selected["id"], selected["nombre"])
            except Exception as exc:
                st.exception(exc)
        informeresult = st.session_state.get("informeresult")
        if informeresult:
            renderkeyvaluegrid("informebarco", [
                ("Spreadsheet", informeresult.get("spreadsheetname")),
                ("Total PAX", str(informeresult.get("totalpax", 0))),
                ("Total Hojas", str(len(informeresult.get("rows", [])))),
                ("Total €", f"{sum(r.get('Total', 0) for r in informeresult.get('rows', [])):.2f} €"),
            ])
            rows = informeresult.get("rows", [])
            if rows:
                tablehtml = """
                <div class="report-table-wrap">
                  <table class="report-table">
                    <thead><tr>
                      <th>Localizador</th><th>Agencia</th><th>Estado</th><th>Estado Pago</th>
                      <th>Depósito</th><th>Total</th><th>PAX</th><th>Cabinas</th><th>Itinerario</th><th>Duración</th>
                    </tr></thead><tbody>
                """
                for row in rows:
                    locator = row.get("Localizador", "")
                    sheeturl = row.get("SheetUrl", "#")
                    tablehtml += f"""
                      <tr>
                        <td><a class="report-link" href="{sheeturl}" target="_blank" rel="noopener noreferrer">{locator}</a></td>
                        <td>{row.get("Agencia", "")}</td>
                        <td>{formatestadobadge(row.get("Estado"))}</td>
                        <td>{formatestadopagobadge(row.get("Estado Pago"))}</td>
                        <td>{row.get("Cantidad Deposito", 0):.2f} €</td>
                        <td>{row.get("Total", 0):.2f} €</td>
                        <td>{row.get("PAX", 0)}</td>
                        <td>{row.get("Cabinas", 0)}</td>
                        <td>{row.get("Itinerario", "")}</td>
                        <td>{row.get("Duracion", "")}</td>
                      </tr>
                    """
                tablehtml += "</tbody></table></div>"
                st.html(tablehtml)
    except Exception as exc:
        st.exception(exc)
    st.markdown("</div>", unsafe_allow_html=True)

# ── FOOTER ──
footercol1, footercol2 = st.columns([3, 1])
with footercol1:
    st.markdown('<div class="portal-footer"><div class="footer-text">Crucemundo Hub</div></div>', unsafe_allow_html=True)
with footercol2:
    if st.button("Cerrar sesión", key="btnlogout"):
        dologout()

st.markdown("</div>", unsafe_allow_html=True)
