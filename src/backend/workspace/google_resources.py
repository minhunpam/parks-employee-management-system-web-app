# Built-in modules
import re
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
    
