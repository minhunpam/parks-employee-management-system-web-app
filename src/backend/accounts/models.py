from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import UserManager

# Create your models here.
class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

