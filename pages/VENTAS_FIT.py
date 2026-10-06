# ============================================================
# PÁGINA: VENTAS_FIT
# ============================================================

import base64
import io
import random
import re
import threading
import time
from collections import deque
from datetime import datetime

import pandas as pd
import pytz
import streamlit as st

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

st.set_page_config(
    page_title="Ventas FIT – Crucemundo Hub",
    page_icon="favicon1.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# RATE LIMITER PARA GOOGLE SHEETS
# ============================================================

class RateLimiter:
    def __init__(self, max_calls=50, per_seconds=60):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self.calls = deque()
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now_monotonic = time.monotonic()

            while (
                self.calls
                and now_monotonic - self.calls[0] > self.per_seconds
            ):
                self.calls.popleft()

            if len(self.calls) >= self.max_calls:
                sleep_time = (
                    self.per_seconds
                    - (now_monotonic - self.calls[0])
                    + 0.10
                )

                if sleep_time > 0:
                    time.sleep(sleep_time)

                now_monotonic = time.monotonic()

                while (
                    self.calls
                    and now_monotonic - self.calls[0] > self.per_seconds
                ):
                    self.calls.popleft()

            self.calls.append(time.monotonic())


sheets_rate_limiter = RateLimiter(
    max_calls=50,
    per_seconds=60,
)


# ============================================================
# CONSTANTES
# ============================================================

DRIVEROOTID = "11TP9aDv3ss5PWjeNsbr6WQ3mUS9ioEvm"

TIMEZONE = pytz.timezone("Europe/Madrid")

GOOGLE_SHEETS_MIME = (
    "application/vnd.google-apps.spreadsheet"
)

COLUMNS_ORDER = [
    "#",
    "BARCO",
    "AGENCIA",
    "CODIGO",
    "GRUPO",
    "CONFIRMACION",
    "FECHA BOOKING",
    "ITINERARIO",
    "FECHA SALIDA",
    "FECHA LLEGADA",
    "NETO",
    "BRUTO",
    "ESTADO RESERVA",
    "PAGO",
    "COMERCIAL",
    "PERSONAS",
    "IDIOMA",
]

DATA_COLUMNS = COLUMNS_ORDER[1:]


# Celdas que deben leerse de cada pestaña
CELLS_NEEDED = [
    "G11",
    "G13",
    "G5",
    "P5",
    "R5",
    "C3",
    "G19",
    "G17",
    "K17",
    "G10",
    "G57",
    "Q10",
    "G23",
]

RANGE_NETO = "Q33:R39"
RANGE_PERSONA = "G24"
RANGE_BRUTO = "Q55"

ALL_RANGES_NEEDED = CELLS_NEEDED + [
    RANGE_NETO,
    RANGE_PERSONA,
    RANGE_BRUTO,
]


# Número de pestañas que se leen por cada batchGet.
# Si algún libro tiene hojas especialmente pesadas,
# puedes bajarlo a 5.
SHEETS_PER_BATCH = 10


# ============================================================
# PATRONES
# ============================================================

LOCALIZADOR_RE = re.compile(
    r"^[A-Z]{2,3}\d{6}-\d+$",
    re.IGNORECASE,
)

SALIDA_PATTERN = re.compile(
    r"^[A-Z0-9_]+_\d{6}$",
    re.IGNORECASE,
)


# ============================================================
# LOGO
# ============================================================

def get_logo_base64():
    try:
        with open("crucemundo_final.gif", "rb") as file:
            encoded = base64.b64encode(
                file.read()
            ).decode("utf-8")

            return (
                "data:image/gif;base64,"
                + encoded
            )

    except Exception:
        return ""


LOGOURL = get_logo_base64()


# ============================================================
# HELPERS DE TIEMPO
# ============================================================

def now():
    return (
        datetime.now(pytz.utc)
        .astimezone(TIMEZONE)
        .replace(tzinfo=None)
    )


def getsaludo(lang="es"):
    hour = now().hour

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


# ============================================================
# HELPERS GENERALES
# ============================================================

def chunks(items, size):
    """
    Divide una lista en grupos del tamaño indicado.
    """

    for position in range(0, len(items), size):
        yield items[position:position + size]


def escape_sheet_title(title):
    """
    Escapa apóstrofes en nombres de pestañas para utilizarlos
    correctamente dentro de rangos A1.

    Ejemplo:
        John's booking
        John''s booking
    """

    return str(title).replace("'", "''")


def confirmacion_prefix(value):
    """
    Convierte:
        ABC123456-1
    en:
        ABC123456
    """

    return str(value).split("-")[0].strip()


# ============================================================
# RETRY Y CONTROL DE ERRORES DE GOOGLE
# ============================================================

def execute_with_retry(
    request,
    max_intentos=6,
    base_delay=2.0,
    rate_limiter=None,
):
    intentos = 0

    while True:
        if rate_limiter:
            rate_limiter.wait()

        try:
            return request.execute()

        except (
            BrokenPipeError,
            ConnectionResetError,
            TimeoutError,
            OSError,
        ) as error:
            intentos += 1

            if intentos >= max_intentos:
                raise Exception(
                    "Fallo de conexión tras "
                    f"{max_intentos} intentos: {error}"
                ) from error

            wait_time = (
                base_delay * (2 ** (intentos - 1))
                + random.uniform(0, 0.5)
            )

            time.sleep(wait_time)

        except HttpError as error:
            status = getattr(
                error.resp,
                "status",
                None,
            )

            if status == 429:
                intentos += 1

                if intentos >= max_intentos:
                    raise Exception(
                        "Cuota excedida tras "
                        f"{max_intentos} intentos: {error}"
                    ) from error

                wait_time = min(
                    base_delay * (2 ** intentos),
                    65,
                ) + random.uniform(0, 1)

                time.sleep(wait_time)

            elif status in (500, 502, 503, 504):
                intentos += 1

                if intentos >= max_intentos:
                    raise

                wait_time = (
                    base_delay * (2 ** (intentos - 1))
                    + random.uniform(0, 0.5)
                )

                time.sleep(wait_time)

            else:
                raise


# ============================================================
# SERVICIOS DE GOOGLE
# ============================================================

@st.cache_resource
def _creds():
    if "gcpserviceaccount" not in st.secrets:
        raise Exception(
            "Falta la sección gcpserviceaccount "
            "en el archivo secrets.toml."
        )

    return (
        service_account
        .Credentials
        .from_service_account_info(
            st.secrets["gcpserviceaccount"],
            scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/spreadsheets",
            ],
        )
    )


