from importlib import import_module

from django.test import TestCase
from django.utils import timezone

from employees.models import (
    Employee,
    EmployeeMonth,
    EmployeeYear,
)


class LegacyRepairMigrationTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(
            first_name="Ada",
            last_name="Legacy",
            email="legacy@example.com",
            employment_start_date=timezone.localdate(),
            work_days_per_week=4,
        )

        # work_days_per_week = 4, annual_allowed_vacation-days = 25


    def test_repair_is_capped_and_idempotent(self):
        employee_year = EmployeeYear.objects.create(employee=self.employee, year=2026)
        EmployeeYear.objects.filter(pk=employee_year.pk).update(
            annual_allowed_vacation_days=25, vacation_balance=25
        )

        jan_2026 = EmployeeMonth.objects.create(
            employee=self.employee, year=2026, month=1, vacation_days_used=3
        )
        feb_2026 = EmployeeMonth.objects.create(
            employee=self.employee, year=2026, month=2, vacation_days_used=2
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
        jan_2026.refresh_from_db()
        feb_2026.refresh_from_db()

        first_result = (
            employee_year.annual_allowed_vacation_days,
            employee_year.vacation_balance,
            jan_2026.opening_vacation_balance,
            jan_2026.closing_vacation_balance,
            feb_2026.opening_vacation_balance,
            feb_2026.closing_vacation_balance,
        )

        migration.repair_legacy_balances(apps, None)
        employee_year.refresh_from_db()
        jan_2026.refresh_from_db()
        feb_2026.refresh_from_db()

        second_result = (
            employee_year.annual_allowed_vacation_days,
            employee_year.vacation_balance,
            jan_2026.opening_vacation_balance,
            jan_2026.closing_vacation_balance,
            feb_2026.opening_vacation_balance,
            feb_2026.closing_vacation_balance,
        )

        self.assertEqual(first_result, (20, 15, 20, 17, 17, 15))
        self.assertEqual(second_result, first_result)
