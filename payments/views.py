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
    data = json.loads(request.body)

    if data.get("type") == "payment":
        payment_id = data["data"]["id"]

        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        payment = sdk.payment().get(payment_id)["response"]

        if payment["status"] == "approved":
            appointment_id = payment.get("external_reference")

            appointment = Appointment.objects.filter(
                id=appointment_id
            ).first()

            if not appointment:
                return HttpResponse(status=200)

            if appointment.status == "expired":
                return HttpResponse(status=200)

            if appointment.deposit_paid:
                return HttpResponse(status=200)

            appointment.deposit_paid = True
            appointment.status = "scheduled"
            appointment.payment_reference = payment_id
            appointment.save()

    return HttpResponse(status=200)
    
class CreateDepositPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        total_price = request.data.get("total_price")
        appointment_id = request.data.get("appointment_id", "temp")

        if not total_price:
            return Response({"error": "total_price requerido"}, status=400)

        deposit_amount = round(float(total_price) * 0.20, 2)

        preference = create_mp_preference(
            amount=deposit_amount,
            description="Anticipo de cita (20%)",
            appointment_id=appointment_id
        )

        return Response({
            "init_point": preference["init_point"]
        })
        
class PaymentSuccessView(APIView):
    def get(self, request):
        payment_id = request.GET.get("payment_id")
        status = request.GET.get("status")

        if status == "approved":
            metadata = request.GET  # aquí reconstruyes la cita
            Appointment.objects.create(
                client=request.user,
                deposit_paid=True,
                payment_reference=payment_id,
                
            )

        return redirect("/gracias/")
    
@api_view(["GET"])
def deposit_status(request, appointment_id):
    appt = Appointment.objects.get(id=appointment_id)
    return Response({
        "deposit_paid": appt.deposit_paid
    })


class CheckDepositStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, appointment_id):
        exists = Appointment.objects.filter(
            id=appointment_id,
            deposit_paid=True
        ).exists()

        return Response({"paid": exists})

