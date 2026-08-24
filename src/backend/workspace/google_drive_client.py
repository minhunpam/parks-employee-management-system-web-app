# Built-in modules
import io
import re
from typing import ClassVar

# Django modules
from django.core.exceptions import ObjectDoesNotExist

# Google modules
from googleapiclient.http import MediaIoBaseDownload

# Local modules
from .models import WorkspaceConfiguration
from employees.models import Employee

class GoogleDriveClient:
    IMPORT_FOLDER_NAME: ClassVar[str] = "Import"
    EXPORT_FOLDER_NAME: ClassVar[str] = "Export"
    CSV_FILENAME_URL_REGEX_PATTERN: ClassVar[re.Pattern] = re.compile(
        r"^Schicht_(?P<employee_firstname>.+)_(?P<month>[^_]+)_(?P<year>20\d{2})\.csv$"
    )
    GERMAN_MONTHS: ClassVar[tuple[str, ...]] = (
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    )
    
    def __init__(self, drive_service):
        self.drive_service = drive_service

    def prepare_csv_import_and_export_folders(self, root_folder_id, configuration):
        year = configuration.period_year
        
        folder_name, german_month = self._get_month_folder_name_and_german_month(configuration)
        import_folder, import_folder_created = self._get_or_create_folder(root_folder_id, self.IMPORT_FOLDER_NAME)
        export_folder, export_folder_created = self._get_or_create_folder(root_folder_id, self.EXPORT_FOLDER_NAME)
        
        month_import_folder, month_import_folder_created = self._get_or_create_folder(import_folder["id"], folder_name)
        month_export_folder, month_export_folder_created = self._get_or_create_folder(export_folder["id"], folder_name)
        
        files = [
            item for item in self._drive_children(month_import_folder["id"])
            if (
                item.get("name", "").lower().endswith(".csv")
                and "[archived]" not in item.get("name", "").lower()
            )
        ]

        invalid_files = []
        valid_files = []
        not_employee_list = []
        for item in files:
            match = re.fullmatch(self.CSV_FILENAME_URL_REGEX_PATTERN, item.get("name", ""))
            employee_firstname = match.group("employee_firstname")
            try:
                _ = Employee.objects.get(first_name__iexact=employee_firstname)
            except ObjectDoesNotExist:
                not_employee_list.append(employee_firstname)
            
            if (
                not match
                or match.group("month") != german_month
                or int(match.group("year")) != year
            ):
                invalid_files.append(item.get("name", ""))
            else:
                valid_files.append(item)

        if not_employee_list:
            raise ValueError(f"This is the list of employee(s) who has/have been the offical staff {not_employee_list}. "
                "Please check again and register them before importing their data")

        return {
            "import_folder": import_folder,
            "month_import_folder": month_import_folder,
            "month_export_folder": month_export_folder,
            "folder_name": folder_name,
            "german_month": german_month,
            "year": year,
            "import_folder_created": import_folder_created,
            "month_import_folder_created": month_import_folder_created,
            "export_folder_created": export_folder_created,
            "month_export_folder_created": month_export_folder_created,
            "files": valid_files,
            "invalid_files": invalid_files,
        }

    def _get_or_create_folder(self, parent_id, name):
        is_created = True
        
        folders = [
            item for item in self._drive_children(parent_id, "application/vnd.google-apps.folder")
            if item.get("name") == name
        ]
        if folders:
            is_created = False
            return folders[0], is_created

        folder = self.drive_service.files().create(
            body={
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            },
            fields="id,name,mimeType",
            supportsAllDrives=False,
        ).execute()
        
        return folder, True

    def _drive_children(self, parent_folder_id, mime_type=None):
        query = f"'{parent_folder_id}' in parents and trashed = false"
        if mime_type:
            query += f" and mimeType = '{mime_type}'"

        files = []
        page_token = None
        while True:
            response = self.drive_service.files().list(
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

    def download_file_content(self, file_id):
        request = self.drive_service.files().get_media(fileId=file_id,)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        content = buffer.getvalue()
        if content.lstrip().startswith(b"{"):
            raise ValueError("Google Drive returned file metadata instead of CSV content.")

        return content

    def validate_drive_resources(self, folder_id, spreadsheet_id):
        folder = self.drive_service.files().get(
            fileId=folder_id,
            fields="id,name,mimeType,capabilities(canEdit)",
            supportsAllDrives=False,
        ).execute()

        if folder.get("mimeType") != "application/vnd.google-apps.folder":
            raise ValueError("The Drive resource is not a folder.")
        if not folder.get("capabilities", {}).get("canEdit"):
            raise PermissionError("You need write access to the Drive root folder.")

        spreadsheet_file = self.drive_service.files().get(
            fileId=spreadsheet_id,
            fields="id,mimeType,capabilities(canEdit)",
            supportsAllDrives=False,
        ).execute()
        if spreadsheet_file.get("mimeType") != "application/vnd.google-apps.spreadsheet":
            raise ValueError("The Google resource is not a spreadsheet.")
        if not spreadsheet_file.get("capabilities", {}).get("canEdit"):
            raise PermissionError("You need write access to the main spreadsheet.")

        return folder

    def archive_file(self, file_id, file_name):
        if file_name.lower().endswith(".csv"):
            archived_name = f"{file_name[:-4]}[ARCHIVED].csv"
        else:
            archived_name = f"{file_name}[ARCHIVED]"

        return self.drive_service.files().update(
            fileId=file_id,
            body={"name": archived_name},
            fields="id,name",
        ).execute()

    @staticmethod
    def _get_month_folder_name_and_german_month(configuration: WorkspaceConfiguration):
        month = configuration.period_month
        year = configuration.period_year
        
        return (
            f"{month:02d}_{year}",
            GoogleDriveClient.GERMAN_MONTHS[month - 1],
        )
    