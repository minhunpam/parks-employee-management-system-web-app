from django.test import TestCase

from employees.models import (
    Employee,
    EmployeeMonth,
    EmployeeYear,
    annual_allowed_vacation_days,
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
        )

        self.assertEqual(employee.registered_work_days_per_week, employee.work_days_per_week)

        employee_year = EmployeeYear.objects.create(employee=employee, year=2026)
        employee_month = EmployeeMonth.objects.create(employee=employee, year=2026, month=1)

        self.assertEqual(employee_year.annual_allowed_vacation_days, 20)
        self.assertEqual(employee_year.vacation_balance, 20)
        self.assertEqual(employee_month.opening_vacation_balance, 20)

    def test_signed_balances_persist(self):
        employee = Employee.objects.create(
            first_name="Ada",
            last_name="Deficit",
            email="deficit@example.com",
            employment_start_date="2026-01-01",
            work_days_per_week=5,
        )
        employee_year = EmployeeYear.objects.create(
            employee=employee, year=2026, carried_over_vacation_days=-3,
            vacation_balance=-3,
        )
        employee_month = EmployeeMonth.objects.create(
            employee=employee, year=2026, month=1,
            opening_vacation_balance=-3, vacation_days_used=4,
        )

        self.assertEqual(EmployeeYear.objects.get(pk=employee_year.pk).vacation_balance, -3)
        self.assertEqual(EmployeeMonth.objects.get(pk=employee_month.pk).closing_vacation_balance, -7)
