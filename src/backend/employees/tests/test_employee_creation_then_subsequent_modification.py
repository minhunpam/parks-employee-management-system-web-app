from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from employees.models import (
    Employee,
    EmployeeMonth,
    EmployeeYear,
)

class EmployeeCreationThenSubsequentModificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="manager@example.com",
            password="password"
        )
        self.client.force_login(self.user)

    def registration_payload(self, work_days=2):
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

    def test_employee_creation_then_subsequent_modification(self):
        response = self.client.post(
            reverse("employees:register"),
            data=self.registration_payload(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        employee = Employee.objects.get(email="registered@example.com")
        self.assertEqual(employee.work_days_per_week, 2)
        self.assertEqual(employee.registered_work_days_per_week, 2)

        employee_month = EmployeeMonth.objects.get(
            employee=employee,
            year=employee.created_at.year,
            month=employee.created_at.month,
        )
        self.assertIsNotNone(employee_month)
        self.assertEqual(employee_month.opening_vacation_balance, 10)
        self.assertEqual(employee_month.closing_vacation_balance, 10)

        employee_year = EmployeeYear.objects.get(
            employee=employee,
            year=employee.created_at.year,
        )
        self.assertIsNotNone(employee_year)
        self.assertEqual(employee_year.annual_allowed_vacation_days, 10)
        self.assertEqual(employee_year.vacation_balance, 10)

        # The modification starts here
        payload = self.registration_payload()
        payload["work_days_per_week"] = "3"
        response = self.client.patch(
            reverse("employees:employee-details", args=[employee.pk]),
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        employee.refresh_from_db()
        employee_month.refresh_from_db()
        employee_year.refresh_from_db()

        self.assertEqual(employee_month.opening_vacation_balance, 15)
        self.assertEqual(employee_month.closing_vacation_balance, 15)

        self.assertEqual(employee_year.annual_allowed_vacation_days, 15)
        self.assertEqual(employee_year.vacation_balance, 15)

        # Import a new month
        june = EmployeeMonth.objects.create(
            employee=employee,
            year=employee.created_at.year,
            month=6
        )
        self.assertEqual(june.opening_vacation_balance, 15)
        self.assertEqual(june.closing_vacation_balance, 15)

        # Modify `work_days_per_week` of the employee; however, since there exists a previos month
        # `registered_work_days_per_work` is locked now
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

        # the current month record should be recalculated now
        employee_month.refresh_from_db()
        self.assertEqual(employee_month.opening_vacation_balance, 10)
        self.assertEqual(employee_month.closing_vacation_balance, 10)
