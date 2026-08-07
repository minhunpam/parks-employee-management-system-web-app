from cmath import e
import csv
import io
import re
from datetime import date, datetime
from urllib.parse import parse_qs, urlparse

from cryptography.fernet import Fernet
from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from typing import ClassVar

class GoogleResources:
    DRIVE_FOLDER_URL_REGEX_PATTERN: ClassVar[re.Pattern] = re.compile(r"/folders/([^/?#]+)")
    SPREADSHEET_URL_REGEX_PATTERN: ClassVar[re.Pattern] = re.compile(r"/spreadsheets/d/([^/?#]+)")
    CSV_FILENAME_URL_REGEX_PATTERN: ClassVar[re.Pattern] = re.compile(
        r"^Schicht_(?P<employee_name>.+)_(?P<month>[^_]+)_(?P<year>20\d{2})\.csv$"
    )
    
    IMPORT_FOLDER_NAME: ClassVar[str] = "Import"
    GERMAN_MONTHS: ClassVar[tuple[str, ...]] = (
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    )

    @staticmethod
    def parse_resource_id(value, resource_type):
        value = value.strip()
        if not value:
            raise ValueError("A resource ID or URL is required.")

        pattern = (
            GoogleResources.DRIVE_FOLDER_URL_REGEX_PATTERN
            if resource_type == "folder"
            else GoogleResources.SPREADSHEET_URL_REGEX_PATTERN
        )
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

    @staticmethod
    def build_services(connection):
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
            build("drive", "v3", credentials=credentials, cache_discovery=False),
            build("sheets", "v4", credentials=credentials, cache_discovery=False),
        )

    @staticmethod
    def _import_previous_period():
        today = date.today()
        year, month = today.year, today.month - 1
        if month == 0:
            year, month = year - 1, 12

        return (
            f"{month:02d}_{year}",
            GoogleResources.GERMAN_MONTHS[month - 1],
            year,
        )

    @staticmethod
    def _drive_children(drive, parent_folder_id, mime_type=None):
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

    @staticmethod
    def _get_or_create_folder(drive, parent_id, name):
        is_created = True
        
        folders = [
            item for item in GoogleResources._drive_children(
                drive, parent_id, "application/vnd.google-apps.folder"
            )
            if item.get("name") == name
        ]
        if folders:
            is_created = False
            return folders[0], is_created

        folder = drive.files().create(
            body={
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            },
            fields="id,name,mimeType",
            supportsAllDrives=False,
        ).execute()
        
        return folder, True

    @staticmethod
    def prepare_csv_import_folder(drive, root_folder_id):
        folder_name, german_month, year = GoogleResources._import_previous_period()
        import_folder, import_created = GoogleResources._get_or_create_folder(
            drive, root_folder_id, GoogleResources.IMPORT_FOLDER_NAME
        )
        month_folder, month_created = GoogleResources._get_or_create_folder(
            drive, import_folder["id"], folder_name
        )

        files = [
            item for item in GoogleResources._drive_children(drive, month_folder["id"])
            if (
                item.get("name", "").lower().endswith(".csv")
                and "[archived]" not in item.get("name", "").lower()
            )
        ]

        invalid_files = []
        valid_files = []
        for item in files:
            match = re.fullmatch(GoogleResources.CSV_FILENAME_URL_REGEX_PATTERN, item.get("name", ""))
            if (
                not match
                or match.group("month") != german_month
                or int(match.group("year")) != year
            ):
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

    @staticmethod
    def download_file_content(drive_service, file_id):
        request = drive_service.files().get_media(
            fileId=file_id,
        )
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        content = buffer.getvalue()
        if content.lstrip().startswith(b"{"):
            raise ValueError("Google Drive returned file metadata instead of CSV content.")

        return content

    @staticmethod
    def validate_resources(drive_service, sheets_service, root_folder_id, spreadsheet_id):
        folder = drive_service.files().get(
            fileId=root_folder_id,
            fields="id,name,mimeType,capabilities(canEdit)",
            supportsAllDrives=False,
        ).execute()

        if folder.get("mimeType") != "application/vnd.google-apps.folder":
            raise ValueError("The Drive resource is not a folder.")
        if not folder.get("capabilities", {}).get("canEdit"):
            raise PermissionError("You need write access to the Drive root folder.")

        spreadsheet_file = drive_service.files().get(
            fileId=spreadsheet_id,
            fields="id,mimeType,capabilities(canEdit)",
            supportsAllDrives=False,
        ).execute()
        if spreadsheet_file.get("mimeType") != "application/vnd.google-apps.spreadsheet":
            raise ValueError("The Google resource is not a spreadsheet.")
        if not spreadsheet_file.get("capabilities", {}).get("canEdit"):
            raise PermissionError("You need write access to the main spreadsheet.")

        spreadsheet = sheets_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="spreadsheetId,properties(title),sheets(properties(sheetId,title))",
        ).execute()
        
        return folder, spreadsheet

