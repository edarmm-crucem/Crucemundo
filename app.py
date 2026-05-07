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
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    * { box-sizing: border-box; }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background: #FFFFFF !important; }
    [data-testid="stAppViewContainer"] { background: #FFFFFF !important; }
    [data-testid="stHeader"] { background: transparent !important; }
    section[data-testid="stSidebar"] { display: none !important; }
    .block-container, section.stMain > .block-container, .stMainBlockContainer, [data-testid="stMainBlockContainer"] {
        padding-top: 0rem !important; padding-bottom: 1rem !important; padding-left: 1rem !important; padding-right: 1rem !important;
        max-width: 1900px !important; margin: 0 auto !important;
    }
    .login-page { min-height: auto; display: flex; align-items: flex-start; justify-content: center; padding: 0.2rem 1rem 1rem; }
    .login-shell { width: 100%; max-width: 390px; margin: 0 auto; }
    .login-head { text-align: center; margin-bottom: 0.55rem; }
    .login-logo { height: 56px; width: auto; margin: 0 auto 0.65rem auto; display: block; }
    .login-title { font-size: 1.08rem; font-weight: 700; color: #1F2937; }
    .login-subtitle { font-size: 0.78rem; color: #7C869D; margin-top: 0.28rem; }
    .login-form-box { background: transparent !important; border: none !important; padding: 0 !important; }
    .login-note { margin-top: 0.65rem; text-align: center; font-size: 0.72rem; color: #8A93A5; }
    div[data-testid="stTextInput"] label, div[data-testid="stSelectbox"] label, div[data-testid="stDateInput"] label, div[data-testid="stNumberInput"] label {
        color: #4D576D !important; font-size: 0.78rem !important; font-weight: 500 !important;
    }
    div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] div[data-baseweb="select"] > div, div[data-testid="stDateInput"] input, div[data-testid="stNumberInput"] input {
        background: #F8FAFC !important; border: 1px solid #E5EAF2 !important; border-radius: 12px !important; color: #1F2937 !important;
    }
    div.stButton { width: fit-content !important; }
    div.stButton button, div[data-testid="stFormSubmitButton"] button, .logout-btn div button, .download-btn button {
        color: #214D92 !important; border: 1px solid rgba(33,77,146,0.14) !important; border-radius: 999px !important;
        min-height: 38px !important; padding: 0 1.15rem !important; font-size: 0.76rem !important; font-weight: 600 !important; box-shadow: none !important;
    }
    .portal-header { padding: 0.1rem 0 0.55rem 0; display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 0.55rem; }
    .portal-header-left { display: flex; align-items: center; gap: 0.9rem; }
    .portal-logo { height: 42px; width: auto; object-fit: contain; display: block; }
    .portal-title, .portal-title-en { font-size: 0.96rem; font-weight: 700; color: #1F2937; line-height: 1.15; }
    .portal-title-en { margin-top: 0.12rem; }
    .portal-subtitle, .portal-subtitle-en { font-size: 0.72rem; color: #7C869D; line-height: 1.2; }
    .portal-subtitle { margin-top: 0.12rem; }
    .portal-subtitle-en { margin-top: 0.08rem; }
    .user-top { font-size: 0.72rem; color: #566079; white-space: nowrap; }
    .main-content { padding: 0; }
    .section-head-row, .section-head-row-green { display: flex; align-items: center; justify-content: flex-start; gap: 0.55rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
    .section-head-row-green { margin-top: -0.15rem; }
    .section-eyebrow {
        display: inline-flex; align-items: center; padding: 0.34rem 0.74rem; border-radius: 999px; background: #EAF1FF; border: 1px solid #D6E3FF;
        color: #2E5FB8; font-size: 0.66rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0 !important;
    }
    .web-chip, .web-chip-green {
        display: inline-flex; align-items: center; justify-content: center; padding: 0.34rem 0.74rem; border-radius: 999px;
        font-size: 0.70rem; font-weight: 700; line-height: 1; text-decoration: none; white-space: nowrap;
    }
    .web-chip { background: #FFF3BF; border: 1px solid #F4D35E; color: #7A5900 !important; }
    .web-chip-green { background: #E9F8EE; border: 1px solid #BEE3C8; color: #1E6B3A !important; }
    .user-pill { display: inline-flex; align-items: center; gap: 0.4rem; margin: 0.02rem 0 1rem; padding: 0.38rem 0.68rem; border-radius: 999px; background: #fff; border: 1px solid #E4E7EF; font-size: 0.72rem; color: #5D6880; max-width: 100%; word-break: break-word; }
    .action-box { width: 100%; min-height: 122px; border-radius: 20px; padding: 0.78rem 0.90rem; margin-bottom: 0.70rem; display: flex; flex-direction: column; justify-content: space-between; gap: 0.55rem; border: 1px solid transparent; }
    .card-es { background: #F3F7FF; border-color: #D9E5FF; }
    .card-grupos { background: #F4FBF6; border-color: #D8EEDC; }
    .card-salida { background: #FFF8F1; border-color: #F1DFC7; }
    .card-crucero { background: #F7F4FF; border-color: #E4DDF9; }
    .card-nueva-agencia { background: #F1FAF4; border-color: #D7EEDC; }
    .card-buscar-agencia { background: #FFF7EF; border-color: #F4E1CA; }
    .card-cvcfit { background: #FFF2F7; border-color: #F4D7E3; }
    .card-cvcagencias { background: #EEF9F1; border-color: #D5EEDB; }
    .card-irconfirmacion { background: #F6F7FB; border-color: #E1E5EF; }
    .card-informebarco { background: #EEF8FB; border-color: #D5EAF1; }
    .action-top { display: flex; align-items: flex-start; gap: 0.65rem; }
    .action-icon { width: 36px; height: 36px; border-radius: 11px; display: flex; align-items: center; justify-content: center; font-size: 0.98rem; flex-shrink: 0; }
    .action-text { display: flex; flex-direction: column; gap: 0.08rem; min-width: 0; overflow: hidden; }
    .action-title, .action-title-en { font-size: 0.88rem; font-weight: 700; color: #1F2937; line-height: 1.08; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .action-title-en { margin-top: 0.03rem; font-size: 0.80rem; color: #5C677D; font-weight: 600; }
    .action-desc, .action-desc-en { display: none !important; }
    .action-button-wrap { display: flex !important; justify-content: flex-start !important; align-items: center !important; width: 100 !important; margin-top: 0.05rem; }
    .panel-inline { margin-top: 1rem; padding-top: 0.2rem; width: 100%; max-width: 1200px; }
    .done-link { display: inline-flex; align-items: center; gap: 0.35rem; margin-top: 0.65rem; background: #D9E9FF; color: #214D92 !important; border: 1px solid #BDD6FF; border-radius: 999px; padding: 0.42rem 0.88rem; font-size: 0.71rem; font-weight: 600; text-decoration: none; }
    .agency-card, .cvcfit-card, .cvcfit-status-card, .cvcagencias-card, .cvcagencias-status-card, .process-card, .irconfirmacion-card, .informebarco-card { background: #FBFCFF; border: 1px solid #E6EBF3; border-radius: 18px; padding: 1rem; margin-top: 0.75rem; }
    .agency-grid, .cvcfit-grid, .cvcagencias-grid, .process-grid, .irconfirmacion-grid, .informebarco-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.85rem 1rem; }
    .agency-item-label, .cvcfit-item-label, .cvcagencias-item-label, .process-item-label, .irconfirmacion-item-label, .informebarco-item-label { font-size: 0.68rem; color: #7E889D; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.16rem; }
    .agency-item-value, .cvcfit-item-value, .cvcagencias-item-value, .process-item-value, .irconfirmacion-item-value, .informebarco-item-value { font-size: 0.8rem; color: #1F2937; line-height: 1.35; word-break: break-word; }
    .cvcfit-log-line, .cvcagencias-log-line, .irconfirmacion-log-line { font-size: 0.74rem; color: #465066; line-height: 1.45; margin-bottom: 0.35rem; word-break: break-word; }
    .report-table-wrap { margin-top: 1rem; overflow-x: auto; }
    .report-table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #E6EBF3; border-radius: 16px; overflow: hidden; }
    .report-table th, .report-table td { font-size: 0.76rem; padding: 0.65rem 0.7rem; border-bottom: 1px solid #EEF2F7; text-align: left; vertical-align: top; }
    .report-table th { background: #F7FAFD; color: #44506A; font-weight: 700; white-space: nowrap; }
    .report-table td { color: #1F2937; }
    .portal-footer { margin-top: 1rem; padding: 0.5rem 0 0 0; display: flex; justify-content: space-between; align-items: center; gap: 0.8rem; flex-wrap: wrap; }
    .footer-text { font-size: 0.71rem; color: #A2ABBD; }
    @media (max-width: 1600px) {
        .agency-grid, .cvcfit-grid, .cvcagencias-grid, .process-grid, .irconfirmacion-grid, .informebarco-grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 1300px) {
        .portal-header, .portal-footer { flex-direction: column; align-items: flex-start; }
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
# HEADER
# ============================================================
USEREMAIL = st.session_state.get("useremail", "").strip()
DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Sin usuario"
SALUDO = get_saludo("es")
SALUDOEN = get_saludo("en")

excursionesurl = f"https://docs.google.com/spreadsheets/d/{EXCURSIONES_SHEET_ID}/edit"
driverooturl = f"https://drive.google.com/drive/folders/{DRIVE_ROOT_ID}"
groupsrooturl = f"https://drive.google.com/drive/folders/{GROUPS_ROOT_ID}"
cvcfitfolderurl = f"https://drive.google.com/drive/folders/{FOLDER_ID}"

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
        <a class="web-chip-green" href="{driverooturl}" target="_blank" rel="noopener noreferrer">Abre Drive Root</a>
        <a class="web-chip-green" href="{groupsrooturl}" target="_blank" rel="noopener noreferrer">Abre Drive Groups</a>
        <a class="web-chip-green" href="{cvcfitfolderurl}" target="_blank" rel="noopener noreferrer">Abre Folder Sesiones</a>
        <a class="web-chip-green" href="https://docs.google.com/spreadsheets/d/1K-TnE3QEhCplOP-IFHbKZc-vtKAxFEUBbZVK14EjJI/edit?gid=0#gid=0" target="_blank" rel="noopener noreferrer">Abre MASTERCABINAS</a>
        <a class="web-chip-green" href="{excursionesurl}" target="_blank" rel="noopener noreferrer">Abre EXCURSIONES</a>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(f'<div class="user-pill">{DISPLAYUSER} · {USEREMAIL}</div>', unsafe_allow_html=True)


# ============================================================
# TARJETAS
# ============================================================
def render_action_card(col, config):
    with col:
        st.markdown(
            f"""
            <div class="action-box {config['cardclass']}">
                <div class="action-top">
                    <div class="action-icon">{config['icon']}</div>
                    <div class="action-text">
                        <div class="action-title">{config['titlees']}</div>
                        <div class="action-title-en">{config['titleen']}</div>
                    </div>
                </div>
                <div class="action-button-wrap">
            """,
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


cards = [
    {
        "cardclass": "card-es",
        "icon": "🧾",
        "titlees": "Nueva Confirmación",
        "titleen": "New Confirmation",
        "buttonlabel": "Crear Sesión",
        "key": "btncreares",
        "action": lambda: create_master_session("es", TEMPLATE_ID_ES, "MASTER", "Crear Sesión MASTER CONFIRMATION"),
        "disabled": False,
    },
    {
        "cardclass": "card-grupos",
        "icon": "👥",
        "titlees": "Nueva Confirmación GRUPOS",
        "titleen": "New GROUPS Confirmation",
        "buttonlabel": "Crear Sesión GRUPOS",
        "key": "btncreargrupos",
        "action": lambda: create_master_session("grupos", TEMPLATE_ID_GRUPOS, "MASTER GRUPOS", "Crear Sesión MASTER GROUPS"),
        "disabled": False,
    },
    {
        "cardclass": "card-salida",
        "icon": "🛳️",
        "titlees": "Ir a Salida",
        "titleen": "Go to Departure",
        "buttonlabel": "Buscar Salida",
        "key": "btnirsalida",
        "action": lambda: open_panel("salida"),
    },
    {
        "cardclass": "card-crucero",
        "icon": "➕",
        "titlees": "Crear Crucero",
        "titleen": "Create Cruise",
        "buttonlabel": "Nuevo Crucero",
        "key": "btncrearcruceroopen",
        "action": lambda: open_panel("crucero"),
    },
    {
        "cardclass": "card-nueva-agencia",
        "icon": "🏢",
        "titlees": "Nueva Agencia",
        "titleen": "New Agency",
        "buttonlabel": "Nueva Agencia",
        "key": "btnnuevaagencia",
        "action": lambda: open_panel("nuevaagencia"),
    },
    {
        "cardclass": "card-buscar-agencia",
        "icon": "🔎",
        "titlees": "Buscar Agencia",
        "titleen": "Find Agency",
        "buttonlabel": "Buscar Agencia",
        "key": "btnbuscaragencia",
        "action": lambda: open_panel("buscaragencia"),
    },
    {
        "cardclass": "card-cvcfit",
        "icon": "📄",
        "titlees": "CVC Fit",
        "titleen": "CVC Fit",
        "buttonlabel": "Abrir CVC Fit",
        "key": "btncvcfitopen",
        "action": lambda: open_panel("cvcfit"),
    },
    {
        "cardclass": "card-cvcagencias",
        "icon": "📑",
        "titlees": "CVC Agencias",
        "titleen": "CVC Agencies",
        "buttonlabel": "Abrir CVC Agencias",
        "key": "btncvcagenciasopen",
        "action": lambda: open_panel("cvcagencias"),
    },
    {
        "cardclass": "card-irconfirmacion",
        "icon": "📍",
        "titlees": "Ir a Confirmación",
        "titleen": "Go to Confirmation",
        "buttonlabel": "Buscar Localizador",
        "key": "btnirconfirmacionopen",
        "action": lambda: open_panel("irconfirmacion"),
    },
    {
        "cardclass": "card-informebarco",
        "icon": "📊",
        "titlees": "Informe por Barco",
        "titleen": "Report by Ship",
        "buttonlabel": "Abrir Informe",
        "key": "btninformebarcoopen",
        "action": lambda: open_panel("informebarco"),
    },
]

row1 = st.columns(6, gap="medium")
for col, card in zip(row1, cards[:6]):
    render_action_card(col, card)

row2 = st.columns(4, gap="medium")
for col, card in zip(row2, cards[6:10]):
    render_action_card(col, card)


# ============================================================
# PANELES
# ============================================================
st.markdown('<div class="panel-inline">', unsafe_allow_html=True)

if st.session_state.get("opensalidaform"):
    st.subheader("Ir a Salida / Go to Departure")

    years = get_years()
    st.selectbox(
        "Año",
        options=[""] + years,
        key="salidayearwidget",
        on_change=on_year_change,
    )

    if st.session_state.get("salidayear"):
        boats = get_boats(st.session_state["salidayear"])
        st.selectbox(
            "Barco",
            options=[""] + boats,
            key="salidaboatwidget",
            on_change=on_boat_change,
        )

    if st.session_state.get("salidayear") and st.session_state.get("salidaboat"):
        departures = get_departures(st.session_state["salidayear"], st.session_state["salidaboat"])
        names = [d["nombre"] for d in departures]
        st.selectbox(
            "Salida",
            options=[""] + names,
            key="salidanamewidget",
            on_change=on_salida_change,
        )

        if st.session_state.get("salidaname"):
            selected = next((d for d in departures if d["nombre"] == st.session_state["salidaname"]), None)
            if selected:
                st.markdown(
                    f'<a class="done-link" href="{selected["url"]}" target="_blank" rel="noopener noreferrer">Abrir salida</a>',
                    unsafe_allow_html=True,
                )

if st.session_state.get("opencruceroform"):
    st.subheader("Crear Crucero / Create Cruise")
    with st.form("cruceroform"):
        crucero_years = get_years()
        st.selectbox("Año", options=[""] + crucero_years, key="cruceroyearwidget")
        crucero_boats = get_boats(st.session_state.get("cruceroyearwidget")) if st.session_state.get("cruceroyearwidget") else []
        st.selectbox("Barco", options=[""] + crucero_boats, key="cruceroboatwidget")
        fecha = st.date_input("Fecha salida", value=date.today())
        submitted = st.form_submit_button("Crear crucero")

        if submitted:
            if not st.session_state.get("cruceroboatwidget"):
                st.error("Debes elegir barco.")
            else:
                try:
                    result = create_crucero_file(st.session_state["cruceroboatwidget"], fecha)
                    if result["status"] == "duplicate":
                        st.warning("El archivo ya existe.")
                        st.markdown(
                            f'<a class="done-link" href="{result["url"]}" target="_blank" rel="noopener noreferrer">Abrir existente</a>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.success("Crucero creado correctamente.")
                        st.markdown(
                            f'<a class="done-link" href="{result["url"]}" target="_blank" rel="noopener noreferrer">Abrir crucero</a>',
                            unsafe_allow_html=True,
                        )
                except Exception as exc:
                    st.error(str(exc))

if st.session_state.get("opennuevaagenciaform"):
    st.subheader("Nueva Agencia / New Agency")
    with st.form("agenciaform"):
        agencydata = {}
        agencydata["Nombre"] = st.text_input("Nombre")
        agencydata["CODIGO"] = st.text_input("CODIGO")
        agencydata["Grupo Gest"] = st.text_input("Grupo Gest")
        agencydata["Telefono"] = st.text_input("Telefono")
        agencydata["Email"] = st.text_input("Email")
        agencydata["Direccion"] = st.text_input("Direccion")
        agencydata["COMISION AGENCIA"] = st.number_input("COMISION AGENCIA", value=0.0, step=0.1)
        agencydata["COMISION AGENCIA CON OFERTA "] = st.number_input("COMISION AGENCIA CON OFERTA", value=0.0, step=0.1)
        agencydata["COMISION AGENCIA OFERTA 2X1 "] = st.number_input("COMISION AGENCIA OFERTA 2X1", value=0.0, step=0.1)
        agencydata["IVA"] = st.number_input("IVA", value=0.0, step=0.1)
        agencydata["IVA SERVICIO OPCIONAL"] = st.number_input("IVA SERVICIO OPCIONAL", value=0.0, step=0.1)

        submitted = st.form_submit_button("Guardar agencia")

        if submitted:
            try:
                agencydata["COMISION AGENCIA"] = percent_to_sheet_decimal(agencydata["COMISION AGENCIA"])
                agencydata["COMISION AGENCIA CON OFERTA "] = percent_to_sheet_decimal(agencydata["COMISION AGENCIA CON OFERTA "])
                agencydata["COMISION AGENCIA OFERTA 2X1 "] = percent_to_sheet_decimal(agencydata["COMISION AGENCIA OFERTA 2X1 "])
                agencydata["IVA"] = percent_to_sheet_decimal(agencydata["IVA"])
                agencydata["IVA SERVICIO OPCIONAL"] = percent_to_sheet_decimal(agencydata["IVA SERVICIO OPCIONAL"])
                append_agency_row(agencydata)
                st.success("Agencia guardada.")
            except Exception as exc:
                st.error(str(exc))

if st.session_state.get("openbuscaragenciaform"):
    st.subheader("Buscar Agencia / Find Agency")
    query = st.text_input("Buscar por nombre, código, teléfono, email o dirección")
    if query:
        matches = search_agencies(query)
        if not matches:
            st.info("No se han encontrado coincidencias.")
        else:
            options = [f"{m['Nombre']} · {m['CODIGO']}" for m in matches]
            idx = st.selectbox("Selecciona agencia", options=range(len(options)), format_func=lambda i: options[i])
            agency = matches[idx]
            render_key_value_grid("agency", [
                ("Nombre", agency.get("Nombre", "")),
                ("CODIGO", agency.get("CODIGO", "")),
                ("Grupo Gest", agency.get("Grupo Gest", "")),
                ("Telefono", agency.get("Telefono", "")),
                ("Email", agency.get("Email", "")),
                ("Direccion", agency.get("Direccion", "")),
                ("Comisión agencia", agency.get("COMISION AGENCIA", "")),
                ("Comisión oferta", agency.get("COMISION AGENCIA CON OFERTA ", "")),
                ("Comisión 2x1", agency.get("COMISION AGENCIA OFERTA 2X1 ", "")),
                ("IVA", agency.get("IVA", "")),
                ("IVA servicio opcional", agency.get("IVA SERVICIO OPCIONAL", "")),
            ])

if st.session_state.get("opencvcfitform"):
    st.subheader("CVC Fit")
    locator = st.text_input("Localizador", key="cvcfitlocatorwidget")
    if st.button("Buscar y generar PDF", key="run_cvcfit"):
        run_cvc_search(locator, "CVC Fit", "CVC Fit", "cvcfit")

    result = st.session_state.get("cvcfit_result")
    if result:
        st.success("PDF generado correctamente.")
        st.download_button(
            "Descargar PDF",
            data=result["pdf_bytes"],
            file_name=result["filename"],
            mime="application/pdf",
            key="download_cvcfit_pdf",
        )
        render_key_value_grid("cvcfit", [
            ("Localizador", result.get("locator", "")),
            ("Nombre", result.get("nombre", "")),
            ("Spreadsheet", result.get("spreadsheet_name", "")),
        ])
        st.markdown(
            f'<a class="done-link" href="{result["spreadsheet_url"]}" target="_blank" rel="noopener noreferrer">Abrir spreadsheet</a>',
            unsafe_allow_html=True,
        )

if st.session_state.get("opencvcagenciasform"):
    st.subheader("CVC Agencias")
    locator = st.text_input("Localizador", key="cvcagenciaslocatorwidget")
    if st.button("Buscar y generar PDF", key="run_cvcagencias"):
        run_cvc_search(locator, "CVC Agencias", "CVC Agencias", "cvcagencias")

    result = st.session_state.get("cvcagencias_result")
    if result:
        st.success("PDF generado correctamente.")
        st.download_button(
            "Descargar PDF",
            data=result["pdf_bytes"],
            file_name=result["filename"],
            mime="application/pdf",
            key="download_cvcagencias_pdf",
        )
        render_key_value_grid("cvcagencias", [
            ("Localizador", result.get("locator", "")),
            ("Nombre", result.get("nombre", "")),
            ("Spreadsheet", result.get("spreadsheet_name", "")),
        ])
        st.markdown(
            f'<a class="done-link" href="{result["spreadsheet_url"]}" target="_blank" rel="noopener noreferrer">Abrir spreadsheet</a>',
            unsafe_allow_html=True,
        )

if st.session_state.get("openirconfirmacionform"):
    st.subheader("Ir a Confirmación / Go to Confirmation")
    locator = st.text_input("Localizador", key="irconfirmacionlocatorwidget")
    if st.button("Buscar localizador", key="run_irconfirmacion"):
        try:
            result = find_locator_confirmation(locator)
            st.session_state["irconfirmacion_result"] = result
        except Exception as exc:
            st.error(str(exc))

    result = st.session_state.get("irconfirmacion_result")
    if result:
        for line in result.get("log", []):
            st.write(line)
        if result.get("status") == "found":
            st.success("Localizador encontrado.")
            st.markdown(
                f'<a class="done-link" href="{result["url"]}" target="_blank" rel="noopener noreferrer">Abrir confirmación</a>',
                unsafe_allow_html=True,
            )

if st.session_state.get("openinformebarcoform"):
    st.subheader("Informe por Barco / Report by Ship")

    report_type = st.selectbox(
        "Tipo",
        options=["", "NORMAL", "GROUP"],
        key="informetypewidget",
    )

    if report_type:
        root_id = DRIVE_ROOT_ID if report_type == "NORMAL" else GROUPS_ROOT_ID
        years = get_years_by_root(root_id)
        year = st.selectbox("Año", options=[""] + years, key="informeyearwidget")

        if year:
            boats = get_boats_by_root(root_id, year)
            boat = st.selectbox("Barco", options=[""] + boats, key="informeboatwidget")

            if boat:
                departures = get_departures_by_root(root_id, year, boat)
                dep_names = [d["nombre"] for d in departures]
                dep = st.selectbox("Salida", options=[""] + dep_names, key="informesalidawidget")

                if dep and st.button("Extraer informe", key="run_informebarco"):
                    selected = next((d for d in departures if d["nombre"] == dep), None)
                    if selected:
                        try:
                            report = extract_informe_por_barco(selected["id"], selected["nombre"])
                            st.session_state["informeresult"] = report
                        except Exception as exc:
                            st.error(str(exc))

    report = st.session_state.get("informeresult")
    if report:
        st.success(f"Informe generado. Total importe: {report['total_importe']} € · Total PAX: {report['total_pax']}")
        if report["rows"]:
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
                            <th>Tipo Documento</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for row in report["rows"]:
                table_html += f"""
                    <tr>
                        <td>{row['Hoja']}</td>
                        <td>{row['Localizador']}</td>
                        <td>{row['Agencia']}</td>
                        <td>{row['Estado Pago']}</td>
                        <td>{row['Total €']}</td>
                        <td>{row['Cantidad Deposito']}</td>
                        <td>{row['PAX']}</td>
                        <td>{row['Cabinas']}</td>
                        <td>{row['Itinerario']}</td>
                        <td>{row['Duracion']}</td>
                        <td>{row['Tipo Documento']}</td>
                    </tr>
                """
            table_html += """
                    </tbody>
                </table>
            </div>
            """
            st.markdown(table_html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# FOOTER
# ============================================================
st.markdown(
    """
    <div class="portal-footer">
        <div class="footer-text">Crucemundo Hub</div>
        <div class="logout-btn">
    """,
    unsafe_allow_html=True,
)

if st.button("Cerrar sesión", key="logout_btn"):
    do_logout()

st.markdown(
    """
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
