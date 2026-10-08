from decimal import Decimal
from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone


from employees.models import (
    Employee,
    EmployeeMonth,
    EmployeeYear,
    annual_allowed_vacation_days,
    recalculate_current_month,
    schedule_change_balance,
    persist_vacation_balance,
)


class ScheduleRecalculationTests(TestCase):
    def test_schedule_change_after_ten_months_reaches_twenty_five_days(self):
        employee = Employee.objects.create(
            first_name="Ada",
            last_name="Ten Months",
            email="ten-months@example.com",
            employment_start_date=date(2026, 1, 1),
            work_days_per_week=4,
        )

        EmployeeYear.objects.create(employee=employee, year=2026)
        for month in range(1, 13):
            EmployeeMonth.objects.create(
                employee=employee, year=2026, month=month,
                work_days_per_week=4,
            )

        employee.work_days_per_week = 5
        employee.save(update_fields=["work_days_per_week"])
        with patch("employees.models.timezone.localdate", return_value=date(2026, 11, 1)):
            recalculate_current_month(employee)

        december = EmployeeMonth.objects.get(employee=employee, year=2026, month=12)
        self.assertEqual(december.closing_vacation_balance, 25)

    def test_schedule_change_usage_example_rounds_to_twenty_three_days(self):
        employee = Employee.objects.create(
            first_name="Ada", last_name="Usage", email="usage-example@example.com",
            employment_start_date=date(2026, 1, 1), work_days_per_week=4,
            registered_work_days_per_week=4,
        )
        EmployeeYear.objects.create(employee=employee, year=2026)
        for month in range(1, 13):
            EmployeeMonth.objects.create(
                employee=employee, year=2026, month=month,
                work_days_per_week=4,
                vacation_days_used=2 if month == 1 else 0,
            )
        employee.work_days_per_week = 5
        employee.save(update_fields=["work_days_per_week"])
        with patch("employees.models.timezone.localdate", return_value=date(2026, 11, 1)):
            recalculate_current_month(employee)
        december = EmployeeMonth.objects.get(employee=employee, year=2026, month=12)
        self.assertEqual(december.closing_vacation_balance, 23)

    def test_ten_month_conversion_examples(self):
        self.assertAlmostEqual(
            schedule_change_balance(4, 5, 10, 0), Decimal("20.8333333333"), places=5
        )
        self.assertEqual(
            schedule_change_balance(4, 5, 10, 2), Decimal("18.75")
        )
        self.assertEqual(persist_vacation_balance(Decimal("22.9166666667")), 23)


    def setUp(self):
        self.employee = Employee.objects.create(
            first_name="Ada",
            last_name="Schedule",
            email="schedule@example.com",
            employment_start_date=timezone.localdate(),
            work_days_per_week=5,
        )
        today = timezone.localdate()

        self.employee_year = EmployeeYear.objects.create(
            employee=self.employee,
            year=today.year
        )

        self.previous_employee_month = EmployeeMonth.objects.create(
            employee=self.employee, year=today.year, month=max(today.month - 1, 1),
            opening_vacation_balance=25,
            vacation_days_used=2,
        )

        self.current_employee_month = EmployeeMonth.objects.create(
            employee=self.employee,
            year=today.year,
            month=today.month,
            opening_vacation_balance=self.previous_employee_month.closing_vacation_balance,
            vacation_days_used=1,
        )
        self.future_employee_month = EmployeeMonth.objects.create(
            employee=self.employee, year=today.year, month=today.month % 12 + 1,
            opening_vacation_balance=self.current_employee_month.closing_vacation_balance,
            vacation_days_used=1,
        )
        self.next_year = EmployeeMonth.objects.create(
            employee=self.employee, year=today.year + 1, month=1,
            opening_vacation_balance=self.future_employee_month.closing_vacation_balance,
            vacation_days_used=1,
        )

    def test_schedule_change_recalculates_current_and_future_only(self):
        previous_closing = self.previous_employee_month.closing_vacation_balance
        self.employee.work_days_per_week = 4
        self.employee.save(update_fields=["work_days_per_week"])
        recalculate_current_month(self.employee)

        self.employee_year.refresh_from_db()
        self.previous_employee_month.refresh_from_db()
        self.current_employee_month.refresh_from_db()
        self.future_employee_month.refresh_from_db()

        self.assertEqual(previous_closing, self.previous_employee_month.closing_vacation_balance)
        converted = schedule_change_balance(5, 4, timezone.localdate().month - 1, 2)
        print(f"converted: {converted}")
        remaining_months = Decimal(annual_allowed_vacation_days(4)) * Decimal(12 - timezone.localdate().month + 1) / Decimal("12.0")
        print(f"remaining_months: {remaining_months}")

        expected_opening = persist_vacation_balance(
            converted + remaining_months
        )
        print(expected_opening)
        self.assertEqual(self.current_employee_month.opening_vacation_balance, expected_opening)
        self.assertEqual(
            self.future_employee_month.opening_vacation_balance,
            self.current_employee_month.closing_vacation_balance,
        )
        self.assertEqual(self.employee_year.annual_allowed_vacation_days, 20)

    def test_schedule_change_handles_missing_previous_month(self):
        employee = Employee.objects.create(
            first_name="Ada",
            last_name="Missing",
            email="missing-month@example.com",
            employment_start_date=date(2026, 1, 1),
            work_days_per_week=4,
            registered_work_days_per_week=4,
        )
        EmployeeYear.objects.create(employee=employee, year=2026)
        EmployeeMonth.objects.create(
            employee=employee, year=2026, month=11, work_days_per_week=4,
        )
        employee.work_days_per_week = 5
        employee.save(update_fields=["work_days_per_week"])

        with patch("employees.models.timezone.localdate", return_value=date(2026, 11, 1)):
            recalculate_current_month(employee)
        month = EmployeeMonth.objects.get(employee=employee, year=2026, month=11)
        self.assertEqual(month.opening_vacation_balance, 25)
        self.assertEqual(month.closing_vacation_balance, 25)

    def test_negative_balance_carries_into_the_next_year(self):
        self.previous_employee_month.opening_vacation_balance = 0
        self.previous_employee_month.vacation_days_used = 30
        self.previous_employee_month.save()
        self.current_employee_month.opening_vacation_balance = 0
        self.current_employee_month.vacation_days_used = 4
        self.current_employee_month.save()
        self.employee.work_days_per_week = 4
        self.employee.save(update_fields=["work_days_per_week"])
        recalculate_current_month(self.employee)
        self.next_year.refresh_from_db()
        next_year = EmployeeYear.objects.get(employee=self.employee, year=self.next_year.year)
        self.assertLess(next_year.carried_over_vacation_days, 0)
        self.assertEqual(
            self.next_year.opening_vacation_balance,
            next_year.carried_over_vacation_days,
        )

    def test_repeated_schedule_changes_use_latest_value(self):
        self.employee.work_days_per_week = 4
        self.employee.save(update_fields=["work_days_per_week"])
        recalculate_current_month(self.employee)
        self.employee.work_days_per_week = 6
        self.employee.save(update_fields=["work_days_per_week"])
        recalculate_current_month(self.employee)
        self.employee_year.refresh_from_db()
        self.assertEqual(self.employee_year.annual_allowed_vacation_days, 25)
        self.assertEqual(self.employee.employee_months.count(), 4)
