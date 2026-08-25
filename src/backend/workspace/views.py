# Built-in modules
import re

from cryptography.fernet import Fernet
import secrets
import json

# Django modules
from django.views.decorators.http import require_GET, require_POST
from django.http import HttpResponseBadRequest, JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

# Google modules
from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from googleapiclient.errors import HttpError

# Local modules
from accounts.google_oauth import build_google_client_config
from accounts.models import GoogleConnection
from .models import WorkspaceConfiguration
from employees.models import EmployeeMonth
from .google_resources import parse_resource_id
from .csv_parser import parse_csv_content
from utils.validator import (
    validate_connection_and_configuration,
    get_validated_workspace_resources,
    validate_folder_and_spreadsheet_ids
)
from .google_drive_client import GoogleDriveClient
from .google_sheets_client import GoogleSheetsClient
from . import sheets_preview_helpers

@login_required
def entry(request):
    connection = getattr(request.user, "google_connection", None)
    configuration = getattr(request.user, "owned_workspace", None)

    validation_response = validate_connection_and_configuration(connection, configuration)
    if validation_response is not None:
        return validation_response
    
    return render(
        request,
        "workspace/entry.html",
        {"configuration": configuration},
    )

def _validate_csv_import_context(request):
    '''
    This function centralizes the validation and preparation of the CSV import context and it can be used by
    relevant endpoints to ensure consistent CSV import behavior.
    - Validate the Google connection and configuration
    - Validate the configured root folder and spreadsheet IDs
    - Prepare the CSV import folder

    Returns:
        dict: The validated CSV import context
    '''
    connection = getattr(request.user, "google_connection", None)
    configuration = getattr(request.user, "owned_workspace", None)

    validation_response = validate_connection_and_configuration(connection, configuration)
    if validation_response is not None:
        return validation_response

    try:
        google_drive_client, google_sheets_client, _, folder, spreadsheet = (
            get_validated_workspace_resources(
                connection,
                configuration.root_folder_id,
                configuration.spreadsheet_id,
            )
        )
        import_state = google_drive_client.prepare_csv_import_folders(folder["id"], configuration)
    except RefreshError:
        return JsonResponse(
            {
                "error": "Your Google connection has expired or been revoked. Please reconnect Google.",
                "code": "google_reconnect_required",
            },
            status=401,
        )
    except PermissionError as error:
        return JsonResponse({"error": str(error)}, status=403)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except HttpError as error:
        return JsonResponse({"error": str(error)}, status=502)

    return {
        "folder": folder,
        "spreadsheet": spreadsheet,
        "import_state": import_state,
        "google_drive_client": google_drive_client,
        "google_sheets_client": google_sheets_client,
    }

def _csv_import_state_response(context):
    import_state = context["import_state"]
    spreadsheet = context["spreadsheet"]

    if import_state["invalid_import_files"]:
        return JsonResponse(
            {
                "status": "invalid_files",
                "message": "Some CSV filenames do not follow the required convention.",
                "folder": {
                    "id": import_state["month_import_folder"]["id"],
                    "name": import_state["folder_name"],
                },
                "invalid_files": import_state["invalid_import_files"],
            },
            status=422,
        )

    if not import_state["valid_import_files"]:
        return JsonResponse(
            {
                "status": "awaiting_upload",
                "message": (
                    f"Upload employee CSV files to the {import_state['folder_name']} "
                    "folder before importing."
                ),
                "folder": {
                    "id": import_state["month_import_folder"]["id"],
                    "name": import_state["folder_name"],
                },
            },
            status=400,
        )

    return JsonResponse(
        {
            "status": "ready",
            "folder": {
                "id": import_state["month_import_folder"]["id"],
                "name": import_state["folder_name"],
            },
            "files": [
                {"id": file["id"], "name": file["name"]}
                for file in import_state["valid_import_files"]
            ],
            "spreadsheet": {
                "id": spreadsheet["spreadsheetId"],
                "name": spreadsheet.get("properties", {}).get("title"),
            },
        },
        status=200,
    )

