# Built-in modules
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Django modules
from django.conf import settings
from django.test import SimpleTestCase

# Local modules
from .google_resources import parse_resource_id
from .google_resources import build_google_services

class ParseResourceIdTests(SimpleTestCase):
       def test_plain_folder_id(self):
           result = parse_resource_id("folder123", "folder")

           self.assertEqual(result, "folder123")

       def test_folder_url(self):
           result = parse_resource_id(
               "https://drive.google.com/drive/folders/folder123?usp=sharing",
               "folder",
           )

           self.assertEqual(result, "folder123")

       def test_spreadsheet_url(self):
           result = parse_resource_id(
               "https://docs.google.com/spreadsheets/d/sheet456/edit",
               "spreadsheet",
           )

           self.assertEqual(result, "sheet456")

       def test_url_with_query_id(self):
           result = parse_resource_id(
               "https://drive.google.com/open?id=resource789",
               "folder",
           )

           self.assertEqual(result, "resource789")

       def test_empty_value_raises_error(self):
           with self.assertRaises(ValueError):
               parse_resource_id("", "folder")

       def test_invalid_url_raises_error(self):
           '''
           For this invalid url, it would not match the given pattern so it has to move on to the url
           parsing and fails in the last condition
           '''
           with self.assertRaises(ValueError):
               parse_resource_id("https://example.com/file123", "folder")

class BuildGoogleResourcesTests(SimpleTestCase):
    def test_builds_drive_and_sheets_services(self):
        connection = SimpleNamespace(
            encrypted_refresh_token="encrypted-token"
        )

        decrypted_token = b"refresh-token"
        credentials = Mock()
        drive_service = Mock()
        sheets_service = Mock()

        fernet = Mock()
        fernet.decrypt.return_value = decrypted_token

        with (
            patch("workspace.google_resources.Fernet", return_value=fernet) as fernet_class,
            patch(
                "workspace.google_resources.Credentials",
                return_value=credentials,
            ) as credentials_class,
            patch("workspace.google_resources.Request") as request_class,
            patch(
                "workspace.google_resources.build",
                side_effect=[drive_service, sheets_service],
            ) as build_class,
        ):
            result = build_google_services(connection)

        self.assertEqual(result, (drive_service, sheets_service))

        print(f"Type of drive service: {type(drive_service)}")
        print(f"Type of sheets service: {type(sheets_service)}")
        
        fernet_class.assert_called_once_with(settings.FERNET_KEY)
        fernet.decrypt.assert_called_once_with(b"encrypted-token")

        credentials_class.assert_called_once_with(
            token=None,
            refresh_token="refresh-token",
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            scopes=settings.DRIVE_SCOPES,
        )

        credentials.refresh.assert_called_once_with(request_class.return_value)

        self.assertEqual(
            build_class.call_args_list[0].args,
            ("drive", "v3"),
        )
        self.assertEqual(
            build_class.call_args_list[1].args,
            ("sheets", "v4"),
        )
        