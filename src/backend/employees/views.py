import json
from decimal import Decimal, InvalidOperation
from datetime import date

# Django modules
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods

# Local modules
from .models import (
    Employee,
    EmployeeMonth,
    EmployeeYear,
    monthly_hours_from_weekly,
    recalculate_current_month,
)

@login_required
def employee_dashboard(request):
    return render(request, "employees/employee-dashboard.html")

@login_required
@require_GET
def employee_dashboard_data(request):
    tab = request.GET.get("tab", "employees")
    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "")
    year = request.GET.get("year", "")
    month = request.GET.get("month", "")
    sort = request.GET.get("sort", "default")
    direction = "-" if request.GET.get("direction") == "desc" else ""

    try:
        page = max(int(request.GET.get("page", 1)), 1)
        page_size = min(max(int(request.GET.get("page_size", 25)), 1), 100)
    except ValueError:
        return JsonResponse({"error": "Invalid pagination values."}, status=400)

    if tab == "employees":
        queryset = Employee.objects.filter(owner=request.user)
        if search:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search)
                | models.Q(last_name__icontains=search)
                | models.Q(email__icontains=search)
            )
        if status:
            queryset = queryset.filter(working_status=status)

        total = queryset.count()
        active = queryset.filter(working_status=Employee.WorkingStatus.ACTIVE).count()
        archived = queryset.filter(working_status=Employee.WorkingStatus.ARCHIVED).count()
        employee_sort_fields = {
            "first_name": "first_name",
            "last_name": "last_name",
            "email": "email",
            "working_status": "working_status",
            "employment_start_date": "employment_start_date"
        }
        ordering = direction + employee_sort_fields.get(sort, "last_name")
        rows = list(queryset.order_by(ordering, "first_name")[((page - 1) * page_size):(page * page_size)])

        return JsonResponse({
            "tab": tab,
            "rows": [{
                "id": employee.id,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "email": employee.email,
                "working_status": employee.get_working_status_display(),
                "work_days_per_week": employee.work_days_per_week,
                "employment_start_date": employee.employment_start_date.isoformat(),
                "employment_end_date": employee.employment_end_date.isoformat() if employee.employment_end_date else "—",
            } for employee in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "summary": {"total": total, "active": active, "archived": archived},
        })

    if tab == "monthly":
        queryset = EmployeeMonth.objects.select_related("employee").filter(employee__owner=request.user)
        if search:
            queryset = queryset.filter(
                models.Q(employee__first_name__icontains=search)
                | models.Q(employee__last_name__icontains=search)
                | models.Q(employee__email__icontains=search)
            )
        if year:
            queryset = queryset.filter(year=year)
        if month:
            queryset = queryset.filter(month=month)

        total = queryset.count()
        summary_queryset = queryset
        monthly_sort_fields = {
            "employee": "employee__last_name",
            "year": "year",
            "month": "month",
            "opening_hour_account_balance": "opening_hour_account_balance",
            "closing_hour_account_balance": "closing_hour_account_balance",
            "opening_vacation_balance": "opening_vacation_balance",
            "closing_vacation_balance": "closing_vacation_balance",
        }
        ordering = direction + monthly_sort_fields.get(sort, "year")
        rows = list(queryset.order_by(ordering, "-month", "employee__last_name")[((page - 1) * page_size):(page * page_size)])

        return JsonResponse({
            "tab": tab,
            "rows": [{
                "id": record.id,
                "employee": f"{record.employee.first_name} {record.employee.last_name}",
                "year": record.year,
                "month": record.month,
                "opening_hour_account_balance": str(record.opening_hour_account_balance),
                "closing_hour_account_balance": str(record.closing_hour_account_balance),
                "opening_vacation_balance": record.opening_vacation_balance,
                "closing_vacation_balance": record.closing_vacation_balance,
                "work_days_per_week": record.work_days_per_week,
            } for record in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "summary": {
                "records": total,
                "closing_hours": str(sum((record.closing_hour_account_balance for record in summary_queryset), Decimal("0"))),
                "vacation_used": sum(record.vacation_days_used for record in summary_queryset),
            },
        })

    if tab == "yearly":
        queryset = EmployeeYear.objects.select_related("employee").filter(employee__owner=request.user)
        if search:
            queryset = queryset.filter(
                models.Q(employee__first_name__icontains=search)
                | models.Q(employee__last_name__icontains=search)
                | models.Q(employee__email__icontains=search)
            )
        if year:
            queryset = queryset.filter(year=year)

        total = queryset.count()
        yearly_sort_fields = {
            "employee": "employee__last_name",
            "year": "year",
            "annual_allowed_vacation_days": "annual_allowed_vacation_days",
            "carried_over_vacation_days": "carried_over_vacation_days",
            "vacation_balance": "vacation_balance"
        }
        ordering = direction + yearly_sort_fields.get(sort, "year")
        rows = list(queryset.order_by(ordering, "employee__last_name")[((page - 1) * page_size):(page * page_size)])

        return JsonResponse({
            "tab": tab,
            "rows": [{
                "id": record.id,
                "employee": f"{record.employee.first_name} {record.employee.last_name}",
                "year": record.year,
                "annual_allowed_vacation_days": record.annual_allowed_vacation_days,
                "carried_over_vacation_days": record.carried_over_vacation_days,
                "vacation_balance": record.vacation_balance,
            } for record in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "summary": {
                "records": total,
                "entitlement": sum(record.annual_allowed_vacation_days + record.carried_over_vacation_days for record in queryset),
                "balance": sum(record.vacation_balance for record in queryset),
            },
        })

    return JsonResponse({"error": "Unknown dashboard tab."}, status=400)


@login_required
def employee_register(request):
    return render(request, "employees/employee-registration.html")

@login_required
@require_POST
def register(request):

    try:
        payload = json.loads(request.body)

        registered_employee = Employee(
            owner=request.user,
            first_name=payload["first_name"],
            last_name=payload["last_name"],
            email=payload["email"],
            working_status=payload["working_status"],
            employment_start_date=date.fromisoformat(payload["employment_start_date"]),
            employment_end_date=date.fromisoformat(payload["employment_end_date"]) if payload["employment_end_date"] else None,
            work_days_per_week=int(payload["work_days_per_week"]),
            registered_work_days_per_week=int(payload["work_days_per_week"]),
            weekly_target_hours=Decimal(payload["weekly_target_hours"]),
        )
        registered_employee.monthly_target_hours = monthly_hours_from_weekly(
            registered_employee.weekly_target_hours
        )
        registered_employee.full_clean()
    except (KeyError, TypeError, ValueError, InvalidOperation, ValidationError) as error:
        details = error.message_dict if isinstance(error, ValidationError) else {"form": ["Please provide valid employee details."]}
        return JsonResponse({"error": details}, status=400)

    registered_employee.save()

    EmployeeYear.objects.create(
        employee=registered_employee,
        year=registered_employee.created_at.year,
    )

    EmployeeMonth.objects.create(
        employee=registered_employee,
        year=registered_employee.created_at.year,
        month=registered_employee.created_at.month,
    )


    return JsonResponse(
        {
            "message": "Employee registered successfully",
        },
        status=200
    )

@login_required
@require_http_methods(["GET", "PATCH"])
def employee_details(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id, owner=request.user)
    has_pre_registration_month = _has_pre_registration_month(employee, employee.created_at)

    if request.method == "PATCH":
        try:
            payload = json.loads(request.body)

            if payload.get("action") == "archive":
                employee.working_status = Employee.WorkingStatus.ARCHIVED
                employee.employment_end_date = date.today()
            else:
                previous_work_days = employee.work_days_per_week
                previous_weekly_hours = employee.weekly_target_hours
                employee.first_name = payload["first_name"]
                employee.last_name = payload["last_name"]
                employee.email = payload["email"]
                employee.working_status = payload["working_status"]
                employee.employment_start_date = date.fromisoformat(
                    payload["employment_start_date"]
                )
                employee.employment_end_date = (
                    date.fromisoformat(payload["employment_end_date"])
                    if payload.get("employment_end_date") else None
                )

                new_work_days_per_week = int(payload["work_days_per_week"])

                if not has_pre_registration_month and new_work_days_per_week != employee.registered_work_days_per_week:
                    employee.registered_work_days_per_week = new_work_days_per_week

                employee.work_days_per_week = new_work_days_per_week
                employee.weekly_target_hours = Decimal(payload["weekly_target_hours"])
                employee.monthly_target_hours = monthly_hours_from_weekly(
                    employee.weekly_target_hours
                )

            employee.full_clean()
            employee.save()

            if (
                payload.get("action") != "archive"
                and (
                    previous_work_days != employee.work_days_per_week
                    or previous_weekly_hours != employee.weekly_target_hours
                )
            ):
                recalculate_current_month(employee)

        except (KeyError, TypeError, ValueError, InvalidOperation, ValidationError) as error:
            details = error.message_dict if isinstance(error, ValidationError) else {"form": ["Please provide valid employee details."]}

            return JsonResponse({"error": details}, status=400)

        message = (
            "Employee archived successfully."
            if payload.get("action") == "archive"
            else "Employee details updated successfully."
        )

        return JsonResponse({
            "message": message,
            "employee": {
                "work_days_per_week": employee.work_days_per_week,
                "registered_work_days_per_week": employee.registered_work_days_per_week,
            },
        })

    return render(
        request,
        "employees/employee-details.html",
        {
            "employee": employee,
        },
    )

def _has_pre_registration_month(employee, registration_datetime):
    return (
        EmployeeMonth.objects
        .filter(employee=employee)
        .filter(
            models.Q(year__lt=registration_datetime.year)
            | models.Q(year=registration_datetime.year, month__lt=registration_datetime.month)
        ).exists()
    )
