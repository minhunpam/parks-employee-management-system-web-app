from django.urls import path

from .views import (
    employee_dashboard,
    register_employee,
)

app_name = "employees"

urlpatterns = [
    path("dashboard/", employee_dashboard, name="employee-dashboard",),
    path("register-employee/", register_employee, name="register-employee",),
]