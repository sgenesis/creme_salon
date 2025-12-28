from django.contrib import admin

from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "appointment",
        "mp_payment_id",
        "status",
        "amount",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("mp_payment_id",)

