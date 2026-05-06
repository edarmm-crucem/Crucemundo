# ************************************************************
# ******************** 1. IMPORTS ****************************
# ************************************************************
import streamlit as st
from datetime import datetime, date
import urllib.parse
import time
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import requests


# ************************************************************
# **************** 2. CONFIGURACION APP **********************
# ************************************************************
st.set_page_config(
    page_title="Crucemundo Hub",
    page_icon="🛳️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ************************************************************
# *************** 3. CONSTANTES Y IDS ************************
# ************************************************************
LOGO_ID = "1N7eaCKP1Jeg8KuDXRjJ8tZLhnKStMZ8"
LOGO_URL = f"https://lh3.googleusercontent.com/d/{LOGO_ID}"

TEMPLATE_ID_ES = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
TEMPLATE_ID_GRUPOS = "1Z7ktX3PhVkMibWpzdrDDqAT4aPsmjzSJPf1SgZcL5-w"
TEMPLATE_ID_CRUCERO = "1zSJPi6St_Z5Jw1c6eieVnKI4NyEdP7E9n3WTZ9yy3C0"

EXCURSIONES_SHEET_ID = "1ojMHeoosUyel8BA2XTmDsmyDJf_vvJrrJNOyxn2u1jg"
AGENCY_SHEET_ID = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
AGENCY_SHEET_NAME = "Datos"

# Folder de sesiones / trabajo general
DRIVE_ROOT_ID = "11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm"

# Folder específico para buscar la CVC Fit
CVCFIT_FOLDER_ID = "1MxMdeBlUG6v5n2upobsjNbQNQ8F_C_sO"

VALID_USERS = {
    "support@crucemundo.com": "Albina",
    "sales@crucemundo.com": "Sales",
    "cruise@crucemundo.com": "Cruise",
    "tania@crucemundo.com": "Tania",
    "incoming@crucemundo.com": "Incoming",
    "operations@crucemundo.com": "Operations",
    "edarmm@gmail.com": "Esteban",
}
VALID_PASSWORD = st.secrets["app_password"]

AGENCY_FIELDS = [
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


# ************************************************************
# *************** 4. SESSION STATE ***************************
# ************************************************************
defaults = {
    "authenticated": False,
    "useremail": "",
    "displayname": "",
    "confirmstate": "idle",
    "historial": [],
    "sessiontype": "",
    "activepanel": None,
    "opensalidaform": False,
    "opencruceroform": False,
    "opennuevaagenciaform": False,
    "openbuscaragenciaform": False,
    "opencvcfitform": False,
    "salidayear": None,
    "salidaboat": None,
    "salidaname": None,
    "cruceroyear": None,
    "cruceroboat": None,
    "agencymatches": [],
    "agencyselectedidx": None,
    "cvcfit_locator": "",
    "cvcfit_result": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ************************************************************
# *************** 5. HELPERS GENERALES ***********************
# ************************************************************
def get_saludo():
    hora = datetime.now().hour
    if 6 <= hora < 14:
        return "Buenos días"
    elif 14 <= hora < 21:
        return "Buenas tardes"
    return "Buenas noches"


def get_saludo_en():
    hora = datetime.now().hour
    if 6 <= hora < 14:
        return "Good morning"
    elif 14 <= hora < 21:
        return "Good afternoon"
    return "Good evening"


def clear_salida_state():
    for k in [
        "salidayear", "salidaboat", "salidaname",
        "salidayearwidget", "salidaboatwidget", "salidanamewidget"
    ]:
        st.session_state.pop(k, None)


def clear_crucero_state():
    for k in [
        "cruceroyear", "cruceroboat",
        "cruceroyearwidget", "cruceroboatwidget"
    ]:
        st.session_state.pop(k, None)


def clear_agencia_state():
    for k in [
        "agencymatches", "agencyselectedidx", "agencysearchquery",
        "agnombre", "agcodigo", "aggrupogest", "agtelefono", "agemail",
        "agdireccion", "agcomision", "agcomisionoferta", "agcomision2x1",
        "agiva", "agivaservicioopcional"
    ]:
        st.session_state.pop(k, None)


def clear_cvcfit_state():
    for k in ["cvcfit_locator", "cvcfit_result", "cvcfitlocatorwidget"]:
        st.session_state.pop(k, None)


def close_all_panels():
    st.session_state["opensalidaform"] = False
    st.session_state["opencruceroform"] = False
    st.session_state["opennuevaagenciaform"] = False
    st.session_state["openbuscaragenciaform"] = False
    st.session_state["opencvcfitform"] = False


def open_panel(panelname):
    close_all_panels()
    if panelname == "salida":
        clear_crucero_state()
        clear_agencia_state()
        clear_cvcfit_state()
        st.session_state["opensalidaform"] = True
    elif panelname == "crucero":
        clear_salida_state()
        clear_agencia_state()
        clear_cvcfit_state()
        st.session_state["opencruceroform"] = True
    elif panelname == "nuevaagencia":
        clear_salida_state()
        clear_crucero_state()
        clear_agencia_state()
        clear_cvcfit_state()
        st.session_state["opennuevaagenciaform"] = True
    elif panelname == "buscaragencia":
        clear_salida_state()
        clear_crucero_state()
        clear_agencia_state()
        clear_cvcfit_state()
        st.session_state["openbuscaragenciaform"] = True
    elif panelname == "cvcfit":
        clear_salida_state()
        clear_crucero_state()
        clear_agencia_state()
        clear_cvcfit_state()
        st.session_state["opencvcfitform"] = True
    st.session_state["activepanel"] = panelname


def clear_all_selectors():
    clear_salida_state()
    clear_crucero_state()
    clear_agencia_state()
    clear_cvcfit_state()
    close_all_panels()
    st.session_state["activepanel"] = None


def do_logout():
    keys_to_delete = [
        "authenticated", "useremail", "displayname", "confirmstate", "sessiontype",
        "activepanel", "opensalidaform", "opencruceroform", "opennuevaagenciaform",
        "openbuscaragenciaform", "opencvcfitform",
        "salidayear", "salidaboat", "salidaname", "cruceroyear", "cruceroboat",
        "salidayearwidget", "salidaboatwidget", "salidanamewidget",
        "cruceroyearwidget", "cruceroboatwidget",
        "nombrecopia", "copyurl", "processtitle",
        "agencymatches", "agencyselectedidx", "agencysearchquery",
        "agnombre", "agcodigo", "aggrupogest", "agtelefono", "agemail",
        "agdireccion", "agcomision", "agcomisionoferta", "agcomision2x1",
        "agiva", "agivaservicioopcional",
        "cvcfit_locator", "cvcfit_result", "cvcfitlocatorwidget"
    ]
    for k in keys_to_delete:
        st.session_state.pop(k, None)
    st.rerun()


def render_step(label, detail, state):
    dot_class = {"done": "sd-done", "active": "sd-active", "wait": "sd-wait"}[state]
    text_class = {"done": "st-done", "active": "st-active", "wait": "st-wait"}[state]
    symbol = {"done": "✓", "active": "•", "wait": "•"}[state]
    st.markdown(
        f"""
        <div class="step">
            <div class="step-dot {dot_class}">{symbol}</div>
            <div class="step-content">
                <div class="{text_class}">{label}</div>
                <div class="step-detail">{detail}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def iniciar_proceso(sessiontype, templateid, prefixname, processtitle):
    clear_all_selectors()
    now = datetime.now()
    fechastr = now.strftime("%Y%m%d-%H%M")
    displayuser = st.session_state.get("displayname", "").strip() or "Sin usuario"
    nombrecopia = f"SESION - {displayuser} - {prefixname} - {fechastr}"
    copyurl = (
        f"https://docs.google.com/spreadsheets/d/{templateid}/copy"
        f"?copyDestination={DRIVE_ROOT_ID}"
        f"&title={urllib.parse.quote(nombrecopia)}"
    )
    st.session_state["confirmstate"] = "step1"
    st.session_state["sessiontype"] = sessiontype
    st.session_state["nombrecopia"] = nombrecopia
    st.session_state["copyurl"] = copyurl
    st.session_state["processtitle"] = processtitle
    st.rerun()


def reset_salida_downstream(level):
    if level == "year":
        st.session_state["salidaboat"] = None
        st.session_state["salidaname"] = None
        st.session_state.pop("salidaboatwidget", None)
        st.session_state.pop("salidanamewidget", None)
    elif level == "boat":
        st.session_state["salidaname"] = None
        st.session_state.pop("salidanamewidget", None)


def on_year_change():
    st.session_state["salidayear"] = st.session_state.get("salidayearwidget")
    reset_salida_downstream("year")


def on_boat_change():
    st.session_state["salidaboat"] = st.session_state.get("salidaboatwidget")
    reset_salida_downstream("boat")


def on_salida_change():
    st.session_state["salidaname"] = st.session_state.get("salidanamewidget")


def reset_crucero_downstream(level):
    if level == "year":
        st.session_state["cruceroboat"] = None
        st.session_state.pop("cruceroboatwidget", None)


def on_crucero_year_change():
    st.session_state["cruceroyear"] = st.session_state.get("cruceroyearwidget")
    reset_crucero_downstream("year")


def on_crucero_boat_change():
    st.session_state["cruceroboat"] = st.session_state.get("cruceroboatwidget")


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def normalize_phone(value):
    if value is None:
        return ""
    return re.sub(r"\D", "", str(value))


def percent_to_sheet_decimal(value):
    if value is None:
        return ""
    return round(float(value) / 100, 4)


def safe_filename(text):
    text = re.sub(r'[\\/:*?"<>|]', "", str(text))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def first_line(value):
    if value is None:
        return ""
    return str(value).splitlines()[0].strip()


# ************************************************************
# *************** 6. GOOGLE AUTH / SERVICES ******************
# ************************************************************
@st.cache_resource
def get_google_creds():
    if "gcp_service_account" not in st.secrets:
        raise Exception("Falta gcp_service_account en secrets.")
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )


@st.cache_resource
def get_drive_service():
    creds = get_google_creds()
    return build("drive", "v3", credentials=creds)


@st.cache_resource
def get_sheets_service():
    creds = get_google_creds()
    return build("sheets", "v4", credentials=creds)


# ************************************************************
# *************** 7. DRIVE / SHEETS HELPERS ******************
# ************************************************************
def list_folder_items(parentid, folders_only=False):
    service = get_drive_service()
    q = f"'{parentid}' in parents and trashed=false"
    if folders_only:
        q += " and mimeType='application/vnd.google-apps.folder'"
    results = []
    pagetoken = None
    while True:
        response = service.files().list(
            q=q,
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


def list_spreadsheets_in_folder_recent_first(folder_id):
    service = get_drive_service()
    q = (
        f"'{folder_id}' in parents and trashed=false "
        "and mimeType='application/vnd.google-apps.spreadsheet'"
    )
    results = []
    pagetoken = None
    while True:
        response = service.files().list(
            q=q,
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


def find_child_folder(parentid, foldername):
    folders = list_folder_items(parentid, folders_only=True)
    for f in folders:
        if f["name"].strip() == foldername.strip():
            return f
    return None


def create_folder(parentid, foldername):
    service = get_drive_service()
    body = {
        "name": foldername,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parentid],
    }
    return service.files().create(
        body=body,
        fields="id, name",
        supportsAllDrives=True,
    ).execute()


def get_or_create_folder(parentid, foldername):
    existing = find_child_folder(parentid, foldername)
    if existing:
        return existing
    return create_folder(parentid, foldername)


def find_file_by_name(parentid, filename):
    items = list_folder_items(parentid, folders_only=False)
    for f in items:
        if f["name"].strip() == filename.strip():
            return f
    return None


def copy_file_to_folder(fileid, newname, parentfolderid, description=None):
    service = get_drive_service()
    body = {"name": newname, "parents": [parentfolderid]}
    if description:
        body["description"] = description
    return service.files().copy(
        fileId=fileid,
        body=body,
        fields="id, name, webViewLink",
        supportsAllDrives=True,
    ).execute()


def update_crucero_sheet(spreadsheetid, barco):
    sheetsservice = get_sheets_service()
    spreadsheet = sheetsservice.spreadsheets().get(
        spreadsheetId=spreadsheetid
    ).execute()
    sheets = spreadsheet.get("sheets", [])
    if not sheets:
        raise Exception("El spreadsheet no contiene hojas.")
    firstsheet = sheets[0]
    firstsheetid = firstsheet["properties"]["sheetId"]
    firstsheettitle = firstsheet["properties"]["title"]

    sheetsservice.spreadsheets().values().update(
        spreadsheetId=spreadsheetid,
        range=f"{firstsheettitle}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": [[barco]]},
    ).execute()

    sheetsservice.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheetid,
        body={
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": firstsheetid,
                            "title": barco,
                        },
                        "fields": "title",
                    }
                }
            ]
        },
    ).execute()


def append_agency_row(agencydata):
    sheetsservice = get_sheets_service()
    values = [[
        agencydata.get("Nombre", ""),
        agencydata.get("CODIGO", ""),
        agencydata.get("Grupo Gest", ""),
        agencydata.get("Telefono", ""),
        agencydata.get("Email", ""),
        agencydata.get("Direccion", ""),
        agencydata.get("COMISION AGENCIA", ""),
        agencydata.get("COMISION AGENCIA CON OFERTA ", ""),
        agencydata.get("COMISION AGENCIA OFERTA 2X1 ", ""),
        agencydata.get("IVA", ""),
        agencydata.get("IVA SERVICIO OPCIONAL", ""),
    ]]
    sheetsservice.spreadsheets().values().append(
        spreadsheetId=AGENCY_SHEET_ID,
        range=f"{AGENCY_SHEET_NAME}!A:K",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()


def get_agencies():
    sheetsservice = get_sheets_service()
    response = sheetsservice.spreadsheets().values().get(
        spreadsheetId=AGENCY_SHEET_ID,
        range=f"{AGENCY_SHEET_NAME}!A:K",
    ).execute()
    rows = response.get("values", [])
    agencies = []
    for idx, row in enumerate(rows, start=1):
        row = row + [""] * (11 - len(row))
        data = {
            "rownumber": idx,
            "Nombre": row[0],
            "CODIGO": row[1],
            "Grupo Gest": row[2],
            "Telefono": row[3],
            "Email": row[4],
            "Direccion": row[5],
            "COMISION AGENCIA": row[6],
            "COMISION AGENCIA CON OFERTA ": row[7],
            "COMISION AGENCIA OFERTA 2X1 ": row[8],
            "IVA": row[9],
            "IVA SERVICIO OPCIONAL": row[10],
        }
        joined = " ".join([
            normalize_text(data["Nombre"]),
            normalize_text(data["CODIGO"]),
            normalize_text(data["Grupo Gest"]),
            normalize_text(data["Telefono"]),
            normalize_text(data["Email"]),
            normalize_text(data["Direccion"]),
        ])
        data["searchblob"] = joined
        data["phonenorm"] = normalize_phone(data["Telefono"])
        agencies.append(data)
    return agencies


def search_agencies(query):
    agencies = get_agencies()
    q = normalize_text(query)
    qphone = normalize_phone(query)
    if not q and not qphone:
        return []
    matches = []
    for ag in agencies:
        if q and q in ag["searchblob"]:
            matches.append(ag)
            continue
        if qphone and qphone in ag["phonenorm"]:
            matches.append(ag)
    return matches


@st.cache_data(ttl=300)
def get_years():
    folders = list_folder_items(DRIVE_ROOT_ID, folders_only=True)
    years = [f["name"].strip() for f in folders if re.fullmatch(r"\d{4}", f["name"].strip())]
    return sorted(years, reverse=True)


@st.cache_data(ttl=300)
def get_year_folder_id(yearname):
    folder = find_child_folder(DRIVE_ROOT_ID, yearname)
    return folder["id"] if folder else None


@st.cache_data(ttl=300)
def get_boats(yearname):
    yearfolderid = get_year_folder_id(yearname)
    if not yearfolderid:
        return []
    folders = list_folder_items(yearfolderid, folders_only=True)
    boats = sorted([f["name"].strip() for f in folders if f["name"].strip()])
    return boats


@st.cache_data(ttl=300)
def get_departures(yearname, boatname):
    yearfolderid = get_year_folder_id(yearname)
    if not yearfolderid:
        return []
    boatfolder = find_child_folder(yearfolderid, boatname)
    if not boatfolder:
        return []
    files = list_folder_items(boatfolder["id"], folders_only=False)
    pattern = re.compile(rf"^{re.escape(boatname)}_\d{{6}}$")
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


def create_crucero_file(barco, fechaobj):
    if not barco or not fechaobj:
        raise Exception("Faltan datos de barco o fecha.")
    anio = str(fechaobj.year)
    yy = fechaobj.strftime("%y")
    mm = fechaobj.strftime("%m")
    dd = fechaobj.strftime("%d")
    fechaes = fechaobj.strftime("%d/%m/%Y")
    nombrenuevo = f"{barco}_{yy}{mm}{dd}"

    carpetaanio = get_or_create_folder(DRIVE_ROOT_ID, anio)
    carpetabarco = get_or_create_folder(carpetaanio["id"], barco)

    duplicado = find_file_by_name(carpetabarco["id"], nombrenuevo)
    if duplicado:
        return {
            "status": "duplicate",
            "name": nombrenuevo,
            "url": duplicado.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{duplicado['id']}/edit",
        }

    descripcion = (
        f"Barco: {barco} | Salida: {fechaes} | "
        f"Creado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | "
        f"Los archivos de sesión deben borrarse a los 30 días."
    )
    copia = copy_file_to_folder(TEMPLATE_ID_CRUCERO, nombrenuevo, carpetabarco["id"], descripcion)
    spreadsheetid = copia["id"]
    update_crucero_sheet(spreadsheetid, barco)

    get_years.clear()
    get_year_folder_id.clear()
    get_boats.clear()
    get_departures.clear()

    return {
        "status": "created",
        "name": nombrenuevo,
        "url": copia.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{copia['id']}/edit",
        "year": anio,
        "boat": barco,
    }


# ************************************************************
# *************** 8. CVC FIT NUEVO ***************************
# ************************************************************
def get_sheet_titles_with_ids(spreadsheet_id):
    sheetsservice = get_sheets_service()
    spreadsheet = sheetsservice.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    result = []
    for s in spreadsheet.get("sheets", []):
        props = s.get("properties", {})
        result.append({
            "title": props.get("title", ""),
            "sheetId": props.get("sheetId"),
        })
    return result


def get_single_cell(spreadsheet_id, sheet_title, a1):
    sheetsservice = get_sheets_service()
    values = sheetsservice.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_title}'!{a1}",
        majorDimension="ROWS",
    ).execute().get("values", [])
    if values and values[0]:
        return values[0][0]
    return ""


def export_sheet_pdf_bytes(spreadsheet_id, gid):
    creds = get_google_creds()
    if not creds.valid:
        creds.refresh(Request())

    export_url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export"
        f"?format=pdf"
        f"&gid={gid}"
        f"&size=A4"
        f"&portrait=true"
        f"&fitw=true"
        f"&scale=4"
        f"&sheetnames=false"
        f"&printtitle=false"
        f"&pagenumbers=false"
        f"&gridlines=false"
        f"&fzr=false"
        f"&top_margin=0.50"
        f"&bottom_margin=0.50"
        f"&left_margin=0.50"
        f"&right_margin=0.50"
    )

    headers = {"Authorization": f"Bearer {creds.token}"}
    response = requests.get(export_url, headers=headers, timeout=60)
    response.raise_for_status()
    return response.content


def build_cvc_fit_pdf_from_locator(locator):
    locator_clean = str(locator).strip()
    if not locator_clean:
        raise Exception("Debes introducir un localizador.")

    spreadsheets = list_spreadsheets_in_folder_recent_first(CVCFIT_FOLDER_ID)
    if not spreadsheets:
        raise Exception("No se han encontrado Google Sheets en el folder indicado.")

    for file in spreadsheets:
        spreadsheet_id = file["id"]

        try:
            sheet_map = get_sheet_titles_with_ids(spreadsheet_id)
            titles = {s["title"]: s["sheetId"] for s in sheet_map}

            if "BOOKING ES" not in titles:
                continue
            if "CVC Fit" not in titles:
                continue

            g11_value = first_line(get_single_cell(spreadsheet_id, "BOOKING ES", "G11")).strip()
            if g11_value != locator_clean:
                continue

            nombre = first_line(get_single_cell(spreadsheet_id, "BOOKING ES", "G24"))
            nombre_safe = safe_filename(nombre if nombre else "Sin nombre")
            pdf_name = safe_filename(f"CVC Fit {nombre_safe} {locator_clean}.pdf")

            pdf_bytes = export_sheet_pdf_bytes(spreadsheet_id, titles["CVC Fit"])

            return {
                "locator": locator_clean,
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": file["name"],
                "spreadsheet_url": file.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
                "nombre": nombre,
                "filename": pdf_name,
                "pdf_bytes": pdf_bytes,
            }

        except Exception:
            continue

    raise Exception("No se ha encontrado el localizador en BOOKING ES!G11 de ningún Sheet del folder.")


# ************************************************************
# *************** 9. ESTILOS CSS *****************************
# ************************************************************
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

    * { box-sizing: border-box; }
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        background: #FFFFFF !important;
    }
    [data-testid="stAppViewContainer"] { background: #FFFFFF !important; }
    [data-testid="stHeader"] { background: transparent !important; }
    section[data-testid="stSidebar"] { display: none !important; }

    .block-container, section.stMain > .block-container, .stMainBlockContainer, [data-testid="stMainBlockContainer"] {
        padding-top: 0rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 1900px !important;
        margin: 0 auto !important;
    }

    .login-page { min-height: auto; display: flex; align-items: flex-start; justify-content: center; padding: 0.2rem 1rem 1rem; }
    .login-shell { width: 100%; max-width: 390px; margin: 0 auto; }
    .login-head { text-align: center; margin-bottom: 0.55rem; }
    .login-logo { height: 56px; width: auto; margin: 0 auto 0.65rem auto; display: block; }
    .login-title { font-size: 1.08rem; font-weight: 700; color: #1F2937; }
    .login-subtitle { font-size: 0.78rem; color: #7C869D; margin-top: 0.28rem; }
    .login-form-box { background: transparent !important; border: none !important; padding: 0 !important; }
    .login-note { margin-top: 0.65rem; text-align: center; font-size: 0.72rem; color: #8A93A5; }

    div[data-testid="stTextInput"] label,
    div[data-testid="stSelectbox"] label,
    div[data-testid="stDateInput"] label,
    div[data-testid="stNumberInput"] label {
        color: #4D576D !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
    }

    div[data-testid="stTextInput"] input,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    div[data-testid="stDateInput"] input,
    div[data-testid="stNumberInput"] input {
        background: #F8FAFC !important;
        border: 1px solid #E5EAF2 !important;
        border-radius: 12px !important;
        color: #1F2937 !important;
    }

    div.stButton { width: fit-content !important; }
    div.stButton button,
    div[data-testid="stFormSubmitButton"] button,
    .logout-btn div button,
    .download-btn button {
        color: #214D92 !important;
        border: 1px solid rgba(33,77,146,0.14) !important;
        border-radius: 999px !important;
        min-height: 38px !important;
        padding: 0 1.15rem !important;
        font-size: 0.76rem !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }

    .portal-header {
        padding: 0.1rem 0 0.55rem 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 0.55rem;
    }

    .portal-header-left { display: flex; align-items: center; gap: 0.9rem; }
    .portal-logo { height: 42px; width: auto; object-fit: contain; display: block; }
    .portal-title, .portal-title-en {
        font-size: 0.96rem; font-weight: 700; color: #1F2937; line-height: 1.15;
    }
    .portal-title-en { margin-top: 0.12rem; }
    .portal-subtitle, .portal-subtitle-en {
        font-size: 0.72rem; color: #7C869D; line-height: 1.2;
    }
    .portal-subtitle { margin-top: 0.12rem; }
    .portal-subtitle-en { margin-top: 0.08rem; }
    .user-top { font-size: 0.72rem; color: #566079; white-space: nowrap; }

    .main-content { padding: 0; }
    .section-head-row {
        display: flex; align-items: center; justify-content: flex-start;
        gap: 0.55rem; margin-bottom: 0.75rem; flex-wrap: wrap;
    }
    .section-head-row-green {
        display: flex; align-items: center; justify-content: flex-start;
        gap: 0.55rem; margin-top: -0.15rem; margin-bottom: 0.75rem; flex-wrap: wrap;
    }
    .section-eyebrow {
        display: inline-flex; align-items: center; padding: 0.34rem 0.74rem;
        border-radius: 999px; background: #EAF1FF; border: 1px solid #D6E3FF;
        color: #2E5FB8; font-size: 0.66rem; font-weight: 700;
        letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0 !important;
    }
    .web-chip {
        display: inline-flex; align-items: center; justify-content: center;
        padding: 0.34rem 0.74rem; border-radius: 999px; background: #FFF3BF;
        border: 1px solid #F4D35E; color: #7A5900 !important; font-size: 0.70rem;
        font-weight: 700; line-height: 1; text-decoration: none; white-space: nowrap;
    }
    .web-chip-green {
        display: inline-flex; align-items: center; justify-content: center;
        padding: 0.34rem 0.74rem; border-radius: 999px; background: #E9F8EE;
        border: 1px solid #BEE3C8; color: #1E6B3A !important; font-size: 0.70rem;
        font-weight: 700; line-height: 1; text-decoration: none; white-space: nowrap;
    }
    .user-pill {
        display: inline-flex; align-items: center; gap: 0.4rem; margin: 0.02rem 0 1rem;
        padding: 0.38rem 0.68rem; border-radius: 999px; background: #fff;
        border: 1px solid #E4E7EF; font-size: 0.72rem; color: #5D6880;
        max-width: 100%; word-break: break-word;
    }

    .action-box {
        width: 100%; min-height: 210px; border-radius: 22px; padding: 1rem;
        margin-bottom: 0.85rem; display: flex; flex-direction: column;
        justify-content: space-between; gap: 0.9rem; border: 1px solid transparent;
    }

    .card-es { background: #F3F7FF; border-color: #D9E5FF; }
    .card-grupos { background: #F4FBF6; border-color: #D8EEDC; }
    .card-salida { background: #FFF8F1; border-color: #F1DFC7; }
    .card-crucero { background: #F7F4FF; border-color: #E4DDF9; }
    .card-excursiones { background: #EEF8FB; border-color: #D5EAF1; }
    .card-nueva-agencia { background: #F1FAF4; border-color: #D7EEDC; }
    .card-buscar-agencia { background: #FFF7EF; border-color: #F4E1CA; }
    .card-cvcfit { background: #FFF2F7; border-color: #F4D7E3; }

    .action-top { display: flex; align-items: flex-start; gap: 0.75rem; }
    .action-icon {
        width: 38px; height: 38px; border-radius: 12px; display: flex;
        align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0;
    }
    .action-text { display: flex; flex-direction: column; gap: 0.10rem; min-width: 0; }
    .action-title, .action-title-en {
        font-size: 0.95rem; font-weight: 700; color: #1F2937; line-height: 1.1;
    }
    .action-title-en { margin-top: 0.05rem; }
    .action-desc, .action-desc-en {
        font-size: 0.73rem; color: #6F7B91; line-height: 1.28;
    }
    .action-desc { margin-top: 0.18rem; }
    .action-desc-en { margin-top: 0.04rem; }
    .action-button-wrap {
        display: flex !important; justify-content: flex-start !important;
        align-items: center !important; width: 100% !important; margin-top: 0.1rem;
    }

    .panel-inline { margin-top: 1rem; padding-top: 0.2rem; width: 100%; max-width: 1100px; }
    .done-link {
        display: inline-flex; align-items: center; gap: 0.35rem; margin-top: 0.65rem;
        background: #D9E9FF; color: #214D92 !important; border: 1px solid #BDD6FF;
        border-radius: 999px; padding: 0.42rem 0.88rem; font-size: 0.71rem;
        font-weight: 600; text-decoration: none;
    }

    .step { display: flex; align-items: flex-start; gap: 0.65rem; margin-bottom: 0.6rem; }
    .step:last-child { margin-bottom: 0; }
    .step-dot {
        width: 18px; height: 18px; border-radius: 50%; flex-shrink: 0;
        margin-top: 0.05rem; display: flex; align-items: center; justify-content: center;
        font-size: 0.55rem; font-weight: 700;
    }
    .sd-done { background: #EEF7F1; border: 1px solid #D8ECDF; color: #2E7D58; }
    .sd-active { background: #F2F4F9; border: 1px solid #DDE2EC; color: #6E778B; }
    .sd-wait { background: #F8F9FC; border: 1px solid #E6E9F0; color: #B1B8C9; }
    .step-content { display: flex; flex-direction: column; min-width: 0; flex: 1; }
    .st-done, .st-active, .st-wait { font-size: 0.76rem; }
    .st-done { color: #394255; }
    .st-active { color: #1F2937; font-weight: 600; }
    .st-wait { color: #A2ABBD; }
    .step-detail {
        font-size: 0.7rem; color: #8790A4; margin-top: 0.08rem;
        word-wrap: break-word !important; overflow-wrap: break-word !important; white-space: normal !important;
    }

    .agency-card, .cvcfit-card {
        background: #FBFCFF; border: 1px solid #E6EBF3; border-radius: 18px;
        padding: 1rem; margin-top: 0.75rem;
    }
    .agency-grid, .cvcfit-grid {
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.85rem 1rem;
    }
    .agency-item-label, .cvcfit-item-label {
        font-size: 0.68rem; color: #7E889D; text-transform: uppercase;
        letter-spacing: 0.04em; margin-bottom: 0.16rem;
    }
    .agency-item-value, .cvcfit-item-value {
        font-size: 0.8rem; color: #1F2937; line-height: 1.35; word-break: break-word;
    }

    .history-row {
        display: flex; align-items: center; gap: 0.75rem; padding: 0.28rem 0;
        margin-bottom: 0.35rem; width: 100%; max-width: 620px;
    }
    .history-num {
        width: 22px; height: 22px; border-radius: 7px; background: #F2F4F9;
        border: 1px solid #E3E7F1; display: flex; align-items: center; justify-content: center;
        font-size: 0.62rem; font-weight: 600; color: #5D6880; flex-shrink: 0;
    }
    .history-name {
        font-size: 0.75rem; color: #394255; flex: 1; word-wrap: break-word;
        overflow-wrap: break-word; white-space: normal;
    }
    .history-time { font-size: 0.68rem; color: #A2ABBD; white-space: nowrap; }
    .history-link {
        font-size: 0.71rem; color: #5D6880; text-decoration: none; font-weight: 500; white-space: nowrap;
    }

    .portal-footer {
        margin-top: 1rem; padding: 0.5rem 0 0 0; display: flex;
        justify-content: space-between; align-items: center; gap: 0.8rem; flex-wrap: wrap;
    }
    .footer-text { font-size: 0.71rem; color: #A2ABBD; }

    @media (max-width: 1600px) {
        .agency-grid, .cvcfit-grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 1300px) {
        .portal-header { flex-direction: column; align-items: flex-start; }
        .portal-footer { flex-direction: column; align-items: flex-start; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ************************************************************
# *************** 10. LOGIN **********************************
# ************************************************************
if not st.session_state["authenticated"]:
    st.markdown('<div class="login-page"><div class="login-shell">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="login-head">
            <img class="login-logo" src="{LOGO_URL}" alt="Logo">
            <div class="login-title">Acceso</div>
            <div class="login-subtitle">Access</div>
        </div>
        """,
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
            elif emailclean not in VALID_USERS:
                st.error("Usuario no autorizado / Unauthorized user.")
            elif password != VALID_PASSWORD:
                st.error("Contraseña incorrecta / Incorrect password.")
            else:
                st.session_state["authenticated"] = True
                st.session_state["useremail"] = emailclean
                st.session_state["displayname"] = VALID_USERS[emailclean]
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="login-note">El mail valida el acceso y el alias se usará para nombrar la sesión / Email validates access and the alias will be used to name the session.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()


# ************************************************************
# *************** 11. VARIABLES UI ***************************
# ************************************************************
USEREMAIL = st.session_state.get("useremail", "").strip()
DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Sin usuario"
SALUDO = get_saludo()
SALUDOEN = get_saludo_en()
confirmstate = st.session_state.get("confirmstate", "idle")
excursionesurl = f"https://docs.google.com/spreadsheets/d/{EXCURSIONES_SHEET_ID}/edit"
drive_root_url = f"https://drive.google.com/drive/folders/{DRIVE_ROOT_ID}"
cvcfit_folder_url = f"https://drive.google.com/drive/folders/{CVCFIT_FOLDER_ID}"


# ************************************************************
# *************** 12. CABECERA *******************************
# ************************************************************
st.markdown(
    f"""
    <div class="portal-header">
        <div class="portal-header-left">
            <img class="portal-logo" src="{LOGO_URL}" alt="Logo">
            <div>
                <div class="portal-title">{SALUDO}, {DISPLAYUSER}. ¿Qué hacemos hoy?</div>
                <div class="portal-title-en">{SALUDOEN}, {DISPLAYUSER}. What are we doing today?</div>
                <div class="portal-subtitle">Herramientas y automatizaciones · Backend Google Drive</div>
                <div class="portal-subtitle-en">Tools and automations · Google Drive backend</div>
            </div>
        </div>
        <div class="user-top">{DISPLAYUSER}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-content">', unsafe_allow_html=True)
st.markdown(
    """
    <div class="section-head-row">
        <div class="section-eyebrow">ACCIONES RÁPIDAS · QUICK ACTIONS</div>
        <a class="web-chip" href="https://www.crucemundo.es" target="_blank" rel="noopener noreferrer">Ir a Crucemundo</a>
        <a class="web-chip" href="https://mail.google.com" target="_blank" rel="noopener noreferrer">Gmail</a>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="section-head-row-green">
        <a class="web-chip-green" href="{drive_root_url}" target="_blank" rel="noopener noreferrer">Abrir folder raíz</a>
        <a class="web-chip-green" href="{cvcfit_folder_url}" target="_blank" rel="noopener noreferrer">Abrir folder CVC Fit</a>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(f'<div class="user-pill">{DISPLAYUSER} · {USEREMAIL}</div>', unsafe_allow_html=True)


# ************************************************************
# *************** 13. TARJETAS PRINCIPALES *******************
# ************************************************************
col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8, gap="medium")

with col1:
    st.markdown(
        f"""
        <div class="action-box card-es">
            <div class="action-top">
                <div class="action-icon">📄</div>
                <div class="action-text">
                    <div class="action-title">Nueva Confirmación</div>
                    <div class="action-title-en">New Confirmation</div>
                    <div class="action-desc">Crear sesión MASTER de trabajo para {DISPLAYUSER}</div>
                    <div class="action-desc-en">Create MASTER working session for {DISPLAYUSER}</div>
                </div>
            </div>
            <div class="action-button-wrap">
        """,
        unsafe_allow_html=True,
    )
    if confirmstate in ["idle", "done"]:
        if st.button("Crear Sesión ES", key="btncreares"):
            iniciar_proceso("es", TEMPLATE_ID_ES, "MASTER", "Estado del Proceso · Process Status · Crear Sesión MASTER/CONFIRMATION")
    else:
        st.button("Crear Sesión ES", key="btncrearesdis", disabled=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

with col2:
    st.markdown(
        f"""
        <div class="action-box card-grupos">
            <div class="action-top">
                <div class="action-icon">👥</div>
                <div class="action-text">
                    <div class="action-title">Nueva Confirmación GRUPOS</div>
                    <div class="action-title-en">New GROUPS Confirmation</div>
                    <div class="action-desc">Crear sesión MASTER GRUPOS de trabajo para {DISPLAYUSER}</div>
                    <div class="action-desc-en">Create MASTER GROUPS working session for {DISPLAYUSER}</div>
                </div>
            </div>
            <div class="action-button-wrap">
        """,
        unsafe_allow_html=True,
    )
    if confirmstate in ["idle", "done"]:
        if st.button("Crear Sesión GRUPOS", key="btncreargrupos"):
            iniciar_proceso("grupos", TEMPLATE_ID_GRUPOS, "MASTER GRUPOS", "Estado del Proceso · Process Status · Crear Sesión MASTER/GRUPOS")
    else:
        st.button("Crear Sesión GRUPOS", key="btncreargruposdis", disabled=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

with col3:
    st.markdown(
        """
        <div class="action-box card-salida">
            <div class="action-top">
                <div class="action-icon">🔎</div>
                <div class="action-text">
                    <div class="action-title">Ir a Salida</div>
                    <div class="action-title-en">Go to Departure</div>
                    <div class="action-desc">Buscar una salida existente por año, barco y código de salida</div>
                    <div class="action-desc-en">Find an existing departure by year, ship and departure code</div>
                </div>
            </div>
            <div class="action-button-wrap">
        """,
        unsafe_allow_html=True,
    )
    if st.button("Buscar Salida", key="btnirsalida"):
        open_panel("salida")
        st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

with col4:
    st.markdown(
        """
        <div class="action-box card-crucero">
            <div class="action-top">
                <div class="action-icon">🛳️</div>
                <div class="action-text">
                    <div class="action-title">Crear crucero</div>
                    <div class="action-title-en">Create Cruise</div>
                    <div class="action-desc">Crear salida nueva desde plantilla y guardarla en año/barco</div>
                    <div class="action-desc-en">Create a new departure from template and save it in year/ship</div>
                </div>
            </div>
            <div class="action-button-wrap">
        """,
        unsafe_allow_html=True,
    )
    if st.button("Nuevo Crucero", key="btncrearcruceroopen"):
        open_panel("crucero")
        st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

with col5:
    st.markdown(
        """
        <div class="action-box card-excursiones">
            <div class="action-top">
                <div class="action-icon">🧭</div>
                <div class="action-text">
                    <div class="action-title">Excursiones</div>
                    <div class="action-title-en">Excursions</div>
                    <div class="action-desc">Abrir la hoja de Excursiones</div>
                    <div class="action-desc-en">Open the Excursions sheet</div>
                </div>
            </div>
            <div class="action-button-wrap">
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<a class="done-link" href="{excursionesurl}" target="_blank" rel="noopener noreferrer">Abrir Excursiones</a>',
        unsafe_allow_html=True,
    )
    st.markdown("</div></div>", unsafe_allow_html=True)

with col6:
    st.markdown(
        """
        <div class="action-box card-nueva-agencia">
            <div class="action-top">
                <div class="action-icon">🏢</div>
                <div class="action-text">
                    <div class="action-title">Nueva Agencia</div>
                    <div class="action-title-en">New Agency</div>
                    <div class="action-desc">Crear una agencia y guardarla en la hoja Datos</div>
                    <div class="action-desc-en">Create an agency and save it in Datos sheet</div>
                </div>
            </div>
            <div class="action-button-wrap">
        """,
        unsafe_allow_html=True,
    )
    if st.button("Nueva Agencia", key="btnnuevaagencia"):
        open_panel("nuevaagencia")
        st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

with col7:
    st.markdown(
        """
        <div class="action-box card-buscar-agencia">
            <div class="action-top">
                <div class="action-icon">📇</div>
                <div class="action-text">
                    <div class="action-title">Buscar Agencia</div>
                    <div class="action-title-en">Find Agency</div>
                    <div class="action-desc">Buscar por cualquier dato y mostrar la ficha completa</div>
                    <div class="action-desc-en">Search by any known value and show the full record</div>
                </div>
            </div>
            <div class="action-button-wrap">
        """,
        unsafe_allow_html=True,
    )
    if st.button("Buscar Agencia", key="btnbuscaragencia"):
        open_panel("buscaragencia")
        st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

with col8:
    st.markdown(
        """
        <div class="action-box card-cvcfit">
            <div class="action-top">
                <div class="action-icon">🧾</div>
                <div class="action-text">
                    <div class="action-title">CVC Fit</div>
                    <div class="action-title-en">CVC Fit</div>
                    <div class="action-desc">Pide localizador, busca en BOOKING ES!G11 y descarga la hoja CVC Fit en PDF</div>
                    <div class="action-desc-en">Ask for locator, find it in BOOKING ES!G11 and download the CVC Fit sheet as PDF</div>
                </div>
            </div>
            <div class="action-button-wrap">
        """,
        unsafe_allow_html=True,
    )
    if st.button("Abrir CVC Fit", key="btncvcfitopen"):
        open_panel("cvcfit")
        st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)


# ************************************************************
# *************** 14. PANEL SALIDA ***************************
# ************************************************************
if st.session_state.get("opensalidaform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### Seleccionar salida · Select departure")
    try:
        years = get_years()
        currentyear = st.session_state.get("salidayear")
        if currentyear not in years:
            currentyear = None
        selectedyear = st.selectbox(
            "AÑO / YEAR",
            options=years,
            index=years.index(currentyear) if currentyear in years else None,
            placeholder="Selecciona un año / Select a year",
            key="salidayearwidget",
            on_change=on_year_change,
        )
        if selectedyear != st.session_state.get("salidayear"):
            st.session_state["salidayear"] = selectedyear

        boats = get_boats(selectedyear) if selectedyear else []
        currentboat = st.session_state.get("salidaboat")
        if currentboat not in boats:
            currentboat = None
        selectedboat = st.selectbox(
            "BARCO / SHIP",
            options=boats,
            index=boats.index(currentboat) if currentboat in boats else None,
            placeholder="Selecciona un barco / Select a ship",
            key="salidaboatwidget",
            on_change=on_boat_change,
            disabled=not selectedyear,
        )
        if selectedboat != st.session_state.get("salidaboat"):
            st.session_state["salidaboat"] = selectedboat

        departures = get_departures(selectedyear, selectedboat) if selectedyear and selectedboat else []
        departurenames = [d["nombre"] for d in departures]
        currentdeparture = st.session_state.get("salidaname")
        if currentdeparture not in departurenames:
            currentdeparture = None
        selecteddeparture = st.selectbox(
            "SALIDA / DEPARTURE",
            options=departurenames,
            index=departurenames.index(currentdeparture) if currentdeparture in departurenames else None,
            placeholder="Selecciona una salida / Select a departure",
            key="salidanamewidget",
            on_change=on_salida_change,
            disabled=not selectedboat,
        )
        if selecteddeparture != st.session_state.get("salidaname"):
            st.session_state["salidaname"] = selecteddeparture

        if selecteddeparture:
            selectedobj = next((d for d in departures if d["nombre"] == selecteddeparture), None)
            if selectedobj:
                st.markdown(
                    f'<a class="done-link" href="{selectedobj["url"]}" target="_blank" rel="noopener noreferrer">Abrir salida · Open departure</a>',
                    unsafe_allow_html=True,
                )
    except Exception as e:
        st.exception(e)
    st.markdown("</div>", unsafe_allow_html=True)


# ************************************************************
# *************** 15. PANEL CREAR CRUCERO ********************
# ************************************************************
if st.session_state.get("opencruceroform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### Crear crucero · Create cruise")
    try:
        years = get_years()
        currentcyear = st.session_state.get("cruceroyear")
        if currentcyear not in years:
            currentcyear = None
        cruceroyear = st.selectbox(
            "AÑO DESTINO / TARGET YEAR",
            options=years,
            index=years.index(currentcyear) if currentcyear in years else None,
            placeholder="Selecciona un año / Select a year",
            key="cruceroyearwidget",
            on_change=on_crucero_year_change,
        )
        if cruceroyear != st.session_state.get("cruceroyear"):
            st.session_state["cruceroyear"] = cruceroyear

        cruceroboats = get_boats(cruceroyear) if cruceroyear else []
        currentcboat = st.session_state.get("cruceroboat")
        if currentcboat not in cruceroboats:
            currentcboat = None
        cruceroboat = st.selectbox(
            "BARCO / SHIP",
            options=cruceroboats,
            index=cruceroboats.index(currentcboat) if currentcboat in cruceroboats else None,
            placeholder="Selecciona un barco / Select a ship",
            key="cruceroboatwidget",
            on_change=on_crucero_boat_change,
            disabled=not cruceroyear,
        )
        if cruceroboat != st.session_state.get("cruceroboat"):
            st.session_state["cruceroboat"] = cruceroboat

        fechasalida = st.date_input("FECHA DE SALIDA / DEPARTURE DATE", value=date.today(), format="DD/MM/YYYY")
        if cruceroboat and fechasalida:
            previewname = f"{cruceroboat}_{fechasalida.strftime('%y%m%d')}"
            st.caption(f"Nombre previsto / Expected name: {previewname}")

        if st.button("Crear Crucero", key="btncrearcruceroaction", disabled=not (cruceroyear and cruceroboat and fechasalida)):
            if int(cruceroyear) != fechasalida.year:
                st.error("El año seleccionado no coincide con el año de la fecha / Selected year does not match the date year.")
            else:
                result = create_crucero_file(cruceroboat, fechasalida)
                if result["status"] == "duplicate":
                    st.warning(f"Ya existe / Already exists: {result['name']}")
                    st.markdown(
                        f'<a class="done-link" href="{result["url"]}" target="_blank" rel="noopener noreferrer">Abrir archivo existente · Open existing file</a>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.success(f"Archivo creado / File created: {result['name']}")
                    st.markdown(
                        f'<a class="done-link" href="{result["url"]}" target="_blank" rel="noopener noreferrer">Abrir crucero · Open cruise</a>',
                        unsafe_allow_html=True,
                    )
    except Exception as e:
        st.exception(e)
    st.markdown("</div>", unsafe_allow_html=True)


# ************************************************************
# *************** 16. PANEL NUEVA AGENCIA ********************
# ************************************************************
if st.session_state.get("opennuevaagenciaform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### Nueva Agencia · New Agency")
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
                    "Nombre": agnombre.strip(),
                    "CODIGO": agcodigo.strip(),
                    "Grupo Gest": aggrupogest.strip(),
                    "Telefono": agtelefono.strip(),
                    "Email": agemail.strip(),
                    "Direccion": agdireccion.strip(),
                    "COMISION AGENCIA": percent_to_sheet_decimal(agcomision),
                    "COMISION AGENCIA CON OFERTA ": percent_to_sheet_decimal(agcomisionoferta),
                    "COMISION AGENCIA OFERTA 2X1 ": percent_to_sheet_decimal(agcomision2x1),
                    "IVA": percent_to_sheet_decimal(agiva),
                    "IVA SERVICIO OPCIONAL": percent_to_sheet_decimal(agivaservicioopcional),
                }
                try:
                    append_agency_row(agencydata)
                    st.success(f"Agencia guardada correctamente: {agencydata['Nombre']}")
                except Exception as e:
                    st.exception(e)
    st.markdown("</div>", unsafe_allow_html=True)


# ************************************************************
# *************** 17. PANEL BUSCAR AGENCIA *******************
# ************************************************************
if st.session_state.get("openbuscaragenciaform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### Buscar Agencia · Find Agency")
    searchquery = st.text_input(
        "Introduce lo que sepas (nombre, código, grupo, teléfono, email o dirección)",
        key="agencysearchquery",
        placeholder="Ej: Viajes Pepe / AG123 / 912345678 / info@...",
    )
    if st.button("Buscar coincidencias", key="btnejecutarbusquedaagencia"):
        try:
            matches = search_agencies(searchquery)
            st.session_state["agencymatches"] = matches
            st.session_state["agencyselectedidx"] = None
        except Exception as e:
            st.exception(e)

    matches = st.session_state.get("agencymatches", [])
    if searchquery and not matches:
        st.info("No hay coincidencias.")

    if len(matches) == 1:
        st.success("Se ha encontrado 1 coincidencia.")
        selectedagency = matches[0]
        st.markdown('<div class="agency-card"><div class="agency-grid">', unsafe_allow_html=True)
        for field in AGENCY_FIELDS:
            st.markdown(
                f"""
                <div>
                    <div class="agency-item-label">{field}</div>
                    <div class="agency-item-value">{selectedagency.get(field, "") or "-"}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div></div>", unsafe_allow_html=True)
    elif len(matches) > 1:
        st.warning(f"Hay {len(matches)} coincidencias. Selecciona la correcta.")
        options = [f"{i+1}. {ag['Nombre']} · {ag['CODIGO']} · {ag['Telefono']} · {ag['Email']}" for i, ag in enumerate(matches)]
        selectedlabel = st.selectbox(
            "Elige la agencia correcta",
            options=options,
            index=None,
            placeholder="Selecciona una coincidencia",
        )
        if selectedlabel:
            selectedidx = options.index(selectedlabel)
            selectedagency = matches[selectedidx]
            st.markdown('<div class="agency-card"><div class="agency-grid">', unsafe_allow_html=True)
            for field in AGENCY_FIELDS:
                st.markdown(
                    f"""
                    <div>
                        <div class="agency-item-label">{field}</div>
                        <div class="agency-item-value">{selectedagency.get(field, "") or "-"}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ************************************************************
# *************** 18. PANEL CVC FIT **************************
# ************************************************************
if st.session_state.get("opencvcfitform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### CVC Fit")
    locator = st.text_input(
        "Localizador",
        key="cvcfitlocatorwidget",
        placeholder="Introduce el localizador exacto de BOOKING ES!G11",
    )

    if st.button("Generar PDF CVC Fit", key="btncvcfitaction", disabled=not locator):
        try:
            result = build_cvc_fit_pdf_from_locator(locator)
            st.session_state["cvcfit_result"] = result
            st.success("PDF localizado y generado correctamente.")
        except Exception as e:
            st.session_state["cvcfit_result"] = None
            st.exception(e)

    result = st.session_state.get("cvcfit_result")
    if result:
        st.markdown('<div class="cvcfit-card"><div class="cvcfit-grid">', unsafe_allow_html=True)
        fields = [
            ("Localizador", result["locator"]),
            ("Nombre", result["nombre"]),
            ("Spreadsheet", result["spreadsheet_name"]),
            ("Archivo PDF", result["filename"]),
        ]
        for label, value in fields:
            st.markdown(
                f"""
                <div>
                    <div class="cvcfit-item-label">{label}</div>
                    <div class="cvcfit-item-value">{value if value not in [None, ''] else '-'}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div></div>", unsafe_allow_html=True)

        st.markdown(
            f'<a class="done-link" href="{result["spreadsheet_url"]}" target="_blank" rel="noopener noreferrer">Abrir hoja origen</a>',
            unsafe_allow_html=True,
        )

        st.download_button(
            "Descargar PDF",
            data=result["pdf_bytes"],
            file_name=result["filename"],
            mime="application/pdf",
            key="btncvcfitdownload",
        )
    st.markdown("</div>", unsafe_allow_html=True)


# ************************************************************
# *************** 19. PROCESO CONFIRMACIONES *****************
# ************************************************************
savedname = st.session_state.get("nombrecopia")
savedurl = st.session_state.get("copyurl")
processtitle = st.session_state.get("processtitle", "Estado del Proceso · Process Status")

if confirmstate in ["step1", "step2", "step3", "done"]:
    st.markdown('<div class="panel-inline" style="max-width:520px;">', unsafe_allow_html=True)
    st.markdown(f"### {processtitle}")
    if confirmstate == "step1":
        render_step("Progreso · Progress", "Preparando plantilla · Preparing template...", "active")
    elif confirmstate == "step2":
        render_step("Progreso · Progress", "Generando copia en Drive · Creating Drive copy...", "active")
    elif confirmstate == "step3":
        render_step("Progreso · Progress", "Abriendo sesión · Opening session...", "active")
    elif confirmstate == "done":
        render_step("Progreso · Progress", "Completo · Complete", "done")
        st.markdown(
            f"""
            <div style="margin-top:0.8rem;">
                <div style="font-size:0.76rem;color:#1F2937;font-weight:600;">Sesión creada · Session created</div>
                <div style="font-size:0.71rem;color:#657087;margin-top:0.15rem;line-height:1.3;">
                    Puedes abrir tu sesión en el botón de abajo · You can open your session with the button below.
                </div>
                <a class="done-link" href="{savedurl}" target="_blank" rel="noopener noreferrer">Abrir sesión · Open session</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if confirmstate == "step1":
        time.sleep(0.7)
        st.session_state["confirmstate"] = "step2"
        st.rerun()
    elif confirmstate == "step2":
        time.sleep(0.7)
        st.session_state["confirmstate"] = "step3"
        st.rerun()
    elif confirmstate == "step3":
        time.sleep(0.7)
        st.session_state["confirmstate"] = "done"
        existing = [h["nombre"] for h in st.session_state["historial"]]
        if savedname and savedname not in existing:
            st.session_state["historial"].insert(0, {
                "nombre": savedname,
                "hora": datetime.now().strftime("%H:%M:%S"),
                "url": savedurl,
            })
        st.rerun()


# ************************************************************
# *************** 20. AUTO-OPEN SESION ***********************
# ************************************************************
if confirmstate == "done" and savedname and not st.session_state.get(f"opened_{savedname}"):
    st.session_state[f"opened_{savedname}"] = True
    st.markdown(
        f"<script>setTimeout(()=>window.open('{savedurl}','_blank'),300);</script>",
        unsafe_allow_html=True,
    )


# ************************************************************
# *************** 21. LOGOUT + HISTORIAL + FOOTER ************
# ************************************************************
st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)
st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
if st.button("Cerrar sesión / Logout", key="btnlogout"):
    do_logout()
st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.get("historial"):
    st.markdown('<div style="height:1.2rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-eyebrow">ESTA SESIÓN · THIS SESSION</div>', unsafe_allow_html=True)
    for i, entry in enumerate(st.session_state["historial"], 1):
        st.markdown(
            f"""
            <div class="history-row">
                <div class="history-num">{i}</div>
                <div class="history-name">{entry["nombre"]}</div>
                <div class="history-time">{entry["hora"]}</div>
                <a class="history-link" href="{entry["url"]}" target="_blank" rel="noopener noreferrer">Abrir · Open</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown(
    f"""
    <div class="portal-footer">
        <span class="footer-text">Panel de Control · Control Panel · v4.4.0</span>
        <span class="footer-text">Raíz Drive · Drive Root · {DRIVE_ROOT_ID}</span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)
