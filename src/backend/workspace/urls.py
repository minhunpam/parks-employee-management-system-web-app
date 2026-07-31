from django.urls import path

from .views import entry
from .views import connect
from .views import connect_callback

app_name = "workspace"

urlpatterns = [
    path("entry/", entry, name="entry"),
    path("connect/", connect, name="connect"),
    path("connect/callback/", connect_callback, name="connect-callback")
]