@login_required
@require_POST
def csv_import_check(request):
    context = _validate_csv_import_context(request)
    if isinstance(context, JsonResponse):
        return context
    return _csv_import_state_response(context)

@login_required
@require_POST
def csv_import(request):

    # Revalidate the current files before running the actual import.
    context = _validate_csv_import_context(request)
    if isinstance(context, JsonResponse):
        return context

    import_state = context["import_state"]
    spreadsheet = context["spreadsheet"]
    spreadsheet_id = spreadsheet["spreadsheetId"]
    
    google_drive_client: GoogleDriveClient = context["google_drive_client"]
    google_sheets_client: GoogleSheetsClient = context["google_sheets_client"]
    
    response = _csv_import_state_response(context)
    if response.status_code != 200:
        return response

    month, year = import_state["folder_name"].split("_")
    parsed_files = []
    errors = []

    for file in import_state["valid_import_files"]:
        try:
            content = google_drive_client.download_file_content(file["id"])
            parsed_file = parse_csv_content(
                content,
                file["name"],
                expected_month=int(month),
                expected_year=int(year),
            )
            parsed_files.append(
                {
                    "id": file["id"],
                    "name": file["name"],
                    "employee": parsed_file["employee"],
                    "entry_count": len(parsed_file["entries"]),
                    "entries": parsed_file["entries"],
                }
            )
        except (HttpError, ValueError, UnicodeDecodeError) as error:
            errors.append(
                {
                    "file": file["name"], 
                    "error": str(error),
                },
            ) 

    if errors:
        return JsonResponse(
            {
                "status": "invalid_csv_content",
                "message": "Some CSV files could not be parsed.",
                "errors": errors,
            },
            status=422,
        )

    imported_files = []
    imported_rows = 0

    try:
        for file in parsed_files:
            sheet_title = file["employee"]
            google_sheets_client.create_sheet_if_not_exists(spreadsheet, spreadsheet_id, sheet_title,)

            # Refresh local spreadsheet dictionary
            spreadsheet = google_sheets_client.validate_spreadsheet(spreadsheet_id)
            
            google_sheets_client.setup_sheet_headers_if_not_exists(
                spreadsheet_id,
                sheet_title,
                google_sheets_client.HEADERS["employee_headers"],
            )
            
            imported_rows += google_sheets_client.replace_employee_entries(
                spreadsheet,
                spreadsheet_id,
                sheet_title,
                file["entries"],
            )
            
            imported_files.append(file)
    except HttpError as error:
        return JsonResponse(
            {
                "status": "spreadsheet_update_failed",
                "message": "The CSV data could not be written to the spreadsheet.",
                "error": str(error),
            },
            status=502,
        )

    archive_errors = []
    archived_files = []
    for file in imported_files:
        try:
            archived = google_drive_client.archive_file(file["id"], file["name"])
            archived_files.append(archived.get("name", ""))
        except HttpError as error:
            archive_errors.append(
                {
                    "file": file["name"],
                    "error": str(error),
                }
            )

    if archive_errors:
        return JsonResponse(
            {
                "status": "imported_archive_failed",
                "message": (
                    "The spreadsheet was updated, but some CSV files could not be archived."
                ),
                "imported_rows": imported_rows,
                "archive_errors": archive_errors,
            },
            status=502,
        )

    return JsonResponse(
        {
            "status": "imported",
            "message": "CSV data was imported and the files were archived.",
            "imported_rows": imported_rows,
            "archived_files": archived_files,
            "spreadsheet": {
                "id": spreadsheet["spreadsheetId"],
                "name": spreadsheet.get("properties", {}).get("title"),
            },
            "parsed_files": [
                {
                    "name": file["name"],
                    "employee": file["employee"],
                    "entry_count": file["entry_count"],
                }
                for file in parsed_files
            ],
        },
        status=200,
    )
    
