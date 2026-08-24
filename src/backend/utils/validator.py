
# Django modules
from django.shortcuts import redirect
from django.http import JsonResponse
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

# Local modules
from accounts.models import GoogleConnection
from workspace.models import WorkspaceConfiguration
from workspace.google_oauth import build_services
from workspace.google_drive_client import GoogleDriveClient
from workspace.google_sheets_client import GoogleSheetsClient
from workspace.google_gmail_client import GoogleGmailClient

def validate_connection_and_configuration(
    connection: GoogleConnection, 
    configuration: WorkspaceConfiguration
):
    '''
    Validates the Google connection and workspace configuration.

    Args:
        connection (GoogleConnection): The Google connection taken from the logged-in user.
        configuration (WorkspaceConfiguration): The workspace configuration taken from the logged-in user.

    Returns:
        None: If the connection and configuration are valid.
        HttpResponse: If the connection or configuration is invalid, redirects to the appropriate setup page.
    '''
    if (
        not connection 
        or not connection.encrypted_refresh_token
        or not connection.granted_scopes
    ):
        return redirect("workspace:connect")

    if (
        connection
        and connection.encrypted_refresh_token
        and (
            not configuration
            or not configuration.root_folder_id
            or not configuration.spreadsheet_id
        )
        and connection.granted_scopes
    ):
        return redirect("workspace:setup")

    return None
    
def get_validated_workspace_resources(
    connection: GoogleConnection,
    root_folder_id: str,
    spreadsheet_id: str,
):
    drive_service, sheets_service, gmail_service = build_services(connection)
    google_drive_client = GoogleDriveClient(drive_service)
    google_sheets_client = GoogleSheetsClient(sheets_service)
    google_gmail_client = GoogleGmailClient(gmail_service)
    
    folder = google_drive_client.validate_drive_resources(root_folder_id, spreadsheet_id,)
    spreadsheet = google_sheets_client.validate_spreadsheet(spreadsheet_id)
    
    return google_drive_client, google_sheets_client, google_gmail_client, folder, spreadsheet

def validate_folder_and_spreadsheet_ids(
    connection: GoogleConnection,
    root_folder_id: str,
    spreadsheet_id: str,
):
    try:
        _, _, _, folder, spreadsheet = get_validated_workspace_resources(
            connection, root_folder_id, spreadsheet_id
        )
        return JsonResponse(
            {
                "folder": folder,
                "spreadsheet": spreadsheet,
            },
            status=200,
        )
    except PermissionError as error:
        return JsonResponse({"error": str(error)}, status=403)
    except RefreshError:
        return JsonResponse(
            {
                "error": "Your Google connection has expired or been revoked. Please reconnect Google.",
                "code": "google_reconnect_required",
            },
            status=401,
        )
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except HttpError as error:
        return JsonResponse({"error": str(error)}, status=502)