@st.cache_resource
def drive_svc():
    return build(
        "drive",
        "v3",
        credentials=_creds(),
        cache_discovery=False,
    )


@st.cache_resource
def sheets_svc():
    return build(
        "sheets",
        "v4",
        credentials=_creds(),
        cache_discovery=False,
    )


# ============================================================
# HELPERS DE GOOGLE DRIVE
# ============================================================

def list_children(parent_id, folders_only=False):
    svc = drive_svc()

    query = (
        f"'{parent_id}' in parents "
        "and trashed=false"
    )

    if folders_only:
        query += (
            " and mimeType="
            "'application/vnd.google-apps.folder'"
        )

    items = []
    page_token = None

    while True:
        request = svc.files().list(
            q=query,
            fields=(
                "nextPageToken, "
                "files(id,name,mimeType,webViewLink)"
            ),
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            pageToken=page_token,
            pageSize=1000,
        )

        response = execute_with_retry(request)

        items.extend(
            response.get("files", [])
        )

        page_token = response.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return items


def find_child_folder(parent_id, name):
    requested_name = str(name).strip()

    for folder in list_children(
        parent_id,
        folders_only=True,
    ):
        current_name = (
            folder
            .get("name", "")
            .strip()
        )

        if current_name == requested_name:
            return folder

    return None


@st.cache_data(ttl=300, show_spinner=False)
def get_year_folder_id(year):
    folder = find_child_folder(
        DRIVEROOTID,
        year,
    )

    if folder:
        return folder["id"]

    return None


@st.cache_data(ttl=300, show_spinner=False)
def get_years():
    folders = list_children(
        DRIVEROOTID,
        folders_only=True,
    )

    years = [
        folder.get("name", "").strip()
        for folder in folders
        if re.fullmatch(
            r"\d{4}",
            folder.get("name", "").strip(),
        )
    ]

    return sorted(
        years,
        reverse=True,
    )


# ============================================================
# HELPERS DE GOOGLE SHEETS
# ============================================================

def get_sheet_titles_ids(spreadsheet_id):
    request = (
        sheets_svc()
        .spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            includeGridData=False,
            fields=(
                "sheets.properties."
                "(sheetId,title,hidden)"
            ),
        )
    )

    spreadsheet = execute_with_retry(
        request,
        rate_limiter=sheets_rate_limiter,
    )

    sheets = []

    for sheet in spreadsheet.get("sheets", []):
        properties = sheet.get(
            "properties",
            {},
        )

        title = properties.get(
            "title",
            "",
        )

        sheet_id = properties.get(
            "sheetId",
        )

        hidden = properties.get(
            "hidden",
            False,
        )

        # Se incluyen también las pestañas ocultas.
        # La variable queda disponible por si posteriormente
        # quieres excluirlas.
        sheets.append(
            {
                "title": title,
                "sheetId": sheet_id,
                "hidden": hidden,
            }
        )

    return sheets


