from email.message import EmailMessage

from .google_gmail_client import GoogleGmailClient

FROM_ADDRESS = "daniel@parks-graz.at"
SENDER_NAME = "Daniel Bartol"


def _message(recipient, subject, body, filename, content):
    message = EmailMessage()
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    message.add_attachment(
        content, maintype="application", subtype="pdf", filename=filename
    )
    return message


def build_manager_email(receiving_manager, german_month_name, year, pdf_filename, content):
    body = (
        f"Hallo,\n\n"
        f"anbei findet ihr die aktuelle Planungsübersicht für {german_month_name} {year}.\n\n"
        "Bitte gebt mir kurz Bescheid, ob die Mail bei euch angekommen ist.\n\n"
        "Falls euch bei Urlaub, Stundenkonto oder Warnungen etwas auffällt, "
        "meldet euch bitte direkt bei mir.\n\n"
        "Vielen Dank!\n\nLG Daniel\n"
    )
    return _message(
        receiving_manager, f"Planungsübersicht {german_month_name} {year}", body, pdf_filename, content,
    )


def build_employee_email(receiving_employee, german_month_name, year, pdf_filename, content):
    body = (
        f"Hallo {receiving_employee.first_name},\n\n"
        f"anbei findest du deine Stundenliste für {german_month_name} {year}.\n\n"
        "Bitte prüfe die Stundenliste kurz und gib mir Bescheid, ob die Mail bei dir angekommen ist.\n\n"
        "Falls dir bei den Stunden etwas auffällt oder etwas nicht passt, melde dich bitte direkt bei mir.\n\n"
        "Vielen Dank!\n\nLG Daniel\n"
    )
    return _message(
        receiving_employee.email, f"Stundenliste {german_month_name} {year}", body, pdf_filename, content,
    )


def deliver_manager_summary(
    gmail_client: GoogleGmailClient,
    recipients,
    german_month_name,
    year,
    filename,
    content,
    sent,
):
    results = []
    for recipient in recipients:
        if recipient in sent:
            results.append({"recipient": recipient, "status": "sent"})
            continue
        try:
            email_message = build_manager_email(
                recipient, german_month_name, year, filename, content
            )
            gmail_client.send(email_message)
            sent.append(recipient)
            results.append({"recipient": recipient, "status": "sent"})
        except Exception as error:
            results.append(
                {
                    "recipient": recipient, 
                    "status": "failed", 
                    "error": str(error)
                })
            
    return results
