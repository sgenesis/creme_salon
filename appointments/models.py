import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from employees.models import EmployeeProfile
from django.utils import timezone
import unicodedata
from users.models import CustomUser
from decimal import Decimal

class Service(models.Model):
    CATEGORY_CHOICES = [
        ("manos", "Manos"),
        ("pies", "Pies"),
    ]

    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    duration_hours = models.DecimalField(max_digits=4, decimal_places=1, default=1.0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.category})"


class Appointment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = (
        ('pending_payment', 'Pendiente de pago'),
        ('scheduled', 'Agendada'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
        ("expired", "Expirada"),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending_payment"
    )

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments')
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name='appointments')
    #service = models.ForeignKey(Service, on_delete=models.CASCADE)
    service_manos = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, related_name="citas_manos")
    service_pies = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, related_name="citas_pies")
    

    date = models.DateField()
    time = models.TimeField()

    duration_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True, null=True)
    total_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    # 💳 Campos de pago
    requires_deposit = models.BooleanField(default=True)
    deposit_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    deposit_paid = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client} con {self.employee} el {self.date} a las {self.time}"
    
    def clean(self):
        employee = self.employee
        appointment_time = self.time

        # 1️⃣ Verificar si la manicurista está disponible
        if not employee.available:
            raise ValidationError("La manicurista no está disponible actualmente.")

        # 2️⃣ Verificar horario laboral
        if appointment_time < employee.start_time or appointment_time >= employee.end_time:
            raise ValidationError("La cita está fuera del horario laboral de la manicurista.")

        # 3️⃣ Verificar día laboral
        # Convertir el día de la cita al nombre del día en español
        weekday = self.date.strftime("%A").lower()  # ejemplo: "thursday"
        traduccion_dias = {
            "monday": "lunes",
            "tuesday": "martes",
            "wednesday": "miércoles",
            "thursday": "jueves",
            "friday": "viernes",
            "saturday": "sábado",
            "sunday": "domingo",
        }
        weekday = traduccion_dias.get(weekday, weekday)

        # --- 🔤 Normalización de texto (quita acentos y pasa a minúsculas) ---
        def normalize(text):
            if not text:
                return ""
            text = text.lower()
            text = ''.join(
                c for c in unicodedata.normalize('NFD', text)
                if unicodedata.category(c) != 'Mn'
            )
            return text.strip()

        weekday = normalize(weekday)
        working_days = normalize(employee.working_days)

        dias_semana = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
        dias_laborales = []

        # --- 🗓️ Soporte para rango "Lunes a Sábado" ---
        if " a " in working_days:
            partes = working_days.split(" a ")
            if len(partes) == 2:
                inicio, fin = normalize(partes[0]), normalize(partes[1])
                if inicio in dias_semana and fin in dias_semana:
                    i1, i2 = dias_semana.index(inicio), dias_semana.index(fin)
                    dias_laborales = dias_semana[i1:i2 + 1]
        else:
            # --- 📅 Soporte para lista separada por comas ---
            dias_laborales = [
                normalize(d) for d in working_days.split(",")
                if normalize(d) in dias_semana
            ]

        # Validar si el día de la cita está dentro de los días laborales
        if weekday not in dias_laborales:
            raise ValidationError(f"La manicurista no trabaja el día {weekday}.")

        # 4️⃣ Verificar conflictos de citas existentes
        from appointments.models import Appointment
        if Appointment.objects.filter(
            employee=employee,
            date=self.date,
            time=self.time
        ).exclude(id=self.id).exists():
            raise ValidationError("La manicurista ya tiene una cita programada en ese horario.")

    def save(self, *args, **kwargs):
        self.clean()  # validar antes de guardar
        # 💰 Calcular total_price
        total = Decimal(0)
        if self.service_manos:
            total += self.service_manos.price
        if self.service_pies:
            total += self.service_pies.price
        self.total_price = total

        # 💵 Definir anticipo automático (ej. 20%)
        if self.requires_deposit and self.deposit_amount == 0:
            self.deposit_amount = Decimal('100.00')
            
        super().save(*args, **kwargs)


class PromotionSettings(models.Model):
    active = models.BooleanField(default=False)
    required_services = models.PositiveIntegerField(default=10, help_text="Cantidad de servicios para ganar uno gratis")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Activa" if self.active else "Inactiva"
        return f"Promoción {status} ({self.required_services} servicios)"
    
# class AppointmentLog(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
#     employee = models.CharField(max_length=100)
#     service = models.CharField(max_length=100)
#     date = models.DateField()
#     time = models.CharField(max_length=20)
#     status = models.CharField(max_length=20)  # SUCCESS | ERROR
#     details = models.TextField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.user} | {self.date} {self.time} | {self.status}"
