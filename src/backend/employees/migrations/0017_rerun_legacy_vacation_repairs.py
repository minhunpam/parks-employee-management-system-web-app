from django.db import migrations


def repair_legacy_balances(apps, schema_editor):
    Employee = apps.get_model("employees", "Employee")
    EmployeeYear = apps.get_model("employees", "EmployeeYear")
    EmployeeMonth = apps.get_model("employees", "EmployeeMonth")

    for employee in Employee.objects.all().iterator():
        entitlement_work_days_per_week = min(employee.work_days_per_week * 5, 25)
        years = list(EmployeeYear.objects.filter(employee=employee).order_by("year"))

        for year in years:
            if (
                year.annual_allowed_vacation_days == 25
                and entitlement_work_days_per_week < 25
            ):
                year.annual_allowed_vacation_days = entitlement_work_days_per_week
                year.save(update_fields=["annual_allowed_vacation_days"])

        vacation_balance = None
        employee_month_records = EmployeeMonth.objects.filter(employee=employee).order_by("year", "month")
        previous_year = None

        for employee_month_record in employee_month_records:

            year = next((record for record in years if record.year == employee_month_record.year), None)
            if year is None:
                year, _ = EmployeeYear.objects.get_or_create(
                    employee=employee,
                    year=employee_month_record.year,
                    defaults={"annual_allowed_vacation_days": entitlement_work_days_per_week},
                )
                years.append(year)

            if vacation_balance is None or employee_month_record.year != previous_year:
                vacation_balance = year.annual_allowed_vacation_days + year.carried_over_vacation_days

            employee_month_record.opening_vacation_balance = vacation_balance
            employee_month_record.closing_vacation_balance = vacation_balance - employee_month_record.vacation_days_used
            employee_month_record.save(
                update_fields=[
                    "opening_vacation_balance",
                    "closing_vacation_balance"
                ]
            )
            vacation_balance = employee_month_record.closing_vacation_balance
            previous_year = employee_month_record.year

        for year in years:
            vacation_days_used = sum(
                month.vacation_days_used
                for month in EmployeeMonth.objects.filter(employee=employee, year=year.year)
            )
            year.vacation_balance = (
                year.annual_allowed_vacation_days
                + year.carried_over_vacation_days
                - vacation_days_used
            )
            year.save(update_fields=["vacation_balance"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0016_employeemonth_work_days_per_week"),
    ]

    operations = [
        migrations.RunPython(repair_legacy_balances, noop),
    ]
