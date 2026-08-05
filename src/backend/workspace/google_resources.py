# Built-in modules
import re #ReGex
from datetime import date
from urllib.parse import parse_qs, urlparse
from cryptography.fernet import Fernet

# Django modules
from django.conf import settings

# Google modules
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

DRIVE_FOLDER_URL = re.compile(r"/folders/([^/?#]+)")
SPREADSHEET_URL = re.compile(r"/spreadsheets/d/([^/?#]+)")
IMPORT_FOLDER_NAME = "Import"
GERMAN_MONTHS = (
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
)
CSV_FILENAME = re.compile(
    r"^Schicht_(?P<employee_name>.+)_(?P<month>[^_]+)_(?P<year>20\d{2})\.csv$"
)

def parse_resource_id(value, resource_type):
    value = value.strip()
    if not value:
        raise ValueError("A resource ID or URL is required.")

    pattern = DRIVE_FOLDER_URL if resource_type == "folder" else SPREADSHEET_URL

    match = re.search(pattern, value)
    if match:
        return match.group(1)

    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        query_id = parse_qs(parsed.query).get("id", [None])[0]
        if query_id:
            return query_id
        raise ValueError("Enter a valid Google Drive or Sheets URL.")

    return value


def build_google_services(connection):
    refresh_token = Fernet(settings.FERNET_KEY).decrypt(
        connection.encrypted_refresh_token.encode()
    ).decode()
    
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=settings.DRIVE_SCOPES,
    )
    credentials.refresh(Request())
    
    return (
        # Build the Google Drive and Sheets API clients
        build("drive", "v3", credentials=credentials, cache_discovery=False),
        build("sheets", "v4", credentials=credentials, cache_discovery=False),
    )

def _import_previous_period():
    """
    Return the previous calendar month as its folder and filename parts.
    """
    
    today = date.today()
    year, month = today.year, today.month - 1
    if month == 0:
        year, month = year - 1, 12

    folder_name  = f"{month:02d}_{year}"
    german_month = GERMAN_MONTHS[month - 1]

    return folder_name, german_month, year


def _drive_children(drive, parent_folder_id, mime_type=None):
    '''
    This helper function retrieves all direct child files/folders from a Google Drive folder, optionally
    filtering them by the given MIME type.
    '''
    
    query = f"'{parent_folder_id}' in parents and trashed = false"
    if mime_type:
        query += f" and mimeType = '{mime_type}'"

    files = []
    page_token = None
    while True:
        response = drive.files().list(
            q=query,
            spaces="drive",
            fields="nextPageToken,files(id,name,mimeType)",
            pageToken=page_token,
            supportsAllDrives=False,
            includeItemsFromAllDrives=False,
        ).execute()
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return files


def _get_or_create_folder(drive, parent_id, name):
    folder_created = True
    
    folders = [
        item for item in _drive_children(
            drive, parent_id, "application/vnd.google-apps.folder"
        ) if item.get("name") == name
    ]
    if folders:
        folder_created = False
        return folders[0], folder_created

    folder = drive.files().create(
        body={
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        },
        fields="id,name,mimeType",
        supportsAllDrives=False,
    ).execute()
    
    return folder, folder_created


def prepare_csv_import_folder(drive, root_folder_id):
    """
    Ensure the Import/previous-month folder and inspect its CSV files.
    """
    
    folder_name, german_month, year = _import_previous_period()
    import_folder, import_created = _get_or_create_folder(
        drive, root_folder_id, IMPORT_FOLDER_NAME
    )
    month_folder, month_created = _get_or_create_folder(
        drive, import_folder["id"], folder_name
    )

    files = [
        item for item in _drive_children(drive, month_folder["id"])
        if item.get("mimeType") == "text/csv" or item.get("name", "").lower().endswith(".csv")
    ]

    invalid_files = []
    valid_files = []
    for item in files:
        match = CSV_FILENAME.fullmatch(item.get("name", ""))
        if not match or match.group("month") != german_month or int(match.group("year")) != year:
            invalid_files.append(item.get("name", ""))
        else:
            valid_files.append(item)

    return {
        "import_folder": import_folder,
        "month_folder": month_folder,
        "folder_name": folder_name,
        "german_month": german_month,
        "year": year,
        "import_created": import_created,
        "month_created": month_created,
        "files": valid_files,
        "invalid_files": invalid_files,
    }


def validate_resources(drive, sheets, root_folder_id, spreadsheet_id):
    folder = drive.files().get(
        fileId=root_folder_id,
        fields="id,name,mimeType,capabilities(canEdit)", # tells Google which properties to include in the response
        supportsAllDrives=True,
    ).execute()
        
    if folder.get("mimeType") != "application/vnd.google-apps.folder":
        raise ValueError("The Drive resource is not a folder.")
    if not folder.get("capabilities", {}).get("canEdit"):
        raise PermissionError("You need write access to the Drive root folder.")

    spreadsheet_file = drive.files().get(
        fileId=spreadsheet_id,
        fields="id,mimeType,capabilities(canEdit)",
        supportsAllDrives=True,
    ).execute()
    if spreadsheet_file.get("mimeType") != "application/vnd.google-apps.spreadsheet":
        raise ValueError("The Google resource is not a spreadsheet.")
    if not spreadsheet_file.get("capabilities", {}).get("canEdit"):
        raise PermissionError("You need write access to the main spreadsheet.")

    spreadsheet = sheets.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields="spreadsheetId,properties(title),sheets(properties(title))",
    ).execute()

    return folder, spreadsheet

def _list_files(drive_service) -> None:
    '''
    This function serves the understanding purpose
    It might not be used for the real codebase
    '''
    response = (
        drive_service.files()
        .list(
            pageSize=10,
            fields="files(id, name, mimeType)",
        )
        .execute()
    )

    files = response.get("files", [])

    for file in files:
        print(f"File name: {file["name"]}")
        print(f"File ID: {file["id"]}")
        print(f"File MIME type: {file["mimeType"]}")
        print()


if __name__ == "__main__":
    print(type(DRIVE_FOLDER_URL))
    print(type(SPREADSHEET_URL))
    
