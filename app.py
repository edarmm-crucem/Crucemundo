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

VALID_USERS = {
    "support@crucemundo.com": "Albina",
    "sales@crucemundo.com": "Kristina",
    "cruise@crucemundo.com": "Malvina Shogenova",
    "tania@crucemundo.com": "Tania Bondar",
    "incoming@crucemundo.com": "Tatiana Sereda",
    "operations@crucemundo.com": "Anton Babkin",
    "reservations@crucemundo.com": "Serge",
    "marketing@crucemundo.com": "Asel Botpaeva",
    "alexei@crucemundo.com": "Alexei Prokhorov",
    "anton@crucemundo.com": "Anton Babkin",
    "finance@crucemundo.com": "Aleksandr Dynin",
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


def clear_all_selectors():
    for group_name in ["salida", "crucero", "agencia", "cvcfit", "cvcagencias"]:
        clear_state_group(group_name)
    close_all_panels()
    st.session_state["activepanel"] = None


def open_panel(panel_name):
    clear_all_selectors()
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


def reset_process_state():
    st.session_state["confirmstate"] = "idle"
    st.session_state["sessiontype"] = ""
    st.session_state["nombrecopia"] = ""
    st.session_state["copyurl"] = ""
    st.session_state["processtitle"] = ""
    st.session_state["processresult"] = None


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


def create_work_session(templateid, prefixname, sessiontype):
    displayuser = st.session_state.get("displayname", "").strip() or "Sin usuario"
    fechastr = datetime.now().strftime("%Y%m%d-%H%M")
    nombrecopia = f"SESION - {displayuser} - {prefixname} - {fechastr}"
    descripcion = (
        f"Tipo: {sessiontype} | Usuario: {displayuser} | "
        f"Creado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | "
        f"Sesión generada automáticamente desde Crucemundo Hub."
    )

    progress_bar = st.progress(0.0, text="Iniciando...")
    status_box = st.empty()

    try:
        progress_bar.progress(0.15, text="Preparando sesión...")
        status_box.info("Preparando datos de la nueva sesión...")

        clear_all_selectors()
        reset_process_state()

        progress_bar.progress(0.45, text="Copiando plantilla en Drive...")
        status_box.info("Copiando plantilla en Drive...")

        copia = copy_file_to_folder(templateid, nombrecopia, FOLDER_ID, descripcion)

        progress_bar.progress(0.8, text="Finalizando...")
        status_box.info("Finalizando proceso...")

        result = {
            "status": "ok",
            "name": copia["name"],
            "url": copia.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{copia['id']}/edit",
            "id": copia["id"],
            "sessiontype": sessiontype,
        }

        st.session_state["confirmstate"] = "done"
        st.session_state["sessiontype"] = sessiontype
        st.session_state["nombrecopia"] = result["name"]
        st.session_state["copyurl"] = result["url"]
        st.session_state["processtitle"] = "Estado del Proceso"
        st.session_state["processresult"] = result

        progress_bar.progress(1.0, text="Ok")
        status_box.success("Ok")
        return result

    except Exception as exc:
        progress_bar.empty()
        status_box.empty()
        st.session_state["confirmstate"] = "error"
        st.session_state["processresult"] = None
        raise exc


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
    .section-eyebrow { display: inline-flex; align-items: center; padding: 0.34rem 0.74rem; border-radius: 999px; background: #EAF1FF; border: 1px solid #D6E3FF; color: #2E5FB8; font-size: 0.66rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0 !important; }
    .web-chip, .web-chip-green { display: inline-flex; align-items: center; justify-content: center; padding: 0.34rem 0.74rem; border-radius: 999px; font-size: 0.70rem; font-weight: 700; line-height: 1; text-decoration: none; white-space: nowrap; }
    .web-chip { background: #FFF3BF; border: 1px solid #F4D35E; color: #7A5900 !important; }
    .web-chip-green { background: #E9F8EE; border: 1px solid #BEE3C8; color: #1E6B3A !important; }
    .user-pill { display: inline-flex; align-items: center; gap: 0.4rem; margin: 0.02rem 0 1rem; padding: 0.38rem 0.68rem; border-radius: 999px; background: #fff; border: 1px solid #E4E7EF; font-size: 0.72rem; color: #5D6880; max-width: 100%; word-break: break-word; }
    .action-box { width: 100%; min-height: 210px; border-radius: 22px; padding: 1rem; margin-bottom: 0.85rem; display: flex; flex-direction: column; justify-content: space-between; gap: 0.9rem; border: 1px solid transparent; }
    .card-es { background: #F3F7FF; border-color: #D9E5FF; }
    .card-grupos { background: #F4FBF6; border-color: #D8EEDC; }
    .card-salida { background: #FFF8F1; border-color: #F1DFC7; }
    .card-crucero { background: #F7F4FF; border-color: #E4DDF9; }
    .card-excursiones { background: #EEF8FB; border-color: #D5EAF1; }
    .card-nueva-agencia { background: #F1FAF4; border-color: #D7EEDC; }
    .card-buscar-agencia { background: #FFF7EF; border-color: #F4E1CA; }
    .card-cvcfit { background: #FFF2F7; border-color: #F4D7E3; }
    .card-cvcagencias { background: #EEF9F1; border-color: #D5EEDB; }
    .card-nextcard { background: #F6F7FB; border-color: #E1E5EF; }
    .action-top { display: flex; align-items: flex-start; gap: 0.75rem; }
    .action-icon { width: 38px; height: 38px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0; }
    .action-text { display: flex; flex-direction: column; gap: 0.10rem; min-width: 0; }
    .action-title, .action-title-en { font-size: 0.95rem; font-weight: 700; color: #1F2937; line-height: 1.1; }
    .action-title-en { margin-top: 0.05rem; }
    .action-desc, .action-desc-en { font-size: 0.73rem; color: #6F7B91; line-height: 1.28; }
    .action-desc { margin-top: 0.18rem; }
    .action-desc-en { margin-top: 0.04rem; }
    .action-button-wrap { display: flex !important; justify-content: flex-start !important; align-items: center !important; width: 100% !important; margin-top: 0.1rem; }
    .panel-inline { margin-top: 1rem; padding-top: 0.2rem; width: 100%; max-width: 1100px; }
    .done-link { display: inline-flex; align-items: center; gap: 0.35rem; margin-top: 0.65rem; background: #D9E9FF; color: #214D92 !important; border: 1px solid #BDD6FF; border-radius: 999px; padding: 0.42rem 0.88rem; font-size: 0.71rem; font-weight: 600; text-decoration: none; }
    .agency-card, .cvcfit-card, .cvcfit-status-card, .cvcagencias-card, .cvcagencias-status-card, .process-card {
        background: #FBFCFF; border: 1px solid #E6EBF3; border-radius: 18px; padding: 1rem; margin-top: 0.75rem;
    }
    .agency-grid, .cvcfit-grid, .cvcagencias-grid, .process-grid {
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.85rem 1rem;
    }
    .agency-item-label, .cvcfit-item-label, .cvcagencias-item-label, .process-item-label {
        font-size: 0.68rem; color: #7E889D; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.16rem;
    }
    .agency-item-value, .cvcfit-item-value, .cvcagencias-item-value, .process-item-value {
        font-size: 0.8rem; color: #1F2937; line-height: 1.35; word-break: break-word;
    }
    .cvcfit-log-line, .cvcagencias-log-line {
        font-size: 0.74rem; color: #465066; line-height: 1.45; margin-bottom: 0.35rem; word-break: break-word;
    }
    .portal-footer { margin-top: 1rem; padding: 0.5rem 0 0 0; display: flex; justify-content: space-between; align-items: center; gap: 0.8rem; flex-wrap: wrap; }
    .footer-text { font-size: 0.71rem; color: #A2ABBD; }
    @media (max-width: 1600px) { .agency-grid, .cvcfit-grid, .cvcagencias-grid, .process-grid { grid-template-columns: 1fr; } }
    @media (max-width: 1300px) { .portal-header, .portal-footer { flex-direction: column; align-items: flex-start; } }
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
confirmstate = st.session_state.get("confirmstate", "idle")
excursionesurl = f"https://docs.google.com/spreadsheets/d/{EXCURSIONES_SHEET_ID}/edit"
drive_root_url = f"https://drive.google.com/drive/folders/{DRIVE_ROOT_ID}"
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
        <a class="web-chip-green" href="{cvcfit_folder_url}" target="_blank" rel="noopener noreferrer">Abre Folder CVC Fit</a>
        <a class="web-chip-green" href="https://docs.google.com/spreadsheets/d/1K-Tn_E3QEhCplOP-IFHbKZc-vtKAxFEUBbZVK14EjJI/edit?gid=0#gid=0" target="_blank" rel="noopener noreferrer">Abre Cabinas</a>
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
            <div class="action-box {config['card_class']}">
                <div class="action-top">
                    <div class="action-icon">{config['icon']}</div>
                    <div class="action-text">
                        <div class="action-title">{config['title_es']}</div>
                        <div class="action-title-en">{config['title_en']}</div>
                        <div class="action-desc">{config['desc_es']}</div>
                        <div class="action-desc-en">{config['desc_en']}</div>
                    </div>
                </div>
                <div class="action-button-wrap">
            """,
            unsafe_allow_html=True,
        )

        if config.get("link"):
            st.markdown(
                f'<a class="done-link" href="{config["link"]}" target="_blank">{config["button_label"]}</a>',
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
        "desc_es": f"Crear sesión MASTER de trabajo para {DISPLAYUSER}",
        "desc_en": f"Create MASTER working session for {DISPLAYUSER}",
        "button_label": "Crear Sesión ES",
        "key": "btncreares",
        "action": lambda: create_work_session(
            TEMPLATE_ID_ES,
            "MASTER",
            "es",
        ),
        "disabled": False,
    },
    {
        "card_class": "card-grupos",
        "icon": "👥",
        "title_es": "Nueva Confirmación GRUPOS",
        "title_en": "New GROUPS Confirmation",
        "desc_es": f"Crear sesión MASTER GRUPOS de trabajo para {DISPLAYUSER}",
        "desc_en": f"Create MASTER GROUPS working session for {DISPLAYUSER}",
        "button_label": "Crear Sesión GRUPOS",
        "key": "btncreargrupos",
        "action": lambda: create_work_session(
            TEMPLATE_ID_GRUPOS,
            "MASTER GRUPOS",
            "grupos",
        ),
        "disabled": False,
    },
    {
        "card_class": "card-salida",
        "icon": "🔎",
        "title_es": "Ir a Salida",
        "title_en": "Go to Departure",
        "desc_es": "Buscar una salida existente por año, barco y código de salida",
        "desc_en": "Find an existing departure by year, ship and departure code",
        "button_label": "Buscar Salida",
        "key": "btnirsalida",
        "action": lambda: (open_panel("salida"), st.rerun()),
    },
    {
        "card_class": "card-crucero",
        "icon": "🛳️",
        "title_es": "Crear crucero",
        "title_en": "Create Cruise",
        "desc_es": "Crear salida nueva desde plantilla y guardarla en año/barco",
        "desc_en": "Create a new departure from template and save it in year/ship",
        "button_label": "Nuevo Crucero",
        "key": "btncrearcruceroopen",
        "action": lambda: (open_panel("crucero"), st.rerun()),
    },
    {
        "card_class": "card-excursiones",
        "icon": "🧭",
        "title_es": "Excursiones",
        "title_en": "Excursions",
        "desc_es": "Abrir la hoja de Excursiones",
        "desc_en": "Open the Excursions sheet",
        "button_label": "Abrir Excursiones",
        "key": "btnexcursioneslink",
        "link": excursionesurl,
    },
    {
        "card_class": "card-nueva-agencia",
        "icon": "🏢",
        "title_es": "Nueva Agencia",
        "title_en": "New Agency",
        "desc_es": "Crear una agencia y guardarla en la hoja Datos",
        "desc_en": "Create an agency and save it in Datos sheet",
        "button_label": "Nueva Agencia",
        "key": "btnnuevaagencia",
        "action": lambda: (open_panel("nuevaagencia"), st.rerun()),
    },
    {
        "card_class": "card-buscar-agencia",
        "icon": "📇",
        "title_es": "Buscar Agencia",
        "title_en": "Find Agency",
        "desc_es": "Buscar por cualquier dato y mostrar la ficha completa",
        "desc_en": "Search by any known value and show the full record",
        "button_label": "Buscar Agencia",
        "key": "btnbuscaragencia",
        "action": lambda: (open_panel("buscaragencia"), st.rerun()),
    },
    {
        "card_class": "card-cvcfit",
        "icon": "🧾",
        "title_es": "CVC Fit",
        "title_en": "CVC Fit",
        "desc_es": "Buscar localizador en Booking ES!G11 y descargar PDF de la hoja CVC Fit",
        "desc_en": "Find locator in Booking ES!G11 and download the CVC Fit sheet as PDF",
        "button_label": "Abrir CVC Fit",
        "key": "btncvcfitopen",
        "action": lambda: (open_panel("cvcfit"), st.rerun()),
    },
    {
        "card_class": "card-cvcagencias",
        "icon": "🏷️",
        "title_es": "CVC Agencias",
        "title_en": "CVC Agencies",
        "desc_es": "Buscar localizador en Booking ES!G11 y descargar PDF de la hoja CVC Agencias",
        "desc_en": "Find locator in Booking ES!G11 and download the CVC Agencias sheet as PDF",
        "button_label": "Abrir CVC Agencias",
        "key": "btncvcagenciasopen",
        "action": lambda: (open_panel("cvcagencias"), st.rerun()),
    },
]

cols = st.columns(9, gap="medium")
for col, card in zip(cols, cards):
    render_action_card(col, card)

row2 = st.columns(9, gap="medium")
render_action_card(
    row2[0],
    {
        "card_class": "card-nextcard",
        "icon": "🚀",
        "title_es": "NextCard",
        "title_en": "NextCard",
        "desc_es": "Tarjeta reservada para un uso futuro",
        "desc_en": "Reserved card for future use",
        "button_label": "Próximamente",
        "key": "btnnextcardfuture",
        "disabled": True,
    },
)


# ============================================================
# PANEL ESTADO PROCESO SESIÓN
# ============================================================
if st.session_state.get("confirmstate") == "done" and st.session_state.get("processresult"):
    result = st.session_state["processresult"]
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### Estado del proceso")
    st.success("Ok")
    render_key_value_grid(
        "process",
        [
            ("Tipo de sesión", result.get("sessiontype", "")),
            ("Nombre del archivo", result.get("name", "")),
            ("ID", result.get("id", "")),
            ("Estado", "Ok"),
        ],
    )
    st.markdown(
        f'<a class="done-link" href="{result["url"]}" target="_blank">Abrir sesión creada</a>',
        unsafe_allow_html=True,
    )
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
                    f'<a class="done-link" href="{selectedobj["url"]}" target="_blank">Abrir salida · Open departure</a>',
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
                        f'<a class="done-link" href="{result["url"]}" target="_blank">Abrir archivo existente · Open existing file</a>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.success(f"Archivo creado / File created: {result['name']}")
                    st.markdown(
                        f'<a class="done-link" href="{result["url"]}" target="_blank">Abrir crucero · Open cruise</a>',
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
                ("Localizador", result["locator"]),
                ("Nombre pasajero", result["nombre"]),
                ("Spreadsheet origen", result["spreadsheet_name"]),
                ("Nombre del PDF", result["filename"]),
            ],
        )
        cola, colb = st.columns([1, 3], gap="small")
        with cola:
            st.download_button(
                label="⬇ Descargar PDF",
                data=result["pdf_bytes"],
                file_name=result["filename"],
                mime="application/pdf",
                key="btncvcfitdownload",
                type="primary",
            )
        with colb:
            st.markdown(
                f'<a class="done-link" href="{result["spreadsheet_url"]}" target="_blank">📊 Abrir hoja origen en Drive</a>',
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
                ("Localizador", result["locator"]),
                ("Nombre pasajero", result["nombre"]),
                ("Spreadsheet origen", result["spreadsheet_name"]),
                ("Nombre del PDF", result["filename"]),
            ],
        )
        cola, colb = st.columns([1, 3], gap="small")
        with cola:
            st.download_button(
                label="⬇ Descargar PDF",
                data=result["pdf_bytes"],
                file_name=result["filename"],
                mime="application/pdf",
                key="btncvcagenciasdownload",
                type="primary",
            )
        with colb:
            st.markdown(
                f'<a class="done-link" href="{result["spreadsheet_url"]}" target="_blank">📊 Abrir hoja origen en Drive</a>',
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# FOOTER
# ============================================================
footer_col1, footer_col2 = st.columns([3, 1])
with footer_col1:
    st.markdown('<div class="portal-footer"><div class="footer-text">Crucemundo Hub · Clean version</div></div>', unsafe_allow_html=True)
with footer_col2:
    if st.button("Cerrar sesión", key="btnlogout"):
        do_logout()

st.markdown("</div>", unsafe_allow_html=True)