@login_required
def connect(request):
    client_config = build_google_client_config(
        redirect_uri=settings.GOOGLE_DRIVE_REDIRECT_URI
    )

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=settings.DRIVE_SCOPES,
        autogenerate_code_verifier=True,
    )
    flow.redirect_uri = settings.GOOGLE_DRIVE_REDIRECT_URI

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        login_hint=request.user.email,
    )

    request.session["google_drive_state"] = state
    request.session["google_drive_code_verifier"] = flow.code_verifier

    return redirect(authorization_url)

def connect_callback(request):
    expected_state = request.session.pop("google_drive_state", None)
    returned_state = request.GET.get("state")
    
    if (
        not expected_state
        or not returned_state
        or not secrets.compare_digest(expected_state, returned_state)
    ):
        return HttpResponseBadRequest(b"Invalid OAuth state.")

    client_config = build_google_client_config(
        redirect_uri=settings.GOOGLE_DRIVE_REDIRECT_URI
    )

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=settings.DRIVE_SCOPES,
        state=expected_state,
    )
    flow.redirect_uri = settings.GOOGLE_DRIVE_REDIRECT_URI

    if not (code_verifier := request.session.pop("google_drive_code_verifier", None)):
        return HttpResponseBadRequest(b"Missing OAuth code verifier.")
    
    flow.code_verifier = code_verifier

    flow.fetch_token(authorization_response=request.build_absolute_uri())

    try:
        identity = id_token.verify_oauth2_token(
            flow.credentials.id_token,
            Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
        )
    except (GoogleAuthError, ValueError) as error:
        return HttpResponseBadRequest(error)

    subject = identity["sub"]
    
    connection = GoogleConnection.objects.filter(
        user=request.user
    ).first()

    if connection is None:
        existing_connection = GoogleConnection.objects.filter(
            subject=subject
        ).first()

        if existing_connection and existing_connection.user_id != request.user.pk:
            return HttpResponseBadRequest(b"This Google account is connected to another user.")

        connection = existing_connection or GoogleConnection.objects.create(
            user=request.user,
            subject=subject,
        )
    elif connection.subject != subject:
        return HttpResponseBadRequest(b"Drive authorization used a different Google account.")

    connection.granted_scopes = list(flow.credentials.scopes or [])

    fernet = Fernet(settings.FERNET_KEY)
    if flow.credentials.refresh_token:
        connection.encrypted_refresh_token = fernet.encrypt(
            flow.credentials.refresh_token.encode()
        ).decode()
    
    connection.save(
        update_fields=[
            "granted_scopes",
            "encrypted_refresh_token",
            "updated_at",
        ]
    )

    return redirect("workspace:entry")

@login_required
@require_GET
def setup(request):
    connection = (
        GoogleConnection.objects
        .filter(user=request.user)
        .first()
    )

    if (
        not connection
        or not connection.encrypted_refresh_token
        or not connection.granted_scopes
    ):
        return redirect("workspace:connect")

    configuration = (
        WorkspaceConfiguration.objects
        .select_related("owner")
        .filter(owner=request.user)
        .first()
    )

    return render(
        request,
        "workspace/setup.html",
        {"configuration": configuration},
    )

