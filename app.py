import streamlit as st
from datetime import datetime, date, timedelta
import urllib.parse
import time
import re
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


st.set_page_config(
    page_title="Crucemundo Hub",
    page_icon="🛳️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

LOGO_ID = "1N7eaCKP1Jeg8KuDXRjJ8tZLhnKStMZ8"
LOGO_URL = f"https://lh3.googleusercontent.com/d/{LOGO_ID}"

TEMPLATE_ID_ES = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
TEMPLATE_ID_GRUPOS = "1Z7ktX3PhVkMibWpzdrDDqAT4aPsmjzSJPf1SgZcL5-w"
TEMPLATE_ID_CRUCERO = "1zSJPi6St_Z5Jw1c6eieVnKI4NyEdP7E9n3WTZ9yy3C0"

EXCURSIONES_SHEET_ID = "1ojMHeoosUyel8BA2XTmDsmyDJf_vvJrrJNOyxn2u1jg"
AGENCY_SHEET_ID = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
AGENCY_SHEET_NAME = "Datos"
FOLDER_ID = "1MxMdeBlUG6v5n2upobsjNbQNQ8FCsO"
DRIVE_ROOT_ID = "11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm"

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

BARCOS_MAP = {
    "ALB": "MS_ALBERTINA",
    "ARN": "MS_ARENA",
    "CV": "MS_CRUCEVITA",
    "DC": "MS_DOURO_CRUISER",
    "FID": "MS_FIDELIO",
    "LEO": "MS_LEONORA",
    "RDA": "MS_RIVER_DIAMOND",
    "RSA": "MS_RIVER_SAPPHIRE",
    "SPL": "MS_SWISS_SPLENDOR",
    "VGR": "MS_VISTA_GRACIA",
    "VMI": "MS_VISTAMILLA",
    "VRI": "MS_VISTAR_IO",
}

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
        f"?copyDestination={FOLDER_ID}"
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
            fields="nextPageToken, files(id, name, mimeType, webViewLink, description)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            pageToken=pagetoken,
            pageSize=1000,
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


def extract_first_number(value):
    if value is None:
        return 0
    m = re.search(r"(\d+)", str(value))
    return int(m.group(1)) if m else 0


def safe_filename(text):
    text = re.sub(r'[\\/:*?"<>|]', "", str(text))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def first_line(value):
    if value is None:
        return ""
    return str(value).splitlines()[0].strip()


def parse_nombre_apellidos_from_g24(g24_value):
    raw = first_line(g24_value)
    if "/" in raw:
        nombre, apellidos = raw.split("/", 1)
        return nombre.strip(), apellidos.strip()
    return raw.strip(), ""


def parse_locator(locator):
    locator = normalize_text(locator).upper().replace(" ", "")
    m = re.fullmatch(r"([A-Z]+)(\d{2})(\d{2})(\d{2})-(\d{3})", locator)
    if not m:
        raise Exception("El localizador debe tener formato BARCOAAMMDD-XXX, por ejemplo ALB260101-001.")
    code, yy, mm, dd, seq = m.groups()
    if code not in BARCOS_MAP:
        raise Exception(f"Código de barco no reconocido: {code}")
    full_boat = BARCOS_MAP[code]
    departure_name = f"{full_boat}_{yy}{mm}{dd}"
    year_4 = f"20{yy}"
    fecha_salida = datetime.strptime(f"{year_4}-{mm}-{dd}", "%Y-%m-%d").date()
    return {
        "locator": locator,
        "boat_code": code,
        "boat_name": full_boat,
        "yy": yy,
        "mm": mm,
        "dd": dd,
        "seq": seq,
        "year_folder": year_4,
        "departure_file_name": departure_name,
        "fecha_salida": fecha_salida,
        "fecha_limite_pago": fecha_salida - timedelta(days=30),
    }


def find_drive_file_for_locator(locator_info):
    year_folder = find_child_folder(DRIVE_ROOT_ID, locator_info["year_folder"])
    if not year_folder:
        raise Exception(f"No existe la carpeta del año {locator_info['year_folder']}.")
    boat_folder = find_child_folder(year_folder["id"], locator_info["boat_name"])
    if not boat_folder:
        raise Exception(f"No existe la carpeta del barco {locator_info['boat_name']} en {locator_info['year_folder']}.")
    target_file = find_file_by_name(boat_folder["id"], locator_info["departure_file_name"])
    if not target_file:
        raise Exception(f"No existe el archivo {locator_info['departure_file_name']}.")
    return {
        "id": target_file["id"],
        "name": target_file["name"],
        "url": target_file.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{target_file['id']}/edit",
    }


def get_sheet_titles(spreadsheet_id):
    sheetsservice = get_sheets_service()
    spreadsheet = sheetsservice.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return [s["properties"]["title"] for s in spreadsheet.get("sheets", [])]


def get_sheet_values(spreadsheet_id, range_a1):
    sheetsservice = get_sheets_service()
    return sheetsservice.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_a1,
        majorDimension="ROWS",
    ).execute().get("values", [])


