from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from employees.models import (
    Employee,
    EmployeeMonth,
    determine_work_days_per_week,
)


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
            first_name="Ada",
            last_name="Historical",
            email="historical@example.com",
            employment_start_date=timezone.localdate(),
            work_days_per_week=5,
        )

        self.assertEqual(
            determine_work_days_per_week(employee, employee.created_at.year - 1, 12), 5
        )
        self.assertEqual(
            determine_work_days_per_week(employee, employee.created_at.year, employee.created_at.month), 5
        )

    def test_month_records_store_applicable_workday_policy(self):
        employee = Employee.objects.create(
            first_name="Ada",
            last_name="Snapshot",
            email="snapshot@example.com",
            employment_start_date=timezone.localdate(),
            work_days_per_week=5,
        )

        self.assertEqual(employee.registered_work_days_per_week, 5)

        historical = EmployeeMonth.objects.create(
            employee=employee, year=employee.created_at.year - 1, month=12,
        )

        current = EmployeeMonth.objects.create(
            employee=employee, year=employee.created_at.year,
            month=employee.created_at.month,
        )

        self.assertEqual(historical.work_days_per_week, 5)
        self.assertEqual(current.work_days_per_week, 5)

    def test_registered_baseline_can_change_until_historical_month_exists(self):
        employee = Employee.objects.create(
            owner=self.user,
            first_name="Ada",
            last_name="Editable",
            email="editable@example.com",
            employment_start_date=timezone.localdate(),
            work_days_per_week=4,
        )
        self.assertEqual(employee.registered_work_days_per_week, 4)

        payload = self.registration_payload()
        payload["work_days_per_week"] = "3"
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
        response = self.client.patch(
            reverse("employees:employee-details", args=[employee.pk]),
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        employee.refresh_from_db()
        self.assertEqual(employee.work_days_per_week, 2)
        self.assertEqual(employee.registered_work_days_per_week, 3)


    def test_update_returns_persisted_workday_values(self):
        employee = Employee.objects.create(
            owner=self.user,
            first_name="Ada", last_name="Response", email="response@example.com",
            employment_start_date=timezone.localdate(), work_days_per_week=4,
            registered_work_days_per_week=4,
        )
        EmployeeMonth.objects.create(
            employee=employee,
            year=timezone.localdate().year,
            month=timezone.localdate().month,
        )
        payload = self.registration_payload()
        payload.update({
            "email": employee.email,
            "work_days_per_week": "5",
        })

        response = self.client.patch(
            reverse("employees:employee-details", args=[employee.pk]),
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["employee"], {
            "work_days_per_week": 5,
            "registered_work_days_per_week": 5,
        })

    def test_invalid_update_returns_validation_error(self):
        employee = Employee.objects.create(
            owner=self.user,
            first_name="Ada", last_name="Invalid", email="invalid@example.com",
            employment_start_date=timezone.localdate(), work_days_per_week=4,
            registered_work_days_per_week=4,
        )
        payload = self.registration_payload()
        payload.update({
            "email": employee.email,
            "work_days_per_week": "8",
        })

        response = self.client.patch(
            reverse("employees:employee-details", args=[employee.pk]),
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("work_days_per_week", response.json()["error"])
