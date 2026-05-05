from services_google import get_sheets_service
from config import AGENCY_SHEET_ID, AGENCY_SHEET_NAME

def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip().lower()

def normalize_phone(value):
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())

def percent_to_sheet_decimal(value):
    if value is None:
        return ""
    return round(float(value) / 100, 4)

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
