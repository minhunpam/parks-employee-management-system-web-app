from django.urls import path

from .views import (
    entry,
    csv_import_check,
    csv_import,
    connect,
    connect_callback,
    setup,
    save_configuration,
    create_configuration,
    update_configuration,
    activate_configuration,
    sheets_preview,
    sheets_preview_overview,
    sheets_preview_write,
    pdf_export,
    pdf_export_status,
    pdf_export_generate,
    pdf_export_confirm,
    pdf_export_send_summary,
    pdf_export_send_employees,
)

app_name = "workspace"

urlpatterns = [
    path("entry/", entry, name="entry"),
    path("entry/csv-import-check/", csv_import_check, name="csv-import-check"),
    path("entry/csv-import/", csv_import, name="csv-import"),
    path("connect/", connect, name="connect"),
    path("connect/callback/", connect_callback, name="connect-callback"),

    path("setup/", setup, name="setup"),
    path("setup/api/configurations/", create_configuration, name="configuration-create"),
    path("setup/api/configurations/<int:configuration_id>/", update_configuration, name="configuration-update"),
    path("setup/api/activate/<int:configuration_id>/", activate_configuration, name="configuration-activate"),

    path("sheets-preview/", sheets_preview, name="sheets-preview"),
    path("sheets-preview/api/overview", sheets_preview_overview, name="sheets-overview"),
    path("sheets-preview/api/write", sheets_preview_write, name="sheets-write"),

    path("pdf-export/", pdf_export, name="pdf-export"),
    path("pdf-export/api/status", pdf_export_status, name="pdf-export-status"),
    path("pdf-export/api/pdf-generate", pdf_export_generate, name="pdf-export-generate"),
    path("pdf-export/api/confirm", pdf_export_confirm, name="pdf-export-confirm"),
    path("pdf-export/api/send-summary", pdf_export_send_summary, name="pdf-export-send-summary"),
    path("pdf-export/api/send-employees", pdf_export_send_employees, name="pdf-export-send-employees"),
]
