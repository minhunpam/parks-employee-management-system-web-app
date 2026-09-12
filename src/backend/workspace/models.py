# Django modules
from django.db import models
from django.conf import settings

def default_summary_pdf_state():
    return {
        "confirmed": False,
        "reviewed": False,
    }


class WorkspaceConfiguration(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="workspace_configurations",
    )

    root_folder_id = models.CharField(max_length=255)
    spreadsheet_id = models.CharField(max_length=255)

    period_month = models.PositiveSmallIntegerField()

    period_year = models.PositiveSmallIntegerField()

    manager_recipients = models.JSONField(default=list, blank=True)

    delivery_state = models.JSONField(default=dict, blank=True)

    summary_pdf_confirm_and_review_state = models.JSONField(default=default_summary_pdf_state)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "spreadsheet_id"],
                name="unique_owner_spreadsheet",
            ),
            models.UniqueConstraint(
                fields=["owner", "period_month", "period_year"],
                name="unique_owner_period",
            )
        ]

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def config_period_str(self):
        return f"{self.period_month}/{self.period_year}"

    def _save_delivery_state(self, state):
        self.delivery_state = state
        self.save(
            update_fields=["delivery_state", "updated_at"]
        )

    def _save_summary_pdf_confirm_and_review_state(self, state):
        self.summary_pdf_confirm_and_review_state = state
        self.save(
            update_fields=["summary_pdf_confirm_and_review_state", "updated_at"]
        )
