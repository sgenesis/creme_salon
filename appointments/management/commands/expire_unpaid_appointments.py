from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from appointments.models import Appointment

class Command(BaseCommand):
    help = "Expira citas no pagadas después de 15 minutos"

    def handle(self, *args, **options):
        expiration_time = timezone.now() - timedelta(minutes=15)

        expired = Appointment.objects.filter(
            status="pending_payment",
            deposit_paid=False,
            created_at__lt=expiration_time
        )

        count = expired.count()

        expired.update(status="expired")

        self.stdout.write(
            self.style.SUCCESS(f"{count} citas expiradas correctamente")
        )