# Built-in modules
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import ClassVar
from datetime import datetime, timedelta
import calendar

# Django modules
from django.db import transaction
from django.db.models import Q

# Local modules
from .csv_parser import time_to_minutes, minutes_to_time, public_holidays
from employees.models import (
    Employee,
    EmployeeMonth,
    EmployeeYear,
    annual_allowed_vacation_days,
    determine_work_days_per_week,
)

class GoogleSheetsClient:
    HEADERS: ClassVar[dict[str, list[str]]] = {
        "employee_headers": [
            "Datum", "Dienstbegin", "Pausenbeginn",
            "Pausenende", "Dienstschluss", "Pause Min",
            "Arbeitszeit", "Typ", "Warnung"
        ],
    }

    def __init__(self, sheets_service):
        self.sheets_service =  sheets_service

    def validate_spreadsheet(self, spreadsheet_id):
        spreadsheet = self.sheets_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="spreadsheetId,properties(title),sheets(properties(sheetId,title))",
        ).execute()

        return spreadsheet

    @staticmethod
    def get_sheet(spreadsheet, sheet_title):
        '''
        spreadsheet:  {
            'spreadsheetId': '13WE8Nyr7MdUzEzruudf_ZTPW2gqV8ntcP3IEGLhVMUo',
            'properties': {'title': 'test'},
            'sheets': [
                {'properties': {'sheetId': 1794777344, 'title': 'Angelina'}},
                {'properties': {'sheetId': 661637231, 'title': 'Ademir'}}
            ]
        }
        '''
        return next(
            (
                sheet for sheet in spreadsheet.get("sheets", [])
                if sheet.get("properties", {}).get("title") == sheet_title
            ),
            None,
        )

    @staticmethod
    def has_sheet(spreadsheet, sheet_title):
        return GoogleSheetsClient.get_sheet(spreadsheet, sheet_title) is not None

    def create_sheet_if_not_exists(self, spreadsheet, spreadsheet_id, sheet_title):
        existing_sheet = GoogleSheetsClient.get_sheet(spreadsheet, sheet_title)
        if existing_sheet is not None:
            sheet_id = existing_sheet["properties"]["sheetId"]
            return self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": [
                        {
                            "updateSheetProperties": {
                                "properties": {
                                    "sheetId": sheet_id,
                                    "gridProperties": {
                                        "frozenRowCount": 1
                                    },
                                },
                                "fields": "gridProperties.frozenRowCount",
                            }
                        }
                    ]
                },
            ).execute()

        return self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title": sheet_title,
                                "gridProperties": {
                                    "rowCount": 100,
                                    "columnCount": 26,
                                    "frozenRowCount": 1,
                                },
                            }
                        }
                    }
                ]
            },
        ).execute()

    def setup_sheet_headers_if_not_exists(self, spreadsheet_id, sheet_title, headers):
        response = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_title}'!A1:I1",
        ).execute()

        if not response.get("values"):
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_title}'!A1:I1",
                valueInputOption="RAW",
                body={
                    "values": [headers]
                },
            ).execute()

    def read_sheet_values(self, spreadsheet_id, sheet_title):
        '''
        Read sheet values of `sheet_title` from `spreadsheet_id` from cell A2 to column I (horizontally) and vertically until it hits blank line

        Returns:
            - list: list of data rows
        '''
        response = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_title}'!A2:I",
        ).execute()

        return response.get("values", [])

    def parse_manual_entry(self, payload, spreadsheet_id, sheet_title):
        if not payload.get("employee_id"):
            raise ValueError("employee_id is empty")

        def parse_date(value):
            for date_format in ("%Y-%m-%d", "%d.%m.%Y"):
                try:
                    return datetime.strptime(value, date_format).date()
                except (TypeError, ValueError):
                    continue
            raise ValueError("The entry date is invalid.")

        if payload.get("date"):
            first_date = last_date = parse_date(payload["date"])
        else:
            first_date = parse_date(payload.get("date_range_start"))
            last_date = parse_date(payload.get("date_range_end"))

        if payload.get("type") == "Arbeit" and first_date != last_date:
            raise ValueError("Arbeit entries must use a single date.")
        if first_date > last_date:
            raise ValueError("The date range start cannot be after its end.")
        if (first_date.year, first_date.month) != (last_date.year, last_date.month):
            raise ValueError("The date range must stay within the configured month.")

        type_of_day = payload.get("type", "")
        shift_start = payload.get("start", "")
        shift_end = payload.get("end", "")
        is_public_holiday = first_date in public_holidays(first_date.year)

        pause_start = ""
        pause_end = ""
        warnings = ["Manuell"]
        working_minutes = 0
        pause_minutes = 30

        if type_of_day == "Arbeit" and shift_start and shift_end:
            shift_start_minutes = time_to_minutes(shift_start)
            shift_end_minutes = time_to_minutes(shift_end)
            working_minutes = shift_end_minutes - shift_start_minutes
            if working_minutes > 360:
                pause_start_minutes = shift_start_minutes + 360
                pause_end_minutes = pause_start_minutes + pause_minutes
                pause_start = minutes_to_time(pause_start_minutes)
                pause_end = minutes_to_time(pause_end_minutes)
                shift_end = minutes_to_time(shift_start_minutes + working_minutes + pause_minutes)

            if is_public_holiday and working_minutes != 0:
                working_minutes *= 2
                warnings.append("Feiertag-Arbeit")
        elif type_of_day == "Frei":
            warnings.clear()
        else:
            employee = self._find_employee_for_sheet(sheet_title)
            if type_of_day in {"Urlaub", "Krankenstand", "Feiertag", "Extern"}:
                daily_target_hours = (
                    employee.weekly_target_hours / Decimal(employee.work_days_per_week)
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                working_minutes = int(daily_target_hours * Decimal("60"))
                pause_minutes = 0

        write_values = [
            shift_start,
            pause_start,
            pause_end,
            shift_end,
            pause_minutes,
            float((Decimal(working_minutes) / Decimal("60")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )),
            type_of_day,
            ", ".join(dict.fromkeys(warnings)),
        ]

        working_date = first_date
        while working_date <= last_date:
            row_number = working_date.day + 1
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_title}!B{row_number}:I{row_number}",
                valueInputOption="RAW",
                body={"values": [write_values]},
            ).execute()
            working_date += timedelta(days=1)

    @staticmethod
    def entries_to_rows(entries):
        return [
            [
                working_date,
                entry["shift_start"],
                entry["pause_start"],
                entry["pause_end"],
                entry["shift_end"],
                entry["pause_minutes"],
                entry["shift_total_time"],
                entry["type_of_day"],
                entry.get("warnings", ""),
            ]
            for working_date, entry in entries.items()
        ]

    @staticmethod
    def _row_sort_key(row):
        date_value = row[0] if row else ""
        try:
            date_sort_value = datetime.strptime(date_value, "%d.%m.%Y")
        except (TypeError, ValueError):
            date_sort_value = datetime.max


        '''
        For the current version, sorting by date is sufficient. The time fallback is only useful if the sheet later contains multiple rows for the same date, such as separate rows for
        multiple pauses. Since the current implementation does not yet preserve multiple pause rows
        '''
        time_value = ""
        if len(row) > 1:
            time_value = row[1]
        if not time_value and len(row) > 2:
            time_value = row[2]

        try:
            time_sort_value = time_to_minutes(time_value)
        except (TypeError, ValueError):
            time_sort_value = 999999

        return date_sort_value, time_sort_value

    def replace_employee_entries(self, spreadsheet, spreadsheet_id, sheet_title, entries, owner=None):
        existing_rows = self.read_sheet_values(spreadsheet_id, sheet_title,)
        affected_dates = set(entries.keys())

        unaffected_rows = [
            row for row in existing_rows
            if not row or row[0] not in affected_dates
        ]
        imported_rows = GoogleSheetsClient.entries_to_rows(entries)
        rows = unaffected_rows + imported_rows
        rows.sort(key=GoogleSheetsClient._row_sort_key)


        sunday_row_indices = [
            row_index for row_index, row in enumerate(rows, start=1)
            if datetime.strptime(row[0], "%d.%m.%Y").weekday() == calendar.SUNDAY
        ]

        # Clear values only: formatting and columns after I remain untouched.
        self.sheets_service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_title}'!A2:I",
            body={},
        ).execute()

        if rows:
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_title}'!A2:I{len(rows) + 1}",
                valueInputOption="RAW",
                body={"values": rows},
            ).execute()

        data_row_count = max(len(existing_rows), len(rows))

        requests = []
        requests.extend(GoogleSheetsClient._create_week_borders(spreadsheet, sheet_title, sunday_row_indices, data_row_count,))
        requests.extend(GoogleSheetsClient._format_public_holiday_rows(spreadsheet, sheet_title, rows, data_row_count,))
        requests.extend(GoogleSheetsClient._protect_whole_sheet(spreadsheet, sheet_title))

        if requests:
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": requests
                },
            ).execute()


        self._update_employee_summaries(sheet_title, rows, owner=owner)

        return len(imported_rows)

    @staticmethod
    def _normalize_employee_name(value):
        return " ".join(str(value or "").split()).casefold()

    @classmethod
    def _find_employee_for_sheet(cls, sheet_title, owner=None):
        '''
        Fetch the employee from `sheet_title`
        '''

        normalized_title = cls._normalize_employee_name(sheet_title)
        employee_queryset = Employee.objects.all()
        if owner is not None:
            employee_queryset = employee_queryset.filter(owner=owner)

        employees = [
            employee for employee in employee_queryset
            if normalized_title in {
                cls._normalize_employee_name(employee.first_name),
                cls._normalize_employee_name(f"{employee.first_name} {employee.last_name}"),
            }
        ]

        if not employees:
            raise ValueError(
                f"There is a sheet, named '{sheet_title}', that doesn't seem to be an employee. "
                "Please check that manually in the configured spreadsheet! "
                "A suggested way to delete that sheet manually."
            )
        if len(employees) > 1:
            raise ValueError(f"Spreadsheet sheet '{sheet_title}' matches multiple employees.")

        return employees[0]

    @staticmethod
    def _decimal_cell_value(row, index):
        try:
            return Decimal(str(row[index] or "0")).quantize(Decimal("0.01"))
        except (IndexError, InvalidOperation, TypeError, ValueError):
            return Decimal("0.00")

    @classmethod
    def _summarize_rows(cls, rows):
        paid_absence_types = {"Urlaub", "Krankenstand", "Feiertag", "Feiertag bezahlt", "Extern",}

        worked_hours = Decimal("0.00")
        paid_absence_hours = Decimal("0.00")
        vacation_days_used = 0

        for row in rows:
            if not row or not row[0]:
                continue

            hours = cls._decimal_cell_value(row, 6)
            entry_type = str(row[7] if len(row) > 7 else "").strip()
            entry_warnings = str(row[8] if len(row) > 8 else "").split(",")

            if entry_type in paid_absence_types and "Feiertag-Arbeit" not in entry_warnings:
                paid_absence_hours += hours
            else:
                worked_hours += hours

            if entry_type == "Urlaub":
                vacation_days_used += 1

        return {
            "worked_hours": worked_hours,
            "paid_absence_hours": paid_absence_hours,
            "vacation_days_used": vacation_days_used,
        }

    @classmethod
    def _update_employee_summaries(cls, sheet_title, rows, year=None, month=None, owner=None):
        employee = cls._find_employee_for_sheet(sheet_title, owner=owner)
        dated_rows = [
            row
            for row in rows if row and row[0]
        ]

        if dated_rows:
            dates = [datetime.strptime(row[0], "%d.%m.%Y").date() for row in dated_rows]
            target_month = dates[0].month
            target_year = dates[0].year
        elif year is not None and month is not None:
            target_month = month
            target_year = year
        else:
            return

        summary = cls._summarize_rows(rows)

        with transaction.atomic():
            entitlement_work_days_per_week = determine_work_days_per_week(
                employee, target_year, target_month
            )
            employee_year, _ = EmployeeYear.objects.get_or_create(
                employee=employee,
                year=target_year,
                defaults={
                    "annual_allowed_vacation_days": annual_allowed_vacation_days(
                        entitlement_work_days_per_week
                    )
                },
            )

            different_year_nearest_previous_month = (
                EmployeeMonth.objects.filter(employee=employee)
                .filter(year__lt=target_year)
                .order_by("-year", "-month")
                .first()
            )
            same_year_nearest_previous_month = (
                EmployeeMonth.objects.filter(
                    employee=employee,
                    year=target_year,
                    month__lt=target_month,
                )
                .order_by("-month")
                .first()
            )
            nearest_previous_month = same_year_nearest_previous_month or different_year_nearest_previous_month

            opening_hour_balance = (
                nearest_previous_month.closing_hour_account_balance
                if nearest_previous_month
                else Decimal("0.00")
            )
            opening_vacation_balance = (
                nearest_previous_month.closing_vacation_balance
                if nearest_previous_month
                else annual_allowed_vacation_days(entitlement_work_days_per_week) + employee_year.carried_over_vacation_days
            )

            updated_employee_month, _ = EmployeeMonth.objects.update_or_create(
                employee=employee,
                year=target_year,
                month=target_month,
                defaults={
                    "opening_hour_account_balance": opening_hour_balance,
                    "target_working_hours": employee.monthly_target_hours,
                    "paid_absence_hours": summary["paid_absence_hours"],
                    "worked_hours": summary["worked_hours"],
                    "opening_vacation_balance": opening_vacation_balance,
                    "vacation_days_used": summary["vacation_days_used"],
                },
            )

            subsequent_employee_month_records = list(
                EmployeeMonth.objects
                .filter(
                    Q(year__gt=target_year) | Q(year=target_year, month__gt=target_month),
                    employee=employee,
                )
                .order_by("year", "month")
            )
            affected_years = {target_year} | {month_record.year for month_record in subsequent_employee_month_records}

            hour_balance = updated_employee_month.closing_hour_account_balance
            vacation_balance = updated_employee_month.closing_vacation_balance
            nearest_previous_month = updated_employee_month

            for month_record in subsequent_employee_month_records:
                month_record.opening_hour_account_balance = hour_balance
                if month_record.year != nearest_previous_month.year:
                    later_year, _ = EmployeeYear.objects.get_or_create(
                        employee=employee,
                        year=month_record.year,
                    )
                    later_year.carried_over_vacation_days = vacation_balance
                    later_year.save(update_fields=["carried_over_vacation_days","updated_at",])
                    vacation_balance = (
                        later_year.annual_allowed_vacation_days
                        + later_year.carried_over_vacation_days
                    )

                month_record.opening_vacation_balance = vacation_balance
                month_record.save()

                hour_balance = month_record.closing_hour_account_balance
                vacation_balance = month_record.closing_vacation_balance
                nearest_previous_month = month_record

            for affected_year in affected_years:
                year_record, _ = EmployeeYear.objects.get_or_create(
                    employee=employee,
                    year=affected_year,
                )
                used_vacation_days = sum(
                    record.vacation_days_used
                    for record in EmployeeMonth.objects.filter(
                        employee=employee,
                        year=affected_year,
                    )
                )
                year_record.vacation_balance = (
                    year_record.annual_allowed_vacation_days
                    + year_record.carried_over_vacation_days
                    - used_vacation_days
                )
                year_record.save(update_fields=["vacation_balance", "updated_at"])


    @staticmethod
    def _format_public_holiday_rows(spreadsheet, sheet_title, rows, data_row_count,):
        """
            Highlight public-holiday rows with Google Sheets' light red 3.
        """

        current_sheet = GoogleSheetsClient.get_sheet(spreadsheet, sheet_title)
        if not current_sheet or data_row_count <= 0:
            return []

        sheet_id = current_sheet["properties"]["sheetId"]
        holiday_row_indices = [
            row_index
            for row_index, row in enumerate(rows, start=1)
            if len(row) > 7 and row[7] == "Feiertag"
        ]

        holiday_color = {
            "red": 244 / 255,
            "green": 204 / 255,
            "blue": 204 / 255,
        }
        requests = [
            {
                "repeatCell": { # Clearing the background color of all data rows
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": data_row_count + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 9,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 1,
                                "green": 1,
                                "blue": 1,
                            }
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            }
        ]

        for row_index in holiday_row_indices:
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row_index,
                            "endRowIndex": row_index + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 9,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": holiday_color,
                            }
                        },
                        "fields": "userEnteredFormat.backgroundColor",
                    }
                }
            )

        return requests


    @staticmethod
    def _create_week_borders(spreadsheet, sheet_title, sunday_row_indices, data_row_count,):
        current_sheet = GoogleSheetsClient.get_sheet(spreadsheet, sheet_title)
        requests = []
        if not current_sheet or data_row_count <= 0:
            return requests

        sheet_id = current_sheet["properties"]["sheetId"]

        # Remove borders previously created by this method. Values are cleared
        # during imports without clearing formatting, so Sunday rows can move.
        for row_index in range(1, data_row_count + 1):
            requests.append(
                {
                    "updateBorders": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row_index,
                            "endRowIndex": row_index + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 9,
                        },
                        "bottom": {"style": "NONE"},
                    }
                }
            )

        for sunday_row_index in sunday_row_indices:
            requests.append(
                {
                    "updateBorders": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": sunday_row_index,
                            "endRowIndex": sunday_row_index + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 9,
                        },
                        "bottom": {"style": "SOLID"},
                    }
                }
            )

        return requests


    @staticmethod
    def _protect_whole_sheet(spreadsheet, sheet_title):
        current_sheet = GoogleSheetsClient.get_sheet(spreadsheet, sheet_title)
        requests = []
        if not current_sheet:
            return requests

        sheet_id = current_sheet["properties"]["sheetId"]

        requests.append(
            {
                "addProtectedRange": {
                    "protectedRange": {
                        "range": {
                            "sheetId": sheet_id,
                        },
                        "description": "Managed by PARKS. Use the application to add or correct entries.",
                        "warningOnly": True
                    }
                }
            }
        )

        return requests
