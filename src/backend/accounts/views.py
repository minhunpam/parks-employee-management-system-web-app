# Built-in modules
import secrets

# Django modules
from django.conf import settings
from django.contrib.auth import login, logout
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

# Google modules
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

# Local modules
from .google_oauth import build_google_client_config
from .models import GoogleConnection, User


PENDING_APPROVAL_USER_SESSION_KEY = "pending_approval_user_id"
GOOGLE_OAUTH_POPUP_SESSION_KEY = "google_oauth_popup"


def _google_oauth_popup_response(request, destination):
    print("this runs")
    return render(
        request,
        "accounts/google-oauth-popup-complete.html",
        {
            "destination": destination
        },
    )


def home(request):
    if request.user.is_authenticated:
        if request.user.is_active:
            return redirect("workspace:entry")

        return redirect("accounts:approval_pending")

    return render(request, "accounts/home.html")


def google_login(request):
    if request.user.is_authenticated:
        return redirect("workspace:entry")

    client_config = build_google_client_config(
        redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI
    )

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=settings.GOOGLE_OAUTH_SCOPES,
        autogenerate_code_verifier=True,
    )
    flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI

    authorization_url, state = flow.authorization_url(
        access_type="online",
        prompt="select_account",
    )

    request.session[GOOGLE_OAUTH_POPUP_SESSION_KEY] = request.GET.get("popup") == "1"
    request.session["google_oauth_state"] = state
    request.session["google_oauth_code_verifier"] = flow.code_verifier

    return redirect(authorization_url)

def google_callback(request):
    expected_state = request.session.get("google_oauth_state")
    returned_state = request.GET.get("state")

    if not expected_state:
        return redirect("accounts:home")

    if (
        not returned_state
        or not secrets.compare_digest(expected_state, returned_state)
    ):
        request.session.pop("google_oauth_state", None)
        request.session.pop("google_oauth_code_verifier", None)

        return HttpResponseBadRequest(b"Invalid OAuth state.")

    request.session.pop("google_oauth_state", None)

    if not (code_verifier := request.session.pop("google_oauth_code_verifier", None)):
        return HttpResponseBadRequest(b"Missing OAuth code verifier.")

    if error := request.GET.get("error"):
        return HttpResponseBadRequest(f"Google authentication failed: {error}")

    client_config = build_google_client_config(
        redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI
    )

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=settings.GOOGLE_OAUTH_SCOPES,
        state=expected_state,
    )
    flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI

    flow.code_verifier = code_verifier

    # Sends authorization code to Google's token endpoint and exchanges it for an access token
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
        return HttpResponseBadRequest(b"Google email is not verified.")

    subject = identity["sub"]
    email = identity["email"]

    connection = (
        GoogleConnection.objects
        .select_related("user")
        .filter(subject=subject)
        .first()
    )

    if connection:
        user = connection.user
    else:
        user = User.objects.filter(email__iexact=email).first()

        if user is None:
            user = User.objects.create_user(
                email=email,
                is_active=False
            )

        connection = GoogleConnection.objects.create(
            user=user,
            subject=subject,
        )

    is_popup = request.session.pop(GOOGLE_OAUTH_POPUP_SESSION_KEY, False)
    if not user.is_active:
        # Keep the user associated with the approval page without authenticating
        # them. The page uses this ID to detect activation on refresh.
        request.session[PENDING_APPROVAL_USER_SESSION_KEY] = user.pk
        if is_popup:
            return _google_oauth_popup_response(
                request,
                reverse("accounts:approval-pending"),
            )

        return redirect("accounts:approval-pending")

    login(request, user)

    if is_popup:
        print("this run")
        return _google_oauth_popup_response(
            request,
            reverse("workspace:entry"),
        )

    return redirect("workspace:entry")


def approval_pending(request):
    if request.user.is_authenticated:
        return redirect("workspace:entry")

    pending_user_id = request.session.get(PENDING_APPROVAL_USER_SESSION_KEY)

    if not pending_user_id:
        return redirect("home")

    user = User.objects.filter(pk=pending_user_id).first()

    if not user:
        request.session.pop(PENDING_APPROVAL_USER_SESSION_KEY, None)
        return redirect("home")

    if user.is_active:
        request.session.pop(PENDING_APPROVAL_USER_SESSION_KEY, None)
        login(request, user)
        return redirect("workspace:entry")

    return render(
        request,
        "accounts/approval-pending.html",
        status=403
    )

@require_POST
def google_logout(request):
    logout(request)
    return redirect("home")