@login_required
@require_POST
def save_setup(request):
    
    try:
        payload = json.loads(request.body)
        root_folder_id = parse_resource_id(
            payload.get("root_folder_id", ""), "folder"
        )
        spreadsheet_id = parse_resource_id(
            payload.get("spreadsheet_id", ""), "spreadsheet"
        )
        period_month = int(payload.get("period_month", ""))
        period_year = int(payload.get("period_year", ""))
        manager_recipients = payload.get("manager_recipients", [])
        if not isinstance(manager_recipients, list):
            raise ValueError("Manager recipients must be a list of email addresses.")
        manager_recipients = list(dict.fromkeys(
            email.strip() for email in manager_recipients if email.strip()
        ))
        for email in manager_recipients:
            validate_email(email)
    except (ValueError, TypeError, json.JSONDecodeError, ValidationError) as error:
        return JsonResponse(
            {"error": str(error)},
            status=400
        )

    if not 1 <= period_month <= 12:
        return JsonResponse({"error": "The import month must be between 1 and 12."}, status=400)
    if not 2000 <= period_year <= 2099:
        return JsonResponse({"error": "The import year must be between 2000 and 2099."}, status=400)

    configuration: WorkspaceConfiguration = WorkspaceConfiguration.objects.filter(owner=request.user).first()
    changed = configuration and (
        configuration.root_folder_id != root_folder_id
        or configuration.spreadsheet_id != spreadsheet_id
        or configuration.period_month != period_month
        or configuration.period_year != period_year
        or configuration.manager_recipients != manager_recipients
    )
    if changed and payload.get("confirmation") != "CHANGE WORKSPACE CONFIG":
        return JsonResponse(
            {
                "confirmation_phrase": "CHANGE WORKSPACE CONFIG",
                "requires_confirmation": True,
            },
            status=428,
        )

    connection = request.user.google_connection
    if not connection:
        return redirect("workspace:connect")
    
    response = validate_folder_and_spreadsheet_ids(connection, root_folder_id, spreadsheet_id)
    response_data = json.loads(response.content)
    
    if response.status_code != 200:
        return JsonResponse(
            {
                "error": response_data.get("error", "Invalid root folder or spreadsheet ID."),
            },
            status=response.status_code,
        )

    folder = response_data["folder"]
    spreadsheet = response_data["spreadsheet"]
    
    
    if configuration is None:
        configuration = WorkspaceConfiguration(owner=request.user)
        
    configuration.root_folder_id = root_folder_id
    configuration.spreadsheet_id = spreadsheet_id
    configuration.period_month = period_month
    configuration.period_year = period_year
    configuration.manager_recipients = manager_recipients
    configuration.save()
    
    return JsonResponse(
        {
            "status": "configured",
            "workspace_status": "ready",
            "root_folder": {"id": folder["id"], "name": folder.get("name")},
            "spreadsheet": {
                "id": spreadsheet["spreadsheetId"],
                "name": spreadsheet.get("properties", {}).get("title"),
            },
        },
        status=200,
    )

@login_required
def sheets_preview(request):
    overview_url = reverse("workspace:sheets-overview")
    write_url = reverse("workspace:sheets-write")
    return render(
        request,
        "workspace/sheets-preview.html",
        {
            "sheets_preview_overview_url": overview_url,
            "sheets_preview_refresh_url": overview_url,
            "sheets_preview_write_url": write_url,
        },
    )

