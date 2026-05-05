import streamlit as st
from datetime import datetime, date, timedelta
import re
import urllib.parse
from io import BytesIO
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_UNDERLINE
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Crucemundo Hub",
    page_icon="🛳️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

LOGO_ID = "1N7eaCKP1Jeg8KuDXRjJ8t_ZLhnKStMZ8"
LOGO_URL = f"https://lh3.googleusercontent.com/d/{LOGO_ID}"

TEMPLATE_ID_ES = "15yrUtEyIn6ZWT2Oy22f5ISvqovvBuEfSzBVlTTtiy5E"
TEMPLATE_ID_GRUPOS = "1Z7ktX3PhVkMibWpzdrDDqAT4aPsmjzSJPf1SgZcL5-w"
TEMPLATE_ID_CRUCERO = "1zSJPi6St_Z5Jw1c6eieVnKI4NyEdP7E9n3WTZ9yy3C0"
EXCURSIONES_SHEET_ID = "1ojMHeoosUyel8BA2XTmDsmyDJf_vvJrrJNOyxn2u1jg"
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

BARCOS_MAP = {
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
    "MS_VISTA_RIO": "VRI"
}
BARCOS_INV = {v: k for k, v in BARCOS_MAP.items()}

for k, v in {
    "authenticated": False,
    "user_email": "",
    "display_name": "",
    "confirm_state": "idle",
    "historial": [],
    "session_type": "",
    "active_panel": None,
    "open_salida_form": False,
    "open_crucero_form": False,
    "open_nueva_agencia_form": False,
    "open_buscar_agencia_form": False,
    "open_cvc_fit_form": False,
    "salida_year": None,
    "salida_boat": None,
    "salida_name": None,
    "crucero_year": None,
    "crucero_boat": None,
    "agency_matches": [],
    "agency_selected_idx": None,
    "cvc_locator": "",
    "cvc_result": None,
    "cvc_download_name": "",
    "cvc_download_bytes": None,
}.items():
    st.session_state.setdefault(k, v)

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
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
    for k in ["salida_year", "salida_boat", "salida_name", "salida_year_widget", "salida_boat_widget", "salida_name_widget"]:
        st.session_state.pop(k, None)

def clear_crucero_state():
    for k in ["crucero_year", "crucero_boat", "crucero_year_widget", "crucero_boat_widget"]:
        st.session_state.pop(k, None)

def clear_agencia_state():
    for k in [
        "agency_matches", "agency_selected_idx", "agency_search_query",
        "ag_nombre", "ag_codigo", "ag_grupo_gest", "ag_telefono", "ag_email",
        "ag_direccion", "ag_comision", "ag_comision_oferta", "ag_comision_2x1",
        "ag_iva", "ag_iva_servicio_opcional"
    ]:
        st.session_state.pop(k, None)

def clear_cvc_state():
    for k in ["cvc_locator", "cvc_result", "cvc_download_name", "cvc_download_bytes"]:
        st.session_state.pop(k, None)

def close_all_panels():
    st.session_state["open_salida_form"] = False
    st.session_state["open_crucero_form"] = False
    st.session_state["open_nueva_agencia_form"] = False
    st.session_state["open_buscar_agencia_form"] = False
    st.session_state["open_cvc_fit_form"] = False

def open_panel(panel_name):
    close_all_panels()
    if panel_name == "salida":
        clear_crucero_state(); clear_agencia_state(); clear_cvc_state()
        st.session_state["open_salida_form"] = True
    elif panel_name == "crucero":
        clear_salida_state(); clear_agencia_state(); clear_cvc_state()
        st.session_state["open_crucero_form"] = True
    elif panel_name == "nueva_agencia":
        clear_salida_state(); clear_crucero_state(); clear_agencia_state(); clear_cvc_state()
        st.session_state["open_nueva_agencia_form"] = True
    elif panel_name == "buscar_agencia":
        clear_salida_state(); clear_crucero_state(); clear_agencia_state(); clear_cvc_state()
        st.session_state["open_buscar_agencia_form"] = True
    elif panel_name == "cvc_fit":
        clear_salida_state(); clear_crucero_state(); clear_agencia_state(); clear_cvc_state()
        st.session_state["open_cvc_fit_form"] = True
    st.session_state["active_panel"] = panel_name

def clear_all_selectors():
    clear_salida_state()
    clear_crucero_state()
    clear_agencia_state()
    clear_cvc_state()
    close_all_panels()
    st.session_state["active_panel"] = None

def do_logout():
    keys_to_delete = [
        "authenticated", "user_email", "display_name", "confirm_state",
        "session_type", "active_panel", "open_salida_form", "open_crucero_form",
        "open_nueva_agencia_form", "open_buscar_agencia_form", "open_cvc_fit_form",
        "salida_year", "salida_boat", "salida_name",
        "crucero_year", "crucero_boat",
        "salida_year_widget", "salida_boat_widget", "salida_name_widget",
        "crucero_year_widget", "crucero_boat_widget",
        "nombre_copia", "copy_url", "process_title",
        "agency_matches", "agency_selected_idx", "agency_search_query",
        "ag_nombre", "ag_codigo", "ag_grupo_gest", "ag_telefono", "ag_email",
        "ag_direccion", "ag_comision", "ag_comision_oferta", "ag_comision_2x1",
        "ag_iva", "ag_iva_servicio_opcional",
        "cvc_locator", "cvc_result", "cvc_download_name", "cvc_download_bytes"
    ]
    for k in keys_to_delete:
        st.session_state.pop(k, None)
    st.rerun()

