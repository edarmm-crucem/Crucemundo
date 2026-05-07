import re
from datetime import date, datetime

import requests
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build


st.set_page_config(
    page_title="Crucemundo Hub",
    page_icon="🛳️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CONSTANTES
# ============================================================
LOGO_ID = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGO_URL = f"https://lh3.googleusercontent.com/d/{LOGO_ID}"

TEMPLATE_ID_ES = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
TEMPLATE_ID_GRUPOS = "1Z7ktX3PhVkMibWpzdrDDqAT4aPsmjzSJPf1SgZcL5-w"
TEMPLATE_ID_CRUCERO = "1zSJPi6St_Z5Jw1c6eieVnKI4NyEdP7E9n3WTZ9yy3C0"

EXCURSIONES_SHEET_ID = "1ojMHeoosUyel8BA2XTmDsmyDJf_vvJrrJNOyxn2u1jg"
AGENCY_SHEET_ID = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
AGENCY_SHEET_NAME = "Datos"
FOLDER_ID = "1MxMdeBlUG6v5n2upobsjNbQNQ8F_C_sO"
DRIVE_ROOT_ID = "11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm"
GROUPS_ROOT_ID = "1MMNH3y1E3jJIp6uUnxbwV0toAtdr2F2M"

VALID_USERS = {
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

SHIP_CODE_MAP = {
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
SHIP_CODE_TO_NAME = {v: k for k, v in SHIP_CODE_MAP.items()}

STATE_DEFAULTS = {
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
    "opencvcagenciasform": False,
    "openirconfirmacionform": False,
    "openinformebarcoform": False,
    "salidayear": None,
    "salidaboat": None,
    "salidaname": None,
    "cruceroyear": None,
    "cruceroboat": None,
    "agencymatches": [],
    "agencyselectedidx": None,
    "cvcfit_locator": "",
    "cvcfit_result": None,
    "cvcfit_log": [],
    "cvcagencias_locator": "",
    "cvcagencias_result": None,
    "cvcagencias_log": [],
    "irconfirmacion_locator": "",
    "irconfirmacion_result": None,
    "irconfirmacion_log": [],
    "informetype": None,
    "informeyear": None,
    "informeboat": None,
    "informesalida": None,
    "informeresult": None,
    "nombrecopia": "",
    "copyurl": "",
    "processtitle": "",
    "processresult": None,
}

STATE_GROUPS = {
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
        "agnombre", "agcodigo", "aggrupogest", "agtelefono", "agemail",
        "agdireccion", "agcomision", "agcomisionoferta", "agcomision2x1",
        "agiva", "agivaservicioopcional",
    ],
    "cvcfit": [
        "cvcfit_locator", "cvcfit_result", "cvcfitlocatorwidget", "cvcfit_log",
    ],
    "cvcagencias": [
        "cvcagencias_locator", "cvcagencias_result", "cvcagenciaslocatorwidget", "cvcagencias_log",
    ],
    "irconfirmacion": [
        "irconfirmacion_locator", "irconfirmacion_result", "irconfirmacionlocatorwidget", "irconfirmacion_log",
    ],
    "informebarco": [
        "informetype", "informeyear", "informeboat", "informesalida", "informeresult",
        "informetypewidget", "informeyearwidget", "informeboatwidget", "informesalidawidget",
    ],
    "process": [
        "nombrecopia", "copyurl", "processtitle", "confirmstate", "sessiontype", "processresult",
    ],
}

PANEL_FLAGS = {
    "salida": "opensalidaform",
    "crucero": "opencruceroform",
    "nuevaagencia": "opennuevaagenciaform",
    "buscaragencia": "openbuscaragenciaform",
    "cvcfit": "opencvcfitform",
    "cvcagencias": "opencvcagenciasform",
    "irconfirmacion": "openirconfirmacionform",
    "informebarco": "openinformebarcoform",
}


# ============================================================
# SESSION STATE
# ============================================================
for key, value in STATE_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# HELPERS GENERALES
# ============================================================
def get_saludo(lang="es"):
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


def normalize_text(value):
    return "" if value is None else str(value).strip().lower()


def normalize_phone(value):
    return "" if value is None else re.sub(r"\D", "", str(value))


def percent_to_sheet_decimal(value):
    return "" if value is None else round(float(value) / 100, 4)


def safe_filename(text):
    text = re.sub(r'[\\/:*?"<>|]', "", str(text))
    return re.sub(r"\s+", " ", text).strip()


def first_line(value):
    return "" if value is None else str(value).splitlines()[0].strip()


def clear_state_group(group_name):
    for key in STATE_GROUPS.get(group_name, []):
        st.session_state.pop(key, None)


def close_all_panels():
    for flag in PANEL_FLAGS.values():
        st.session_state[flag] = False


def clear_transient_ui():
    for group_name in STATE_GROUPS.keys():
        clear_state_group(group_name)
    close_all_panels()
    st.session_state["activepanel"] = None
    st.session_state["confirmstate"] = "idle"
    st.session_state["sessiontype"] = ""
    st.session_state["processresult"] = None


def clear_all_selectors():
    clear_transient_ui()


def open_panel(panel_name):
    clear_transient_ui()
    flag = PANEL_FLAGS.get(panel_name)
    if flag:
        st.session_state[flag] = True
        st.session_state["activepanel"] = panel_name


def do_logout():
    for key in list(st.session_state.keys()):
        st.session_state.pop(key, None)
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


def reset_crucero_downstream(level):
    if level == "year":
        st.session_state["cruceroboat"] = None
        st.session_state.pop("cruceroboatwidget", None)


def reset_informe_downstream(level):
    if level == "type":
        st.session_state["informeyear"] = None
        st.session_state["informeboat"] = None
        st.session_state["informesalida"] = None
        st.session_state["informeresult"] = None
        st.session_state.pop("informeyearwidget", None)
        st.session_state.pop("informeboatwidget", None)
        st.session_state.pop("informesalidawidget", None)
    elif level == "year":
        st.session_state["informeboat"] = None
        st.session_state["informesalida"] = None
        st.session_state["informeresult"] = None
        st.session_state.pop("informeboatwidget", None)
        st.session_state.pop("informesalidawidget", None)
    elif level == "boat":
        st.session_state["informesalida"] = None
        st.session_state["informeresult"] = None
        st.session_state.pop("informesalidawidget", None)


def on_year_change():
    st.session_state["salidayear"] = st.session_state.get("salidayearwidget")
    reset_salida_downstream("year")


def on_boat_change():
    st.session_state["salidaboat"] = st.session_state.get("salidaboatwidget")
    reset_salida_downstream("boat")


def on_salida_change():
    st.session_state["salidaname"] = st.session_state.get("salidanamewidget")


def on_crucero_year_change():
    st.session_state["cruceroyear"] = st.session_state.get("cruceroyearwidget")
    reset_crucero_downstream("year")


def on_crucero_boat_change():
    st.session_state["cruceroboat"] = st.session_state.get("cruceroboatwidget")


def on_informe_type_change():
    st.session_state["informetype"] = st.session_state.get("informetypewidget")
    reset_informe_downstream("type")


def on_informe_year_change():
    st.session_state["informeyear"] = st.session_state.get("informeyearwidget")
    reset_informe_downstream("year")


def on_informe_boat_change():
    st.session_state["informeboat"] = st.session_state.get("informeboatwidget")
    reset_informe_downstream("boat")


def on_informe_salida_change():
    st.session_state["informesalida"] = st.session_state.get("informesalidawidget")


def render_key_value_grid(css_prefix, fields):
    st.markdown(f'<div class="{css_prefix}-card"><div class="{css_prefix}-grid">', unsafe_allow_html=True)
    for label, value in fields:
        safe_value = value if value not in [None, ""] else "-"
        st.markdown(
            f"""
            <div>
                <div class="{css_prefix}-item-label">{label}</div>
                <div class="{css_prefix}-item-value">{safe_value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div></div>", unsafe_allow_html=True)


def create_master_session(sessiontype, templateid, prefixname, processtitle):
    clear_transient_ui()

    fechastr = datetime.now().strftime("%Y%m%d-%H%M")
    displayuser = st.session_state.get("displayname", "").strip() or "Sin usuario"
    nombrecopia = f"SESION - {displayuser} - {prefixname} - {fechastr}"
    descripcion = (
        f"Tipo: {sessiontype} | Usuario: {displayuser} | "
        f"Creado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )

    st.session_state["confirmstate"] = "running"
    st.session_state["sessiontype"] = sessiontype
    st.session_state["nombrecopia"] = nombrecopia
    st.session_state["processtitle"] = processtitle
    st.session_state["activepanel"] = "process"

    progress_bar = st.progress(0.0, text="Iniciando...")
    status_box = st.empty()

    try:
        progress_bar.progress(0.2, text="Preparando sesión...")
        status_box.info("Preparando copia en Drive...")

        progress_bar.progress(0.55, text="Creando copia en Drive...")
        copia = copy_file_to_folder(templateid, nombrecopia, FOLDER_ID, descripcion)

        final_url = copia.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{copia['id']}/edit"

        progress_bar.progress(1.0, text="Ok")
        status_box.success("Ok")

        st.session_state["copyurl"] = final_url
        st.session_state["processresult"] = {
            "status": "created",
            "name": copia.get("name", nombrecopia),
            "url": final_url,
            "id": copia.get("id", ""),
        }
        st.session_state["confirmstate"] = "done"
        st.rerun()

    except Exception as exc:
        progress_bar.empty()
        status_box.empty()
        st.session_state["confirmstate"] = "error"
        st.session_state["processresult"] = {"status": "error", "message": str(exc)}
        st.rerun()


# ============================================================
# GOOGLE AUTH / SERVICES
# ============================================================
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
    return build("drive", "v3", credentials=get_google_creds())


@st.cache_resource
def get_sheets_service():
    return build("sheets", "v4", credentials=get_google_creds())


# ============================================================
# DRIVE / SHEETS HELPERS
# ============================================================
def list_folder_items(parentid, folders_only=False):
    service = get_drive_service()
    query = f"'{parentid}' in parents and trashed=false"
    if folders_only:
        query += " and mimeType='application/vnd.google-apps.folder'"

    results = []
    page_token = None
    while True:
        response = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, webViewLink, description, createdTime, modifiedTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            pageToken=page_token,
            pageSize=1000,
            orderBy="modifiedTime desc",
        ).execute()
        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return results


def list_spreadsheets_in_folder_recent_first(folder_id):
    service = get_drive_service()
    query = (
        f"'{folder_id}' in parents and trashed=false "
        "and mimeType='application/vnd.google-apps.spreadsheet'"
    )
    results = []
    page_token = None
    while True:
        response = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, webViewLink, createdTime, modifiedTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            pageToken=page_token,
            pageSize=1000,
            orderBy="modifiedTime desc",
        ).execute()
        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return results


def find_child_folder(parentid, foldername):
    for item in list_folder_items(parentid, folders_only=True):
        if item["name"].strip() == foldername.strip():
            return item
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
    return find_child_folder(parentid, foldername) or create_folder(parentid, foldername)


def find_file_by_name(parentid, filename):
    for item in list_folder_items(parentid, folders_only=False):
        if item["name"].strip() == filename.strip():
            return item
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
    spreadsheet = sheetsservice.spreadsheets().get(spreadsheetId=spreadsheetid).execute()
    sheets = spreadsheet.get("sheets", [])
    if not sheets:
        raise Exception("El spreadsheet no contiene hojas.")

    first_sheet = sheets[0]
    first_sheet_id = first_sheet["properties"]["sheetId"]
    first_sheet_title = first_sheet["properties"]["title"]

    sheetsservice.spreadsheets().values().update(
        spreadsheetId=spreadsheetid,
        range=f"{first_sheet_title}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": [[barco]]},
    ).execute()

    sheetsservice.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheetid,
        body={
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": first_sheet_id, "title": barco},
                        "fields": "title",
                    }
                }
            ]
        },
    ).execute()


def append_agency_row(agencydata):
    sheetsservice = get_sheets_service()
    values = [[agencydata.get(field, "") for field in AGENCY_FIELDS]]
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
        data = {"rownumber": idx}
        for i, field in enumerate(AGENCY_FIELDS):
            data[field] = row[i]

        data["searchblob"] = " ".join(
            normalize_text(data[field])
            for field in ["Nombre", "CODIGO", "Grupo Gest", "Telefono", "Email", "Direccion"]
        )
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
    for agency in agencies:
        if q and q in agency["searchblob"]:
            matches.append(agency)
            continue
        if qphone and qphone in agency["phonenorm"]:
            matches.append(agency)
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
    return sorted([f["name"].strip() for f in folders if f["name"].strip()])


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
            departures.append(
                {
                    "nombre": name,
                    "id": file["id"],
                    "url": file.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{file['id']}/edit",
                }
            )
    departures.sort(key=lambda x: x["nombre"])
    return departures


def create_crucero_file(barco, fechaobj):
    if not barco or not fechaobj:
        raise Exception("Faltan datos de barco o fecha.")

    anio = str(fechaobj.year)
    nombrenuevo = f"{barco}_{fechaobj.strftime('%y%m%d')}"
    fechaes = fechaobj.strftime("%d/%m/%Y")

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
    update_crucero_sheet(copia["id"], barco)

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


# ============================================================
# CVC HELPERS
# ============================================================
def get_sheet_titles_with_ids(spreadsheet_id):
    sheetsservice = get_sheets_service()
    spreadsheet = sheetsservice.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return [
        {
            "title": sheet.get("properties", {}).get("title", ""),
            "sheetId": sheet.get("properties", {}).get("sheetId"),
        }
        for sheet in spreadsheet.get("sheets", [])
    ]


def get_single_cell(spreadsheet_id, sheet_title, a1):
    sheetsservice = get_sheets_service()
    values = sheetsservice.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_title}'!{a1}",
        majorDimension="ROWS",
    ).execute().get("values", [])
    return values[0][0] if values and values[0] else ""


def get_sheet_cells_batch(spreadsheet_id, sheet_title, a1_list):
    sheetsservice = get_sheets_service()
    ranges = [f"'{sheet_title}'!{a1}" for a1 in a1_list]
    response = sheetsservice.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id,
        ranges=ranges,
        majorDimension="ROWS",
    ).execute()
    out = {}
    for a1, vr in zip(a1_list, response.get("valueRanges", [])):
        vals = vr.get("values", [])
        out[a1] = vals[0][0] if vals and vals[0] else ""
    return out


def export_sheet_pdf_bytes(spreadsheet_id, gid):
    creds = get_google_creds().with_scopes([
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
    ])
    creds.refresh(Request())

    export_url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export"
        f"?format=pdf&gid={gid}&size=A4&portrait=true&fitw=true&fith=false"
        f"&sheetnames=false&scale=2&printtitle=false&pagenumbers=false"
        f"&gridlines=false&fzr=false&top_margin=0.50&bottom_margin=0.50"
        f"&left_margin=0.50&right_margin=0.50"
    )
    response = requests.get(
        export_url,
        headers={"Authorization": f"Bearer {creds.token}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.content


def build_cvc_pdf_from_locator(locator, target_sheet, pdf_prefix):
    locator_clean = str(locator).strip()
    if not locator_clean:
        raise Exception("Debes introducir un localizador.")

    yield {"type": "status", "msg": "🔍 Listando spreadsheets en el folder CVC Fit..."}
    spreadsheets = list_spreadsheets_in_folder_recent_first(FOLDER_ID)
    if not spreadsheets:
        raise Exception("No se han encontrado Google Sheets en el folder indicado.")

    total = len(spreadsheets)
    yield {
        "type": "status",
        "msg": f"📁 Encontrados **{total}** spreadsheets. Iniciando búsqueda del localizador `{locator_clean}`...",
    }

    for idx, file in enumerate(spreadsheets, start=1):
        spreadsheet_id = file["id"]
        spreadsheet_name = file["name"]
        yield {
            "type": "progress",
            "current": idx,
            "total": total,
            "file": spreadsheet_name,
            "msg": f"Revisando **{idx}/{total}** · `{spreadsheet_name}`",
        }

        try:
            titles = {s["title"]: s["sheetId"] for s in get_sheet_titles_with_ids(spreadsheet_id)}

            if "Booking ES" not in titles:
                yield {"type": "skip", "msg": f"⤼ Sin hoja *Booking ES* → `{spreadsheet_name}`"}
                continue
            if target_sheet not in titles:
                yield {"type": "skip", "msg": f"⤼ Sin hoja *{target_sheet}* → `{spreadsheet_name}`"}
                continue

            g11_value = first_line(get_single_cell(spreadsheet_id, "Booking ES", "G11"))
            if str(g11_value).strip() != locator_clean:
                yield {"type": "skip", "msg": f"⤼ G11=`{g11_value}` → no coincide en `{spreadsheet_name}`"}
                continue

            yield {
                "type": "status",
                "msg": f"✅ **¡Coincidencia encontrada!** en `{spreadsheet_name}` — Leyendo nombre del pasajero...",
            }

            nombre = first_line(get_single_cell(spreadsheet_id, "Booking ES", "G24"))
            nombre_safe = safe_filename(nombre if nombre else "Sin nombre")
            pdf_name = safe_filename(f"{pdf_prefix} {nombre_safe} {locator_clean}.pdf")

            yield {"type": "status", "msg": f"📄 Generando PDF de la hoja **{target_sheet}**..."}
            pdf_bytes = export_sheet_pdf_bytes(spreadsheet_id, titles[target_sheet])

            yield {
                "type": "done",
                "locator": locator_clean,
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "spreadsheet_url": file.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
                "nombre": nombre,
                "filename": pdf_name,
                "pdf_bytes": pdf_bytes,
            }
            return
        except StopIteration:
            raise
        except Exception as exc:
            yield {"type": "error", "msg": f"⚠️ Error en `{spreadsheet_name}`: {str(exc)}"}

    raise Exception("No se ha encontrado el localizador en Booking ES!G11 de ningún Sheet del folder.")


def run_cvc_search(locator, target_sheet, pdf_prefix, state_key):
    st.session_state[f"{state_key}_result"] = None
    st.session_state[f"{state_key}_log"] = []

    progress_bar = st.progress(0.0, text="Iniciando...")
    status_box = st.empty()
    log_box = st.empty()
    log_lines = []

    try:
        result = None
        for event in build_cvc_pdf_from_locator(locator, target_sheet, pdf_prefix):
            etype = event.get("type")
            if etype == "progress":
                pct = event["current"] / event["total"]
                progress_bar.progress(pct, text=f"Revisando {event['current']}/{event['total']} · {event['file']}")
                status_box.markdown(f"<div class='{state_key}-log-line'>{event['msg']}</div>", unsafe_allow_html=True)
            elif etype == "status":
                log_lines.append(event["msg"])
            elif etype == "skip":
                log_lines.append(f"<span style='color:#9BA5B7;'>{event['msg']}</span>")
            elif etype == "error":
                log_lines.append(f"<span style='color:#D97706;'>{event['msg']}</span>")
            elif etype == "done":
                result = event
                progress_bar.progress(1.0, text="✅ PDF generado correctamente")
                status_box.empty()

            if log_lines:
                log_box.markdown(
                    "<br>".join(f"<div class='{state_key}-log-line'>{line}</div>" for line in log_lines[-12:]),
                    unsafe_allow_html=True,
                )

        if result:
            st.session_state[f"{state_key}_result"] = result
            st.session_state[f"{state_key}_log"] = log_lines
        else:
            st.error("Búsqueda finalizada sin coincidencias.")
    except Exception as exc:
        progress_bar.empty()
        status_box.empty()
        st.error(f"Error: {exc}")
        st.session_state[f"{state_key}_result"] = None


# ============================================================
# NUEVOS HELPERS CONFIRMACION / INFORME
# ============================================================
def parse_locator_input(locator_raw):
    locator = str(locator_raw or "").strip().upper()
    if not locator:
        raise Exception("Debes introducir un localizador.")

    is_group = locator.endswith("_GROUP")
    core = locator[:-6] if is_group else locator

    m = re.fullmatch(r"([A-Z]{2,3})(\d{6})-(\d{3})", core)
    if not m:
        raise Exception("Formato de localizador no válido. Debe ser CODIGOBARCO+AAMMDD-999 o terminar en _GROUP.")

    ship_code, yymmdd, sequence = m.groups()
    boat_name = SHIP_CODE_TO_NAME.get(ship_code)
    if not boat_name:
        raise Exception(f"Código de barco no reconocido: {ship_code}")

    year_full = f"20{yymmdd[:2]}"
    file_base = f"{boat_name}_{yymmdd}"

    return {
        "original": locator,
        "is_group": is_group,
        "core": core,
        "ship_code": ship_code,
        "boat_name": boat_name,
        "yymmdd": yymmdd,
        "sequence": sequence,
        "year_full": year_full,
        "year_folder_name": f"{year_full}_GROUP" if is_group else year_full,
        "file_name": f"{file_base}_GROUP" if is_group else file_base,
        "sheet_name": f"{core}_GROUP" if is_group else core,
        "root_id": GROUPS_ROOT_ID if is_group else DRIVE_ROOT_ID,
    }


def build_sheet_tab_url(spreadsheet_id, sheet_gid):
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_gid}"


def find_locator_confirmation(locator_raw):
    parsed = parse_locator_input(locator_raw)
    log_lines = []

    year_folder = find_child_folder(parsed["root_id"], parsed["year_folder_name"])
    if not year_folder:
        log_lines.append(f"❌ No existe la carpeta de año: {parsed['year_folder_name']}")
        return {
            "status": "missing_year",
            "parsed": parsed,
            "log": log_lines,
        }
    log_lines.append(f"✅ Carpeta de año encontrada: {parsed['year_folder_name']}")

    boat_folder = find_child_folder(year_folder["id"], parsed["boat_name"])
    if not boat_folder:
        log_lines.append(f"❌ No existe la carpeta del barco: {parsed['boat_name']}")
        return {
            "status": "missing_boat",
            "parsed": parsed,
            "log": log_lines,
        }
    log_lines.append(f"✅ Carpeta de barco encontrada: {parsed['boat_name']}")

    file_obj = find_file_by_name(boat_folder["id"], parsed["file_name"])
    if not file_obj:
        log_lines.append(f"❌ No existe el archivo: {parsed['file_name']}")
        return {
            "status": "missing_file",
            "parsed": parsed,
            "log": log_lines,
        }
    log_lines.append(f"✅ Archivo encontrado: {parsed['file_name']}")

    sheets = get_sheet_titles_with_ids(file_obj["id"])
    target_sheet = next((s for s in sheets if s["title"].strip() == parsed["sheet_name"].strip()), None)
    if not target_sheet:
        log_lines.append(f"❌ No existe la pestaña/localizador: {parsed['sheet_name']}")
        return {
            "status": "missing_locator",
            "parsed": parsed,
            "file": file_obj,
            "log": log_lines,
        }

    final_url = build_sheet_tab_url(file_obj["id"], target_sheet["sheetId"])
    log_lines.append(f"✅ Pestaña encontrada: {parsed['sheet_name']}")

    return {
        "status": "found",
        "parsed": parsed,
        "file": file_obj,
        "sheet": target_sheet,
        "url": final_url,
        "log": log_lines,
    }


@st.cache_data(ttl=300)
def get_years_by_root(root_id):
    folders = list_folder_items(root_id, folders_only=True)
    if root_id == DRIVE_ROOT_ID:
        years = [f["name"].strip() for f in folders if re.fullmatch(r"\d{4}", f["name"].strip())]
    else:
        years = [f["name"].strip() for f in folders if re.fullmatch(r"\d{4}_GROUP", f["name"].strip())]
    return sorted(years, reverse=True)


@st.cache_data(ttl=300)
def get_year_folder_id_by_root(root_id, yearname):
    folder = find_child_folder(root_id, yearname)
    return folder["id"] if folder else None


@st.cache_data(ttl=300)
def get_boats_by_root(root_id, yearname):
    yearfolderid = get_year_folder_id_by_root(root_id, yearname)
    if not yearfolderid:
        return []
    folders = list_folder_items(yearfolderid, folders_only=True)
    return sorted([f["name"].strip() for f in folders if f["name"].strip()])


@st.cache_data(ttl=300)
def get_departures_by_root(root_id, yearname, boatname):
    yearfolderid = get_year_folder_id_by_root(root_id, yearname)
    if not yearfolderid:
        return []
    boatfolder = find_child_folder(yearfolderid, boatname)
    if not boatfolder:
        return []

    files = list_folder_items(boatfolder["id"], folders_only=False)
    if root_id == DRIVE_ROOT_ID:
        pattern = re.compile(rf"^{re.escape(boatname)}_\d{{6}}$")
    else:
        pattern = re.compile(rf"^{re.escape(boatname)}_\d{{6}}_GROUP$")

    departures = []
    for file in files:
        name = file["name"].strip()
        if pattern.match(name):
            departures.append(
                {
                    "nombre": name,
                    "id": file["id"],
                    "url": file.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{file['id']}/edit",
                }
            )
    departures.sort(key=lambda x: x["nombre"])
    return departures


def parse_numeric_value(value):
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


def parse_int_from_text(value):
    text = str(value or "").strip().upper().replace("PAX", "").strip()
    m = re.search(r"\d+", text)
    return int(m.group(0)) if m else 0


def get_sheet_title_b2(spreadsheet_id, sheet_title):
    return get_single_cell(spreadsheet_id, sheet_title, "B2")


def extract_informe_por_barco(spreadsheet_id, spreadsheet_name):
    sheets = get_sheet_titles_with_ids(spreadsheet_id)
    rows = []

    for sheet in sheets:
        sheet_title = sheet["title"]
        try:
            b2 = str(get_sheet_title_b2(spreadsheet_id, sheet_title) or "").upper()
            if "CONFIR" not in b2 and "PROFORMA" not in b2:
                continue

            cells = get_sheet_cells_batch(
                spreadsheet_id,
                sheet_title,
                ["G11", "G5", "G57", "Q55", "P57", "G22", "K22", "N22", "P22", "G20", "K20", "N20", "P20", "G19", "G18"]
            )

            pax = sum(parse_int_from_text(cells.get(a1, "")) for a1 in ["G22", "K22", "N22", "P22"])
            cabinas = sum(int(parse_numeric_value(cells.get(a1, ""))) for a1 in ["G20", "K20", "N20", "P20"])
            total_eur = parse_numeric_value(cells.get("Q55", ""))
            deposito = parse_numeric_value(cells.get("P57", ""))
            duracion_num = int(parse_numeric_value(cells.get("G18", "")))

            rows.append({
                "Hoja": sheet_title,
                "Localizador": str(cells.get("G11", "")).strip(),
                "Agencia": str(cells.get("G5", "")).strip(),
                "Estado Pago": str(cells.get("G57", "")).strip(),
                "Total €": total_eur,
                "Cantidad Deposito": deposito,
                "PAX": pax,
                "Cabinas": cabinas,
                "Itinerario": str(cells.get("G19", "")).strip(),
                "Duracion": f"{duracion_num} Dias" if duracion_num else "",
                "Tipo Documento": b2,
                "SheetId": sheet["sheetId"],
            })
        except Exception:
            continue

    total_importe = round(sum(r["Total €"] for r in rows), 2)
    total_pax = sum(r["PAX"] for r in rows)

    return {
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_name": spreadsheet_name,
        "rows": rows,
        "total_importe": total_importe,
        "total_pax": total_pax,
    }


# ============================================================
# CSS
# ============================================================
st.markdown(
    """
    <style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');

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

.login-page {
    min-height: auto;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 0.2rem 1rem 1rem;
}

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
    color: #334155 !important;
    font-size: 0.80rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.01em;
}

div[data-testid="stTextInput"] input,
div[data-testid="stDateInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background: #FFFFFF !important;
    border: 1.6px solid #CBD5E1 !important;
    border-radius: 14px !important;
    color: #1F2937 !important;
    min-height: 46px !important;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.90rem !important;
    font-weight: 600 !important;
    transition: all 0.18s ease !important;
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
.logout-btn div button,
.download-btn button {
    border-radius: 999px !important;
    min-height: 42px !important;
    padding: 0 1.15rem !important;
    font-size: 0.83rem !important;
    font-weight: 800 !important;
    box-shadow: 0 3px 10px rgba(15, 23, 42, 0.08) !important;
    font-family: 'DM Sans', sans-serif !important;
    letter-spacing: 0.01em !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease !important;
    border: 1.5px solid transparent !important;
}

div.stButton button:hover,
div[data-testid="stFormSubmitButton"] button:hover,
.download-btn button:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12) !important;
    filter: saturate(1.04);
}

div.stButton button:focus,
div[data-testid="stFormSubmitButton"] button:focus,
.download-btn button:focus {
    box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.14), 0 8px 18px rgba(37, 99, 235, 0.10) !important;
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
    font-size: 0.96rem;
    font-weight: 800;
    color: #1F2937;
    line-height: 1.15;
}

