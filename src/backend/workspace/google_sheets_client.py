# Built-in modules
import re
from typing import ClassVar
from datetime import datetime
import calendar

# Local modules
from .csv_parser import time_to_minutes

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
        Read sheet values of `sheet_title` from `spreadsheet_id` from cell A2 to column I (horizontally) 
        and vertically until it hits blank line

        Returns:
            - list: list of data rows
        '''
        response = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_title}'!A2:I",
        ).execute()

        return response.get("values", [])

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

    def replace_employee_entries(self, spreadsheet, spreadsheet_id, sheet_title, entries,):
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
        requests.extend(GoogleSheetsClient._create_week_borders(
            spreadsheet,
            sheet_title,
            sunday_row_indices,
            data_row_count,
        ))
        requests.extend(GoogleSheetsClient._format_public_holiday_rows(
            spreadsheet,
            sheet_title,
            rows,
            data_row_count,
        ))
        
        if requests:
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": requests
                },
            ).execute()
        
        return len(imported_rows)

    @staticmethod
    def _format_public_holiday_rows(spreadsheet, sheet_title, rows, data_row_count,):
        """Highlight public-holiday rows with Google Sheets' light red 3."""
        current_sheet = GoogleSheetsClient.get_sheet(spreadsheet, sheet_title)
        if not current_sheet or data_row_count <= 0:
            print("2")
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
            print("1");
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