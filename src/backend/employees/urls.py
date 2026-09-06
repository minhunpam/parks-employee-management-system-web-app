from django.urls import path

from .views import (
    employee_dashboard,
    employee_dashboard_data,
    employee_register,
    register,
    employee_details,
)

app_name = "employees"

urlpatterns = [
    path("employee-dashboard/", employee_dashboard, name="employee-dashboard",),
    path("employee-dashboard/data/", employee_dashboard_data, name="employee-dashboard-data",),
    path("employee-dashboard/<int:employee_id>", employee_details, name="employee-details"),
    path("employee-register/", employee_register, name="employee-register",),
    path("register/", register, name="register",),
]