def get_single_cell(spreadsheet_id, sheet_title, a1):
    values = get_sheet_values(spreadsheet_id, f"'{sheet_title}'!{a1}")
    if values and values[0]:
        return values[0][0]
    return ""


def get_range(spreadsheet_id, sheet_title, a1_range):
    return get_sheet_values(spreadsheet_id, f"'{sheet_title}'!{a1_range}")


def build_money_text(matrix):
    lines = []
    for row in matrix:
        cleaned = [str(c).strip() for c in row if str(c).strip()]
        if cleaned:
            lines.append(" | ".join(cleaned))
    return "\n".join(lines).strip()


def underline_paragraph(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "000000")
    pBdr.append(bottom)
    pPr.append(pBdr)


def build_cvc_fit_doc(data):
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(10)

    def add_line(text="", bold=False, align=None, size=None):
        p = doc.add_paragraph()
        if align is not None:
            p.alignment = align
        r = p.add_run(text)
        r.bold = bold
        if size:
            r.font.size = Pt(size)
        return p

    def add_section_title(text):
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.bold = True
        r.font.size = Pt(11)
        return p

    def add_blank_line():
        doc.add_paragraph()

    add_line("Lugar y fecha: ________________________________", align=WD_ALIGN_PARAGRAPH.RIGHT)

    title = add_line("CONTRATO DE VIAJE COMBINADO", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=14)
    underline_paragraph(title)
    add_blank_line()

    add_section_title("DATOS DE LA AGENCIA DE VIAJES ORGANIZADORA Y MINORISTA")
    add_line("Nombre: CRUCEMUNDO S.L")
    add_line("Domicilio: Av. Europa, 86, building 2A, suite 25, cp. 08850 Gavà, Spain")
    add_line("NIF: B64955172")
    add_line("Teléfono: 934542041")
    add_line("E-mail: info@crucemundo.es")
    add_blank_line()

    add_section_title("DATOS DEL VIAJERO")
    add_line(f"Nombre: {data['nombre']}")
    add_line(f"Apellidos: {data['apellidos']}")
    add_line(f"DNI / Pasaporte: {data['dni']}")
    add_line("Dirección:")
    add_line("Población:")
    add_line("C. Postal:")
    add_line("E-mail:")
    add_line("Teléfono particular:")
    add_line(f"Nº Personas: {data['personas']}")
    add_line(f"Nº Habitaciones: {data['habitaciones']}")
    add_blank_line()

    add_section_title("CONDICIONES DEL VIAJE")
    bloques = [
        "El viajero manifiesta que, antes de quedar obligado por el presente contrato de viaje combinado y oferta correspondiente, ha recibido la información precontractual establecida en el artículo 153.1 del Real Decreto Legislativo 1/2007, de 16 de noviembre, compuesta por el formulario con la información normalizada relativa al viaje combinado ANEXO I y la información aplicable al viaje combinado.",
        "Nombre y datos contacto entidades garantes en caso de insolvencia y del cumplimiento de la ejecución del contrato de viaje combinado de la agencia de viajes: en documento resumen que figura en el ANEXO II.",
        "Condiciones generales: el viajero manifiesta aceptar las Condiciones Generales del contrato de viaje combinado que se acompañan en el ANEXO III y que obran en su poder.",
        "Condiciones particulares: en base a la descripción de los servicios de viaje que figuran en el ANEXO IV.",
    ]
    for t in bloques:
        add_line(t)
    add_blank_line()

    add_section_title("DATOS DEL VIAJE")
    viaje = [
        "Destinos: Según ANEXO IV.",
        "Itinerario: Según ANEXO IV.",
        "Periodos estancia y sus fechas: Según ANEXO IV.",
        "Nº de pernoctaciones incluidas: Según ANEXO IV.",
        "Medio de transporte, características, categoría y duración: Según ANEXO IV.",
        f"Fecha de salida: {data['fecha_salida_str']}.",
        "Hora salida: Según PVP sujeto a cambios / Según ANEXO IV.",
        "Lugar de salida: Según ANEXO IV.",
        "Fecha de regreso: Según ANEXO IV.",
        "Lugar de regreso: Según ANEXO IV.",
        "Hora regreso: Según PVP sujeto a cambios / Según ANEXO IV.",
        "Paradas intermedias y conexiones: Según ANEXO IV.",
        "Ubicación, principales características y categoría del alojamiento: Según ANEXO IV.",
        "Comidas previstas: Según ANEXO IV.",
        "Visitas, excursiones u otros servicios incluidos en viaje: Según ANEXO IV.",
        "Indicación de si es viaje en grupo y, si se puede, tamaño aprox. grupo: Según ANEXO IV.",
        "Idioma prestación servicios: Según ANEXO IV.",
        "Necesidades especiales del viajero aceptadas por el organizador:",
    ]
    for t in viaje:
        add_line(t)
    add_blank_line()

    add_section_title("PRECIO Y FORMA DE PAGO")
    add_line("Precio y Forma de pago:")
    if data["dinero_text"]:
        for linea in data["dinero_text"].splitlines():
            add_line(linea)
    else:
        add_line("(Sin detalle extraído del rango G33:R53)")
    add_line(f"Total: {data['total']}")
    add_line(f"Fecha límite y/o calendario de pago del importe pendiente: {data['fecha_limite_pago_str']}")
    add_line("Modalidades de pago: Transferencia bancaria.")
    add_blank_line()

    add_section_title("INFORMACIÓN ADICIONAL")
    adicionales = [
        "Revisión de los precios: Estos precios han sido calculados en fecha ____________________ en base a los tipos de cambio de divisa, al precio de transporte derivado coste combustible o de otras fuentes de energía y al nivel de impuestos y tasas sobre los servicios de viaje incluidos en el contrato vigentes en dicha fecha. Hasta 20 días antes de la salida, los precios podrán incrementarse de acuerdo con lo establecido en el apartado 11 de las Condiciones Generales ANEXO III. De igual modo el viajero tendrá derecho a reducción de precio por variación a su favor de dichos conceptos, pudiendo la agencia de viajes en tal caso deducir del reembolso los gastos administrativos reales de su tramitación.",
        "El viaje es apto para personas de movilidad reducida (persona cuya movilidad para participar en el viaje se halle reducida por motivos de discapacidad física, sensorial o locomotriz, permanente o temporal, discapacidad o deficiencia intelectual o cualquier otra causa de discapacidad, o por la edad, y cuya situación requiera una atención adecuada y la adaptación a sus necesidades particulares del servicio puesto a disposición de los demás participantes): SI / NO.",
        "Mínimo de personas: La realización del presente viaje requiere la participación de un mínimo de 70 personas. De no llegarse a este mínimo, la agencia tiene derecho a anular el viaje hasta 20 días antes de la fecha de salida. La realización del presente viaje no requiere la participación de un número mínimo de personas.",
        "Requisitos entrada para turistas de los que fue informado el viajero en el momento de efectuar la reserva: DNI / Pasaporte / Visados / Vacunas / Tiempo aproximado obtención visados.",
        "El viajero manifiesta que ha sido informado de la situación y requisitos del país o países objeto de su viaje de acuerdo con la información publicada en la página web del Ministerio de Asuntos Exteriores y Cooperación (www.exteriores.gob.es) y que conoce, por lo tanto, las características y posibles riesgos de toda índole del país o países de destino.",
        "Resolución voluntaria del viaje por el viajero antes de la salida: el viajero, en cualquier momento antes del inicio del viaje, puede resolver el contrato debiendo abonar una penalización de: con más de 42 días antes de la salida, 20%; entre 42 y 28 días antes, 40%; entre 27 y 15 días antes, 60%; entre 14 y 7 días antes, 75%; menos de 7 días antes de la salida, 100%.",
        "Seguro facultativo de asistencia en viaje: El viajero declara haber sido informado de la posibilidad de contratar un seguro de asistencia en viaje de la compañía aseguradora, póliza número ____, así como de las coberturas, exclusiones, condiciones generales y particulares de este seguro. Su voluntad es: No contratar / Contratar.",
        "Seguro facultativo de gastos de anulación por fuerza mayor: El viajero declara haber sido informado de la posibilidad de contratar un seguro de gastos de anulación de la compañía aseguradora, póliza número ____, así como de las coberturas, exclusiones, condiciones generales y particulares de este seguro. Su voluntad es: No contratar / Contratar.",
        "Cesión del viaje: Conforme a lo establecido en el apartado 12 de las Condiciones Generales ANEXO III, el viajero podrá ceder su reserva a una persona que reúna todas las condiciones requeridas.",
        "Datos de contacto en caso de asistencia y falta de conformidad: Representante local, si hay: Nombre / Dirección / Teléfono / e-mail. Otros puntos de contacto o servicio de asistencia de la agencia de viajes: Teléfono +34 934542041, e-mail info@crucemundo.es. Para cualquier aspecto relacionado con asistencia sanitaria, si el viajero ha contratado un seguro de asistencia en viaje, deberá contactar también con el teléfono de la compañía aseguradora.",
        "Contacto información menores no acompañados: En caso de menores no acompañados por un familiar u otro adulto autorizado, pueden establecer contacto directo con el menor o con la persona responsable durante la estancia a través de ____.",
        "Falta de conformidad: El viajero durante el viaje deberá informar toda falta de conformidad en la prestación de los servicios, todo ello de acuerdo con lo establecido en el apartado 16 de las Condiciones Generales ANEXO III.",
        "Responsabilidad: La agencia de viajes es responsable de la correcta ejecución de todos los servicios de viaje incluidos en el contrato, de conformidad con el artículo 161 del Real Decreto Legislativo 1/2007 y está obligada a prestar asistencia si el viajero se halla en dificultades de conformidad con el artículo 163.2 de dicha norma y de acuerdo con lo establecido en las condiciones generales del contrato ANEXO III.",
        "Deberá dirigirse directamente a la compañía aseguradora AXA Seguros Generales, S.A. de Seguros y Reaseguros a través de: 1) Teléfonos 902 013 345 / 91 111 95 44. 2) Email del Depto. de Siniestros: aperturas.empresas@axa.es. 3) Presentando su reclamación en alguna de las oficinas AXA.",
        "Real Decreto 933/2021: Conforme a lo dispuesto en el Real Decreto 933/2021, de 26 de octubre, por el que se establecen las obligaciones de registro documental e información de las personas físicas o jurídicas que contratan actividades de hospedaje y alquiler de vehículos a motor, los datos que se recojan en aplicación de dicha normativa podrán ser accesibles a la policía y las autoridades públicas en el desempeño de sus respectivas competencias en el ámbito de prevención, detección e investigación del delito que tengan asignadas. No se procederá a la comunicación a terceros de los datos personales recogidos en virtud de la citada norma, excepto por obligación legal o requerimiento judicial.",
    ]
    for t in adicionales:
        add_line(t)
    add_blank_line()

    add_section_title("FIRMAS")
    add_line("El presente contrato de viaje combinado se firma por duplicado en el lugar y fecha arriba indicado y a un único efecto, entregándose en este mismo momento un ejemplar al viajero.")
    add_line("Firma viajero: ____________________")
    add_line("Firma agencia de viajes: ____________________")

    doc.add_page_break()

    add_line("ANEXO I", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=13)
    add_line("CERTIFICADO DE SEGURO DE CAUCIÓN AG. VIAJES", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=12)
    add_blank_line()

    annex_paragraphs = [
        "El presente certificado se emite al amparo de lo establecido en el artículo 155.2.c del Real Decreto Legislativo 1/2007, de 16 de noviembre, por el que se aprueba el texto refundido de la Ley General para la Defensa de los Consumidores y Usuarios y otras leyes complementarias.",
        "Crucemundo S.L. dispone de la garantía por insolvencia establecida para los viajes combinados en el Art. 252-10 de la Ley 22/2010, de 20 de julio, del Código de Consumo de Cataluña, formalizada a través de la póliza de caución número 72974394 con la compañía aseguradora AXA Seguros Generales, S.A. de Seguros y Reaseguros, domiciliada en la calle Monseñor Palmer, 1, 07014 Palma de Mallorca. Dicha garantía está plenamente vigente.",
        "Procedimiento en caso de que, dándose la situación de insolvencia de la agencia de viajes cubierta por la garantía, el consumidor precise activarla.",
        "Para la gestión y cumplimiento del objeto del contrato, puede resultar necesario y obligatorio para la prestación del servicio, que sus datos, incluida información sobre alergias, intolerancias alimentarias, minusvalías, etc., tengan que ser comunicados a proveedores tales como compañías aéreas, navieras, hoteles y otros proveedores de servicios, los cuales estarán obligados a utilizar los datos, única y exclusivamente, para dar cumplimiento al objeto del contrato. Estos proveedores, dependiendo del país de destino de su viaje, podrán estar ubicados en países para los que sea necesario realizar una transferencia internacional de datos incluyendo, si fuera el caso, aquellos que no ofrezcan un nivel de protección equiparable a la exigida por la UE, considerándose por tanto una transferencia internacional de datos autorizada expresamente por el interesado.",
        "Conservación de los datos: Mantendremos su información personal mientras exista una relación contractual y/o comercial con usted, o mientras usted no ejerza su derecho de supresión, cancelación y/o limitación del tratamiento de sus datos. También mantendremos sus datos únicamente al efecto de cumplimiento legal un máximo de 10 años desde la finalización del contrato, si por las características del viaje estuviera afectado por la Ley 10/2010, de 28 de abril, de prevención del blanqueo de capitales y la financiación del terrorismo. Los datos accesorios que Ud. nos informa, p.e. preferencias alimentarias, posibles intolerancias, etc., serán eliminados de nuestros sistemas una vez concluido el servicio o viaje.",
        "Reclamaciones tras el viaje: El viajero podrá dirigir sus reclamaciones a la dirección postal que consta en el encabezamiento y a la siguiente dirección de correo electrónico: info@crucemundo.es.",
        "Tratamiento de datos personales: De acuerdo con Reglamento (UE) 2016/679 del Parlamento Europeo y del Consejo, de 27 de abril de 2016 (RGPD) y la Ley Orgánica 3/2018, de 5 de diciembre, de Protección de Datos Personales y Garantía de los Derechos Digitales, el cliente acepta que los datos personales que informa en este documento así como los que puedan ser facilitados en el futuro para el mismo fin, sean recogidos y tratados por la agencia. Dichos datos han sido recogidos por la agencia con la finalidad de gestionar y desarrollar el conjunto de servicios estipulados en este contrato con el cliente, siendo necesarios para cumplir dichos propósitos. El afectado podrá ejercitar los derechos reconocidos en el RGPD y, en particular, los de acceso, limitación, rectificación, supresión, oposición y olvido, a través de un escrito que podrá dirigir a la sede social de la Agencia en la dirección indicada, con la referencia Protección de Datos.",
        "Comunicación y transferencia de datos: La Agencia le informa que, dependiendo de la modalidad de pago de los servicios, se procederá a la comunicación de los datos incluidos en dicho fichero (Nombre, CIF/NIF, Nº-Cuenta) a las Entidades Financieras (Bancos y Cajas) con las que trabaja la Agencia, a los solos efectos de gestionar las transferencias, cobros y pagos a que dé lugar la relación comercial y el uso de nuestros servicios.",
    ]
    for txt in annex_paragraphs:
        add_line(txt)

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio


