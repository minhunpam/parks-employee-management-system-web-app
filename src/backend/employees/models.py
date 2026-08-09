# Built-in modules
from decimal import Decimal
from typing import override

# Django modules
from django.core.exceptions import ValidationError
from django.db import models

DEFAULT_WORK_DAYS_PER_WEEK = 5
DEFAULT_MONTHLY_TARGET_HOURS_STRING = "173.00"
ANNUAL_ALLOWED_VACATION_DAYS = 25

class Employee(models.Model):
    # Django automatically generates an id primary key
    class WorkingStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"
        
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    # Working Status
    working_status = models.CharField(
        max_length=10, 
        choices=WorkingStatus.choices, 
        default=WorkingStatus.ACTIVE)
    employment_start_date = models.DateField()
    employment_end_date = models.DateField(null=True, blank=True)

    @override
    def clean(self):
        super().clean()

        if (
            self.employment_start_date
            and self.employment_end_date
            and self.employment_end_date <= self.employment_start_date
        ):
            raise ValidationError({
                "employment_end_date": (
                    "Employment end date must be after the employment start date."
                )
            })

    # Work agreement
    work_days_per_week = models.PositiveIntegerField(default=DEFAULT_WORK_DAYS_PER_WEEK)
    monthly_target_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal(DEFAULT_MONTHLY_TARGET_HOURS_STRING)
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(employment_end_date__isnull=True)
                    | models.Q(
                        employment_end_date__gt=models.F("employment_start_date")
                    )
                ),
                name="employment_end_after_start",
            ),
        ]

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class EmployeeYear(models.Model):
    # Django automatically generates an id primary key
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employee_years")
    year = models.PositiveIntegerField()
    annual_allowed_vacation_days = models.PositiveIntegerField(default=ANNUAL_ALLOWED_VACATION_DAYS)
    carried_over_vacation_days = models.PositiveIntegerField(default=0)
    vacation_balance = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "year"],
                name="unique_employee_year",
            ),
        ]

class EmployeeMonth(models.Model):
    # Django automatically generates an id primary key
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employee_months")
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()

    opening_hour_account_balance = models.IntegerField()
    target_working_hours = models.PositiveIntegerField()
    paid_absence_hours = models.PositiveIntegerField()
    worked_hours = models.PositiveIntegerField()
    credited_working_hours = models.PositiveIntegerField()
    hour_difference = models.IntegerField()
    closing_hour_account_balance = models.IntegerField()

    opening_vacation_balance = models.PositiveIntegerField()
    vacation_days_used = models.PositiveIntegerField()
    closing_vacation_balance = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)