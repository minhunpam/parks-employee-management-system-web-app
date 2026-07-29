from django.urls import path

from .views import google_login
from .views import google_callback

app_name = "accounts"

urlpatterns = [
    path("google/", google_login, name="google-login"),
    path("google/callback/", google_callback, name="google-callback"),
]
