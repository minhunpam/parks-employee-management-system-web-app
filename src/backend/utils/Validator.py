
# Django modules
from django.shortcuts import redirect
from django.http import JsonResponse

# Local modules
from accounts.models import GoogleConnection
from workspace.models import WorkspaceConfiguration
from workspace.google_resources import (
    build_google_services,
    validate_resources,
)

class Validator:
    @staticmethod
    def validate_connection_and_configuration(
        connection: GoogleConnection, 
        configuration: WorkspaceConfiguration
    ):
        print("This function runs")
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

        print("Done")
        return None
        
    @staticmethod
    def validate_folder_and_spreadsheet_ids(
        connection: GoogleConnection,
        root_folder_id: str,
        spreadsheet_id: str
    ):
        try:
            drive, sheets = build_google_services(connection)
            folder, spreadsheet = validate_resources(
                drive, sheets, root_folder_id, spreadsheet_id
            )
            return JsonResponse(
                {
                    "folder": folder,
                    "spreadsheet": spreadsheet
                },
                status=200
            )
        except PermissionError as error:
            return JsonResponse(
                {
                    "error": str(error)
                }, 
                status=403
            )