@login_required
@require_GET
def sheets_preview_overview(request):
    connection: GoogleConnection = getattr(request.user, "google_connection", None)
    configuration: WorkspaceConfiguration = getattr(request.user, "owned_workspace", None)
    validation_response = validate_connection_and_configuration(connection, configuration)
    if validation_response is not None:
        return validation_response

    try:
        _, google_sheets_client, _, _, spreadsheet = get_validated_workspace_resources(
            connection,
            configuration.root_folder_id,
            configuration.spreadsheet_id,
        )
    except RefreshError:
        return JsonResponse(
            {
                "error": "Your Google connection has expired or been revoked. Please reconnect Google.",
                "code": "google_reconnect_required",
            },
            status=401,
        )
    except PermissionError as error:
        return JsonResponse({"error": str(error)}, status=403)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except HttpError as error:
        return JsonResponse({"error": str(error)}, status=502)

    spreadsheet_id = spreadsheet["spreadsheetId"]
    employees = {}
    sheet_records = []

    try:
        for sheet in spreadsheet.get("sheets", []):
            properties = sheet.get("properties", {})
            sheet_title = properties.get("title")
            if not sheet_title:
                continue

            raw_rows = google_sheets_client.read_sheet_values(spreadsheet_id, sheet_title)
            employee = GoogleSheetsClient._find_employee_for_sheet(sheet_title)

            # Google Sheets is the source of truth for daily activity. Rebuild
            # the database summaries before reading them for the overview.
            google_sheets_client._update_employee_summaries(
                sheet_title,
                raw_rows,
                year=configuration.period_year,
                month=configuration.period_month,
            )

            rows = [
                sheets_preview_helpers._handle_row(row, row_index)
                for row_index, row in enumerate(raw_rows)
                if row and row[0]
            ]
            
            employees[sheet_title.casefold()] = {
                "name": sheet_title,
                "sheetId": properties.get("sheetId"),
                "rows": rows,
            }
            
            sheet_records.append((employee, sheet_title, raw_rows))
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except HttpError as error:
        return JsonResponse({"error": "The spreadsheet data could not be read.", "detail": str(error)}, status=502)

    overview_rows = []
    worked_hours = 0.0
    vacation_days = 0.0
    total_warning_count = 0

    for employee, sheet_title, raw_rows in sheet_records:
        month_record = EmployeeMonth.objects.filter(
            employee=employee,
            year=configuration.period_year,
            month=configuration.period_month,
        ).first()
        
        if month_record is None:
            continue

        warnings_str, individual_warning_count = sheets_preview_helpers._sheet_warnings(raw_rows)
        worked_hours += float(month_record.worked_hours)
        vacation_days += month_record.vacation_days_used
        total_warning_count += individual_warning_count

        overview_rows.append({
            "employeeId": sheet_title.casefold(),
            "employee": sheet_title,
            "target": sheets_preview_helpers._hours(month_record.target_working_hours),
            "worked": sheets_preview_helpers._hours(month_record.worked_hours),
            "difference": sheets_preview_helpers._hours(month_record.hour_difference),
            "opening": sheets_preview_helpers._hours(month_record.opening_hour_account_balance),
            "closing": sheets_preview_helpers._hours(month_record.closing_hour_account_balance),
            "vacation": sheets_preview_helpers._days(month_record.closing_vacation_balance),
            "warnings": warnings_str,
        })

    return JsonResponse({
        "data": {
            "configuration_period": configuration.config_period_str,
            "spreadsheetUrl": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
            "overview": {
                "headers": [
                    "Employee", "Target hours", "Worked hours", "Difference",
                    "Opening balance", "Closing balance", "Vacation balance", "Warnings",
                ],
                "rows": overview_rows,
            },
            "employees": employees,
        },
    }, status=200)

@login_required
@require_POST
def sheets_preview_write(request):
    connection: GoogleConnection = getattr(request.user, "google_connection", None)
    configuration: WorkspaceConfiguration = getattr(request.user, "owned_workspace", None)
    validation_response = validate_connection_and_configuration(connection, configuration)
    if validation_response is not None:
        return validation_response

    try:
        _, google_sheets_client, _, _, spreadsheet = get_validated_workspace_resources(
            connection,
            configuration.root_folder_id,
            configuration.spreadsheet_id,
        )
    except RefreshError:
        return JsonResponse(
            {
                "error": "Your Google connection has expired or been revoked. Please reconnect Google.",
                "code": "google_reconnect_required",
            },
            status=401,
        )
    except PermissionError as error:
        return JsonResponse({"error": str(error)}, status=403)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except HttpError as error:
        return JsonResponse({"error": str(error)}, status=502)

    spreadsheet_id = spreadsheet["spreadsheetId"]

    payload = json.loads(request.body)
    sheet_title = payload["employee_id"]

    google_sheets_client.parse_manual_entry(payload, spreadsheet_id, sheet_title)
    
    return JsonResponse(
        {
            "status": "success",
            "message": "The employee entry was saved successfully.",
            "entry": {
                "employee": sheet_title,
                "date": payload.get("date"),
                "type": payload.get("type"),
            },
        },
        status=200,
    )

