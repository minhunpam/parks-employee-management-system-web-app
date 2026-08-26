# Built-in modules
import calendar
import io
from datetime import date, datetime
from pathlib import Path

# Reportlab modules
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# Local modules
from .google_sheets_client import GoogleSheetsClient
from .sheets_helpers import _cell
from employees.models import Employee, EmployeeMonth

GREEN = colors.HexColor("#2d5f1c")
PALE_GREEN = colors.HexColor("#dcebd7")
PALE_YELLOW = colors.HexColor("#fff1c9")
PALE_RED = colors.HexColor("#f2cccc")
BLACK = colors.black

EMPLOYEE_COLUMNS = [
    "Datum", "Dienstbeginn", "Pausenbeginn", "Pausenende", "Dienstschluss", "Pause Min", "Arbeitszeit", "Typ",
]

def _date_from_row(row):
    try:
        return datetime.strptime(_cell(row, 0), "%d.%m.%Y").date()
    except ValueError:
        return None

def build_snapshot(spreadsheet, sheets_client, spreadsheet_id, configuration):
    """
    Read every employee sheet once and return the export snapshot.
    """
    
    employees = []
    for sheet in spreadsheet.get("sheets", []):
        title = sheet.get("properties", {}).get("title")
        if not title:
            continue
            
        employee = GoogleSheetsClient._find_employee_for_sheet(title)
        rows = sheets_client.read_sheet_values(spreadsheet_id, title)
        rows = [
            row for row in rows
            if _date_from_row(row)
            and _date_from_row(row).year == configuration.period_year
            and _date_from_row(row).month == configuration.period_month
        ]
        if rows:
            employees.append(
                {
                    "employee": employee, 
                    "sheet_title": title, 
                    "rows": rows
                }
            )

    if not employees:
        raise ValueError("No employee records exist for the configured month.")
    return {
        "month": configuration.period_month, 
        "year": configuration.period_year, 
        "employees": employees
    }


def _format_number(value):
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("pdf-title", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=21, alignment=TA_CENTER, textColor=BLACK),
        "section": ParagraphStyle("pdf-section", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=11),
        "body": ParagraphStyle("pdf-body", parent=styles["BodyText"], fontName="Helvetica", fontSize=8, leading=10),
        "body_bold": ParagraphStyle("pdf-body-bold", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=10),
        "small": ParagraphStyle("pdf-medium", parent=styles["BodyText"], fontName="Helvetica", fontSize=7, leading=9),
        "small_bold": ParagraphStyle("pdf-medium-bold", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7, leading=9),
        "medium": ParagraphStyle("pdf-medium", parent=styles["BodyText"], fontName="Helvetica", fontSize=8, leading=9),
        "medium_bold": ParagraphStyle("pdf-medium-bold", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=9),
        "white_header": ParagraphStyle("pdf-white-header", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=11, alignment=TA_CENTER, textColor=colors.white),
    }


def _table(data, widths, header=True, font_size=8, row_colors=None):
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.45, BLACK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
    ]
    
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN), 
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), 
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")
            ])
        
    if row_colors:
        for row_index, color in row_colors.items():
            commands.append(("BACKGROUND", (0, row_index), (-1, row_index), color))
    table.setStyle(TableStyle(commands))
    
    return table


def _all_calendar_rows(rows, month, year):
    rows_by_date = {_date_from_row(row): row for row in rows}
    result = []
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        current = date(year, month, day)
        source = rows_by_date.get(current, [])
        result.append([current.strftime("%d.%m.%Y")] + [_cell(source, index) for index in range(1, 8)])
        
    return result

