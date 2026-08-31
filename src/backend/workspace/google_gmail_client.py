from email.message import EmailMessage
import base64


class GoogleGmailClient:
    def __init__(self, gmail_service):
        self.gmail_service = gmail_service

    def send(self, message: EmailMessage):
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        
        return self.gmail_service.users().messages().send(
            userId="me", 
            body={
                "raw": raw
            }
        ).execute()
    
    