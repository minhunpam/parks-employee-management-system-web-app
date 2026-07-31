from django.urls import path

from .views import entry

app_name = "workspace"

urlpatterns = [
    path("entry/", entry, name="entry"),
]