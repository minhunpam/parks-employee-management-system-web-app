        
def _sheet_warnings(rows):
    warnings = {}
    total_warning_count = 0
    for row in rows:
        value = str(_cell(row, 8)).strip() if len(row) > 8 else ""
        for warning in value.split(","):
            if warning.strip(): 
                if not warning in warnings:
                    warnings[warning] = 1
                else:
                    warnings[warning] += 1

                total_warning_count += 1

    warning_list = [f"{warning}: x{warnings[warning]}" for warning in warnings]
    
    return ", ".join(warning_list) or "—", total_warning_count

def _handle_row(row: list[str], row_index=None):
    warnings = ", ".join(dict.fromkeys(_cell(row, 8).split(","))) or "—"
    pause = _cell(row, 5) or "—"
    return {
        "rowIndex": row_index,
        "date": _cell(row, 0) or "—",
        "shiftStart": _cell(row, 1) or "—",
        "pauseStart": _cell(row, 2) or "—",
        "pauseEnd": _cell(row, 3) or "—",
        "shiftEnd": _cell(row, 4) or "—",
        "pauseTime": f"{0 if pause == "—" else pause} min",
        "shiftTotalTime": _hours(_cell(row, 6)),
        "type": _cell(row, 7) or "—",
        "warnings": warnings, 
    }
    
def _cell(row, index, default=""):
    return row[index] if index < len(row) else default

def _hours(value):
    return f"{_number(value):.2f} h"
    
def _days(value):
    return f"{_number(value):.1f} d"

def _number(value):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0