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
from django.conf import settings

# Google modules
from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from googleapiclient.errors import HttpError
from httplib2 import GoogleLoginAuthentication

# Local modules
from accounts.google_oauth import build_google_client_config
from accounts.models import GoogleConnection
from .models import WorkspaceConfiguration
from .google_resources import GoogleResources, CsvParser, GoogleSheetsHelper
from utils.Validator import Validator


@login_required
def entry(request):
    connection = getattr(request.user, "google_connection", None)
    configuration = getattr(request.user, "owned_workspace", None)

    validation_response = Validator.validate_connection_and_configuration(connection, configuration)
    if validation_response is not None:
        return validation_response
    
    return render(
        request,
        "workspace/entry.html",
        {"configuration": configuration},
    )

def _validated_csv_import_context(request):
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

    validation_response = Validator.validate_connection_and_configuration(
        connection, configuration
    )
    if validation_response is not None:
        return validation_response

    try:
        drive_service, sheets_service, folder, spreadsheet = (
            Validator.get_validated_workspace_resources(
                connection,
                configuration.root_folder_id,
                configuration.spreadsheet_id,
            )
        )
        import_state = GoogleResources.prepare_csv_import_folder(
            drive_service, folder["id"]
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

    return {
        "drive_service": drive_service,
        "sheets_service": sheets_service,
        "folder": folder,
        "spreadsheet": spreadsheet,
        "import_state": import_state,
    }

def _csv_import_state_response(context):
    import_state = context["import_state"]
    spreadsheet = context["spreadsheet"]

    if import_state["invalid_files"]:
        return JsonResponse(
            {
                "status": "invalid_files",
                "message": "Some CSV filenames do not follow the required convention.",
                "folder": {
                    "id": import_state["month_folder"]["id"],
                    "name": import_state["folder_name"],
                },
                "invalid_files": import_state["invalid_files"],
            },
            status=422,
        )

    if not import_state["files"]:
        return JsonResponse(
            {
                "status": "awaiting_upload",
                "message": (
                    f"Upload employee CSV files to the {import_state['folder_name']} "
                    "folder before importing."
                ),
                "folder": {
                    "id": import_state["month_folder"]["id"],
                    "name": import_state["folder_name"],
                },
            },
            status=400,
        )

    return JsonResponse(
        {
            "status": "ready",
            "folder": {
                "id": import_state["month_folder"]["id"],
                "name": import_state["folder_name"],
            },
            "files": [
                {"id": file["id"], "name": file["name"]}
                for file in import_state["files"]
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
    context = _validated_csv_import_context(request)
    if isinstance(context, JsonResponse):
        return context
    return _csv_import_state_response(context)

@login_required
@require_POST
def csv_import(request):

    # Revalidate the current files before running the actual import.
    context = _validated_csv_import_context(request)
    if isinstance(context, JsonResponse):
        return context

    import_state = context["import_state"]
    spreadsheet = context["spreadsheet"]
    spreadsheet_id = spreadsheet["spreadsheetId"]
    
    drive_service = context["drive_service"]
    sheets_service = context["sheets_service"]
    
    response = _csv_import_state_response(context)
    if response.status_code != 200:
        return response

    month, year = import_state["folder_name"].split("_")
    parsed_files = []
    errors = []

    for file in import_state["files"]:
        try:
            content = GoogleResources.download_file_content(
                drive_service, file["id"]
            )
            parsed_file = CsvParser.parse_csv_content(
                content,
                file["name"],
                expected_month=6,
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
            GoogleSheetsHelper.create_sheet_if_not_exists(
                sheets_service,
                spreadsheet,
                spreadsheet_id,
                sheet_title,
            )

            # Refresh local spreadsheet dictionary
            spreadsheet = sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields="spreadsheetId,properties(title),sheets(properties(sheetId,title))",
            ).execute()
            
            GoogleSheetsHelper.setup_sheet_headers_if_not_exists(
                sheets_service,
                spreadsheet_id,
                sheet_title,
                GoogleSheetsHelper.HEADERS["employee_headers"],
            )
            imported_rows += GoogleSheetsHelper.replace_employee_entries(
                sheets_service,
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
            archived = GoogleSheetsHelper.archive_file(drive_service, file["id"], file["name"],)
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
        print("Redirecting to connect because connection is missing or invalid.")
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
        root_folder_id = GoogleResources.parse_resource_id(
            payload.get("root_folder_id", ""), "folder"
        )
        spreadsheet_id = GoogleResources.parse_resource_id(
            payload.get("spreadsheet_id", ""), "spreadsheet"
        )
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        return JsonResponse({"error": str(error)}, status=400)

    configuration = WorkspaceConfiguration.objects.filter(owner=request.user).first()
    changed = configuration and (
        configuration.root_folder_id != root_folder_id
        or configuration.spreadsheet_id != spreadsheet_id
    )
    if changed and payload.get("confirmation") != "CHANGE WORKSPACE CONFIG":
        return JsonResponse(
            {
                "error": "Type CHANGE WORKSPACE CONFIG to confirm this change.",
                "requires_confirmation": True,
            },
            status=400,
        )

    connection = request.user.google_connection
    if not connection:
        return redirect("workspace:connect")
    
    response = Validator.validate_folder_and_spreadsheet_ids(connection, root_folder_id, spreadsheet_id)
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

