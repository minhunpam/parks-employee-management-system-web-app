# Built-in modules
import secrets

# Local modules
from accounts.google_oauth import build_google_client_config
from accounts.models import GoogleConnection
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest

# Django modules
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import id_token

# Google modules
from google_auth_oauthlib.flow import Flow

from .models import WorkspaceConfiguration


@login_required
def entry(request):
    connection = getattr(request.user, "google_connection", None)
    workspace_config = getattr(request.user, "owned_workspace", None)

    if (
        not connection 
        or not connection.encrypted_refresh_token
        or not connection.granted_scopes
    ):
        return redirect("workspace:connect")

    if (
        connection
        and connection.encrypted_refresh_token
        and (
            not workspace_config
            or not workspace_config.root_folder_id
            or not workspace_config.spreadsheet_id
        )
        and connection.granted_scopes
    ):
        return redirect("workspace:setup")
    

    return render(request, "workspace/entry.html")

@login_required
def connect(request):
    client_config = build_google_client_config(
        redirect_uri=settings.GOOGLE_DRIVE_REDIRECT_URI
    )

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=settings.DRIVE_SCOPES,
        autogenerate_code_verifier=True,
    )
    flow.redirect_uri = settings.GOOGLE_DRIVE_REDIRECT_URI

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        login_hint=request.user.email,
    )

    request.session["google_drive_state"] = state
    request.session["google_drive_code_verifier"] = flow.code_verifier

    return redirect(authorization_url)

def connect_callback(request):
    expected_state = request.session.pop("google_drive_state", None)
    returned_state = request.GET.get("state")
    
    if (
        not expected_state
        or not returned_state
        or not secrets.compare_digest(expected_state, returned_state)
    ):
        return HttpResponseBadRequest(b"Invalid OAuth state.")

    client_config = build_google_client_config(
        redirect_uri=settings.GOOGLE_DRIVE_REDIRECT_URI
    )

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=settings.DRIVE_SCOPES,
        state=expected_state,
    )
    flow.redirect_uri = settings.GOOGLE_DRIVE_REDIRECT_URI

    if not (code_verifier := request.session.pop("google_drive_code_verifier", None)):
        return HttpResponseBadRequest(b"Missing OAuth code verifier.")
    
    flow.code_verifier = code_verifier

    flow.fetch_token(authorization_response=request.build_absolute_uri())

    try:
        identity = id_token.verify_oauth2_token(
            flow.credentials.id_token,
            Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
        )
    except (GoogleAuthError, ValueError) as error:
        return HttpResponseBadRequest(error)

    
    connection = request.user.google_connection

    if identity["sub"] != connection.subject:
        return HttpResponseBadRequest(
            "Drive authorization used a different Google account."
        )

    connection.granted_scopes = list(
        flow.credentials.scopes or []
    )

    fernet = Fernet(settings.FERNET_KEY)
    print(f"credentials refresh token: {flow.credentials.refresh_token}")
    if flow.credentials.refresh_token:
        connection.encrypted_refresh_token = fernet.encrypt(
            flow.credentials.refresh_token.encode()
        ).decode()
    
    connection.save(
        update_fields=[
            "granted_scopes",
            "encrypted_refresh_token",
            "updated_at",
        ]
    )

    return redirect("workspace:entry")

@login_required
@require_GET
def setup(request):
    connection = (
        GoogleConnection.objects
        .filter(user=request.user)
        .first()
    )

    if (
        not connection
        or not connection.encrypted_refresh_token
        or not connection.granted_scopes
    ):
        print("Redirecting to connect because connection is missing or invalid.")
        return redirect("workspace:connect")

    configuration = (
        WorkspaceConfiguration.objects
        .select_related("owner")
        .filter(owner=request.user)
        .first()
    )

    return render(
        request,
        "workspace/setup.html",
        {"configuration": configuration},
    )