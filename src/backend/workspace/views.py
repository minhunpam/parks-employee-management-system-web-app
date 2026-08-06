# Built-in modules
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
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from googleapiclient.errors import HttpError

# Local modules
from accounts.google_oauth import build_google_client_config
from accounts.models import GoogleConnection
from .models import WorkspaceConfiguration
from .google_resources import GoogleResources
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
        drive, sheets, folder, spreadsheet = (
            Validator.get_validated_workspace_resources(
                connection,
                configuration.root_folder_id,
                configuration.spreadsheet_id,
            )
        )
        import_state = GoogleResources.prepare_csv_import_folder(
            drive, folder["id"]
        )
    except PermissionError as error:
        return JsonResponse({"error": str(error)}, status=403)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except HttpError as error:
        return JsonResponse({"error": str(error)}, status=502)

    return {
        "drive": drive,
        "sheets": sheets,
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
            status=200,
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
    """Revalidate the current files before running the actual import."""
    context = _validated_csv_import_context(request)
    if isinstance(context, JsonResponse):
        return context

    state_response = _csv_import_state_response(context)
    if state_response.status_code != 200:
        return state_response

    # The parsing and Sheets-writing phase will be added here. Keeping the
    # revalidation in this endpoint makes it independent from the check call.
    return JsonResponse(
        {"error": "CSV import execution is not implemented yet."},
        status=501,
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

    
    connection = request.user.google_connection

    if identity["sub"] != connection.subject:
        return HttpResponseBadRequest(
            b"Drive authorization used a different Google account."
        )

    connection.granted_scopes = list(
        flow.credentials.scopes or []
    )

    fernet = Fernet(settings.FERNET_KEY)
    print(f"credentials refresh token: {flow.credentials.refresh_token}")
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
    
    has_employee_sheet = any(
        sheet.get("properties", {}).get("title") == "Mitarbeiterdaten"
        for sheet in spreadsheet.get("sheets", [])
    )

    if not has_employee_sheet:
        return JsonResponse(
            {
                "status": "not_configured",
                "workspace_status": "needs_attention",
                "error": "The Mitarbeiterdaten sheet is missing.",
            },
            status=422,
        )
    
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