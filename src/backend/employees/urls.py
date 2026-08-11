from django.urls import path

from .views import (
    employee_dashboard,
    employee_register,
    register,
)

app_name = "employees"

urlpatterns = [
    path("dashboard/", employee_dashboard, name="employee-dashboard",),
    path("employee-register/", employee_register, name="employee-register",),
    path("register/", register, name="register",),
]