def _employee_pdf(item, month_name, month, year):
    employee: Employee = item["employee"]
    month_record: EmployeeMonth = employee.employee_months.filter(year=year, month=month).first()
    if month_record is None:
        raise ValueError(f"No monthly summary exists for {employee.first_name}")
    
    target = month_record.target_working_hours
    closing_hours = month_record.closing_hour_account_balance
    opening_vacation = month_record.opening_vacation_balance
    closing_vacation = month_record.closing_vacation_balance

    styles = _styles()
    logo_path = Path(__file__).resolve().parents[2] / "frontend" / "static" / "images" / "parks_logo.png"
    logo = Image(str(logo_path), width=42 * mm, height=20 * mm)
    header = Table(
        [
            [logo, Paragraph("Offizielle Stundenübersicht", styles["title"])]
        ], 
        colWidths=[55 * mm, 190 * mm]
    )
    header.setStyle(TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), 
            ("LEFTPADDING", (0, 0), (-1, -1), 0), 
            ("RIGHTPADDING", (0, 0), (-1, -1), 0)
        ])
    )

    identity = Table(
        [
            [
                Paragraph("Mitarbeiter", styles["body_bold"]), 
                Paragraph(f"{employee.first_name} {employee.last_name}", styles["body"])
            ],
            [
                Paragraph("Monat", styles["body_bold"]), 
                Paragraph(f"{month_name} {year}", styles["body"])
            ],
        ], 
        colWidths=[35 * mm, 60 * mm],
        hAlign="LEFT"
    )
    identity.setStyle(TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"), 
            ("LEFTPADDING", (0, 0), (-1, -1), 3), 
            ("RIGHTPADDING", (0, 0), (-1, -1), 3)
        ])
    )

    summary_data = [
        [
            Paragraph(
                "Kurz-Zusammenfassung", 
                ParagraphStyle("summary-title", fontName="Helvetica-Bold", fontSize=11, alignment=TA_CENTER)
            ), ""
        ],
        ["Soll Arbeitszeit Monat", _format_number(target)],
        ["Ist Arbeitszeit Monat", _format_number(month_record.credited_working_hours)],
        ["Aktuelles Stundenkonto", _format_number(closing_hours)],
        ["Urlaubstage vor Monat", _format_number(opening_vacation)],
        ["Urlaubstage nach Monat", _format_number(closing_vacation)],
    ]
    summary_table = Table(summary_data, colWidths=[42 * mm, 25 * mm])
    summary_table.setStyle(TableStyle(
        [
            ("SPAN", (0, 0), (-1, 0)), 
            ("BACKGROUND", (0, 0), (-1, 0), PALE_YELLOW), 
            ("GRID", (0, 0), (-1, -1), 0.45, BLACK), 
            ("ALIGN", (1, 1), (1, -1), "RIGHT"), 
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), 
            ("FONTSIZE", (0, 0), (-1, -1), 10), 
            ("LEFTPADDING", (0, 0), (-1, -1), 3), 
            ("RIGHTPADDING", (0, 0), (-1, -1), 3)
        ])
    )

    explanation = [
        [Paragraph("Erklärung", styles["medium_bold"])],
        [Paragraph("Soll Arbeitszeit Monat = vereinbarte Sollstunden für diesen Monat.", styles["medium"])],
        [Paragraph("Ist Arbeitszeit Monat = tatsächlich gearbeitete Stunden in diesem Monat.", styles["medium"])],
        [Paragraph("Aktuelles Stundenkonto = Plus- oder Minusstunden nach diesem Monat.", styles["medium"])],
        [Paragraph("Urlaubstage vor Monat = Urlaubskonto vor diesem Monat.", styles["medium"])],
        [Paragraph("Urlaubstage nach Monat = Urlaubskonto nach diesem Monat. Minuswerte bedeuten vorgezogenen/überzogenen Urlaub.", styles["medium"])],
    ]
    explanation_table = Table(explanation, colWidths=[125 * mm])
    explanation_table.setStyle(TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), PALE_YELLOW), 
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 3), 
            ("RIGHTPADDING", (0, 0), (-1, -1), 3), 
            ("TOPPADDING", (0, 0), (-1, -1), 3), 
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3)
        ])
    )

    daily_data = [[Paragraph(header, styles["white_header"]) for header in EMPLOYEE_COLUMNS]]
    daily_data.extend(_all_calendar_rows(item["rows"], month, year))
    daily_table = _table(daily_data, [20 * mm, 23 * mm, 25 * mm, 25 * mm, 24 * mm, 23 * mm, 23 * mm, 23 * mm], font_size=10)

    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=9 * mm, leftMargin=9 * mm, topMargin=8 * mm, bottomMargin=8 * mm)
    document.build(
        [
            header, 
            Spacer(1, 7 * mm), 
            identity, 
            Spacer(1, 4 * mm), 
            Table(
                [
                    [summary_table, explanation_table]
                ], 
                colWidths=[75 * mm, 135 * mm], 
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "TOP"), 
                    ("LEFTPADDING", (0, 0), (-1, -1), 0), 
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0)
                ],
                hAlign="LEFT"
            ), 
            Spacer(1, 12 * mm), 
            daily_table, 
            Spacer(1, 5 * mm), 
            Paragraph("Bitte kontrolliere deine Stunden. Falls etwas nicht stimmt, melde dich bitte zeitnah.", styles["medium"])
        ]
    )
    
    filename = f"Schicht_{employee.first_name}_{month_name}_{year}_EXPORT.pdf"
    
    return filename, buffer.getvalue()

