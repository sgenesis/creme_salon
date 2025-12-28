from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    USER_ROLES = (
        ('client', 'Cliente'),
        ('employee', 'Manicurista'),
        ('admin', 'Administrador'),
    )

    role = models.CharField(max_length=20, choices=USER_ROLES, default='client')
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    
    # 🔹 Campos de promociones
    total_services = models.PositiveIntegerField(default=0)      # Total de servicios realizados
    has_free_service = models.BooleanField(default=False)        # Si tiene un servicio gratis pendiente
    services_for_promo = models.PositiveIntegerField(default=10) # Cuántos servicios necesita para promoción
    promo_system_active = models.BooleanField(default=True)      # Si aplica promociones para este usuario

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


