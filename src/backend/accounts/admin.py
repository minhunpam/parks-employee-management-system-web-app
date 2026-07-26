from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

# Register your models here.
@admin.register(User) # Register User model in Django Admin using this UserAdmin configuration
class UserAdmin(BaseUserAdmin):
    ordering = ("email",) # Users are sorted by email in ascending order
    list_display = (
        "email",
        "is_active",
        "is_staff",
        "is_superuser",
    ) # This controls which columns appear in the user overview table
    search_fields = ("email",) # Adds a search box that searches the `email` field

    '''
    - This defines the form layout when an admin opens an existing user
    - Each field set has the form:
    (
        "Section tilte",
        {
            "fields": (...)
        }
    )
    '''
    fieldsets = (
        (
            None, 
            {
                "fields": ("email", "password")
            }
        ),
        (
            "Personal Information",
            {
                "fields": ("first_name", "last_name")
            }
        ),
        (
            "Permissions",
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")
            }
        ),
        (
            "Important Dates",
            {
                "fields": ("last_login", "date_joined")
            }
        )
    )

    '''
    Creating a new user
    - This controls the form shown when an administrator clicks
    '''
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",), 
                # Applies Django Admin's `wide` CSS class to the fieldset
                # It mainly effects the form layout and presentation
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )

