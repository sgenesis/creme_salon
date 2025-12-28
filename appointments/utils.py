from django.core.mail import EmailMultiAlternatives
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from pathlib import Path


def send_appointment_confirmation(appointment):
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    services = []

    if appointment.service_manos:
        services.append(appointment.service_manos.name)

    if appointment.service_pies:
        services.append(appointment.service_pies.name)

    service_text = ", ".join(services) if services else "Sin servicio"

    context = {
        "client": appointment.client.get_full_name(),
        "employee": appointment.employee.user.first_name,  # ✅ FIX AQUÍ
        "services": service_text,
        "date": appointment.date,
        "time": appointment.time.strftime("%H:%M"),
    }

    print("📩 Datos enviados al webhook:", context)

    subject = "Confirmación de tu cita – Crème Studio"
    from_email = "no-reply@cremestudio.com"
    to = [appointment.client.email]

    html_content = render_to_string("emails/appointment_confirmation.html", context)
    msg = EmailMultiAlternatives(subject, html_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()