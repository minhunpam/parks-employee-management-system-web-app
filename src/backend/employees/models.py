# Built-in modules
from decimal import Decimal, ROUND_HALF_UP
from typing import override

# Django modules
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

DEFAULT_WORK_DAYS_PER_WEEK = 5
DEFAULT_WEEKLY_TARGET_HOURS = Decimal("40.00")
DEFAULT_MONTHLY_TARGET_HOURS_STRING = "173.00"
DEFAULT_MONTHLY_TARGET_HOURS = 173
WEEKLY_TO_MONTHLY = Decimal("13") / Decimal("3")
ANNUAL_ALLOWED_VACATION_DAYS = 25


def monthly_hours_from_weekly(weekly_hours):
    return (Decimal(weekly_hours) * WEEKLY_TO_MONTHLY).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

def current_year():
    return timezone.localdate().year

def current_month():
    return timezone.localdate().month

class Employee(models.Model):
    # Django automatically generates an id primary key
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="employees",
        null=True,
        blank=True,
    )

    class WorkingStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()

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
    work_days_per_week = models.PositiveIntegerField(
        default=DEFAULT_WORK_DAYS_PER_WEEK,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(7)
        ],
    )
    weekly_target_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=DEFAULT_WEEKLY_TARGET_HOURS,
        validators=[
            MinValueValidator(Decimal("1.00")),
            MaxValueValidator(Decimal("50.00"))
        ],
    )
    monthly_target_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal(DEFAULT_MONTHLY_TARGET_HOURS_STRING),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "email"],
                name="unique_owner_employee_email",
            ),
            models.CheckConstraint(
                condition=models.Q(work_days_per_week__gte=1, work_days_per_week__lte=7),
                name="work_days_per_week_range",
            ),
            models.CheckConstraint(
                condition=models.Q(weekly_target_hours__gte=Decimal("1.00"), weekly_target_hours__lte=Decimal("50.00")),
                name="weekly_target_hours_range",
            ),
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
    year = models.PositiveIntegerField(default=current_year)
    annual_allowed_vacation_days = models.PositiveIntegerField(default=ANNUAL_ALLOWED_VACATION_DAYS)
    carried_over_vacation_days = models.PositiveIntegerField(default=0)
    vacation_balance = models.PositiveIntegerField(default=ANNUAL_ALLOWED_VACATION_DAYS)

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
    year = models.PositiveIntegerField(default=current_year)
    month = models.PositiveIntegerField(default=current_month)

    opening_hour_account_balance = models.DecimalField(max_digits=8,
        decimal_places=2,
        default=0,
    )
    target_working_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
    )
    paid_absence_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )
    worked_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )
    credited_working_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )
    hour_difference = models.DecimalField(
        max_digits=8,
        decimal_places=2,
    )
    closing_hour_account_balance = models.DecimalField(
        max_digits=8,
        decimal_places=2,
    )
    opening_vacation_balance = models.PositiveIntegerField(default=ANNUAL_ALLOWED_VACATION_DAYS)
    vacation_days_used = models.PositiveIntegerField(default=0)
    closing_vacation_balance = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "year", "month"],
                name="unique_employee_year_month"
            )
        ]


    @override
    def save(self, *args, **kwargs):
        if self._state.adding and self.employee_id:
            self.target_working_hours = self.employee.monthly_target_hours

        self.credited_working_hours = (
            self.paid_absence_hours + self.worked_hours
        )

        self.hour_difference = (
            self.credited_working_hours - self.target_working_hours
        )

        self.closing_hour_account_balance = (
            self.opening_hour_account_balance + self.hour_difference
        )

        self.closing_vacation_balance = (
            self.opening_vacation_balance - self.vacation_days_used
        )

        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {
                "credited_working_hours", "hour_difference",
                "closing_hour_account_balance", "closing_vacation_balance",
            }
        super().save(*args, **kwargs)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


@transaction.atomic
def recalculate_current_month(employee):
    """
        Apply a changed agreement to this month and carry only balances forward.
    """

    today = timezone.localdate()
    current = EmployeeMonth.objects.filter(
        employee=employee, year=today.year, month=today.month
    ).first()

    if current is None:
        return
    current.target_working_hours = employee.monthly_target_hours
    current.save()

    balance = current.closing_hour_account_balance
    for record in EmployeeMonth.objects.filter(employee=employee).filter(
        Q(year__gt=today.year) |
        Q(year=today.year, month__gt=today.month)
    ).order_by("year", "month"):
        record.opening_hour_account_balance = balance
        record.save(
            update_fields=["opening_hour_account_balance"]
        )
