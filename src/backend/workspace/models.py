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

    period_month = models.PositiveSmallIntegerField()

    period_year = models.PositiveSmallIntegerField()

    manager_recipients = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["spreadsheet_id", "period_month", "period_year"],
                name="unique_spreadsheet_month_year",
            )
        ]

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def config_period_str(self):
        return f"{self.period_month}/{self.period_year}"