# ============================================================
# HELPERS NUMÉRICOS Y DE FECHAS
# ============================================================

def parse_numeric(value):
    if value is None or value == "":
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()

    text = re.sub(
        r"[€$£\s%]",
        "",
        text,
    )

    if not text:
        return 0.0

    # Ejemplos:
    # 1.234,56
    # 12.345,67
    if (
        re.search(r"\d\.\d{3},", text)
        or (
            text.count(",") == 1
            and text.count(".") >= 1
            and text.rfind(",") > text.rfind(".")
        )
    ):
        text = (
            text
            .replace(".", "")
            .replace(",", ".")
        )

    # Ejemplo:
    # 1234,56
    elif (
        text.count(",") == 1
        and "." not in text
    ):
        text = text.replace(",", ".")

    # Ejemplo:
    # 1.234
    elif (
        text.count(".") >= 1
        and "," not in text
    ):
        parts = text.split(".")

        if len(parts[-1]) == 3:
            text = text.replace(".", "")

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text,
    )

    if not match:
        return 0.0

    try:
        return float(match.group())

    except (ValueError, TypeError):
        return 0.0


def fmt_date(value):
    if value in (None, ""):
        return ""

    return str(value).strip()


# ============================================================
# CONVERSIÓN DE UNA PESTAÑA EN FILA
# ============================================================

