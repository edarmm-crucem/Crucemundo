import re
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

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
