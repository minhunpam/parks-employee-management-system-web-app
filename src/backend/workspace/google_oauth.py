# Built-in modules
from cryptography.fernet import Fernet

# Django modules
from django.conf import settings

# Google modules
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def build_services(connection):
    refresh_token = Fernet(settings.FERNET_KEY).decrypt(
        connection.encrypted_refresh_token.encode()
    ).decode()

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=settings.DRIVE_SCOPES,
    )
    credentials.refresh(Request())

    return (
        build("drive", "v3", credentials=credentials, cache_discovery=False),
        build("sheets", "v4", credentials=credentials, cache_discovery=False),
    )