def build_cvc_fit_from_locator(locator):
    locator_info = parse_locator(locator)
    drive_file = find_drive_file_for_locator(locator_info)
    spreadsheet_id = drive_file["id"]

    sheet_titles = get_sheet_titles(spreadsheet_id)
    if locator_info["locator"] not in sheet_titles:
        raise Exception(f"No existe una pestaña con nombre {locator_info['locator']} dentro del spreadsheet.")

    sheet_title = locator_info["locator"]

    g24 = get_single_cell(spreadsheet_id, sheet_title, "G24")
    p24 = get_single_cell(spreadsheet_id, sheet_title, "P24")

    nombre, apellidos = parse_nombre_apellidos_from_g24(g24)
    dni = first_line(p24)

    values_people = [
        get_single_cell(spreadsheet_id, sheet_title, "G22"),
        get_single_cell(spreadsheet_id, sheet_title, "K22"),
        get_single_cell(spreadsheet_id, sheet_title, "N22"),
        get_single_cell(spreadsheet_id, sheet_title, "P22"),
    ]
    personas = sum(extract_first_number(v) for v in values_people)

    values_rooms = [
        get_single_cell(spreadsheet_id, sheet_title, "G20"),
        get_single_cell(spreadsheet_id, sheet_title, "K20"),
        get_single_cell(spreadsheet_id, sheet_title, "N20"),
        get_single_cell(spreadsheet_id, sheet_title, "P20"),
    ]
    habitaciones = sum(extract_first_number(v) for v in values_rooms)

    dinero = get_range(spreadsheet_id, sheet_title, "G33:R53")
    total = get_single_cell(spreadsheet_id, sheet_title, "Q55")

    fecha_salida = locator_info["fecha_salida"]
    fecha_limite_pago = locator_info["fecha_limite_pago"]

    filename = safe_filename(
        f"CVC Fit {apellidos} {nombre} {locator_info['boat_name']} salida {fecha_salida.strftime('%d %m')}.docx"
    )

    payload = {
        "locator": locator_info["locator"],
        "boat_name": locator_info["boat_name"],
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_url": drive_file["url"],
        "sheet_title": sheet_title,
        "nombre": nombre,
        "apellidos": apellidos,
        "dni": dni,
        "personas": personas,
        "habitaciones": habitaciones,
        "dinero_matrix": dinero,
        "dinero_text": build_money_text(dinero),
        "total": total,
        "fecha_salida": fecha_salida,
        "fecha_salida_str": fecha_salida.strftime("%d/%m/%Y"),
        "fecha_limite_pago": fecha_limite_pago,
        "fecha_limite_pago_str": fecha_limite_pago.strftime("%d/%m/%Y"),
        "filename": filename,
    }
    return payload


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

    div.st-key-btncreares button { background: #EEF4FF !important; }
    div.st-key-btncreargrupos button { background: #ECF8EF !important; }
    div.st-key-btnirsalida button { background: #FFF3E4 !important; }
    div.st-key-btncrearcruceroopen button,
    div.st-key-btncrearcruceroaction button { background: #F1EBFF !important; }
    div.st-key-btnexcursiones button { background: #E9F7FB !important; }
    div.st-key-btnnuevaagencia button,
    div.st-key-btnguardaragencia button { background: #EAF8F0 !important; }
    div.st-key-btnbuscaragencia button,
    div.st-key-btnejecutarbusquedaagencia button { background: #FFF4EA !important; }
    div.st-key-btncvcfitopen button,
    div.st-key-btncvcfitaction button,
    div.st-key-btncvcfitdownload button { background: #FFEFF5 !important; }

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
    .card-es .action-icon { background: #E6EEFF; border: 1px solid #D2DFFF; }
    .card-grupos .action-icon { background: #E7F5EA; border: 1px solid #D0EAD7; }
    .card-salida .action-icon { background: #FFF0DD; border: 1px solid #F2DEC0; }
    .card-crucero .action-icon { background: #EEE8FF; border: 1px solid #DDD2FF; }
    .card-excursiones .action-icon { background: #E2F2F7; border: 1px solid #CFE6EE; }
    .card-nueva-agencia .action-icon { background: #E2F4E7; border: 1px solid #CFE5D6; }
    .card-buscar-agencia .action-icon { background: #FDEBD9; border: 1px solid #F2D9B9; }
    .card-cvcfit .action-icon { background: #FFE3EE; border: 1px solid #F5CADC; }

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


USEREMAIL = st.session_state.get("useremail", "").strip()
DISPLAYUSER = st.session_state.get("displayname", "").strip() or "Sin usuario"
SALUDO = get_saludo()
SALUDOEN = get_saludo_en()
confirmstate = st.session_state.get("confirmstate", "idle")
excursionesurl = f"https://docs.google.com/spreadsheets/d/{EXCURSIONES_SHEET_ID}/edit"

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
st.markdown(f'<div class="user-pill">{DISPLAYUSER} · {USEREMAIL}</div>', unsafe_allow_html=True)

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
        f'<a class="done-link" href="{excursionesurl}" target="_blank">Abrir Excursiones</a>',
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

row2col1, row2col2, row2col3, row2col4, row2col5, row2col6, row2col7 = st.columns(7, gap="medium")

with row2col1:
    st.markdown(
        """
        <div class="action-box card-cvcfit">
            <div class="action-top">
                <div class="action-icon">🧾</div>
                <div class="action-text">
                    <div class="action-title">CVC Fit</div>
                    <div class="action-title-en">CVC Fit</div>
                    <div class="action-desc">Buscar por localizador y generar el DOC del contrato</div>
                    <div class="action-desc-en">Find by locator and generate the contract DOC</div>
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
    except Exception as e:
        st.exception(e)
    st.markdown("</div>", unsafe_allow_html=True)


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
            previewname = f"{cruceroboat}{fechasalida.strftime('%y%m%d')}"
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
    except Exception as e:
        st.exception(e)
    st.markdown("</div>", unsafe_allow_html=True)


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


if st.session_state.get("opencvcfitform"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("### CVC Fit")
    locator = st.text_input(
        "Localizador",
        key="cvcfitlocatorwidget",
        placeholder="Ej: ALB260101-001",
    )

    if st.button("Generar CVC Fit", key="btncvcfitaction", disabled=not locator):
        try:
            payload = build_cvc_fit_from_locator(locator)
            doc_io = build_cvc_fit_doc(payload)
            payload["doc_bytes"] = doc_io.getvalue()
            st.session_state["cvcfit_result"] = payload
            st.success("Documento generado correctamente.")
        except Exception as e:
            st.session_state["cvcfit_result"] = None
            st.exception(e)

    result = st.session_state.get("cvcfit_result")
    if result:
        st.markdown('<div class="cvcfit-card"><div class="cvcfit-grid">', unsafe_allow_html=True)
        fields = [
            ("Localizador", result["locator"]),
            ("Barco", result["boat_name"]),
            ("Salida", result["fecha_salida_str"]),
            ("Límite pago", result["fecha_limite_pago_str"]),
            ("Nombre", result["nombre"]),
            ("Apellidos", result["apellidos"]),
            ("DNI", result["dni"]),
            ("Personas", result["personas"]),
            ("Habitaciones", result["habitaciones"]),
            ("Total", result["total"]),
            ("Pestaña", result["sheet_title"]),
            ("Archivo Drive", result["filename"]),
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
            f'<a class="done-link" href="{result["spreadsheet_url"]}" target="_blank">Abrir hoja origen</a>',
            unsafe_allow_html=True,
        )

        st.download_button(
            "Descargar DOCX",
            data=result["doc_bytes"],
            file_name=result["filename"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="btncvcfitdownload",
        )
    st.markdown("</div>", unsafe_allow_html=True)


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
                <a class="done-link" href="{savedurl}" target="_blank">Abrir sesión · Open session</a>
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

if confirmstate == "done" and savedname and not st.session_state.get(f"opened_{savedname}"):
    st.session_state[f"opened_{savedname}"] = True
    st.markdown(
        f"<script>setTimeout(()=>window.open('{savedurl}','_blank'),300);</script>",
        unsafe_allow_html=True,
    )

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
                <a class="history-link" href="{entry["url"]}" target="_blank">Abrir · Open</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown(
    f"""
    <div class="portal-footer">
        <span class="footer-text">Panel de Control · Control Panel · v4.3.1</span>
        <span class="footer-text">Raíz Drive · Drive Root · {DRIVE_ROOT_ID}</span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)
