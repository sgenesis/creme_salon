import json
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render
import mercadopago
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response

from payments.models import DepositPayment
from .mercadopago_utils import create_mp_preference
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from .mercadopago_utils import create_mp_preference

from appointments.models import Appointment
from payments.models import Payment

sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

@csrf_exempt
def mercadopago_webhook(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return HttpResponse(status=400)

    if data.get("type") != "payment":
        return HttpResponse(status=200)

    payment_id = data.get("data", {}).get("id")
    if not payment_id:
        return HttpResponse(status=200)

    payment = sdk.payment().get(payment_id)["response"]

    if payment.get("status") != "approved":
        return HttpResponse(status=200)

    appointment_id = payment.get("external_reference")
    amount = payment["transaction_amount"]

    appointment = Appointment.objects.filter(id=appointment_id).first()
    if not appointment:
        return HttpResponse(status=200)

    if appointment.deposit_paid:
        return HttpResponse(status=200)

    # Validar monto
    if float(amount) != 100.00:
        return HttpResponse(status=200)

    # Guardar pago
    DepositPayment.objects.create(
        appointment=appointment,
        mp_payment_id=payment_id,
        mp_status=payment["status"],
        amount=amount
    )

    appointment.deposit_paid = True
    appointment.status = "scheduled"
    appointment.payment_reference = payment_id
    appointment.save()

    return HttpResponse(status=200)

    
class CreateDepositPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        appointment_id = request.data.get("appointment_id")

        if not appointment_id:
            return Response({"error": "appointment_id requerido"}, status=400)
        
        appointment = Appointment.objects.filter(id=appointment_id).first()
        if not appointment:
            return Response({"error": "Cita no encontrada"}, status=404)

        depositAmount = 100.00

        preference = create_mp_preference(
            deposit_amount=depositAmount,
            description="Anticipo fijp $100",
            appointment_id=appointment_id
        )

        return Response({
            "init_point": preference["init_point"]
        })
        
class PaymentSuccessView(APIView):
    def get(self, request):
        return redirect("/gracias/")
    


class CheckDepositStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, appointment_id):
        appt = Appointment.objects.filter(id=appointment_id).first()
        return Response({
            "deposit_paid": bool(appt and appt.deposit_paid)
        })