def _summary_pdf(snapshot, month_name):
    styles = _styles()
    rows = [[Paragraph(header, styles["white_header"]) for header in ["Mitarbeiter", "Urlaub", "Stundenkonto", "Warnungen"]]]
    
    row_colors = {}
    personal_status = {
        "alles_ok": 0,
        "urlaub_einplanen": 0,
        "ueberstunden_abbauen": 0,
    }
    for item in snapshot["employees"]:
        employee: Employee = item["employee"]
        month_record: EmployeeMonth = employee.employee_months.filter(year=snapshot["year"], month=snapshot["month"]).first()
        if month_record is None:
            raise ValueError(f"No monthly summary exists for {employee.first_name}")
        
        vacation_balance = month_record.closing_vacation_balance 
        working_hour_balance = month_record.closing_hour_account_balance

        if working_hour_balance >= 0 and vacation_balance >= 0:
            warning = "Alles OK"
            personal_status["alles_ok"] += 1
        else:
            warning = "Urlaub einplanen"
            personal_status["urlaub_einplanen"] += 1
                    
        if working_hour_balance > 20:
            warning = "MUSS Überstunden abbauen"
            personal_status["ueberstunden_abbauen"] += 1
            
        rows.append([employee.first_name, _format_number(vacation_balance), _format_number(working_hour_balance), warning])
        row_colors[len(rows) - 1] = PALE_GREEN if warning == "Alles OK" else PALE_RED if "Überstunden" in warning else PALE_YELLOW

    personal_status_table = Table(
        [
            ["Stand", datetime.now().strftime("%d.%m.%Y %H:%M")], 
            ["Überstunden abbauen", f"{personal_status["ueberstunden_abbauen"]}"], 
            ["Urlaub einplanen", f"{personal_status["urlaub_einplanen"]}"], 
            ["Alles OK", f"{personal_status["alles_ok"]}"]
        ], 
        colWidths=[45 * mm, 50 * mm],
    )
    
    personal_status_table.setStyle(TableStyle(
        [
            ("GRID", (0, 0), (-1, -1), 0.45, BLACK), 
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), 
            ("ALIGN", (1, 0), (1, -1), "RIGHT"), 
            ("BACKGROUND", (0, 1), (-1, 1), PALE_RED), 
            ("BACKGROUND", (0, 2), (-1, 2), PALE_YELLOW), 
            ("BACKGROUND", (0, 3), (-1, 3), PALE_GREEN)
        ]
    ))
    
    table = _table(rows, [45 * mm, 30 * mm, 35 * mm, 38 * mm, 95 * mm], row_colors=row_colors)
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=15 * mm)
    document.build(
        [
            Table(
                [
                    [Paragraph(
                        "Personalstatus", 
                        ParagraphStyle("summary-title", fontName="Helvetica-Bold", fontSize=14, textColor=colors.white, alignment=TA_CENTER))
                    ]
                ], 
                colWidths=[245 * mm],
                style=[
                    ("BACKGROUND", (0, 0), (-1, -1), GREEN), 
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
                ]), 
            personal_status_table, 
            Spacer(1, 15 * mm), 
            table
        ])
    
    return f"Monatsübersicht_{month_name}_{snapshot['year']}_EXPORT.pdf", buffer.getvalue()


def render_export_batch(snapshot, german_month):
    summary_filename, summary_content = _summary_pdf(snapshot, german_month)
    employee_reports = []
    
    for item in snapshot["employees"]:
        employee_filename, employee_content = _employee_pdf(item, german_month, snapshot["month"], snapshot["year"])
        employee_reports.append(
            {
                "employee": item["employee"], 
                "filename": employee_filename, 
                "content": employee_content,
            })
        
    return {
        "summary": {
                "filename": summary_filename, 
                "content": summary_content,
        }, 
        "employees": employee_reports,
    }
