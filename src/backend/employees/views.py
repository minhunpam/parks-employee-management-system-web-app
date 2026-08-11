import json
from datetime import date

# Django modules
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

# Local modules
from .models import Employee

@login_required
def employee_dashboard(request):
    return render(request, "employees/employee-dashboard.html")

@login_required
def employee_register(request):
    return render(request, "employees/employee-registration.html")

@login_required
@require_POST
def register(request):

    try:
        payload = json.loads(request.body)
        # print(f"payload: {payload}")
        # print(type(payload["employment_start_date"]))
    
        registered_employee = Employee(
            first_name=payload["first_name"],
            last_name=payload["last_name"],
            email=payload["email"],
            working_status=payload["working_status"],
            employment_start_date=date.fromisoformat(payload["employment_start_date"]),
            employment_end_date=date.fromisoformat(payload["employment_end_date"]) if payload["employment_end_date"] else None,
            work_days_per_week=int(payload["work_days_per_week"]),
            monthly_target_hours=float(payload["monthly_target_hours"]),
        )
        registered_employee.full_clean()
    except (ValidationError) as error:
        return JsonResponse({"error": error.message_dict}, status=400)

    registered_employee.save()    
    return JsonResponse(
        {
            "message": "Employee registered successfully",
        },
        status=200
    )

    