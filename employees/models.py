import uuid
from django.db import models
from django.conf import settings
from users.models import CustomUser

class EmployeeProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employee_profile')
    bio = models.TextField(blank=True, null=True)
    available = models.BooleanField(default=True)
    specialties = models.CharField(max_length=255, help_text="Ej: Uñas acrílicas, Gelish, Decorado, etc.")
    working_days = models.CharField(max_length=100, help_text="Ej: Lunes a Sábado")
    start_time = models.TimeField(default='10:00')
    end_time = models.TimeField(default='18:00')

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({'Disponible' if self.available else 'No disponible'})"