.portal-title-en { margin-top: 0.12rem; }
.portal-subtitle, .portal-subtitle-en { font-size: 0.72rem; color: #667085; line-height: 1.2; }
.portal-subtitle { margin-top: 0.12rem; }
.portal-subtitle-en { margin-top: 0.08rem; }
.user-top { font-size: 0.72rem; color: #566079; white-space: nowrap; }
.main-content { padding: 0; }

.section-head-row, .section-head-row-green {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 0.55rem;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
}

.section-head-row-green { margin-top: -0.15rem; }

.section-eyebrow {
    display: inline-flex;
    align-items: center;
    padding: 0.34rem 0.74rem;
    border-radius: 999px;
    background: #E0ECFF;
    border: 1px solid #BFD4FF;
    color: #1E4FBF;
    font-size: 0.66rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0 !important;
}

.web-chip, .web-chip-green {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.38rem 0.82rem;
    border-radius: 999px;
    font-size: 0.71rem;
    font-weight: 800;
    line-height: 1;
    text-decoration: none;
    white-space: nowrap;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
}

.web-chip {
    background: #FFE69A;
    border: 1px solid #F2C94C;
    color: #7A5900 !important;
}

.web-chip-green {
    background: #DDF7E6;
    border: 1px solid #9FDEB4;
    color: #17663B !important;
}

.user-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0.02rem 0 1rem;
    padding: 0.42rem 0.78rem;
    border-radius: 999px;
    background: #fff;
    border: 1px solid #D9E2EC;
    font-size: 0.73rem;
    font-weight: 700;
    color: #4B5565;
    max-width: 100%;
    word-break: break-word;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.panel-inline {
    background: linear-gradient(180deg, #FFFFFF 0%, #FAFBFD 100%);
    border: 1px solid #DCE5F0;
    border-radius: 22px;
    padding: 1rem 1rem 1.1rem 1rem;
    margin-top: 0.95rem;
    box-shadow: 0 8px 28px rgba(15, 23, 42, 0.05);
}

.panel-inline h3 {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 800 !important;
    color: #1F2937 !important;
    margin-bottom: 0.65rem !important;
    font-size: 1rem !important;
}

.action-box {
    width: 100%;
    min-height: 20px;
    border-radius: 22px;
    padding: 1rem;
    margin-bottom: 0.85rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 0.9rem;
    border: 1px solid transparent;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
}

.card-es {
    background: #EAF3FF;
    border-color: #BFD7FF;
    --card-btn-bg: #CFE3FF;
    --card-btn-border: #94BEFF;
    --card-btn-text: #1E4E93;
    --card-btn-shadow: rgba(30, 78, 147, 0.16);
}

.card-grupos {
    background: #EAF8EE;
    border-color: #BDE3C7;
    --card-btn-bg: #CDEFD7;
    --card-btn-border: #93D0A7;
    --card-btn-text: #1F6A3A;
    --card-btn-shadow: rgba(31, 106, 58, 0.15);
}

.card-salida {
    background: #FFF2E3;
    border-color: #F1CFA9;
    --card-btn-bg: #FFF2E3;
    --card-btn-border: #F1B97B;
    --card-btn-text: #8A5318;
    --card-btn-shadow: rgba(138, 83, 24, 0.16);
}

.card-crucero {
    background: #F0EAFE;
    border-color: #D3C4FA;
    --card-btn-bg: #DDD0FF;
    --card-btn-border: #B9A0F8;
    --card-btn-text: #5A3E9E;
    --card-btn-shadow: rgba(90, 62, 158, 0.16);
}

.card-nueva-agencia {
    background: #EAF8EF;
    border-color: #BEE3C9;
    --card-btn-bg: #D0EFDA;
    --card-btn-border: #98D0AA;
    --card-btn-text: #256245;
    --card-btn-shadow: rgba(37, 98, 69, 0.16);
}

.card-buscar-agencia {
    background: #FFF1E5;
    border-color: #F1D1B0;
    --card-btn-bg: #FFDDBF;
    --card-btn-border: #F0B77E;
    --card-btn-text: #8B5620;
    --card-btn-shadow: rgba(139, 86, 32, 0.16);
}

.card-cvcfit {
    background: #FDECF3;
    border-color: #F1C3D6;
    --card-btn-bg: #F7D2E2;
    --card-btn-border: #E89BBB;
    --card-btn-text: #9B3A63;
    --card-btn-shadow: rgba(155, 58, 99, 0.16);
}

.card-cvcagencias {
    background: #EBF8EF;
    border-color: #BFE1C9;
    --card-btn-bg: #D0EFD8;
    --card-btn-border: #97D0A9;
    --card-btn-text: #2C6A44;
    --card-btn-shadow: rgba(44, 106, 68, 0.16);
}

.card-irconfirmacion {
    background: #F0F3F8;
    border-color: #CFD8E6;
    --card-btn-bg: #E0E7F1;
    --card-btn-border: #B8C6DC;
    --card-btn-text: #4A5874;
    --card-btn-shadow: rgba(74, 88, 116, 0.16);
}

.card-informebarco {
    background: #EAF7FB;
    border-color: #BFDDE8;
    --card-btn-bg: #D2EDF6;
    --card-btn-border: #97CEE0;
    --card-btn-text: #2B6881;
    --card-btn-shadow: rgba(43, 104, 129, 0.16);
}

.action-box[data-card] div.stButton button,
.action-box[data-card] .done-link {
    background: var(--card-btn-bg) !important;
    border: 1.5px solid var(--card-btn-border) !important;
    color: var(--card-btn-text) !important;
    box-shadow: 0 6px 14px var(--card-btn-shadow) !important;
    font-family: 'DM Sans', sans-serif !important;
}

.action-box[data-card] div.stButton button:hover,
.action-box[data-card] .done-link:hover {
    filter: brightness(0.98) saturate(1.06);
    box-shadow: 0 10px 20px var(--card-btn-shadow) !important;
}
por este otro:

css
.card-es {
    background: #EAF3FF;
    border-color: #BFD7FF;
    --card-btn-bg: #EAF3FF;
    --card-btn-border: #9CC3FF;
    --card-btn-text: #1E4E93;
    --card-btn-hover-bg: #1E4E93;
    --card-btn-hover-border: #163B70;
    --card-btn-hover-text: #FFFFFF;
    --card-btn-shadow: rgba(30, 78, 147, 0.16);
}

.card-grupos {
    background: #EAF8EE;
    border-color: #BDE3C7;
    --card-btn-bg: #EAF8EE;
    --card-btn-border: #9ED1AE;
    --card-btn-text: #1F6A3A;
    --card-btn-hover-bg: #1F6A3A;
    --card-btn-hover-border: #174E2B;
    --card-btn-hover-text: #FFFFFF;
    --card-btn-shadow: rgba(31, 106, 58, 0.15);
}

.card-salida {
    background: #FFF2E3;
    border-color: #F1CFA9;
    --card-btn-bg: #FFF2E3;
    --card-btn-border: #EDBB84;
    --card-btn-text: #8A5318;
    --card-btn-hover-bg: #8A5318;
    --card-btn-hover-border: #6E4011;
    --card-btn-hover-text: #FFFFFF;
    --card-btn-shadow: rgba(138, 83, 24, 0.16);
}

.card-crucero {
    background: #F0EAFE;
    border-color: #D3C4FA;
    --card-btn-bg: #F0EAFE;
    --card-btn-border: #BDA7F6;
    --card-btn-text: #5A3E9E;
    --card-btn-hover-bg: #5A3E9E;
    --card-btn-hover-border: #432D78;
    --card-btn-hover-text: #FFFFFF;
    --card-btn-shadow: rgba(90, 62, 158, 0.16);
}

.card-nueva-agencia {
    background: #EAF8EF;
    border-color: #BEE3C9;
    --card-btn-bg: #EAF8EF;
    --card-btn-border: #9CCFB0;
    --card-btn-text: #256245;
    --card-btn-hover-bg: #256245;
    --card-btn-hover-border: #1A4A33;
    --card-btn-hover-text: #FFFFFF;
    --card-btn-shadow: rgba(37, 98, 69, 0.16);
}

.card-buscar-agencia {
    background: #FFF1E5;
    border-color: #F1D1B0;
    --card-btn-bg: #FFF1E5;
    --card-btn-border: #EABB8A;
    --card-btn-text: #8B5620;
    --card-btn-hover-bg: #8B5620;
    --card-btn-hover-border: #6D4117;
    --card-btn-hover-text: #FFFFFF;
    --card-btn-shadow: rgba(139, 86, 32, 0.16);
}

.card-cvcfit {
    background: #FDECF3;
    border-color: #F1C3D6;
    --card-btn-bg: #FDECF3;
    --card-btn-border: #E9A7C4;
    --card-btn-text: #9B3A63;
    --card-btn-hover-bg: #9B3A63;
    --card-btn-hover-border: #7A294C;
    --card-btn-hover-text: #FFFFFF;
    --card-btn-shadow: rgba(155, 58, 99, 0.16);
}

.card-cvcagencias {
    background: #EBF8EF;
    border-color: #BFE1C9;
    --card-btn-bg: #EBF8EF;
    --card-btn-border: #9FD0AE;
    --card-btn-text: #2C6A44;
    --card-btn-hover-bg: #2C6A44;
    --card-btn-hover-border: #1F5031;
    --card-btn-hover-text: #FFFFFF;
    --card-btn-shadow: rgba(44, 106, 68, 0.16);
}

.card-irconfirmacion {
    background: #F0F3F8;
    border-color: #CFD8E6;
    --card-btn-bg: #F0F3F8;
    --card-btn-border: #B8C6DC;
    --card-btn-text: #4A5874;
    --card-btn-hover-bg: #4A5874;
    --card-btn-hover-border: #374359;
    --card-btn-hover-text: #FFFFFF;
    --card-btn-shadow: rgba(74, 88, 116, 0.16);
}

.card-informebarco {
    background: #EAF7FB;
    border-color: #BFDDE8;
    --card-btn-bg: #EAF7FB;
    --card-btn-border: #9BCCE0;
    --card-btn-text: #2B6881;
    --card-btn-hover-bg: #2B6881;
    --card-btn-hover-border: #1E4E61;
    --card-btn-hover-text: #FFFFFF;
    --card-btn-shadow: rgba(43, 104, 129, 0.16);
}
.action-top { display: flex; align-items: flex-start; gap: 0.75rem; }
.action-icon {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    flex-shrink: 0;
    background: rgba(255,255,255,0.42);
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.35);
}

.action-text { display: flex; flex-direction: column; gap: 0.12rem; min-width: 0; }

.action-title,
.action-title-en {
    font-family: 'DM Sans', sans-serif !important;
    line-height: 1.1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.action-title {
    font-size: 0.96rem;
    font-weight: 800;
    color: #1F2937;
}

.action-title-en {
    margin-top: 0.08rem;
    color: #41506B;
    font-size: 0.83rem;
    font-weight: 700;
}

.action-button-wrap {
    display: flex !important;
    justify-content: flex-start !important;
    align-items: center !important;
    width: 100% !important;
    margin-top: 0.1rem;
}

.action-button-wrap a.done-link {
    margin-top: 0 !important;
}

.done-link {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border-radius: 999px;
    padding: 0.48rem 0.96rem;
    font-size: 0.82rem;
    font-weight: 800;
    font-family: 'DM Sans', sans-serif !important;
    text-decoration: none;
    white-space: nowrap;
    box-shadow: 0 5px 14px rgba(15, 23, 42, 0.08);
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}

.done-link:hover {
    transform: translateY(-1px);
    filter: saturate(1.04);
}

/* Botones de tarjetas: heredan la personalidad cromática de su tarjeta */
.action-box[data-card] div.stButton button,
.action-box[data-card] .done-link {
    background: var(--card-btn-bg) !important;
    border: 1.5px solid var(--card-btn-border) !important;
    color: var(--card-btn-text) !important;
    box-shadow: 0 6px 14px var(--card-btn-shadow) !important;
    font-family: 'DM Sans', sans-serif !important;
}

.action-box[data-card] div.stButton button:hover,
.action-box[data-card] .done-link:hover {
    background: var(--card-btn-hover-bg) !important;
    border-color: var(--card-btn-hover-border) !important;
    color: var(--card-btn-hover-text) !important;
    box-shadow: 0 10px 22px var(--card-btn-shadow) !important;
    transform: translateY(-1px);
    filter: none !important;
}

/* Botones e inputs dentro de paneles: más visibles */
.panel-inline div.stButton button,
.panel-inline div[data-testid="stFormSubmitButton"] button,
.panel-inline .download-btn button,
.panel-inline .stDownloadButton button {
    background: linear-gradient(180deg, #2F6DF6 0%, #245FE0 100%) !important;
    color: #FFFFFF !important;
    border: 1.5px solid #1E4FC7 !important;
    box-shadow: 0 8px 20px rgba(37, 99, 235, 0.22) !important;
    font-family: 'DM Sans', sans-serif !important;
}

.panel-inline div.stButton button:hover,
.panel-inline div[data-testid="stFormSubmitButton"] button:hover,
.panel-inline .stDownloadButton button:hover {
    filter: brightness(1.03);
    box-shadow: 0 10px 24px rgba(37, 99, 235, 0.26) !important;
}

.agency-card, .cvcfit-card, .cvcfit-status-card, .cvcagencias-card, .cvcagencias-status-card, .process-card, .irconfirmacion-card, .informebarco-card {
    background: #FBFCFF;
    border: 1px solid #DCE5F0;
    border-radius: 18px;
    padding: 1rem;
    margin-top: 0.75rem;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
}

.agency-grid, .cvcfit-grid, .cvcagencias-grid, .process-grid, .irconfirmacion-grid, .informebarco-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.85rem 1rem;
}

.agency-item-label, .cvcfit-item-label, .cvcagencias-item-label, .process-item-label, .irconfirmacion-item-label, .informebarco-item-label {
    font-size: 0.68rem;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.16rem;
    font-weight: 700;
}

.agency-item-value, .cvcfit-item-value, .cvcagencias-item-value, .process-item-value, .irconfirmacion-item-value, .informebarco-item-value {
    font-size: 0.82rem;
    color: #1F2937;
    line-height: 1.35;
    word-break: break-word;
    font-weight: 600;
}

.cvcfit-log-line, .cvcagencias-log-line, .irconfirmacion-log-line {
    font-size: 0.74rem;
    color: #465066;
    line-height: 1.45;
    margin-bottom: 0.35rem;
    word-break: break-word;
}

.report-table-wrap { margin-top: 1rem; overflow-x: auto; }

.report-table {
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    border: 1px solid #DCE5F0;
    border-radius: 16px;
    overflow: hidden;
}

.report-table th, .report-table td {
    font-size: 0.76rem;
    padding: 0.65rem 0.7rem;
    border-bottom: 1px solid #EEF2F7;
    text-align: left;
    vertical-align: top;
}

.report-table th {
    background: #F5F8FC;
    color: #334155;
    font-weight: 800;
    white-space: nowrap;
}

.report-table td {
    color: #1F2937;
    font-weight: 500;
}

.portal-footer {
    margin-top: 1rem;
    padding: 0.5rem 0 0 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.8rem;
    flex-wrap: wrap;
}

.footer-text { font-size: 0.71rem; color: #A2ABBD; }

@media (max-width: 1600px) {
    .agency-grid, .cvcfit-grid, .cvcagencias-grid, .process-grid, .irconfirmacion-grid, .informebarco-grid {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 1300px) {
    .portal-header, .portal-footer {
        flex-direction: column;
        align-items: flex-start;
    }
}
</style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOGIN
# ============================================================
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


# ============================================================
# VARIABLES UI
# ============================================================
USEREMAIL = st.session_state.get("useremail", "").strip()
DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Sin usuario"
SALUDO = get_saludo("es")
SALUDOEN = get_saludo("en")
excursionesurl = f"https://docs.google.com/spreadsheets/d/{EXCURSIONES_SHEET_ID}/edit"
drive_root_url = f"https://drive.google.com/drive/folders/{DRIVE_ROOT_ID}"
groups_root_url = f"https://drive.google.com/drive/folders/{GROUPS_ROOT_ID}"
cvcfit_folder_url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"


# ============================================================
# CABECERA
# ============================================================
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
        <a class="web-chip-green" href="{drive_root_url}" target="_blank" rel="noopener noreferrer">Abre Drive Root</a>
        <a class="web-chip-green" href="{groups_root_url}" target="_blank" rel="noopener noreferrer">Abre Drive Groups</a>
        <a class="web-chip-green" href="{cvcfit_folder_url}" target="_blank" rel="noopener noreferrer">Abre Folder Sesiones</a>
        <a class="web-chip-green" href="https://docs.google.com/spreadsheets/d/1K-Tn_E3QEhCplOP-IFHbKZc-vtKAxFEUBbZVK14EjJI/edit?gid=0#gid=0" target="_blank" rel="noopener noreferrer">Abre MASTER_CABINAS</a>
        <a class="web-chip-green" href="https://docs.google.com/spreadsheets/d/1ojMHeoosUyel8BA2XTmDsmyDJf_vvJrrJNOyxn2u1jg/edit?gid=0#gid=0" target="_blank" rel="noopener noreferrer">Abre EXCURSIONES</a>
         <a class="web-chip-green" href="https://docs.google.com/spreadsheets/d/1Z4sZolu-F44_WfMV7ZiYlelSU3SLU6JVO1MmqLeIZ0k/edit?gid=0#gid=0" target="_blank" rel="noopener noreferrer">Abre MASTER CLIENTES</a>
          <a class="web-chip-green" href="https://docs.google.com/spreadsheets/d/1mlUYqtwTzLCR_HJr9TCD7VWrGI6nDhMtwi27cMJL_1s/edit?gid=0#gid=0" target="_blank" rel="noopener noreferrer">Abre Ventas FIT</a>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(f'<div class="user-pill">{DISPLAYUSER} · {USEREMAIL}</div>', unsafe_allow_html=True)


# ============================================================
# TARJETAS PRINCIPALES
# ============================================================
def render_action_card(col, config):
    with col:
        st.markdown(
            f"""
            <div class="action-box {config['card_class']}" data-card="{config['card_class']}">
                <div class="action-top">
                    <div class="action-icon">{config['icon']}</div>
                    <div class="action-text">
                        <div class="action-title">{config['title_es']}</div>
                        <div class="action-title-en">{config['title_en']}</div>
                    </div>
                </div>
                <div class="action-button-wrap">
            """,
            unsafe_allow_html=True,
        )

        if config.get("link"):
            st.markdown(
                f'<a class="done-link" href="{config["link"]}" target="_blank" rel="noopener noreferrer">{config["button_label"]}</a>',
                unsafe_allow_html=True,
            )
        else:
            disabled = config.get("disabled", False)
            if not disabled and st.button(config["button_label"], key=config["key"]):
                action = config.get("action")
                if action:
                    action()
            elif disabled:
                st.button(config["button_label"], key=config["key"], disabled=True)

        st.markdown("</div></div>", unsafe_allow_html=True)


cards = [
    {
        "card_class": "card-es",
        "icon": "📄",
        "title_es": "Nueva Confirmación",
        "title_en": "New Confirmation",
        "button_label": "Crear Sesión",
        "key": "btncreares",
        "action": lambda: create_master_session(
            "es",
            TEMPLATE_ID_ES,
            "MASTER",
            "Crear Sesión MASTER / CONFIRMATION"
        ),
        "disabled": False,
    },
    {
        "card_class": "card-grupos",
        "icon": "👥",
        "title_es": "Nueva Confirmación GRUPOS",
        "title_en": "New GROUPS Confirmation",
        "button_label": "Crear Sesión GRUPOS",
        "key": "btncreargrupos",
        "action": lambda: create_master_session(
            "grupos",
            TEMPLATE_ID_GRUPOS,
            "MASTER GRUPOS",
            "Crear Sesión MASTER / GROUPS"
        ),
        "disabled": False,
    },
    {
        "card_class": "card-salida",
        "icon": "🔎",
        "title_es": "Ir a Salida",
        "title_en": "Go to Departure",
        "button_label": "Buscar Salida",
        "key": "btnirsalida",
        "action": lambda: (open_panel("salida"), st.rerun()),
    },
    {
        "card_class": "card-crucero",
        "icon": "🛳️",
        "title_es": "Crear Crucero",
        "title_en": "Create Cruise",
        "button_label": "Nuevo Crucero",
        "key": "btncrearcruceroopen",
        "action": lambda: (open_panel("crucero"), st.rerun()),
    },
    {
        "card_class": "card-nueva-agencia",
        "icon": "🏢",
        "title_es": "Nueva Agencia",
        "title_en": "New Agency",
        "button_label": "Nueva Agencia",
        "key": "btnnuevaagencia",
        "action": lambda: (open_panel("nuevaagencia"), st.rerun()),
    },
    {
        "card_class": "card-buscar-agencia",
        "icon": "📇",
        "title_es": "Buscar Agencia",
        "title_en": "Find Agency",
        "button_label": "Buscar Agencia",
        "key": "btnbuscaragencia",
        "action": lambda: (open_panel("buscaragencia"), st.rerun()),
    },
    {
        "card_class": "card-cvcfit",
        "icon": "🧾",
        "title_es": "CVC Fit",
        "title_en": "CVC Fit",
        "button_label": "Abrir CVC Fit",
        "key": "btncvcfitopen",
        "action": lambda: (open_panel("cvcfit"), st.rerun()),
    },
    {
        "card_class": "card-cvcagencias",
        "icon": "🏷️",
        "title_es": "CVC Agencias",
        "title_en": "CVC Agencies",
        "button_label": "Abrir CVC Agencias",
        "key": "btncvcagenciasopen",
        "action": lambda: (open_panel("cvcagencias"), st.rerun()),
    },
    {
        "card_class": "card-irconfirmacion",
        "icon": "📌",
        "title_es": "Ir a Confirmación",
        "title_en": "Go to Confirmation",
        "button_label": "Buscar Localizador",
        "key": "btnirconfirmacionopen",
        "action": lambda: (open_panel("irconfirmacion"), st.rerun()),
    },
    {
        "card_class": "card-informebarco",
        "icon": "💶",
        "title_es": "Informe € por Barco",
        "title_en": "€ Report by Ship",
        "button_label": "Abrir Informe",
        "key": "btninformebarcoopen",
        "action": lambda: (open_panel("informebarco"), st.rerun()),
    },
]

# ANCHOS PERSONALIZADOS
row1 = st.columns([1.45, 1.45, 1.05, 1.05, 1.10, 1.10], gap="medium")
for col, card in zip(row1, cards[:6]):
    render_action_card(col, card)

row2 = st.columns([0.5, 0.5, 0.5, 0.5], gap="medium")
for col, card in zip(row2, cards[6:10]):
    render_action_card(col, card)


# ============================================================
# PANEL PROCESO SESIONES MASTER
# ============================================================
if st.session_state.get("confirmstate") in ["done", "error"]:
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)

    session_type = st.session_state.get("sessiontype", "")
    process_title = st.session_state.get("processtitle", "Proceso")
    process_result = st.session_state.get("processresult") or {}

    if session_type == "es":
        st.markdown("### Sesion MASTER_CONFIRMATION")
    elif session_type == "grupos":
        st.markdown("### Sesion MASTER_GROUPS")
    else:
        st.markdown(f"### {process_title}")

    if st.session_state.get("confirmstate") == "done":
        st.success("Ok")

        render_key_value_grid(
            "process",
            [
                ("Tipo de sesión", "MASTER / CONFIRMATION" if session_type == "es" else "MASTER / GROUPS"),
                ("Nombre creado", process_result.get("name", st.session_state.get("nombrecopia", "-"))),
                ("Usuario", DISPLAYUSER),
                ("Estado", "Creada correctamente"),
            ],
        )

        final_url = process_result.get("url", "")
        if final_url:
            st.markdown(
                f'<a class="done-link" href="{final_url}" target="_blank" rel="noopener noreferrer">Abrir sesión creada</a>',
                unsafe_allow_html=True,
            )

    elif st.session_state.get("confirmstate") == "error":
        st.error(f"No se pudo crear la sesión: {process_result.get('message', 'Error desconocido')}")

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# PANEL SALIDA
# ============================================================
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
    except Exception as exc:
        st.exception(exc)
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# PANEL CREAR CRUCERO
# ============================================================
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
    except Exception as exc:
        st.exception(exc)
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# PANEL NUEVA AGENCIA
# ============================================================
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
                except Exception as exc:
                    st.exception(exc)
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# PANEL BUSCAR AGENCIA
# ============================================================
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
            st.session_state["agencymatches"] = search_agencies(searchquery)
            st.session_state["agencyselectedidx"] = None
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
        selectedlabel = st.selectbox(
            "Elige la agencia correcta",
            options=options,
            index=None,
            placeholder="Selecciona una coincidencia",
        )
        if selectedlabel:
            selectedagency = matches[options.index(selectedlabel)]

    if selectedagency:
        render_key_value_grid("agency", [(field, selectedagency.get(field, "")) for field in AGENCY_FIELDS])
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# PANEL CVC FIT
# ============================================================
if st.session_state.get("opencvcfitform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### CVC Fit")
    locator = st.text_input(
        "Localizador",
        key="cvcfitlocatorwidget",
        placeholder="Introduce el localizador exacto de Booking ES!G11",
    )
    if st.button("Generar PDF CVC Fit", key="btncvcfitaction", disabled=not locator):
        run_cvc_search(locator, "CVC Fit", "CVC Fit", "cvcfit")

    log_lines_saved = st.session_state.get("cvcfit_log", [])
    if log_lines_saved:
        st.markdown('<div class="cvcfit-status-card" style="margin-top:0.75rem;">', unsafe_allow_html=True)
        st.markdown("**Log de la búsqueda:**")
        st.markdown("<br>".join(f"<div class='cvcfit-log-line'>{line}</div>" for line in log_lines_saved), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    result = st.session_state.get("cvcfit_result")
    if result:
        render_key_value_grid(
            "cvcfit",
            [
                ("Localizador", result.get("locator", "")),
                ("Nombre pasajero", result.get("nombre", "")),
                ("Spreadsheet", result.get("spreadsheet_name", "")),
            ],
        )
        st.download_button(
            "Descargar PDF CVC Fit",
            data=result["pdf_bytes"],
            file_name=result["filename"],
            mime="application/pdf",
            key="downloadcvcfitpdf",
        )
        st.markdown(
            f'<a class="done-link" href="{result["spreadsheet_url"]}" target="_blank" rel="noopener noreferrer">Abrir spreadsheet</a>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# PANEL CVC AGENCIAS
# ============================================================
if st.session_state.get("opencvcagenciasform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### CVC Agencias")
    locator = st.text_input(
        "Localizador",
        key="cvcagenciaslocatorwidget",
        placeholder="Introduce el localizador exacto de Booking ES!G11",
    )
    if st.button("Generar PDF CVC Agencias", key="btncvcagenciasaction", disabled=not locator):
        run_cvc_search(locator, "CVC Agencias", "CVC Agencias", "cvcagencias")

    log_lines_saved = st.session_state.get("cvcagencias_log", [])
    if log_lines_saved:
        st.markdown('<div class="cvcagencias-status-card" style="margin-top:0.75rem;">', unsafe_allow_html=True)
        st.markdown("**Log de la búsqueda:**")
        st.markdown("<br>".join(f"<div class='cvcagencias-log-line'>{line}</div>" for line in log_lines_saved), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    result = st.session_state.get("cvcagencias_result")
    if result:
        render_key_value_grid(
            "cvcagencias",
            [
                ("Localizador", result.get("locator", "")),
                ("Nombre pasajero", result.get("nombre", "")),
                ("Spreadsheet", result.get("spreadsheet_name", "")),
            ],
        )
        st.download_button(
            "Descargar PDF CVC Agencias",
            data=result["pdf_bytes"],
            file_name=result["filename"],
            mime="application/pdf",
            key="downloadcvcagenciaspdf",
        )
        st.markdown(
            f'<a class="done-link" href="{result["spreadsheet_url"]}" target="_blank" rel="noopener noreferrer">Abrir spreadsheet</a>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# PANEL IR A CONFIRMACION
# ============================================================
if st.session_state.get("openirconfirmacionform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### Ir a Confirmación")
    locator = st.text_input(
        "Localizador",
        key="irconfirmacionlocatorwidget",
        placeholder="Ej: ALB250601-001 o ALB250601-001_GROUP",
    )
    if st.button("Buscar confirmación", key="btnirconfirmacionaction", disabled=not locator):
        try:
            result = find_locator_confirmation(locator)
            st.session_state["irconfirmacion_result"] = result
            st.session_state["irconfirmacion_log"] = result.get("log", [])
        except Exception as exc:
            st.error(str(exc))
            st.session_state["irconfirmacion_result"] = None
            st.session_state["irconfirmacion_log"] = []

    log_lines_saved = st.session_state.get("irconfirmacion_log", [])
    if log_lines_saved:
        st.markdown('<div class="irconfirmacion-card" style="margin-top:0.75rem;">', unsafe_allow_html=True)
        st.markdown("**Resultado de la búsqueda:**")
        st.markdown("<br>".join(f"<div class='irconfirmacion-log-line'>{line}</div>" for line in log_lines_saved), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    result = st.session_state.get("irconfirmacion_result")
    if result and result.get("status") == "found":
        parsed = result.get("parsed", {})
        render_key_value_grid(
            "irconfirmacion",
            [
                ("Localizador", parsed.get("original", "")),
                ("Barco", parsed.get("boat_name", "")),
                ("Archivo", result.get("file", {}).get("name", "")),
                ("Pestaña", result.get("sheet", {}).get("title", "")),
            ],
        )
        st.markdown(
            f'<a class="done-link" href="{result["url"]}" target="_blank" rel="noopener noreferrer">Abrir confirmación</a>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# PANEL INFORME BARCO
# ============================================================
if st.session_state.get("openinformebarcoform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### Informe € por Barco")

    tipo_options = ["NORMAL", "GROUPS"]
    current_tipo = st.session_state.get("informetype")
    if current_tipo not in tipo_options:
        current_tipo = None

    informetype = st.selectbox(
        "TIPO",
        options=tipo_options,
        index=tipo_options.index(current_tipo) if current_tipo in tipo_options else None,
        placeholder="Selecciona tipo",
        key="informetypewidget",
        on_change=on_informe_type_change,
    )
    if informetype != st.session_state.get("informetype"):
        st.session_state["informetype"] = informetype

    root_id = GROUPS_ROOT_ID if informetype == "GROUPS" else DRIVE_ROOT_ID

    years = get_years_by_root(root_id) if informetype else []
    current_year = st.session_state.get("informeyear")
    if current_year not in years:
        current_year = None

    informeyear = st.selectbox(
        "AÑO",
        options=years,
        index=years.index(current_year) if current_year in years else None,
        placeholder="Selecciona año",
        key="informeyearwidget",
        on_change=on_informe_year_change,
        disabled=not informetype,
    )
    if informeyear != st.session_state.get("informeyear"):
        st.session_state["informeyear"] = informeyear

    boats = get_boats_by_root(root_id, informeyear) if informetype and informeyear else []
    current_boat = st.session_state.get("informeboat")
    if current_boat not in boats:
        current_boat = None

    informeboat = st.selectbox(
        "BARCO",
        options=boats,
        index=boats.index(current_boat) if current_boat in boats else None,
        placeholder="Selecciona barco",
        key="informeboatwidget",
        on_change=on_informe_boat_change,
        disabled=not informeyear,
    )
    if informeboat != st.session_state.get("informeboat"):
        st.session_state["informeboat"] = informeboat

    departures = get_departures_by_root(root_id, informeyear, informeboat) if informetype and informeyear and informeboat else []
    departure_names = [d["nombre"] for d in departures]
    current_dep = st.session_state.get("informesalida")
    if current_dep not in departure_names:
        current_dep = None

    informesalida = st.selectbox(
        "SALIDA",
        options=departure_names,
        index=departure_names.index(current_dep) if current_dep in departure_names else None,
        placeholder="Selecciona salida",
        key="informesalidawidget",
        on_change=on_informe_salida_change,
        disabled=not informeboat,
    )
    if informesalida != st.session_state.get("informesalida"):
        st.session_state["informesalida"] = informesalida

    if st.button("Generar informe", key="btngenerarinforme", disabled=not informesalida):
        try:
            selected = next((d for d in departures if d["nombre"] == informesalida), None)
            if not selected:
                st.error("No se ha encontrado la salida seleccionada.")
            else:
                st.session_state["informeresult"] = extract_informe_por_barco(selected["id"], selected["nombre"])
        except Exception as exc:
            st.exception(exc)

    informeresult = st.session_state.get("informeresult")
    if informeresult:
        render_key_value_grid(
            "informebarco",
            [
                ("Spreadsheet", informeresult.get("spreadsheet_name", "")),
                ("Total Importe", f"{informeresult.get('total_importe', 0):,.2f} €"),
                ("Total PAX", str(informeresult.get("total_pax", 0))),
                ("Total Hojas", str(len(informeresult.get("rows", [])))),
            ],
        )

        rows = informeresult.get("rows", [])
        if rows:
            table_html = """
            <div class="report-table-wrap">
            <table class="report-table">
                <thead>
                    <tr>
                        <th>Hoja</th>
                        <th>Localizador</th>
                        <th>Agencia</th>
                        <th>Estado Pago</th>
                        <th>Total €</th>
                        <th>Depósito</th>
                        <th>PAX</th>
                        <th>Cabinas</th>
                        <th>Itinerario</th>
                        <th>Duración</th>
                        <th>Tipo</th>
                    </tr>
                </thead>
                <tbody>
            """
            for row in rows:
                table_html += f"""
                    <tr>
                        <td>{row.get('Hoja', '')}</td>
                        <td>{row.get('Localizador', '')}</td>
                        <td>{row.get('Agencia', '')}</td>
                        <td>{row.get('Estado Pago', '')}</td>
                        <td>{row.get('Total €', 0):,.2f} €</td>
                        <td>{row.get('Cantidad Deposito', 0):,.2f} €</td>
                        <td>{row.get('PAX', 0)}</td>
                        <td>{row.get('Cabinas', 0)}</td>
                        <td>{row.get('Itinerario', '')}</td>
                        <td>{row.get('Duracion', '')}</td>
                        <td>{row.get('Tipo Documento', '')}</td>
                    </tr>
                """
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


st.markdown(
    """
    <div class="portal-footer">
        <div class="footer-text">Crucemundo Hub</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("</div>", unsafe_allow_html=True)