class CsvParser:
    @staticmethod
    def parse_csv_content(content, file_name, expected_month, expected_year):
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("cp1252")

        filename_match = re.fullmatch(GoogleResources.CSV_FILENAME_URL_REGEX_PATTERN, file_name)
        if not filename_match:
            raise ValueError("The CSV filename does not follow the required convention.")

        entries = {}
        reader = csv.reader(io.StringIO(text), delimiter=";")
        for line_number, row in enumerate(reader, start=1):
            cells = [str(cell or "").strip() for cell in row]
            
            date_value = next(
                (
                    cell for cell in cells
                    if re.fullmatch(r"\d{2}\.\d{2}\.20\d{2}", cell)
                ),
                None,
            )
            
            if not date_value:
                continue
                
            parsed_date = datetime.strptime(date_value, "%d.%m.%Y")
            if (
                parsed_date.month != expected_month
                or parsed_date.year != expected_year
            ):
                raise ValueError(
                    f"Line {line_number} contains a date ({parsed_date}) outside the target month."
                )

                
            times = [
                cell for cell in cells
                if re.fullmatch(r"\d{2}:\d{2}", cell)
            ]

            if len(times) < 2:
                continue

            shift_start = datetime.strptime(times[0], "%H:%M")
            shift_end = datetime.strptime(times[1], "%H:%M")
            shift_duration = (shift_end - shift_start).total_seconds() / 3600

            remark = next(
                (
                    cell for cell in cells
                    if cell == "18=Dienstschluß" or cell == "19=Pause"
                ),
                None,
            )
            
            shifts = entries.get(date_value, None)
            if shifts is None:
                entries[date_value] = []
            entries[date_value].append(
                {
                    "start": times[0],
                    "end": times[1],
                    "shift_duration": round(shift_duration, 2),
                    "remark": remark,
                }
            )
            

        if not entries:
            raise ValueError("The CSV contains no importable work entries.")

        entries = CsvParser._handle_entries(entries)
        
        return {
            "employee": filename_match.group("employee_name"),
            "file_name": file_name,
            "entries": entries,
        }

    @staticmethod
    def _handle_entries(entries: dict[str, list[dict]]):
        resulted_entries = {}
        
        for working_date, shifts in entries.items():
            shift_start = ""
            pause_start = ""
            pause_end = ""
            shift_end = ""
            pause_minutes = 0
            shift_total_time = 0.0
            type_of_day = "Arbeit"

            if len(shifts) == 1 and shifts[0]["remark"] == "19=Pause":
                shift_start = shifts[0]["start"]
                shift_end = shifts[0]["end"]
                shift_total_time = shifts[0]["shift_duration"]

                resulted_entries[working_date] = {
                    "shift_start": shift_start,
                    "pause_start": pause_start,
                    "pause_end": pause_end,
                    "shift_end": shift_end,
                    "shift_total_time": shift_total_time,
                    "pause_minutes": pause_minutes,
                    "type_of_day": type_of_day,
                }
                continue

            previous_shift_end = ""
            
            for shift_counter, shift in enumerate(shifts):
                shift_duration = shift["shift_duration"]
                shift_total_time += shift_duration
                
                if shift["remark"] == "19=Pause":
                    if shift_counter == 0:
                        shift_start = shift["start"]
                        
                    pause_start = shift["end"]
                elif shift["remark"] == "18=Dienstschluß" or shift["remark"] is None:
                    pause_end = shift["start"]
                    shift_end = shift["end"]
                    

                if previous_shift_end:
                    previous_shift_end_time = datetime.strptime(previous_shift_end, "%H:%M")
                    new_shift_start_time = datetime.strptime(shift["start"], "%H:%M")
                    print(f"previous shift end time: {previous_shift_end_time}, new shift start time: {new_shift_start_time}")
                    pause_duration = (new_shift_start_time - previous_shift_end_time).total_seconds() / 60
                    pause_minutes += pause_duration

                previous_shift_end = shift["end"]
                
            resulted_entries[working_date] = {
                "shift_start": shift_start,
                "pause_start": pause_start,
                "pause_end": pause_end,
                "shift_end": shift_end,
                "shift_total_time": shift_total_time,
                "pause_minutes": pause_minutes,
                "type_of_day": type_of_day,
            }

        return resulted_entries

