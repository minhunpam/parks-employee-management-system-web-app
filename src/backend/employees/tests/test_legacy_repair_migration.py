from importlib import import_module

from django.test import TestCase
from django.utils import timezone

from employees.models import (
    Employee,
    EmployeeMonth,
    EmployeeYear,
)


class LegacyRepairMigrationTests(TestCase):
    def test_repair_is_capped_and_idempotent(self):
        employee = Employee.objects.create(
            first_name="Ada",
            last_name="Legacy",
            email="legacy@example.com",
            employment_start_date=timezone.localdate(),
            work_days_per_week=4,
        )

        employee_year = EmployeeYear.objects.create(employee=employee, year=2026)
        employee_year.__class__.objects.filter(pk=employee_year.pk).update(
            annual_allowed_vacation_days=25, vacation_balance=25
        )

        employee_month = EmployeeMonth.objects.create(
            employee=employee, year=2026, month=1, vacation_days_used=3
        )
        migration = import_module(
            "employees.migrations.0015_repair_legacy_vacation_balances"
        )
        apps = type("Apps", (), {
            "get_model": staticmethod(lambda app, model: {
                "Employee": Employee,
                "EmployeeYear": EmployeeYear,
                "EmployeeMonth": EmployeeMonth,
            }[model])
        })()

        migration.repair_legacy_balances(apps, None)
        employee_year.refresh_from_db()
        employee_month.refresh_from_db()

        first_result = (
            employee_year.annual_allowed_vacation_days,
            employee_year.vacation_balance,
            employee_month.closing_vacation_balance
        )

        migration.repair_legacy_balances(apps, None)
        employee_year.refresh_from_db()
        employee_month.refresh_from_db()

        self.assertEqual(first_result, (
            employee_year.annual_allowed_vacation_days,
            employee_year.vacation_balance,
            employee_month.closing_vacation_balance
        ))
        self.assertEqual(first_result, (20, 17, 17))
