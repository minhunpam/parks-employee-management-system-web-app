from decimal import Decimal
from importlib import import_module

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import (
    Employee,
    EmployeeMonth,
    EmployeeYear,
    annual_allowed_vacation_days,
    monthly_hours_from_weekly,
    determine_work_days_per_week,
    recalculate_current_month,
)


class VacationEntitlementTests(TestCase):
    def test_entitlement_is_capped_at_twenty_five_days(self):
        self.assertEqual(
            [annual_allowed_vacation_days(days) for days in range(1, 8)],
            [5, 10, 15, 20, 25, 25, 25],
        )

    def test_new_year_and_month_use_employee_entitlement(self):
        employee = Employee.objects.create(
            first_name="Ada",
            last_name="Reduced",
            email="reduced@example.com",
            employment_start_date="2026-01-01",
            work_days_per_week=4,
            registered_work_days_per_week=4,
        )
        year = EmployeeYear.objects.create(employee=employee, year=2026)
        month = EmployeeMonth.objects.create(employee=employee, year=2026, month=1)
        self.assertEqual(year.annual_allowed_vacation_days, 20)
        self.assertEqual(year.vacation_balance, 20)
        self.assertEqual(month.opening_vacation_balance, 20)

    def test_signed_balances_persist(self):
        employee = Employee.objects.create(
            first_name="Ada",
            last_name="Deficit",
            email="deficit@example.com",
            employment_start_date="2026-01-01",
            work_days_per_week=5,
        )
        year = EmployeeYear.objects.create(
            employee=employee, year=2026, carried_over_vacation_days=-3,
            vacation_balance=-3,
        )
        month = EmployeeMonth.objects.create(
            employee=employee, year=2026, month=1,
            opening_vacation_balance=-3, vacation_days_used=4,
        )
        self.assertEqual(EmployeeYear.objects.get(pk=year.pk).vacation_balance, -3)
        self.assertEqual(EmployeeMonth.objects.get(pk=month.pk).closing_vacation_balance, -7)


class RegistrationBaselineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="manager@example.com", password="password"
        )
        self.client.force_login(self.user)

    def registration_payload(self, work_days=4):
        return {
            "first_name": "Ada",
            "last_name": "Registered",
            "email": "registered@example.com",
            "working_status": "active",
            "employment_start_date": timezone.localdate().isoformat(),
            "employment_end_date": "",
            "work_days_per_week": str(work_days),
            "weekly_target_hours": "40.00",
        }

    def test_registration_copies_workdays_to_current_and_registered_fields(self):
        response = self.client.post(
            reverse("employees:register"),
            data=self.registration_payload(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        employee = Employee.objects.get(email="registered@example.com")
        self.assertEqual(employee.work_days_per_week, 4)
        self.assertEqual(employee.registered_work_days_per_week, 4)

    def test_month_selection_uses_registered_baseline_before_registration(self):
        employee = Employee.objects.create(
            first_name="Ada", last_name="Historical", email="historical@example.com",
            employment_start_date=timezone.localdate(), work_days_per_week=5,
            registered_work_days_per_week=4,
        )
        self.assertEqual(
            determine_work_days_per_week(employee, employee.created_at.year - 1, 12), 4
        )
        self.assertEqual(
            determine_work_days_per_week(employee, employee.created_at.year, employee.created_at.month), 5
        )

    def test_registered_baseline_can_change_until_historical_month_exists(self):
        employee = Employee.objects.create(
            owner=self.user,
            first_name="Ada", last_name="Editable", email="editable@example.com",
            employment_start_date=timezone.localdate(), work_days_per_week=4,
            registered_work_days_per_week=4,
        )
        payload = self.registration_payload()
        payload.update({
            "email": employee.email,
            "work_days_per_week": "3",
            "registered_work_days_per_week": "3",
        })
        response = self.client.patch(
            reverse("employees:employee-details", args=[employee.pk]),
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        employee.refresh_from_db()
        self.assertEqual(employee.registered_work_days_per_week, 3)

        EmployeeMonth.objects.create(
            employee=employee,
            year=employee.created_at.year - 1,
            month=12,
        )
        payload["work_days_per_week"] = "2"
        payload["registered_work_days_per_week"] = "2"
        response = self.client.patch(
            reverse("employees:employee-details", args=[employee.pk]),
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        employee.refresh_from_db()
        self.assertEqual(employee.registered_work_days_per_week, 3)


class LegacyRepairMigrationTests(TestCase):
    def test_repair_is_capped_and_idempotent(self):
        employee = Employee.objects.create(
            first_name="Ada", last_name="Legacy", email="legacy@example.com",
            employment_start_date=timezone.localdate(), work_days_per_week=4,
        )
        year = EmployeeYear.objects.create(employee=employee, year=2026)
        year.__class__.objects.filter(pk=year.pk).update(
            annual_allowed_vacation_days=25, vacation_balance=25
        )
        month = EmployeeMonth.objects.create(
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
        year.refresh_from_db()
        month.refresh_from_db()
        first_result = (year.annual_allowed_vacation_days, year.vacation_balance, month.closing_vacation_balance)
        migration.repair_legacy_balances(apps, None)
        year.refresh_from_db()
        month.refresh_from_db()
        self.assertEqual(first_result, (year.annual_allowed_vacation_days, year.vacation_balance, month.closing_vacation_balance))
        self.assertEqual(first_result, (20, 17, 17))


class ScheduleRecalculationTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(
            first_name="Ada", last_name="Schedule", email="schedule@example.com",
            employment_start_date=timezone.localdate(), work_days_per_week=5,
            registered_work_days_per_week=5,
        )
        today = timezone.localdate()
        self.year = EmployeeYear.objects.create(employee=self.employee, year=today.year)
        self.previous = EmployeeMonth.objects.create(
            employee=self.employee, year=today.year, month=max(today.month - 1, 1),
            opening_vacation_balance=25, vacation_days_used=2,
        )
        self.current = EmployeeMonth.objects.create(
            employee=self.employee, year=today.year, month=today.month,
            opening_vacation_balance=self.previous.closing_vacation_balance,
            vacation_days_used=1,
        )
        self.future = EmployeeMonth.objects.create(
            employee=self.employee, year=today.year, month=today.month % 12 + 1,
            opening_vacation_balance=self.current.closing_vacation_balance,
            vacation_days_used=1,
        )
        self.next_year = EmployeeMonth.objects.create(
            employee=self.employee, year=today.year + 1, month=1,
            opening_vacation_balance=self.future.closing_vacation_balance,
            vacation_days_used=1,
        )

    def test_schedule_change_recalculates_current_and_future_only(self):
        previous_closing = self.previous.closing_vacation_balance
        self.employee.work_days_per_week = 4
        self.employee.save(update_fields=["work_days_per_week"])
        recalculate_current_month(self.employee)
        self.year.refresh_from_db()
        self.previous.refresh_from_db()
        self.current.refresh_from_db()
        self.future.refresh_from_db()
        self.assertEqual(previous_closing, self.previous.closing_vacation_balance)
        self.assertEqual(self.current.opening_vacation_balance, previous_closing)
        self.assertEqual(self.current.closing_vacation_balance, previous_closing - 1)
        self.assertEqual(self.future.opening_vacation_balance, self.current.closing_vacation_balance)
        self.assertEqual(self.year.annual_allowed_vacation_days, 20)

    def test_negative_balance_carries_into_the_next_year(self):
        self.previous.opening_vacation_balance = -3
        self.previous.vacation_days_used = 0
        self.previous.save()
        self.current.opening_vacation_balance = -3
        self.current.vacation_days_used = 4
        self.current.save()
        self.employee.work_days_per_week = 4
        self.employee.save(update_fields=["work_days_per_week"])
        recalculate_current_month(self.employee)
        self.next_year.refresh_from_db()
        next_year = EmployeeYear.objects.get(employee=self.employee, year=self.next_year.year)
        self.assertLess(next_year.carried_over_vacation_days, 0)
        self.assertEqual(
            self.next_year.opening_vacation_balance,
            next_year.annual_allowed_vacation_days + next_year.carried_over_vacation_days,
        )

    def test_repeated_schedule_changes_use_latest_value(self):
        self.employee.work_days_per_week = 4
        self.employee.save(update_fields=["work_days_per_week"])
        recalculate_current_month(self.employee)
        self.employee.work_days_per_week = 6
        self.employee.save(update_fields=["work_days_per_week"])
        recalculate_current_month(self.employee)
        self.year.refresh_from_db()
        self.assertEqual(self.year.annual_allowed_vacation_days, 25)
        self.assertEqual(self.employee.employee_months.count(), 4)


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

        '''
        This with-block asserts that `employee.full_clean()` must raise a ValidationError
        - If validation raises the expected error, the test passes
        - Otherwise, test fails
        '''
        employee.work_days_per_week = 8
        with self.assertRaises(ValidationError):
            employee.full_clean()

        employee.work_days_per_week = 7
        employee.weekly_target_hours = Decimal("50.01")
        with self.assertRaises(ValidationError):
            employee.full_clean()

        employee.weekly_target_hours = Decimal("0.99")
        with self.assertRaises(ValidationError):
            employee.full_clean()