def render_step(label, detail, state):
    dot_class = {"done": "sd-done", "active": "sd-active", "wait": "sd-wait"}[state]
    text_class = {"done": "st-done", "active": "st-active", "wait": "st-wait"}[state]
    symbol = {"done": "✓", "active": "•", "wait": "•"}[state]
    st.markdown(f"""
    <div class="step">
        <div class="step-dot {dot_class}">{symbol}</div>
        <div class="step-content">
            <div class="{text_class}">{label}</div>
            <div class="step-detail">{detail}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def iniciar_proceso(session_type, template_id, prefix_name, process_title):
    clear_all_selectors()
    now = datetime.now()
    fecha_str = now.strftime("%Y%m%d_%H%M")
    display_user = st.session_state.get("display_name", "").strip() or "Sin usuario"
    nombre_copia = f"SESION - {display_user} - {prefix_name} - {fecha_str}"
    copy_url = (
        f"https://docs.google.com/spreadsheets/d/{template_id}/copy"
        f"?copyDestination={DRIVE_ROOT_ID}"
        f"&title={urllib.parse.quote(nombre_copia)}"
    )
    st.session_state["confirm_state"] = "step1"
    st.session_state["session_type"] = session_type
    st.session_state["nombre_copia"] = nombre_copia
    st.session_state["copy_url"] = copy_url
    st.session_state["process_title"] = process_title
    st.rerun()

def reset_salida_downstream(level):
    if level == "year":
        st.session_state["salida_boat"] = None
        st.session_state["salida_name"] = None
        st.session_state.pop("salida_boat_widget", None)
        st.session_state.pop("salida_name_widget", None)
    elif level == "boat":
        st.session_state["salida_name"] = None
        st.session_state.pop("salida_name_widget", None)

def on_year_change():
    st.session_state["salida_year"] = st.session_state.get("salida_year_widget")
    reset_salida_downstream("year")

def on_boat_change():
    st.session_state["salida_boat"] = st.session_state.get("salida_boat_widget")
    reset_salida_downstream("boat")

def on_salida_change():
    st.session_state["salida_name"] = st.session_state.get("salida_name_widget")

def reset_crucero_downstream(level):
    if level == "year":
        st.session_state["crucero_boat"] = None
        st.session_state.pop("crucero_boat_widget", None)

def on_crucero_year_change():
    st.session_state["crucero_year"] = st.session_state.get("crucero_year_widget")
    reset_crucero_downstream("year")

def on_crucero_boat_change():
    st.session_state["crucero_boat"] = st.session_state.get("crucero_boat_widget")

def normalize_text(value):
    return "" if value is None else str(value).strip().lower()

def normalize_phone(value):
    return "" if value is None else re.sub(r"\D+", "", str(value))

def percent_to_sheet_decimal(value):
    return "" if value is None else round(float(value) / 100, 4)

def parse_locator(locator):
    m = re.fullmatch(r"([A-Z]{3})(\d{6})-(\d{3})", locator.strip().upper())
    if not m:
        raise ValueError("Formato inválido. Debe ser BARCOAAMMDD-XXX. Ejemplo: ALB260101-001")
    return m.group(1), m.group(2), m.group(3)

def first_number(value):
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else 0

# ──────────────────────────────────────────────────────────────────────────────
# GOOGLE DRIVE / SHEETS API
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_google_creds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
    )

@st.cache_resource
def get_drive_service():
    return build("drive", "v3", credentials=get_google_creds())

@st.cache_resource
def get_sheets_service():
    return build("sheets", "v4", credentials=get_google_creds())

def list_folder_items(parent_id, folders_only=False):
    service = get_drive_service()
    q = f"'{parent_id}' in parents and trashed=false"
    if folders_only:
        q += " and mimeType='application/vnd.google-apps.folder'"
    results = []
    page_token = None
    while True:
        response = service.files().list(
            q=q,
            fields="nextPageToken, files(id, name, mimeType, webViewLink, description)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            pageToken=page_token,
            pageSize=1000
        ).execute()
        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return results

def find_child_folder(parent_id, folder_name):
    for f in list_folder_items(parent_id, folders_only=True):
        if f["name"].strip() == folder_name.strip():
            return f
    return None

def find_file_by_name(parent_id, file_name):
    for f in list_folder_items(parent_id, folders_only=False):
        if f["name"].strip() == file_name.strip():
            return f
    return None

def get_sheet_id_by_name(spreadsheet_id, sheet_name):
    ss = get_sheets_service().spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sh in ss.get("sheets", []):
        if sh["properties"]["title"].strip() == sheet_name.strip():
            return sh["properties"]["sheetId"]
    return None

def get_sheet_values(spreadsheet_id, rng):
    resp = get_sheets_service().spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=rng).execute()
    return resp.get("values", [])

def get_source_spreadsheet_for_locator(ship_code, yymmdd):
    barco = BARCOS_INV.get(ship_code)
    if not barco:
        raise ValueError(f"Código de barco no reconocido: {ship_code}")
    year = f"20{yymmdd[:2]}"
    year_folder = find_child_folder(DRIVE_ROOT_ID, year)
    if not year_folder:
        raise FileNotFoundError(f"No existe la carpeta del año {year}")
    boat_folder = find_child_folder(year_folder["id"], barco)
    if not boat_folder:
        raise FileNotFoundError(f"No existe la carpeta del barco {barco}")
    source_name = f"{barco}{yymmdd}"
    source_file = find_file_by_name(boat_folder["id"], source_name)
    if not source_file:
        raise FileNotFoundError(f"No existe el archivo {source_name}")
    return source_file["id"], source_file.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{source_file['id']}/edit", barco, year, source_name

def extract_cvc_data(spreadsheet_id, sheet_name):
    g24 = get_sheet_values(spreadsheet_id, f"'{sheet_name}'!G24")
    p24 = get_sheet_values(spreadsheet_id, f"'{sheet_name}'!P24")
    row20 = [get_sheet_values(spreadsheet_id, f"'{sheet_name}'!{c}20") for c in ["G", "K", "N", "P"]]
    row22 = [get_sheet_values(spreadsheet_id, f"'{sheet_name}'!{c}22") for c in ["G", "K", "N", "P"]]
    dinero = get_sheet_values(spreadsheet_id, f"'{sheet_name}'!G33:R53")
    total = get_sheet_values(spreadsheet_id, f"'{sheet_name}'!Q55")

    g24v = g24[0][0] if g24 and isinstance(g24[0], list) and g24[0] else (g24[0][0] if g24 else "")
    p24v = p24[0][0] if p24 and isinstance(p24[0], list) and p24[0] else (p24[0][0] if p24 else "")

    nombre_apellidos = str(g24v).split("/", 1)
    nombre = nombre_apellidos[0].strip() if nombre_apellidos else ""
    apellidos = nombre_apellidos[1].strip() if len(nombre_apellidos) > 1 else ""
    dni = str(p24v).split("/", 1)[0].strip()

    personas = sum(first_number(v[0] if v and isinstance(v, list) else v) for v in row20)
    habitaciones = sum(first_number(v[0] if v and isinstance(v, list) else v) for v in row22)
    total_value = total[0][0] if total and isinstance(total[0], list) and total[0] else (total[0] if total else "")

    return {
        "nombre": nombre,
        "apellidos": apellidos,
        "dni": dni,
        "personas": personas,
        "habitaciones": habitaciones,
        "dinero": dinero,
        "total": total_value
    }

def build_docx_bytes(data, locator, barco, yymmdd):
    fecha_salida = datetime.strptime(yymmdd, "%y%m%d")
    fecha_limite = (fecha_salida - timedelta(days=30)).strftime("%d/%m/%Y")
    today = datetime.now().strftime("%d/%m/%Y")

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(10)

    def add_line(text="", bold=False, underline=False):
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.bold = bold
        r.underline = underline
        return p

    add_line(f"Lugar y fecha: {today}")
    add_line("Contrato de Viaje Combinado", underline=True)
    add_line("")
    add_line("Datos de la agencia de viajes (organizadora y minorista):", bold=True)
    add_line("Nombre: CRUCEMUNDO S.L")
    add_line("Domicilio: Av. Europa, 86, building 2A, suite 25 cp.08850 Gavà, Spain")
    add_line("NIF: B64955172")
    add_line("Teléfono: 934542041")
    add_line("E-mail: info@crucemundo.es")
    add_line("")
    add_line("Datos del viajero:", bold=True)
    add_line(f"Nombre: {data['nombre']}")
    add_line(f"Apellidos: {data['apellidos']}")
    add_line(f"DNI/ Pasaporte: {data['dni']}")
    add_line("Dirección:")
    add_line("Población:                                         C. Postal:                                         e-mail:")
    add_line("Teléfono particular:")
    add_line(f"Nº Personas: {data['personas']}")
    add_line(f"Nº Habitaciones: {data['habitaciones']}")
    add_line("")
    add_line("El viajero manifiesta que, antes de quedar obligado por el presente contrato de viaje combinado y oferta correspondiente, ha recibido la información precontractual establecida en el artículo 153. 1 del Real Decreto Legislativo 1/2007, de 16 de noviembre, compuesta por el formulario con la información normalizada relativa al viaje combinado (ANEXO I) y la información aplicable al viaje combinado.")
    add_line("")
    add_line("Nombre y datos contacto entidad/es garante/s en caso de insolvencia y del cumplimiento de la ejecución del contrato de viaje combinado de la agencia de viajes: En documento resumen que figura en el ANEXO II.")
    add_line("")
    add_line("Condiciones generales: el viajero manifiesta aceptar las Condiciones Generales del contrato de viaje combinado que se acompañan en el ANEXO III y que obran en su poder.")
    add_line("")
    add_line("Condiciones particulares: En base a la descripción de los servicios de viaje que figuran en el ANEXO IV")
    for txt in [
        "Destino/s: Según ANEXO IV",
        "Itinerario: Según ANEXO IV",
        "Periodos estancia y sus fechas: Según ANEXO IV",
        "Nº de pernoctaciones incluidas: Según ANEXO IV",
        "Medio de transporte, características, categoría y duración: Según ANEXO IV",
        "Fecha de salida: Según ANEXO IV",
        "Hora salida/ Según PVP (sujeto a cambios): Según ANEXO IV",
        "Lugar de salida: Según ANEXO IV",
        "Fecha de regreso: Según ANEXO IV",
        "Lugar de regreso: Según ANEXO IV",
        "Hora regreso/ Según PVP (sujeto a cambios): Según ANEXO IV",
        "Paradas intermedias y conexiones: Según ANEXO IV",
        "Ubicación, principales características y categoría del alojamiento: Según ANEXO IV",
        "Comidas previstas: Según ANEXO IV",
        "Visitas, excursiones u otros servicios incluidos en viaje: Según ANEXO IV",
        "Indicación de si es viaje en grupo y, si se puede, tamaño aprox. grupo: Según ANEXO IV",
        "Idioma prestación servicios: Según ANEXO IV",
    ]:
        add_line(txt)
    add_line("")
    add_line("Necesidades especiales del viajero aceptadas por el organizador:")
    add_line("____________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________")
    add_line("")
    add_line(f"Precio y Forma de pago: {data['dinero']}")
    add_line(f"Fecha límite y/o calendario de pago del importe pendiente: {fecha_limite}")
    add_line("Modalidades de pago: Transferencia bancaria")
    add_line("")
    add_line("Revisión de los precios: Estos precios han sido calculados en fecha OBLIGATORIO en base a los tipos de cambio de divisa, al precio de transporte derivado coste combustible o de otras fuentes de energía y al nivel de impuestos y tasas sobre los servicios de viaje incluidos en el contrato vigentes en dicha fecha. Hasta 20 días antes de la salida, los precios podrán incrementarse de acuerdo con lo establecido en el apartado 11 de las Condiciones Generales (ANEXO III). De igual modo el viajero tendrá derecho tendrá derecho a reducción de precio por variación a su favor de dichos conceptos, pudiendo la agencia de viajes en tal caso deducir del reembolso los gastos administrativos reales de su tramitación.")
    add_line("")
    add_line("El viaje es apto para personas de movilidad reducida (persona cuya movilidad para participar en el viaje se halle reducida por motivos de discapacidad física, sensorial o locomotriz, permanente o temporal; discapacidad o deficiencia intelectual; o cualquier otra causa de discapacidad, o por la edad, y cuya situación requiera una atención adecuada y la adaptación a sus necesidades particulares del servicio puesto a disposición de los demás participantes).")
    add_line("")
    add_line("__ SI")
    add_line("__ NO")
    add_line("")
    add_line("Mínimo de personas")
    add_line("La realización del presente viaje requiere la participación de un mínimo de 70 personas. De no llegarse a este mínimo, la agencia tiene derecho a anular el viaje hasta 20 días antes de la fecha de salida.")
    add_line("La realización del presente viaje no requiere la participación de un nº mínimo de personas.")
    add_line("")
    add_line("Requisitos entrada para turistas de los que fue informado el viajero en el momento de efectuar la reserva.")
    add_line("")
    add_line("X DNI     o     X Pasaporte       Visado/s       Vacuna/s:")
    add_line("")
    add_line("Tiempo aproximado obtención visado/s:________________")
    add_line("")
    add_line("El viajero manifiesta que ha sido informado de la situación y requisitos del país/países objeto de su viaje de acuerdo con la información publicada en la página web del Ministerio de Asuntos Exteriores y Cooperación (www.exteriores.gob.es) y que conoce, por lo tanto, las características y posibles riesgos de toda índole del país/países de destino.")
    add_line("")
    add_line("Resolución voluntaria del viaje por el viajero antes de la salida: El viajero en cualquier momento antes del inicio del viaje puede resolver el contrato debiendo de abonar una penalización de:")
    add_line("- Con más de 42 días antes de la salida – 20% de penalización.")
    add_line("- Entre 42 y 28 días antes – 40% de penalización.")
    add_line("- Entre 27 y 15 días antes – 60% de penalización.")
    add_line("- Entre 14 y 7 días antes – 75% de penalización.")
    add_line("- Menos de 7 días antes de la salida – 100% de penalización.")
    add_line("")
    add_line("Seguro facultativo de asistencia en viaje: El viajero declara haber sido informado de la posibilidad de contratar un seguro de asistencia en viaje de la Compañía Aseguradora, póliza número, así como de las coberturas, exclusiones, condiciones generales y particulares de este seguro.")
    add_line("")
    add_line("Su voluntad es de:")
    add_line("o No contratar el seguro de asistencia en viaje ofrecido")
    add_line("o Contratar el seguro de asistencia en viaje ofrecido, aceptando las coberturas, exclusiones, condiciones generales y particulares de este seguro, las cuales le han sido entregadas y declara conocer.")
    add_line("")
    add_line("Seguro facultativo de gastos de anulación por fuerza mayor: El viajero declara haber sido informado de la posibilidad de contratar un seguro de gastos de anulación de la Compañía Aseguradora, póliza número, así como de las coberturas, exclusiones, condiciones generales y particulares de este seguro.")
    add_line("")
    add_line("Su voluntad es de:")
    add_line("o No contratar el seguro de gastos de anulación ofrecido")
    add_line("o Contratar el seguro de gastos de anulación ofrecido, aceptando las exclusiones, coberturas, condiciones generales y particulares de este seguro, las cuales le han sido entregadas y declara conocer.")
    add_line("")
    add_line("Cesión del viaje: Conforme a lo establecido en el apartado 12 de las Condiciones Generales (ANEXO III) el viajero podrá ceder su reserva a una persona que reúna todas las condiciones requeridas.")
    add_line("")
    add_line("Datos de contacto en caso de asistencia y falta de conformidad:")
    add_line("")
    add_line("Representante local (si hay):")
    add_line("Nombre:")
    add_line("Dirección:")
    add_line("Teléfono")
    add_line("e-mail:")
    add_line("")
    add_line("Otros puntos de contacto o servicio de asistencia de la agencia de viajes:")
    add_line("")
    add_line("Teléfono: +34 934542041")
    add_line("e-mail: info@crucemundo.es")
    add_line("")
    add_line("Para cualquier aspecto relacionado con asistencia sanitaria, si el viajero ha contratado un seguro de asistencia en viaje, deberá contactar también con el teléfono de la cía. Aseguradora.")
    add_line("")
    add_line("Contacto información menores no acompañados: En caso de menores no acompañados por un familiar u otro adulto autorizado, pueden establecer contacto directo con el menor o con la persona responsable durante la estancia a través de ____________________")
    add_line("")
    add_line("Falta de conformidad: El viajero durante el viaje deberá informar toda falta de conformidad en la prestación de los servicios, todo ello de acuerdo con lo establecido en el apartado 16 de las Condiciones Generales (ANEXO III)")
    add_line("")
    add_line("Responsabilidad: La agencia de viajes es responsable de la correcta ejecución de todos los servicios de viaje incluidos en el contrato, de conformidad con el artículo 161 del Real Decreto Legislativo 1/2007 y está obligada a prestar asistencia si el viajero se halla en dificultades de conformidad con el artículo 163.2 de dicha norma y de acuerdo con lo establecido en las condiciones generales del contrato (ANEXO III).")
    add_line("")
    add_line("Reclamaciones tras el viaje: El viajero podrá dirigir sus reclamaciones a la dirección postal que consta en el encabezamiento y a la siguiente dirección de correo electrónico: info@crucemundo.es")
    add_line("")
    add_line("Tratamiento de datos personales:")
    add_line("")
    add_line("De acuerdo con Reglamento (UE) 2016/679 del Parlamento Europeo y del Consejo, de 27 de abril de 2016 (RGPD) y la Ley Orgánica 3/2018, de 5 de diciembre, de Protección de Datos Personales y Garantía de los Derechos Digitales, que adapta el Reglamento al ordenamiento jurídico español y completa y desarrolla sus disposiciones, el cliente acepta que los datos personales que informa en este documento así como los que puedan ser facilitados en el futuro para el mismo fin, sean recogidos y tratados por la agencia, con domicilio en dichos datos. Dichos datos han sido recogidos por la agencia con la finalidad de gestionar y desarrollar el conjunto de servicios estipulados en este contrato con el cliente, siendo necesarios para cumplir dichos propósitos.")
    add_line("")
    add_line("El afectado podrá ejercitar los derechos reconocidos en el RGPD y, en particular, los de acceso, limitación, rectificación, supresión, oposición y olvido, a través de un escrito que podrá dirigir a la sede social de la Agencia en la dirección indicada, con la referencia “Protección de Datos”.")
    add_line("")
    add_line("Comunicación y transferencia de datos: La Agencia le informa que, dependiendo de la modalidad de pago de los servicios, se procederá a la comunicación de los datos incluidos en dicho fichero (Nombre, CIF/NIF, N-Cuenta) a las Entidades Financieras (Bancos y Cajas) con las que trabaja la Agencia a los solos efectos de gestionar las transferencias, cobros y pagos a que dé lugar la relación comercial y el uso de nuestros servicios.")
    add_line("Para la gestión y cumplimento del objeto del contrato, puede resultar necesario (y obligatorio para la prestación del servicio), que sus datos (incluida información sobre alergias, intolerancias alimentarias, minusvalías, etc.), tengan que ser comunicados a proveedores tales como compañías aéreas, navieras, hoteles y otros proveedores de servicios, los cuales estarán obligados a utilizar los datos, única y exclusivamente, para dar cumplimiento al objeto del contrato. Estos proveedores, dependiendo del país de destino de su viaje, podrán estar ubicados en países para los que sea necesario realizar una transferencia internacional de dato incluyendo, si fuera el caso, aquellos que no ofrezcan un nivel de protección equiparable a la exigida por la UE, considerándose por tanto una transferencia internacional de datos autorizada expresamente por el interesado.")
    add_line("")
    add_line("Conservación de los datos: Mantendremos su información personal mientras exista una relación contractual y/o comercial con usted, o mientras usted no ejerza su derecho de supresión, cancelación y/o limitación del tratamiento de sus datos. También mantendremos sus datos únicamente al efecto de cumplimiento legal un máximo de 10 años – desde la finalización del contrato- si por las características del viaje estuviera afectado por la Ley 10/2010, de 28 de abril, de prevención del blanqueo de capitales y la financiación del terrorismo. Los datos accesorios que Ud. nos informa (p.e. preferencias alimentarias, posibles intolerancias, etc.) serán eliminados de nuestros sistemas una vez concluido el servicio o viaje.")
    add_line("")
    add_line("Real Decreto 933/2021 : Conforme a lo dispuesto en el Real Decreto 933/2021, de 26 de octubre, por el que se establecen las obligaciones de registro documental e información de las personas físicas o jurídicas que contratan actividades de hospedaje y alquiler de vehículos a motor, los datos que se recojan en aplicación de dicha normativa podrán ser accesibles a la policía y las autoridades públicas en el desempeño de sus respectivas competencias en el ámbito de prevención, detección e investigación del delito que tengan asignadas. No se procederá a la comunicación a terceros de los datos personales recogidos en virtud de la citada norma, excepto por obligación legal o requerimiento judicial.")
    add_line("")
    add_line("El presente contrato de viaje combinado se firma por duplicado en el lugar y fecha arriba indicado y a un único efecto, entregándose en este mismo momento un ejemplar al viajero.")
    add_line("")
    add_line("Firma viajero                                                   Firma agencia de viajes")
    add_line("")
    add_line("ANEXO I: CERTIFICADO DE SEGURO DE CAUCIÓN AG.VIAJES", bold=True)
    add_line("")
    add_line("El presente certificado se emite al amparo de lo establecido en el artículo 155.2.c) del Real Decreto Legislativo 1/2007, de 16 de noviembre, por el que se aprueba el texto refundido de la Ley General para la Defensa de los Consumidores y Usuarios y otras leyes complementarias.")
    add_line("")
    add_line("Crucemundo S.L. dispone de la garantía por insolvencia establecida para los viajes combinados en el Art. 252-10 de la Ley 22/2010, de 20 de julio, del Código de Consumo de Cataluña, formalizada a través de la póliza de caución número 72974394 con la compañía aseguradora AXA Seguros Generales, S.A. de Seguros y Reaseguros, domiciliada en la calle Monseñor Palmer, 1, 07014 Palma de Mallorca. Dicha garantía está plenamente vigente.")
    add_line("")
    add_line("Procedimiento en caso de que, dándose la situación de insolvencia de la agencia de Viajes cubierta por la garantía, el consumidor precise activarla:")
    add_line("Deberá dirigirse directamente a la compañía aseguradora AXA Seguros Generales, S.A. de Seguros y Reaseguros a través de:")
    add_line("1. Teléfonos: 902 013 345 ó 91 111 95 44.")
    add_line("2. Email del Depto de Siniestros: aperturas.empresas@axa.es")
    add_line("3. Presentado su reclamación en alguna de las oficinas AXA.")

    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

def create_cvc_fit(locator):
    ship_code, yymmdd, seq = parse_locator(locator)
    spreadsheet_id, source_url, barco, year, source_name = get_source_spreadsheet_for_locator(ship_code, yymmdd)
    if get_sheet_id_by_name(spreadsheet_id, locator) is None:
        raise FileNotFoundError(f"No existe la pestaña {locator}")
    data = extract_cvc_data(spreadsheet_id, locator)
    docx_bytes = build_docx_bytes(data, locator, barco, yymmdd)
    file_name = f"CVC Fit {data['apellidos']}_{data['nombre']}_{barco}_{yymmdd[:2]}_{yymmdd[2:4]}.docx"
    return file_name, docx_bytes, data, source_url, source_name

# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
* { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background:#FFFFFF !important; }
[data-testid="stAppViewContainer"] { background:#FFFFFF !important; }
[data-testid="stHeader"] { background:transparent !important; }
section[data-testid="stSidebar"] { display:none !important; }

.block-container,
section.stMain .block-container,
.stMainBlockContainer,
[data-testid="stMainBlockContainer"] {
    padding-top:0rem !important;
    padding-bottom:1rem !important;
    padding-left:1rem !important;
    padding-right:1rem !important;
    max-width:1700px !important;
    margin:0 auto !important;
}

.login-page { min-height:auto; display:flex; align-items:flex-start; justify-content:center; padding:0.2rem 1rem 1rem; }
.login-shell { width:100%; max-width:390px; margin:0 auto; }
.login-head { text-align:center; margin-bottom:0.55rem; }
.login-logo { height:56px; width:auto; margin:0 auto 0.65rem auto; display:block; }
.login-title { font-size:1.08rem; font-weight:700; color:#1F2937; }
.login-subtitle { font-size:0.78rem; color:#7C869D; margin-top:0.28rem; }

div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stDateInput"] label,
div[data-testid="stNumberInput"] label {
    color:#4D576D !important;
    font-size:0.78rem !important;
    font-weight:500 !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stDateInput"] input,
div[data-testid="stNumberInput"] input {
    background:#F8FAFC !important;
    border:1px solid #E5EAF2 !important;
    border-radius:12px !important;
    color:#1F2937 !important;
}

div.stButton { width:fit-content !important; }
div.stButton > button,
div[data-testid="stFormSubmitButton"] > button,
.logout-btn > div > button,
div[data-testid="stDownloadButton"] > button {
    color:#214D92 !important;
    border:1px solid rgba(33,77,146,0.14) !important;
    border-radius:999px !important;
    min-height:38px !important;
    padding:0 1.15rem !important;
    font-size:0.76rem !important;
    font-weight:600 !important;
    box-shadow:none !important;
}

div.st-key-btn_crear_es button { background:#EEF4FF !important; }
div.st-key-btn_crear_grupos button { background:#ECF8EF !important; }
div.st-key-btn_ir_salida button { background:#FFF3E4 !important; }
div.st-key-btn_crear_crucero_open button { background:#F1EBFF !important; }
div.st-key-btn_nueva_agencia button { background:#EAF8F0 !important; }
div.st-key-btn_buscar_agencia button { background:#FFF4EA !important; }
div.st-key-btn_cvc_fit button { background:#EDF3FF !important; }
div.st-key-btn_generar_cvc_fit button { background:#EDF3FF !important; }

div.st-key-btn_crear_es button:hover { background:#E5EEFF !important; }
div.st-key-btn_crear_grupos button:hover { background:#E3F3E7 !important; }
div.st-key-btn_ir_salida button:hover { background:#FFEBCF !important; }
div.st-key-btn_crear_crucero_open button:hover { background:#E8DFFF !important; }
div.st-key-btn_nueva_agencia button:hover { background:#DDF3E7 !important; }
div.st-key-btn_buscar_agencia button:hover { background:#FFE9D7 !important; }
div.st-key-btn_cvc_fit button:hover,
div.st-key-btn_generar_cvc_fit button:hover { background:#E2ECFF !important; }

.portal-header {
    padding:0.1rem 0 0.55rem 0;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:1rem;
    margin-bottom:0.55rem;
}
.portal-header-left { display:flex; align-items:center; gap:0.9rem; }
.portal-logo { height:42px; width:auto; object-fit:contain; display:block; }

.portal-title,
.portal-title-en {
    font-size:0.96rem;
    font-weight:700;
    color:#1F2937;
    line-height:1.15;
}
.portal-title-en { margin-top:0.12rem; }

.portal-subtitle,
.portal-subtitle-en {
    font-size:0.72rem;
    color:#7C869D;
    line-height:1.2;
}
.portal-subtitle { margin-top:0.12rem; }
.portal-subtitle-en { margin-top:0.08rem; }

.user-top {
    font-size:0.72rem;
    color:#566079;
    white-space:nowrap;
}

.main-content { padding:0; }

.section-head-row{
    display:flex;
    align-items:center;
    justify-content:flex-start;
    gap:0.55rem;
    margin-bottom:0.75rem;
    flex-wrap:wrap;
}

.section-eyebrow {
    display:inline-flex;
    align-items:center;
    padding:0.34rem 0.74rem;
    border-radius:999px;
    background:#EAF1FF;
    border:1px solid #D6E3FF;
    color:#2E5FB8;
    font-size:0.66rem;
    font-weight:700;
    letter-spacing:0.08em;
    text-transform:uppercase;
    margin-bottom:0 !important;
}

.web-chip{
    display:inline-flex;
    align-items:center;
    justify-content:center;
    padding:0.34rem 0.74rem;
    border-radius:999px;
    background:#FFF3BF;
    border:1px solid #F4D35E;
    color:#7A5900 !important;
    font-size:0.70rem;
    font-weight:700;
    line-height:1;
    text-decoration:none;
    white-space:nowrap;
}

.web-chip:hover{
    background:#FFE58F;
    border-color:#E9C046;
    color:#5F4500 !important;
}

.user-pill {
    display:inline-flex;
    align-items:center;
    gap:0.4rem;
    margin:0.02rem 0 1rem;
    padding:0.38rem 0.68rem;
    border-radius:999px;
    background:#fff;
    border:1px solid #E4E7EF;
    font-size:0.72rem;
    color:#5D6880;
    max-width:100%;
    word-break:break-word;
}

.action-box {
    width:100%;
    min-height:210px;
    border-radius:22px;
    padding:1rem;
    margin-bottom:0.85rem;
    display:flex;
    flex-direction:column;
    justify-content:space-between;
    gap:0.9rem;
    border:1px solid transparent;
}

.card-es { background:#F3F7FF; border-color:#D9E5FF; }
.card-grupos { background:#F4FBF6; border-color:#D8EEDC; }
.card-salida { background:#FFF8F1; border-color:#F1DFC7; }
.card-crucero { background:#F7F4FF; border-color:#E4DDF9; }
.card-excursiones { background:#EEF8FB; border-color:#D5EAF1; }
.card-nueva-agencia { background:#F1FAF4; border-color:#D7EEDC; }
.card-buscar-agencia { background:#FFF7EF; border-color:#F4E1CA; }
.card-cvc-fit { background:#F8FBFF; border-color:#DCE8FF; }

.action-top { display:flex; align-items:flex-start; gap:0.75rem; }

.action-icon {
    width:38px;
    height:38px;
    border-radius:12px;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:1rem;
    flex-shrink:0;
}
.card-es .action-icon { background:#E6EEFF; border:1px solid #D2DFFF; }
.card-grupos .action-icon { background:#E7F5EA; border:1px solid #D0EAD7; }
.card-salida .action-icon { background:#FFF0DD; border:1px solid #F2DEC0; }
.card-crucero .action-icon { background:#EEE8FF; border:1px solid #DDD2FF; }
.card-excursiones .action-icon { background:#E2F2F7; border:1px solid #CFE6EE; }
.card-nueva-agencia .action-icon { background:#E2F4E7; border:1px solid #CFE5D6; }
.card-buscar-agencia .action-icon { background:#FDEBD9; border:1px solid #F2D9B9; }
.card-cvc-fit .action-icon { background:#E8F0FF; border:1px solid #D3E0FF; }

.action-text {
    display:flex;
    flex-direction:column;
    gap:0.10rem;
    min-width:0;
}

.action-title,
.action-title-en {
    font-size:0.95rem;
    font-weight:700;
    color:#1F2937;
    line-height:1.1;
}
.action-title-en { margin-top:0.05rem; }

.action-desc,
.action-desc-en {
    font-size:0.73rem;
    color:#6F7B91;
    line-height:1.28;
}
.action-desc { margin-top:0.18rem; }
.action-desc-en { margin-top:0.04rem; }

.action-button-wrap {
    display:flex !important;
    justify-content:flex-start !important;
    align-items:center !important;
    width:100% !important;
    margin-top:0.1rem;
}

.panel-inline {
    margin-top:1rem;
    padding-top:0.2rem;
    width:100%;
    max-width:1040px;
}

.done-link {
    display:inline-flex;
    align-items:center;
    gap:0.35rem;
    margin-top:0.65rem;
    background:#D9E9FF;
    color:#214D92 !important;
    border:1px solid #BDD6FF;
    border-radius:999px;
    padding:0.42rem 0.88rem;
    font-size:0.71rem;
    font-weight:600;
    text-decoration:none;
}

.step { display:flex; align-items:flex-start; gap:0.65rem; margin-bottom:0.6rem; }
.step:last-child { margin-bottom:0; }
.step-dot {
    width:18px;
    height:18px;
    border-radius:50%;
    flex-shrink:0;
    margin-top:0.05rem;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:0.55rem;
    font-weight:700;
}
.sd-done { background:#EEF7F1; border:1px solid #D8ECDF; color:#2E7D58; }
.sd-active { background:#F2F4F9; border:1px solid #DDE2EC; color:#6E778B; }
.sd-wait { background:#F8F9FC; border:1px solid #E6E9F0; color:#B1B8C9; }
.step-content { display:flex; flex-direction:column; min-width:0; flex:1; }
.st-done, .st-active, .st-wait { font-size:0.76rem; }
.st-done { color:#394255; }
.st-active { color:#1F2937; font-weight:600; }
.st-wait { color:#A2ABBD; }
.step-detail {
    font-size:0.7rem;
    color:#8790A4;
    margin-top:0.08rem;
    word-wrap:break-word !important;
    overflow-wrap:break-word !important;
    white-space:normal !important;
}

.portal-footer {
    margin-top:1rem;
    padding:0.5rem 0 0 0;
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:0.8rem;
    flex-wrap:wrap;
}
.footer-text { font-size:0.71rem; color:#A2ABBD; }

@media (max-width: 1300px) {
    .portal-header { flex-direction:column; align-items:flex-start; }
    .portal-footer { flex-direction:column; align-items:flex-start; }
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# LOGIN
# ──────────────────────────────────────────────────────────────────────────────
if not st.session_state["authenticated"]:
    st.markdown('<div class="login-page"><div class="login-shell">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="login-head">
        <img class="login-logo" src="{LOGO_URL}" alt="Logo">
        <div class="login-title">Acceso</div>
        <div class="login-subtitle">Access</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Mail / Email", placeholder="support@crucemundo.com")
        password = st.text_input("Contraseña / Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Entrar / Login")

        if submitted:
            email_clean = email.strip().lower()
            if not email_clean or not password:
                st.error("Debes introducir mail y contraseña / Please enter email and password.")
            elif email_clean not in VALID_USERS:
                st.error("Usuario no autorizado / Unauthorized user.")
            elif password != VALID_PASSWORD:
                st.error("Contraseña incorrecta / Incorrect password.")
            else:
                st.session_state["authenticated"] = True
                st.session_state["user_email"] = email_clean
                st.session_state["display_name"] = VALID_USERS[email_clean]
                st.rerun()

    st.markdown('</div></div>', unsafe_allow_html=True)
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# APP
# ──────────────────────────────────────────────────────────────────────────────
USER_EMAIL = st.session_state.get("user_email", "").strip()
DISPLAY_USER = st.session_state.get("display_name", "").strip() or "Sin usuario"
SALUDO = get_saludo()
SALUDO_EN = get_saludo_en()
confirm_state = st.session_state.get("confirm_state", "idle")
excursiones_url = f"https://docs.google.com/spreadsheets/d/{EXCURSIONES_SHEET_ID}/edit"

st.markdown(f"""
<div class="portal-header">
    <div class="portal-header-left">
        <img class="portal-logo" src="{LOGO_URL}" alt="Logo">
        <div>
            <div class="portal-title">{SALUDO}, {DISPLAY_USER}. ¿Qué hacemos hoy?</div>
            <div class="portal-title-en">{SALUDO_EN}, {DISPLAY_USER}. What are we doing today?</div>
            <div class="portal-subtitle">Herramientas y automatizaciones · Backend Google Drive</div>
            <div class="portal-subtitle-en">Tools and automations · Google Drive backend</div>
        </div>
    </div>
    <div class="user-top">👤 {DISPLAY_USER}</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

st.markdown("""
<div class="section-head-row">
    <div class="section-eyebrow">ACCIONES RÁPIDAS · QUICK ACTIONS</div>
    <a class="web-chip" href="https://www.crucemundo.es" target="_blank" rel="noopener noreferrer">Ir a Crucemundo</a>
    <a class="web-chip" href="https://mail.google.com/" target="_blank" rel="noopener noreferrer">Gmail</a>
</div>
""", unsafe_allow_html=True)

st.markdown(f'<div class="user-pill">👤 {DISPLAY_USER} · {USER_EMAIL}</div>', unsafe_allow_html=True)

# FILA 1: 7 COLUMNAS
col1, col2, col3, col4, col5, col6, col7 = st.columns(7, gap="medium")

with col1:
    st.markdown(f"""
    <div class="action-box card-es">
        <div class="action-top">
            <div class="action-icon">📋</div>
            <div class="action-text">
                <div class="action-title">Nueva Confirmación</div>
                <div class="action-title-en">New Confirmation</div>
                <div class="action-desc">Crear sesión MASTER de trabajo para {DISPLAY_USER}</div>
                <div class="action-desc-en">Create MASTER working session for {DISPLAY_USER}</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)
    if confirm_state in ("idle", "done"):
        if st.button("Crear Sesión ES", key="btn_crear_es"):
            iniciar_proceso("es", TEMPLATE_ID_ES, "MASTER", "Estado del Proceso · Process Status: Crear Sesión MASTER_CONFIRMATION")
    else:
        st.button("Crear Sesión ES", key="btn_crear_es_dis", disabled=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="action-box card-grupos">
        <div class="action-top">
            <div class="action-icon">👥</div>
            <div class="action-text">
                <div class="action-title">Nueva Confirmación GRUPOS</div>
                <div class="action-title-en">New GROUPS Confirmation</div>
                <div class="action-desc">Crear sesión MASTER GRUPOS de trabajo para {DISPLAY_USER}</div>
                <div class="action-desc-en">Create MASTER GROUPS working session for {DISPLAY_USER}</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)
    if confirm_state in ("idle", "done"):
        if st.button("Crear Sesión GRUPOS", key="btn_crear_grupos"):
            iniciar_proceso("grupos", TEMPLATE_ID_GRUPOS, "MASTER GRUPOS", "Estado del Proceso · Process Status: Crear Sesión MASTER_GRUPOS")
    else:
        st.button("Crear Sesión GRUPOS", key="btn_crear_grupos_dis", disabled=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="action-box card-salida">
        <div class="action-top">
            <div class="action-icon">🧭</div>
            <div class="action-text">
                <div class="action-title">Ir a Salida</div>
                <div class="action-title-en">Go to Departure</div>
                <div class="action-desc">Buscar una salida existente por año, barco y código de salida</div>
                <div class="action-desc-en">Find an existing departure by year, ship and departure code</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)
    if st.button("Buscar Salida", key="btn_ir_salida"):
        open_panel("salida")
        st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="action-box card-crucero">
        <div class="action-top">
            <div class="action-icon">🚢</div>
            <div class="action-text">
                <div class="action-title">Crear crucero</div>
                <div class="action-title-en">Create Cruise</div>
                <div class="action-desc">Crear salida nueva desde plantilla y guardarla en año/barco</div>
                <div class="action-desc-en">Create a new departure from template and save it in year/ship</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)
    if st.button("Nuevo Crucero", key="btn_crear_crucero_open"):
        open_panel("crucero")
        st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

with col5:
    st.markdown("""
    <div class="action-box card-excursiones">
        <div class="action-top">
            <div class="action-icon">🏝️</div>
            <div class="action-text">
                <div class="action-title">Excursiones</div>
                <div class="action-title-en">Excursions</div>
                <div class="action-desc">Abrir la hoja de Excursiones</div>
                <div class="action-desc-en">Open the Excursions sheet</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)
    st.markdown(f'<a class="done-link" href="{excursiones_url}" target="_blank">Abrir Excursiones ↗</a>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

with col6:
    st.markdown("""
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
    """, unsafe_allow_html=True)
    if st.button("Nueva Agencia", key="btn_nueva_agencia"):
        open_panel("nueva_agencia")
        st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

with col7:
    st.markdown("""
    <div class="action-box card-buscar-agencia">
        <div class="action-top">
            <div class="action-icon">🔎</div>
            <div class="action-text">
                <div class="action-title">Buscar Agencia</div>
                <div class="action-title-en">Find Agency</div>
                <div class="action-desc">Buscar por cualquier dato y mostrar la ficha completa</div>
                <div class="action-desc-en">Search by any known value and show the full record</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)
    if st.button("Buscar Agencia", key="btn_buscar_agencia"):
        open_panel("buscar_agencia")
        st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

# FILA 2: 7 COLUMNAS, CVC FIT EN COLUMNA 1
st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
c1, c2, c3, c4, c5, c6, c7 = st.columns(7, gap="medium")

with c1:
    st.markdown("""
    <div class="action-box card-cvc-fit">
        <div class="action-top">
            <div class="action-icon">📝</div>
            <div class="action-text">
                <div class="action-title">CVC Fit</div>
                <div class="action-title-en">CVC Fit</div>
                <div class="action-desc">Generar contrato DOC desde localizador</div>
                <div class="action-desc-en">Generate DOC contract from locator</div>
            </div>
        </div>
        <div class="action-button-wrap">
    """, unsafe_allow_html=True)
    if st.button("Abrir CVC Fit", key="btn_cvc_fit"):
        open_panel("cvc_fit")
        st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

if st.session_state.get("open_cvc_fit_form"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("#### CVC Fit · Generar contrato")
    locator = st.text_input("Localizador", key="cvc_locator", placeholder="ALB260101-001")

    if st.button("Generar DOC", key="btn_generar_cvc_fit"):
        try:
            file_name, docx_bytes, data, source_url, source_name = create_cvc_fit(locator)
            st.session_state["cvc_result"] = {
                "file_name": file_name,
                "data": data,
                "source_url": source_url,
                "source_name": source_name,
            }
            st.session_state["cvc_download_name"] = file_name
            st.session_state["cvc_download_bytes"] = docx_bytes
        except Exception as e:
            st.error(str(e))

    if st.session_state.get("cvc_result"):
        r = st.session_state["cvc_result"]
        st.success("Documento preparado correctamente.")
        st.write(f"Archivo origen: {r['source_name']}")
        st.write(f"Nombre fichero: {r['file_name']}")
        st.write(f"Viajero: {r['data']['nombre']} {r['data']['apellidos']}")
        st.write(f"DNI: {r['data']['dni']}")
        st.write(f"Personas: {r['data']['personas']}")
        st.write(f"Habitaciones: {r['data']['habitaciones']}")
        st.write(f"Total: {r['data']['total']}")
        st.download_button(
            "Descargar DOCX",
            data=st.session_state["cvc_download_bytes"],
            file_name=st.session_state["cvc_download_name"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    st.markdown('</div>', unsafe_allow_html=True)

# PANEL SALIDA
if st.session_state.get("open_salida_form"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("#### Seleccionar salida · Select departure")
    try:
        years = []
        selected_year = st.selectbox(
            "AÑO / YEAR",
            options=years,
            placeholder="Selecciona un año / Select a year",
            key="salida_year_widget",
            on_change=on_year_change
        )
    except Exception as e:
        st.exception(e)
    st.markdown('</div>', unsafe_allow_html=True)

# PANEL CRUCERO
if st.session_state.get("open_crucero_form"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("#### Crear crucero · Create cruise")
    st.info("Mantén aquí tu lógica actual de crucero.")
    st.markdown('</div>', unsafe_allow_html=True)

# PANEL NUEVA AGENCIA
if st.session_state.get("open_nueva_agencia_form"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("#### Nueva Agencia · New Agency")
    st.info("Mantén aquí tu formulario actual de agencia.")
    st.markdown('</div>', unsafe_allow_html=True)

# PANEL BUSCAR AGENCIA
if st.session_state.get("open_buscar_agencia_form"):
    st.markdown('<div class="panel-inline">', unsafe_allow_html=True)
    st.markdown("#### Buscar Agencia · Find Agency")
    st.info("Mantén aquí tu búsqueda actual de agencia.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
if st.button("Cerrar sesión / Logout", key="btn_logout"):
    do_logout()
st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="portal-footer">
    <span class="footer-text">Panel de Control · Control Panel</span>
    <span class="footer-text">Raíz Drive / Drive Root: {DRIVE_ROOT_ID}</span>
</div>
""", unsafe_allow_html=True)
