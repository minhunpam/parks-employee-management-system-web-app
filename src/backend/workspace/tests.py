# Built-in modules
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Django modules
from django.conf import settings
from django.test import SimpleTestCase

# Local modules
from .google_resources import parse_resource_id
from .google_oauth import build_services
from .csv_parser import handle_entries, public_holidays

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

class CsvParserTests(SimpleTestCase):
    def test_minimum_break_is_added_after_six_hours(self):
        '''
        06:39 - 10:37 ---> working time: 3:58
        10:37 - 11:04 ---> pause time: 27 minutes
        11:04 - 15:13 ---> working time: 4:09
        06:39 - 15:13 ---> gross working time: 8:34

        gross working time > 6 hours && pause time < 30 minutes ---> fulfill the condition for pause correction
        '''

        
        result = handle_entries(
            {
                "04.06.2026": [
                    {"start": "06:39", "end": "10:37", "remark": "19=Pause"},
                    {"start": "11:04", "end": "15:13", "remark": "18=Dienstschluß"},
                ]
            }
        )["04.06.2026"]

        self.assertEqual(result["pause_minutes"], 30)
        self.assertEqual(result["pause_start"], "12:39")
        self.assertEqual(result["pause_end"], "13:09")
        self.assertEqual(result["shift_end"], "15:16")
        self.assertEqual(result["shift_total_time"], 8.12)
        self.assertEqual(result["warnings"], "P6")

    def test_zero_duration_pause_marker_is_not_work_time(self):
        result = handle_entries(
            {
                "10.06.2026": [
                    {"start": "08:29", "end": "12:37", "remark": "18=Dienstschluß"},
                    {"start": "12:37", "end": "12:37", "remark": "19=Pause"},
                    {"start": "13:09", "end": "16:32", "remark": "18=Dienstschluß"},
                ]
            }
        )["10.06.2026"]

        self.assertEqual(result["pause_minutes"], 32)
        self.assertEqual(result["shift_start"], "08:29")
        self.assertEqual(result["shift_end"], "16:32")
        self.assertEqual(result["shift_total_time"], 7.52)
        self.assertEqual(result["warnings"], "")

    def test_missing_date_is_a_free_day(self):
        result = handle_entries({"01.06.2026": []})["01.06.2026"]

        self.assertEqual(result["type_of_day"], "Frei")
        self.assertEqual(result["shift_total_time"], 0)
        self.assertEqual(result["warnings"], "")

    def test_public_holiday_is_marked_as_feiertag(self):
        result = handle_entries(
            {"06.04.2026": []},
            holiday_dates=public_holidays(2026),
        )["06.04.2026"]

        self.assertEqual(result["type_of_day"], "Feiertag")

    def test_worked_public_holiday_keeps_shift_data(self):
        result = handle_entries(
            {
                "06.04.2026": [
                    {"start": "08:00", "end": "12:00", "remark": None},
                ]
            },
            holiday_dates=public_holidays(2026),
        )["06.04.2026"]

        self.assertEqual(result["type_of_day"], "Feiertag")
        self.assertEqual(result["shift_start"], "08:00")
        self.assertEqual(result["shift_end"], "12:00")


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
            patch("workspace.google_oauth.Fernet", return_value=fernet) as fernet_class,
            patch(
                "workspace.google_oauth.Credentials",
                return_value=credentials,
            ) as credentials_class,
            patch("workspace.google_oauth.Request") as request_class,
            patch(
                "workspace.google_oauth.build",
                side_effect=[drive_service, sheets_service],
            ) as build_class,
        ):
            result = build_services(connection)

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
        