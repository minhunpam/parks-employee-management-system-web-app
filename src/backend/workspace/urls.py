from django.urls import path

from .views import entry, connect, connect_callback, setup

app_name = "workspace"

urlpatterns = [
    path("entry/", entry, name="entry"),
    path("connect/", connect, name="connect"),
    path("connect/callback/", connect_callback, name="connect-callback"),
    path("setup/", setup, name="setup"),
]
