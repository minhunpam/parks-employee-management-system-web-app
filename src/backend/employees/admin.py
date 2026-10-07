from django.contrib import admin

from .models import Employee, EmployeeMonth, EmployeeYear


@admin.register(EmployeeYear)
class EmployeeYearAdmin(admin.ModelAdmin):
    list_display = (
        "employee__email",
        "year",
        "annual_allowed_vacation_days",
        "carried_over_vacation_days",
        "vacation_balance",
    )
    list_filter = ("year",)
    search_fields = ("employee__first_name", "employee__last_name", "employee__email")


@admin.register(EmployeeMonth)
class EmployeeMonthAdmin(admin.ModelAdmin):
    list_display = (
        "employee__email",
        "year",
        "month",
        "opening_hour_account_balance",
        "closing_hour_account_balance",
        "opening_vacation_balance",
        "closing_vacation_balance",
    )
    list_filter = ("year", "month")
    search_fields = ("employee__first_name", "employee__last_name", "employee__email")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "email",
        "working_status",
        "employment_start_date",
        "employment_end_date",
        "created_at",
    )
    list_filter = ("working_status",)
    search_fields = ("first_name", "last_name", "email")