@login_required
@require_GET
def pdf_export(request):
    connection: GoogleConnection = getattr(request.user, "google_connection", None)
    configuration: WorkspaceConfiguration = getattr(request.user, "owned_workspace", None)
    validation_response = validate_connection_and_configuration(connection, configuration)
    if validation_response is not None:
        return validation_response

    gmail_scope = "https://www.googleapis.com/auth/gmail.send"
    if gmail_scope not in (connection.granted_scopes or []):
        return JsonResponse(
            {
                "data": {
                    "period_label": configuration.config_period_str,
                    "period_month": configuration.period_month,
                    "period_year": configuration.period_year,
                    "ready": False,
                    "readiness_message": "Reconnect Google to grant Gmail permission before sending reports.",
                    "batch_status": "not_generated",
                    "summary_pdf_url": None,
                    "reviewed": False,
                    "confirmed": False,
                    "manager_recipients": configuration.manager_recipients,
                    "employee_reports": [],
                },
                "code": "gmail_scope_required",
                "error": "The Gmail send permission is missing.",
            },
            status=200,
        )
    

    return render(
        request,
        "workspace/pdf-export.html",
        {
            "pdf_export_status_url": reverse("workspace:pdf-export-status"),
            "pdf_export_generate_url": reverse("workspace:pdf-export-generate"),
        },
    )

@login_required
@require_GET
def pdf_export_status(request):
    connection: GoogleConnection = getattr(request.user, "google_connection", None)
    configuration: WorkspaceConfiguration = getattr(request.user, "owned_workspace", None)
    validation_response = validate_connection_and_configuration(connection, configuration)
    if validation_response is not None:
        return validation_response

    try:
        google_drive_client, _, _, folder, spreadsheet = get_validated_workspace_resources(
            connection,
            configuration.root_folder_id,
            configuration.spreadsheet_id,
        )
        import_state = google_drive_client.prepare_csv_import_folders(folder["id"], configuration)
        export_state = google_drive_client.prepare_pdf_export_folders(folder["id"], configuration)
    except RefreshError:
        return JsonResponse(
            {
                "error": "Your Google connection has expired or been revoked. Please reconnect Google.",
                "code": "google_reconnect_required",
            },
            status=401,
        )
    except PermissionError as error:
        return JsonResponse({"error": str(error)}, status=403)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except HttpError as error:
        return JsonResponse({"error": str(error)}, status=502)

    german_month = export_state["german_month"]
    year = export_state["year"]
    summary_export_file = export_state["summary_export_file"]
    employee_export_files = export_state["employee_export_files"]

    invalid_import_files = import_state["invalid_import_files"]
    active_import_files = import_state["valid_import_files"]
    ready = not invalid_import_files and not active_import_files
    readiness_message = (
        "The month is ready for export."
        if ready
        else "Export is blocked until the current month is imported successfully."
    )

    return JsonResponse(
        {
            "data": {
                "period_label": f"{german_month} {year}",
                "period_month": configuration.period_month,
                "period_year": year,
                "ready": ready,
                "readiness_message": readiness_message,
                "batch_status": "generated" if summary_export_file or employee_export_files else "not_generated",
                "generation_message": "Existing export files found." if summary_export_file or employee_export_files else "No export generated.",
                "summary_pdf_url": (
                    f"https://drive.google.com/file/d/{summary_export_file['id']}/view"
                    if summary_export_file else None
                ),
                "reviewed": False,
                "confirmed": False,
                "manager_recipients": configuration.manager_recipients,
                "employee_reports": employee_export_files,
                "summary_delivery": {
                    "status": "not_sent",
                    "message": "Review and confirm the summary first.",
                    "sent_count": 0,
                    "failed_count": 0,
                },
                "employee_delivery": {
                    "status": "not_sent",
                    "message": "Review and confirm the summary first.",
                    "sent_count": 0,
                    "failed_count": 0,
                },
                "delivery_message": "",
                "spreadsheet": {
                    "id": spreadsheet["spreadsheetId"],
                    "name": spreadsheet.get("properties", {}).get("title"),
                },
            }
        },
        status=200,
    )

def pdf_export_generate(request):
    configuration: WorkspaceConfiguration = getattr(request.user, "owned_workspace", None)

    
    
    return JsonResponse(
        {
            "manager_recipients": configuration.manager_recipients,
            "message": "success",
        },
        status=200,
    )