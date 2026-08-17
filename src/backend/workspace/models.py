# Django modules
from django.db import models
from django.conf import settings

class WorkspaceConfiguration(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_workspace",
    )

    root_folder_id = models.CharField(
        max_length=255,
        unique=True,
    )
    spreadsheet_id = models.CharField(
        max_length=255,
        blank=True,
    )

    period_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    period_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
