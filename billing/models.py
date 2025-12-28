from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class CashRegister(models.Model):
    business_date = models.DateField(default=timezone.now)  # ← Nuevo: fecha contable del día
    
    opening_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    closing_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    is_open = models.BooleanField(default=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cash_opened"
    )


    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cash_closed"
    )

    class Meta:
        # evita tener dos registros abiertos para la misma fecha
        constraints = [
            models.UniqueConstraint(fields=["business_date"], condition=models.Q(is_open=True), name="unique_open_cash_per_day")
        ]

    def __str__(self):
        return f"Caja {self.business_date} - {'ABIERTA' if self.is_open else 'CERRADA'}"

    def total_collected(self):
        """Suma las ventas cobradas asociadas a la fecha contable (usa Sale model)."""
        try:
            from sales.models import Sale
            # filtramos por sales cuya date sea el mismo día (date__date)
            qs = Sale.objects.filter(date__date=self.business_date)
            total = qs.aggregate(total=models.Sum('total'))['total'] or Decimal('0.00')
            return total
        except Exception:
            return Decimal('0.00')