# Built-in modules
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Django modules
from django.conf import settings
from django.test import SimpleTestCase, TestCase
from decimal import Decimal

# Local modules
from .google_resources import parse_resource_id
from .google_oauth import build_services
from .csv_parser import handle_entries, public_holidays
from .google_sheets_client import GoogleSheetsClient
from employees.models import Employee, EmployeeMonth, EmployeeYear

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

class GoogleSheetsSummaryPropagationTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(
            first_name="Ademir",
            last_name="Test",
            email="ademir.test@example.com",
            employment_start_date="2026-01-01",
            monthly_target_hours=Decimal("173.00"),
        )
        self.year_2026 = EmployeeYear.objects.create(
            employee=self.employee,
            year=2026,
            annual_allowed_vacation_days=25,
            carried_over_vacation_days=2,
        )
        self.year_2027 = EmployeeYear.objects.create(
            employee=self.employee,
            year=2027,
            annual_allowed_vacation_days=25,
            carried_over_vacation_days=0,
        )

        self.november = EmployeeMonth.objects.create(
            employee=self.employee,
            year=2026,
            month=11,
            opening_hour_account_balance=Decimal("0.00"),
            target_working_hours=Decimal("173.00"),
            paid_absence_hours=Decimal("0.00"),
            worked_hours=Decimal("176.00"),
            opening_vacation_balance=Decimal("23.00"),
            vacation_days_used=3,
        )
        self.january = EmployeeMonth.objects.create(
            employee=self.employee,
            year=2027,
            month=1,
            opening_hour_account_balance=Decimal("0.00"),
            target_working_hours=Decimal("173.00"),
            paid_absence_hours=Decimal("0.00"),
            worked_hours=Decimal("160.00"),
            opening_vacation_balance=22,
            vacation_days_used=2,
        )

    def test_imported_december_updates_previous_and_later_balance_chain(self):
        sheets_service = Mock()
        client = GoogleSheetsClient(sheets_service)
        spreadsheet = {
            "sheets": [{"properties": {"sheetId": 123, "title": "Ademir"}}],
        }
        existing_december_rows = [
            ["01.12.2026", "08:00", "", "", "16:30", "30", "8.00", "Arbeit", ""],
            ["02.12.2026", "", "", "", "", "", "Frei", ""],
        ]
        imported_entries = {
            "02.12.2026": {
                "shift_start": "",
                "pause_start": "",
                "pause_end": "",
                "shift_end": "",
                "pause_minutes": 0,
                "shift_total_time": 8.00,
                "type_of_day": "Urlaub",
                "warnings": "",
            },
        }

        with patch.object(client, "read_sheet_values", return_value=existing_december_rows):
            client.replace_employee_entries(
                spreadsheet,
                "spreadsheet-id",
                "Ademir",
                imported_entries,
            )

        december = EmployeeMonth.objects.get(
            employee=self.employee,
            year=2026,
            month=12,
        )
        january = EmployeeMonth.objects.get(
            employee=self.employee,
            year=2027,
            month=1,
        )
        self.year_2026.refresh_from_db()
        self.year_2027.refresh_from_db()

        self.assertEqual(december.opening_hour_account_balance, Decimal("3.00"))
        self.assertEqual(december.worked_hours, Decimal("8.00"))
        self.assertEqual(december.paid_absence_hours, Decimal("8.00"))
        self.assertEqual(december.vacation_days_used, 1)
        self.assertEqual(december.opening_vacation_balance, Decimal("20.00"))
        self.assertEqual(december.closing_vacation_balance, Decimal("19.00"))

        self.assertEqual(january.opening_hour_account_balance, december.closing_hour_account_balance)
        self.assertEqual(january.opening_vacation_balance, Decimal("44.00"))
        self.assertEqual(january.closing_vacation_balance, Decimal("42.00"))
        self.assertEqual(self.year_2026.vacation_balance, 23)
        self.assertEqual(self.year_2027.carried_over_vacation_days, 19)
        self.assertEqual(self.year_2027.vacation_balance, 42)

