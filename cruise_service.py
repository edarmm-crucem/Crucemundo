import re
from datetime import datetime
import streamlit as st
from config import DRIVE_ROOT_ID, TEMPLATE_ID_CRUCERO
from services_google import (
    list_folder_items,
    find_child_folder,
    get_or_create_folder,
    find_file_by_name,
    copy_file_to_folder,
    get_sheets_service,
)

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
            departures.append({
                "nombre": name,
                "id": file["id"],
                "url": file.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{file['id']}/edit",
            })
    departures.sort(key=lambda x: x["nombre"])
    return departures

def update_crucero_sheet(spreadsheetid, barco):
    sheetsservice = get_sheets_service()
    spreadsheet = sheetsservice.spreadsheets().get(spreadsheetId=spreadsheetid).execute()
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
            "requests": [{
                "updateSheetProperties": {
                    "properties": {"sheetId": firstsheetid, "title": barco},
                    "fields": "title",
                }
            }]
        },
    ).execute()

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
