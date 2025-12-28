from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import CashRegister
from django.db.models import Sum
from sales.models import Sale
from appointments.models import Appointment


class CashStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()

        open_register = CashRegister.objects.filter(business_date=today, is_open=True).first()

        return Response({
            "is_open": bool(open_register),
            "opening_amount": str(open_register.opening_amount) if open_register else None,
            "opened_at": open_register.opened_at.isoformat() if open_register else None,
            "cash_id": str(open_register.id) if open_register else None,
        })


class CashOpenAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        today = timezone.now().date()

        # Evitar caja doble
        # ya abierta para hoy?
        if CashRegister.objects.filter(business_date=today, is_open=True).exists():
            return Response({"error": "La caja de hoy ya está abierta."}, status=status.HTTP_400_BAD_REQUEST)

        amount = request.data.get("opening_amount", 0) or 0
        try:
            amount = float(amount)
        except Exception:
            amount = 0

        cash = CashRegister.objects.create(
            business_date=today,
            opening_amount=amount,
            opened_by=request.user,
            is_open=True
        )

        return Response({"message": "Caja abierta correctamente.", "cash_id": str(cash.id)}, status=status.HTTP_201_CREATED)


class CashCloseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        today = timezone.now().date()

        open_register = CashRegister.objects.filter(business_date=today, is_open=True).first()

        if not open_register:
            return Response({"error": "No hay caja abierta hoy."}, status=status.HTTP_400_BAD_REQUEST)

        amount = request.data.get("closing_amount", 0) or 0
        try:
            amount = float(amount)
        except Exception:
            amount = 0

        open_register.closing_amount = amount
        open_register.closed_at = timezone.now()
        open_register.closed_by = request.user
        open_register.is_open = False
        open_register.save()

        # después del cierre devolvemos resumen del día
        summary = {
            "opening_amount": str(open_register.opening_amount or 0),
            "closing_amount": str(open_register.closing_amount or 0),
            "total_collected": str(open_register.total_collected()),
            "business_date": open_register.business_date.isoformat(),
        }

        return Response({"message": "Caja cerrada correctamente.", "summary": summary}, status=status.HTTP_200_OK)

class CashDayReportAPIView(APIView):
    """
    Reporte / corte del día — puedes llamarlo después de cerrar (o incluso antes).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, date=None):
        # opcional ?date=YYYY-MM-DD
        if date:
            try:
                business_date = timezone.datetime.strptime(date, "%Y-%m-%d").date()
            except Exception:
                return Response({"error": "Formato de fecha inválido"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            business_date = timezone.localdate()

        open_register = CashRegister.objects.filter(business_date=business_date).first()
        opening_amount = open_register.opening_amount if open_register else 0
        closing_amount = open_register.closing_amount if open_register else None

        # datos de ventas/citas
        try:
            total_sales = Sale.objects.filter(date__date=business_date).aggregate(total=models.Sum('total'))['total'] or 0
            completed_appointments = Appointment.objects.filter(date=business_date, status='completed').count()
        except Exception:
            total_sales = 0
            completed_appointments = 0

        return Response({
            "business_date": business_date.isoformat(),
            "opening_amount": str(opening_amount),
            "closing_amount": str(closing_amount) if closing_amount is not None else None,
            "total_sales": str(total_sales),
            "completed_appointments": completed_appointments,
        })