class GoogleSheetsHelper:
    HEADERS: ClassVar[dict[str, list[str]]] = {
        "employee_headers": [
            "Datum", "Dienstbegin", "Pausenbeginn", 
            "Pausenende", "Dienstschluss", "Pause Min", 
            "Arbeitszeit", "Typ", "Warnung"
        ],
    }

    
    @staticmethod
    def get_sheet(spreadsheet, sheet_title):
        '''
        spreadsheet:  {
            'spreadsheetId': '13WE8Nyr7MdUzEzruudf_ZTPW2gqV8ntcP3IEGLhVMUo',
            'properties': {'title': 'test'},
            'sheets': [
                {'properties': {'sheetId': 0, 'title': 'Sheet1'}},
                {'properties': {'sheetId': 1166229168, 'title': 'Hung'}},
                {'properties': {'sheetId': 154702822, 'title': 'Sheet3'}},
                {'properties': {'sheetId': 1794777344, 'title': 'Angelina'}},
                {'properties': {'sheetId': 661637231, 'title': 'Ademir'}}
            ]
        }
        '''
        return next(
            (
                sheet for sheet in spreadsheet.get("sheets", [])
                if sheet.get("properties", {}).get("title") == sheet_title
            ),
            None,
        )

    @staticmethod
    def has_sheet(spreadsheet, sheet_title):
        return GoogleSheetsHelper.get_sheet(spreadsheet, sheet_title) is not None

    @staticmethod
    def create_sheet_if_not_exists(
        sheets_service, spreadsheet, spreadsheet_id, sheet_title
    ):
        existing_sheet = GoogleSheetsHelper.get_sheet(spreadsheet, sheet_title)
        if existing_sheet is not None:
            sheet_id = existing_sheet["properties"]["sheetId"]
            return sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": [
                        {
                            "updateSheetProperties": {
                                "properties": {
                                    "sheetId": sheet_id,
                                    "gridProperties": {
                                        "frozenRowCount": 1
                                    },
                                },
                                "fields": "gridProperties.frozenRowCount",
                            }
                        }
                    ]
                },
            ).execute()

        return sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title": sheet_title,
                                "gridProperties": {
                                    "rowCount": 100,
                                    "columnCount": 26,
                                    "frozenRowCount": 1,
                                },
                            }
                        }
                    }
                ]
            },
        ).execute()

    @staticmethod
    def setup_sheet_header(sheets_service, spreadsheet_id, sheet_title, headers):
        sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_title}'!A1:I1",
                valueInputOption="RAW",
                body={
                    "values": [headers]
                },
            ).execute()

    

if __name__ == "__main__":
    test_file_path = "/home/minhun/dev/parks/parks-employee-management-system-web-app/csv_raw_data/Schicht_Ademir_Juni_2026.csv"
    with open(test_file_path, newline="", encoding="cp1252") as f:
        reader = csv.reader(f, delimiter=";")

        for line_number, row in enumerate(reader, start=1):
            # print(f"Line {line_number}: {row}")
            cells = [str(cell or "").strip() for cell in row]
            print(cells)