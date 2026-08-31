from django.urls import path

from .views import google_login
from .views import google_callback
from .views import approval_pending
from .views import google_logout

app_name = "accounts"

urlpatterns = [
    path("google/login", google_login, name="google-login"),
    path("google/callback/", google_callback, name="google-callback"),
    path("google/logout/", google_logout, name="google-logout"),
    path("approval-pending/", approval_pending, name="approval-pending"),
]
