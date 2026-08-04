from django.contrib import admin
from .models import WorkspaceConfiguration

@admin.register(WorkspaceConfiguration)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "root_folder_id",
        "spreadsheet_id",
        "configured_at",
    )

    search_fields = ("owner__email", "owner__google_connection__subject", )
    
    readonly_fields = (
        "owner",
        "root_folder_id",
        "spreadsheet_id",
        "configured_at",
    )

    def has_add_permission(self, request):
        return False