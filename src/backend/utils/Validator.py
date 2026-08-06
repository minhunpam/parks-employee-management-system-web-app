
# Django modules
from django.shortcuts import redirect
from django.http import JsonResponse
from googleapiclient.errors import HttpError

# Local modules
from accounts.models import GoogleConnection
from workspace.models import WorkspaceConfiguration
from workspace.google_resources import GoogleResources

class Validator:
    @staticmethod
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
        
    @staticmethod
    def get_validated_workspace_resources(
        connection: GoogleConnection,
        root_folder_id: str,
        spreadsheet_id: str,
    ):
        drive, sheets = GoogleResources.build_services(connection)
        folder, spreadsheet = GoogleResources.validate_resources(
            drive, sheets, root_folder_id, spreadsheet_id
        )
        return drive, sheets, folder, spreadsheet

    @staticmethod
    def validate_folder_and_spreadsheet_ids(
        connection: GoogleConnection,
        root_folder_id: str,
        spreadsheet_id: str,
    ):
        try:
            _, _, folder, spreadsheet = Validator.get_validated_workspace_resources(
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
        except ValueError as error:
            return JsonResponse({"error": str(error)}, status=400)
        except HttpError as error:
            return JsonResponse({"error": str(error)}, status=502)
