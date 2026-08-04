from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


# Create your models here.
class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    objects = UserManager()

    # A string describing the name of the field on the user model 
    # that is used as the unique identifier
    USERNAME_FIELD = "email"

    # A list of field names that are prompted when creating a user
    # via `createsuperuser` management command
    REQUIRED_FIELDS = []

class GoogleConnection(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="google_connection",
    )
    subject = models.CharField(
        max_length=255,
        unique=True,
    )
    granted_scopes = models.JSONField(default=list)
    encrypted_refresh_token = models.TextField(blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
