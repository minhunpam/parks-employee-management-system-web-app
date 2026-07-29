# Built-in modules
import secrets
import json

# Django modules
from django.shortcuts import render
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponseBadRequest, JsonResponse

# Google modules
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import id_token


def google_login(request):
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
        }
    }

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=settings.GOOGLE_OAUTH_SCOPES,
        autogenerate_code_verifier=True,
    )
    flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI

    authorization_url, state = flow.authorization_url(
        access_type="online",
        include_granted_scopes="true",
        prompt="select_account",
    )


    request.session["google_oauth_state"] = state
    request.session["google_oauth_code_verifier"] = flow.code_verifier

    return redirect(authorization_url)

def google_callback(request):
    
    expected_state = request.session.pop("google_oauth_state", None)
    returned_state = request.GET.get("state")

    if (
        not expected_state
        or not returned_state
        or not secrets.compare_digest(expected_state, returned_state)
    ):
        return HttpResponseBadRequest("Invalid OAuth state.")

    if error := request.GET.get("error"):
        return HttpResponseBadRequest(f"Google authentication failed: {error}")

    client_config = {
        "web": {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
        }
    }

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=settings.GOOGLE_OAUTH_SCOPES,
        state=expected_state,
    )
    flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI

    if not (code_verifier := request.session.pop(
        "google_oauth_code_verifier",
        None,
    )):
        return HttpResponseBadRequest("Missing OAuth code verifier.")

    
    flow.code_verifier = code_verifier
    
    # Server-to-server authorization code exchange
    flow.fetch_token(
        authorization_response=request.build_absolute_uri()
    )

    try:
        identity = id_token.verify_oauth2_token(
            flow.credentials.id_token,
            Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
        )
    except (GoogleAuthError, ValueError) as error:
        return HttpResponseBadRequest(error)
    
    if identity.get("email_verified") is not True:
        return HttpResponseBadRequest("Google email is not verified.")
    
    return JsonResponse(
        {
            "sub": identity["sub"],
            "email": identity["email"],
            "name": identity.get("name"),
        }
    )
