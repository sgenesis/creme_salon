import uuid
from django.db import models
from django.contrib import admin
from appointments.models import Appointment
from django.views.decorators.csrf import csrf_exempt

class Payment(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="payment")
    mp_payment_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    provider = models.CharField(max_length=30, default="mercadopago")
    reference = models.CharField(max_length=100, unique=True)
    raw_response = models.JSONField(default=dict)
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago MP {self.mp_payment_id}"


# @admin.register(Payment)
# class PaymentAdmin(admin.ModelAdmin):
#     list_display = (
#         "appointment",
#         "amount",
#         "status",
#         "reference",
#         "created_at"
#     )
#     search_fields = ("reference",)



class DepositPayment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name="deposit_payment"
    )

    mp_payment_id = models.CharField(max_length=100, unique=True)
    mp_status = models.CharField(max_length=30)

    amount = models.DecimalField(max_digits=8, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago {self.mp_payment_id} - {self.mp_status}"
