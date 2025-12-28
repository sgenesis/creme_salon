from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment
from users.models import CustomUser

@receiver(post_save, sender=Appointment)
def update_user_service_count(sender, instance, created, **kwargs):
    """
    Cuando se marca una cita como completada, se suma al contador de servicios del cliente.
    """
    user = instance.client

    # Solo actuar si la cita está completada
    if instance.status == 'completed':
        # ⚠️ Importante: evitar contar dos veces la misma cita
        # Verificamos si ya fue contabilizada
        if not hasattr(instance, '_already_updated'):
            instance._already_updated = True  # bandera temporal
            user.total_services += 1

            # Si está activa la promoción y llegó al límite
            if user.promo_system_active and user.total_services >= user.services_for_promo:
                user.has_free_service = True
                user.total_services = 0  # reinicia el conteo
            user.save()