def extract_sheet_row(data_by_range):
    """
    Convierte los rangos de una pestaña en una fila del informe.
    """

    def cell(a1):
        values = (
            data_by_range
            .get(a1, {})
            .get("values", [])
        )

        if values and valuesreturn values[0][0]

        return ""

    localizador = str(
        cell("G11")
    ).strip()

    if not localizador:
        return None

    if localizador.upper().endswith("_GROUP"):
        return None

    if not LOCALIZADOR_RE.fullmatch(localizador):
        return None

    # NETO
    neto_rows = (
        data_by_range
        .get(RANGE_NETO, {})
        .get("values", [])
    )

    neto = sum(
        parse_numeric(value)
        for row in neto_rows
        for value in row
        if value not in (None, "")
    )

    # PERSONAS
    persona_values = (
        data_by_range
        .get(RANGE_PERSONA, {})
        .get("values", [])
    )

    if persona_values and persona_valuestexto_personas = str(
            persona_values[0][0]
        ).strip()

        personas = len(
            [
                line
                for line in texto_personas.splitlines()
                if line.strip()
            ]
        )
    else:
        personas = 0

    # BRUTO
    bruto_values = (
        data_by_range
        .get(RANGE_BRUTO, {})
        .get("values", [])
    )

    if bruto_values and bruto_valuesbruto = parse_numeric(
            bruto_values[0][0]
        )
    else:
        bruto = 0.0

    return {
        "BARCO": str(cell("G13")).strip(),
        "AGENCIA": str(cell("G5")).strip(),
        "CODIGO": str(cell("P5")).strip(),
        "GRUPO": str(cell("R5")).strip(),
        "CONFIRMACION": localizador,
        "FECHA BOOKING": fmt_date(cell("C3")),
        "ITINERARIO": str(cell("G19")).strip(),
        "FECHA SALIDA": fmt_date(cell("G17")),
        "FECHA LLEGADA": fmt_date(cell("K17")),
        "NETO": round(neto, 2),
        "BRUTO": round(bruto, 2),
        "ESTADO RESERVA": str(cell("G10")).strip(),
        "PAGO": str(cell("G57")).strip(),
        "COMERCIAL": str(cell("Q10")).strip(),
        "PERSONAS": personas,
        "IDIOMA": str(cell("G23")).strip(),
    }
    # --------------------------------------------------------
    # NETO
    # --------------------------------------------------------

    neto_rows = (
        data_by_range
        .get(RANGE_NETO, {})
        .get("values", [])
    )

    neto = sum(
        parse_numeric(value)
        for row in neto_rows
        for value in row
        if value not in (None, "")
    )

    # --------------------------------------------------------
    # PERSONAS
    # --------------------------------------------------------

    persona_values = (
        data_by_range
        .get(RANGE_PERSONA, {})
        .get("values", [])
    )

   if persona_values and persona_values```
        texto_personas = str(
            persona_values[0][0]
        ).strip()

        personas = len(
            [
                line
                for line in texto_personas.splitlines()
                if line.strip()
            ]
        )

    else:
        personas = 0

    # --------------------------------------------------------
    # BRUTO
    # --------------------------------------------------------

    bruto_values = (
        data_by_range
        .get(RANGE_BRUTO, {})
        .get("values", [])
    )

    if bruto_values and bruto_values[0\]:
        bruto = parse_numeric(
            bruto_values[0][0]
        )

    else:
        bruto = 0.0

    return {
        "BARCO": str(
            cell("G13")
        ).strip(),

        "AGENCIA": str(
            cell("G5")
        ).strip(),

        "CODIGO": str(
            cell("P5")
        ).strip(),

        "GRUPO": str(
            cell("R5")
        ).strip(),

        "CONFIRMACION": localizador,

        "FECHA BOOKING": fmt_date(
            cell("C3")
        ),

        "ITINERARIO": str(
            cell("G19")
        ).strip(),

        "FECHA SALIDA": fmt_date(
            cell("G17")
        ),

        "FECHA LLEGADA": fmt_date(
            cell("K17")
        ),

        "NETO": round(
            neto,
            2,
        ),

        "BRUTO": round(
            bruto,
            2,
        ),

        "ESTADO RESERVA": str(
            cell("G10")
        ).strip(),

        "PAGO": str(
            cell("G57")
        ).strip(),

        "COMERCIAL": str(
            cell("Q10")
        ).strip(),

        "PERSONAS": personas,

        "IDIOMA": str(
            cell("G23")
        ).strip(),
    }


# ============================================================
# LECTURA OPTIMIZADA DE UN LIBRO
# ============================================================

def read_book(
    spreadsheet_id,
    on_row_cb=None,
    on_sheet_cb=None,
    warning_cb=None,
):
    """
    Lee todas las pestañas de un libro agrupando varias
    pestañas en una única petición batchGet.
    """

    try:
        sheets = get_sheet_titles_ids(
            spreadsheet_id
        )

    except Exception as error:
        message = (
            "No se pudo obtener la lista de pestañas "
            f"del libro `{spreadsheet_id}`: {error}"
        )

        if warning_cb:
            warning_cb(message)
        else:
            st.warning(message)

        return []

    if not sheets:
        return []

    results = []

    for sheet_group in chunks(
        sheets,
        SHEETS_PER_BATCH,
    ):
        requested_ranges = []
        range_mapping = []

        for sheet in sheet_group:
            sheet_title = sheet["title"]

            escaped_title = escape_sheet_title(
                sheet_title
            )

            for a1_range in ALL_RANGES_NEEDED:
                requested_ranges.append(
                    f"'{escaped_title}'!{a1_range}"
                )

                range_mapping.append(
                    (
                        sheet_title,
                        a1_range,
                    )
                )

        try:
            request = (
                sheets_svc()
                .spreadsheets()
                .values()
                .batchGet(
                    spreadsheetId=spreadsheet_id,
                    ranges=requested_ranges,
                    majorDimension="ROWS",
                    valueRenderOption="FORMATTED_VALUE",
                )
            )

            response = execute_with_retry(
                request,
                rate_limiter=sheets_rate_limiter,
            )

        except Exception as error:
            sheet_names = ", ".join(
                sheet["title"]
                for sheet in sheet_group
            )

            message = (
                "Error leyendo las pestañas "
                f"[{sheet_names}] del libro "
                f"`{spreadsheet_id}`: {error}"
            )

            if warning_cb:
                warning_cb(message)
            else:
                st.warning(message)

            for sheet in sheet_group:
                if on_sheet_cb:
                    on_sheet_cb(
                        sheet.get("title", "")
                    )

            continue

        value_ranges = response.get(
            "valueRanges",
            [],
        )

        grouped_data = {
            sheet["title"]: {}
            for sheet in sheet_group
        }

        for index, mapping in enumerate(
            range_mapping
        ):
            sheet_title, a1_range = mapping

            if index < len(value_ranges):
                grouped_data[sheet_title][a1_range] = (
                    value_ranges[index]
                )
            else:
                grouped_data[sheet_title][a1_range] = {
                    "values": []
                }

        for sheet in sheet_group:
            sheet_title = sheet["title"]

            try:
                row = extract_sheet_row(
                    grouped_data[sheet_title]
                )

                if row:
                    results.append(row)

                    if on_row_cb:
                        on_row_cb(row)

            except Exception as error:
                message = (
                    "Error procesando la pestaña "
                    f"'{sheet_title}' del libro "
                    f"`{spreadsheet_id}`: {error}"
                )

                if warning_cb:
                    warning_cb(message)
                else:
                    st.warning(message)

            finally:
                if on_sheet_cb:
                    on_sheet_cb(sheet_title)

    return results

# ============================================================
# ESCANEO DE UN AÑO
# ============================================================

def scan_year(
    year,
    progress_cb
