from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Employee, monthly_hours_from_weekly


class WorkingAgreementTests(TestCase):
    def test_monthly_conversion_uses_half_up_rounding(self):
        self.assertEqual(monthly_hours_from_weekly(Decimal("20.00")), Decimal("86.67"))
        self.assertEqual(monthly_hours_from_weekly(Decimal("40.00")), Decimal("173.33"))

    def test_working_agreement_boundaries_are_validated(self):
        employee = Employee(
            first_name="Ada",
            last_name="Test",
            email="ada@example.com",
            employment_start_date="2026-01-01",
            work_days_per_week=1,
            weekly_target_hours=Decimal("20.00"),
        )
        employee.full_clean()

        employee.work_days_per_week = 8
        with self.assertRaises(ValidationError):
            employee.full_clean()

        employee.work_days_per_week = 7
        employee.weekly_target_hours = Decimal("40.01")
        with self.assertRaises(ValidationError):
            employee.full_clean()