class ManagerEmailTests(SimpleTestCase):
    def test_gmail_client_sends_message_as_base64url_raw_payload(self):
        from email.message import EmailMessage
        from .google_gmail_client import GoogleGmailClient

        gmail_service = Mock()
        gmail_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
            "id": "message-id"
        }
        message = EmailMessage()
        message["To"] = "manager@example.com"
        message.set_content("Hello")

        result = GoogleGmailClient(gmail_service).send(message)

        self.assertEqual(result, {"id": "message-id"})
        request = gmail_service.users.return_value.messages.return_value.send
        request.assert_called_once()
        self.assertEqual(request.call_args.kwargs["userId"], "me")
        self.assertIn("raw", request.call_args.kwargs["body"])

    def test_delivers_summary_separately_to_each_manager(self):
        from .email_delivery import deliver_manager_summary

        gmail_client = Mock()
        sent = []
        results = deliver_manager_summary(
            gmail_client,
            ["first@example.com", "second@example.com"],
            "Juni",
            2026,
            "Monatsübersicht_Juni_2026_EXPORT.pdf",
            b"summary-pdf-content",
            sent,
        )

        self.assertEqual([result["status"] for result in results], ["sent", "sent"])
        self.assertEqual(gmail_client.send.call_count, 2)
        self.assertEqual(sent, ["first@example.com", "second@example.com"])
        for call in gmail_client.send.call_args_list:
            message = call.args[0]
            self.assertEqual(len(list(message.iter_attachments())), 1)
            self.assertEqual(
                list(message.iter_attachments())[0].get_filename(),
                "Monatsübersicht_Juni_2026_EXPORT.pdf",
            )

    def test_does_not_resend_summary_to_manager_already_sent(self):
        from .email_delivery import deliver_manager_summary

        gmail_client = Mock()
        results = deliver_manager_summary(
            gmail_client,
            ["manager@example.com"],
            "Juni",
            2026,
            "summary.pdf",
            b"pdf",
            ["manager@example.com"],
        )

        self.assertEqual(results, [{"recipient": "manager@example.com", "status": "sent"}])
        gmail_client.send.assert_not_called()

    def test_builds_employee_email_with_personal_pdf_and_message(self):
        from .email_delivery import build_employee_email

        employee = SimpleNamespace(first_name="Ademir", email="ademir@example.com")
        message = build_employee_email(
            "Hung",
            employee,
            "Juni",
            2026,
            "Schicht_Ademir_Juni_2026_EXPORT.pdf",
            b"employee-pdf-content",
        )

        self.assertEqual(message["To"], "ademir@example.com")
        self.assertEqual(message["Subject"], "Stundenliste Juni 2026")
        body = message.get_body().get_content()
        self.assertIn("Hallo Ademir,", body)
        self.assertIn("LG Hung", body)
        attachments = list(message.iter_attachments())
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].get_filename(), "Schicht_Ademir_Juni_2026_EXPORT.pdf")
        self.assertEqual(attachments[0].get_payload(decode=True), b"employee-pdf-content")

class BuildGoogleResourcesTests(SimpleTestCase):
    def test_builds_drive_and_sheets_services(self):
        connection = SimpleNamespace(
            encrypted_refresh_token="encrypted-token"
        )

        decrypted_token = b"refresh-token"
        credentials = Mock()
        drive_service = Mock()
        sheets_service = Mock()
        gmail_service = Mock()

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
                side_effect=[drive_service, sheets_service, gmail_service],
            ) as build_class,
        ):
            result = build_services(connection)

        self.assertEqual(result, (drive_service, sheets_service, gmail_service))

        
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
        self.assertEqual(
            build_class.call_args_list[2].args,
            ("gmail", "v1"),
        )

    def test_can_make_gmail_profile_request(self):
        connection = SimpleNamespace(
            encrypted_refresh_token="encrypted-token"
        )
        credentials = Mock()
        gmail_service = Mock()
        gmail_service.users.return_value.getProfile.return_value.execute.return_value = {
            "emailAddress": "connected@example.com",
        }

        fernet = Mock()
        fernet.decrypt.return_value = b"refresh-token"

        with (
            patch("workspace.google_oauth.Fernet", return_value=fernet),
            patch("workspace.google_oauth.Credentials", return_value=credentials),
            patch("workspace.google_oauth.Request"),
            patch(
                "workspace.google_oauth.build",
                side_effect=[Mock(), Mock(), gmail_service],
            ) as build_class,
        ):
            _, _, service = build_services(connection)
            profile = service.users().getProfile(userId="me").execute()

        self.assertEqual(profile["emailAddress"], "connected@example.com")
        self.assertEqual(build_class.call_count, 3)
        self.assertEqual(
            build_class.call_args_list[2].args,
            ("gmail", "v1"),
        )
        self.assertEqual(
            build_class.call_args_list[2].kwargs,
            {"credentials": credentials, "cache_discovery": False},
        )
        gmail_service.users.return_value.getProfile.assert_called_once_with(userId="me")
        gmail_service.users.return_value.getProfile.return_value.execute.assert_called_once_with()
        