# Built-in modules
import re
import io
import csv
import calendar
import holidays
import itertools
from datetime import datetime, date

CSV_FILENAME_URL_REGEX_PATTERN = re.compile(
    r"^Schicht_(?P<employee_name>.+)_(?P<month>[^_]+)_(?P<year>20\d{2})\.csv$"
)

def parse_csv_content(content, file_name, expected_month, expected_year):
    filename_match = re.fullmatch(CSV_FILENAME_URL_REGEX_PATTERN, file_name)
    if not filename_match:
        raise ValueError("The CSV filename does not follow the required convention.")

    employee_name = filename_match.group("employee_name")

    text = content.decode("windows-1252")
    
    entries = {}
    days_in_month = calendar.monthrange(expected_year, expected_month)[1]
    for day in range(1, days_in_month + 1):
        date_str = f"{day:02d}.{expected_month:02d}.{expected_year}"
        entries[date_str] = []
    
    normalized_data = []
    csv_reader = csv.reader(io.StringIO(text), delimiter=";")
    for row in csv_reader:
        cells = [
            str(cell or "").strip() for cell in row
            if cell != ""
        ]

        if not cells:
            continue

        normalized_data.append(cells)

    employee_name_including_row = normalized_data[2]
    file_extracted_employee_name = employee_name_including_row[0]
    if not employee_name in file_extracted_employee_name:
        raise ValueError(
            f"CSV filename says: {employee_name}, but the file extracted name is {file_extracted_employee_name}. "
            f"Please inspect this file again."
        )

    # Delete the first 4 rows and the last 3 rows which contain unnecessary data
    del normalized_data[0:4]
    del normalized_data[-3:]
    
    for line_number, cells in enumerate(normalized_data, start=1):
        date_value = next(
            (
                cell for cell in cells
                if re.fullmatch(r"\d{2}\.\d{2}\.20\d{2}", cell)
            ),
            None,
        )
            
        parsed_date = datetime.strptime(date_value, "%d.%m.%Y")
        if (
            parsed_date.month != expected_month
            or parsed_date.year != expected_year
        ):
            raise ValueError(
                f'''
                Line {line_number} contains a date ({parsed_date}) outside the target month.
                Line content: {cells}
                '''
            )

            
        times = [
            cell for cell in cells
            if re.fullmatch(r"\d{2}:\d{2}", cell)
        ]

        if len(times) != 2:
            raise ValueError(
                f'''
                Line {line_number} does not contain exactly two time cells: {times}
                Line content: {cells}
                '''
            )


        remark = next(
            (
                cell for cell in cells
                if cell == "18=Dienstschluß" or cell == "19=Pause"
            ),
            None,
        )
        
        entries[date_value].append(
            {
                "start": times[0],
                "end": times[1],
                "remark": remark,
            }
        )
        
    if not entries:
        raise ValueError("The CSV contains no importable work entries.")

    holiday_dates = public_holidays(expected_year)
    entries = handle_entries(
        entries,
        holiday_dates=holiday_dates,
    )
    
    return {
        "employee": employee_name,
        "file_name": file_name,
        "entries": entries,
    }

def public_holidays(year: int) -> set[date]:
    """Return statutory public holidays for Graz (Styria), Austria."""
    return set(
        holidays.country_holidays(
            "AT",
            subdiv="6",  # Styria
            years=[year],
        ).keys()
    )

def handle_entries(
    entries: dict[str, list[dict]],
    holiday_dates: set[date] | None = None,
):
    holiday_dates = holiday_dates or set()
    resulted_entries = {}

    for working_date, shifts in entries.items():
        parsed_date = datetime.strptime(working_date, "%d.%m.%Y").date()
        is_public_holiday = parsed_date in holiday_dates

        if not shifts:
            resulted_entries[working_date] = {
                "shift_start": "",
                "pause_start": "",
                "pause_end": "",
                "shift_end": "",
                "shift_total_time": 0.0,
                "pause_minutes": 0,
                "type_of_day": "Feiertag" if is_public_holiday else "Frei",
                "warnings": "Auto-Feiertag" if is_public_holiday else "",
            }
            continue

        shifts = sorted(
            shifts,
            key=lambda shift: time_to_minutes(shift["start"]),
        )

        shift_start = shifts[0]["start"]
        shift_end = shifts[-1]["end"]
        shift_start_minutes = time_to_minutes(shift_start)
        shift_end_minutes = time_to_minutes(shift_end)
        shift_gross_minutes = shift_end_minutes - shift_start_minutes
        
        pause_windows = []
        warnings = []

        for current, following in itertools.pairwise(shifts):
            current_end = time_to_minutes(current["end"])
            following_start = time_to_minutes(following["start"])
            pause_gap = following_start - current_end

            if pause_gap < 0:
                warnings.append("ÜBERLAPPUNG")
            elif 5 <= pause_gap <= 180:
                pause_windows.append(
                    {
                        "start": current["end"],
                        "end": following["start"],
                        "minutes": pause_gap,
                    }
                )
            elif pause_gap > 180:
                warnings.append("LÜCKE")

        pause_minutes = sum(
            pause["minutes"] for pause in pause_windows
        )
        pause_start = pause_windows[0]["start"] if pause_windows else ""
        pause_end = pause_windows[0]["end"] if pause_windows else ""
        working_minutes = max(shift_gross_minutes - pause_minutes, 0) # Avoid negative working minutes

        if len(pause_windows) >= 3:
            warnings.append("P3")
        elif len(pause_windows) == 2:
            warnings.append("P2")

        # Days longer than six hours need at least 30 minutes of pause,
        # and the first pause must begin within the first six hours.
        first_pause_start = (
            time_to_minutes(pause_start)
            if pause_start
            else None
        )
        requires_break_correction = (
            shift_gross_minutes > 360
            and (
                pause_minutes < 30
                or first_pause_start is None
                or first_pause_start - shift_start_minutes > 360
            )
        )

        if requires_break_correction:
            pause_minutes = max(pause_minutes, 30)
            pause_start_minutes = shift_start_minutes + 360
            pause_end_minutes = pause_start_minutes + 30
            pause_start = minutes_to_time(pause_start_minutes)
            pause_end = minutes_to_time(pause_end_minutes)

            # Preserve the calculated working time while moving the end
            # time when a synthetic pause is inserted.
            shift_end = minutes_to_time(
                shift_start_minutes + working_minutes + pause_minutes
            )
            warnings.append("P6")

        
        if is_public_holiday and working_minutes != 0:
            working_minutes *= 2
            warnings.append("Feiertag-Arbeit")
        
        resulted_entries[working_date] = {
            "shift_start": shift_start,
            "pause_start": pause_start,
            "pause_end": pause_end,
            "shift_end": shift_end,
            "shift_total_time": round(working_minutes / 60, 2),
            "pause_minutes": pause_minutes,
            "type_of_day": "Feiertag" if is_public_holiday else "Arbeit",
            "warnings": ", ".join(dict.fromkeys(warnings)),
        }

    return resulted_entries

def time_to_minutes(value: str) -> int:
    parsed_time = datetime.strptime(value, "%H:%M")
    return parsed_time.hour * 60 + parsed_time.minute

def minutes_to_time(value: int) -> str:
    hours, minutes = divmod(value, 60)
    return f"{hours:02d}:{minutes:02d}"
