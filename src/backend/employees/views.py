
# Django modules
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse


@login_required
def employee_dashboard(request):
    return render(request, "employees/employee-dashboard.html")

@login_required
@require_POST
def register_employee(request):
    print("Hello world!")

    return JsonResponse(
        {
            "message": "Employee registered successfully",
        },
        status=200
    )