from decimal import Decimal
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout
import json
from .utils import send_appointment_confirmation
from .models import Service, Appointment, PromotionSettings
from products.models import Product
from rest_framework.authentication import SessionAuthentication
from .serializers import (
    ServiceSerializer,
    AppointmentSerializer,
    PromotionSettingsSerializer,
    EmployeeBasicSerializer,
    AppointmentListSerializer,
    AppointmentSimpleSerializer
)
from employees.models import EmployeeProfile
import logging

from payments.mercadopago_utils import create_mp_preference
import mercadopago
sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

# -------------------------------
# Permiso personalizado para Admin
# -------------------------------
def admin_required(view_func):
    return user_passes_test(lambda u: u.is_superuser or u.role == 'admin')(view_func)

class IsAdminOrSuperuser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)

# -------------------------------
# LOGIN PERSONALIZADO
# -------------------------------
@csrf_exempt
def custom_login_view(request):
    if request.method == 'GET':
        return render(request, 'appointments/login.html')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)  # ✅ crea sesión Django
            return JsonResponse({"ok": True})

        return JsonResponse({"error": "Credenciales inválidas"}, status=401)
# -------------------------------
# DASHBOARD ADMIN/SUPERUSER
# -------------------------------


def salon_dashboard(request):
    print("🚨 USER:", request.user)
    print("🚨 AUTH:", request.user.is_authenticated)

    if not request.user.is_authenticated:
        return redirect("/api/appointments/login/")

    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, "role", None) == "admin"):
        return redirect("/api/appointments/available-view/")

    return render(request, "appointments/salon_dashboard.html")
# -------------------------------
# VISTAS REST FRAMEWORK
# -------------------------------

# Servicios
class ServiceListView(generics.ListAPIView):
    queryset = Service.objects.filter(active=True).order_by('name')
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None  # 👈 DESACTIVA PAGINACIÓN

class ServiceListAdminView(generics.ListAPIView):
    queryset = Service.objects.filter(active=True).order_by('name')
    serializer_class = ServiceSerializer
    permission_classes = [IsAdminOrSuperuser]

# Citas


class AppointmentCreateView(generics.CreateAPIView):
    serializer_class = AppointmentSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appointment = serializer.save(
            client=request.user,
            status="pending",
            deposit_paid=False,
            requires_deposit=True
        )

        # 🔹 Crear preferencia MercadoPago
        preference = create_mp_preference(
            amount=float(appointment.deposit_amount),
            description="Anticipo cita (20%)",
            appointment_id=str(appointment.id)
        )

        return Response({
            "appointment_id": appointment.id,
            "deposit_amount": appointment.deposit_amount,
            "init_point": preference["init_point"]
        }, status=201)

        # Enviar correo
        send_appointment_confirmation(appointment)

class AppointmentListView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'client':
            return user.appointments.all().order_by('-date', '-time')
        elif user.role == 'employee':
            return user.employee_profile.appointments.all().order_by('-date', '-time')
        return Appointment.objects.all().order_by('-date', '-time')

# Admin: Listado y detalle de citas
class AppointmentListAdminView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAdminOrSuperuser]

    def get_queryset(self):
        queryset = Appointment.objects.all().order_by('-date', '-time')
        employee_id = self.request.query_params.get('employee', None)
        if employee_id:
            queryset = queryset.filter(employee__id=employee_id)
        return queryset

class AppointmentDetailAdminView(generics.RetrieveUpdateAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAdminOrSuperuser]
    queryset = Appointment.objects.all()
    lookup_field = 'id'

    def patch(self, request, *args, **kwargs):
        appointment = self.get_object()
        previous_status = appointment.status
        
        status_value = request.data.get('status')

        if status_value not in ['scheduled', 'completed', 'cancelled']:
            return Response({"error": "Estado inválido"}, status=400)

        appointment.status = status_value
        appointment.save()

        # 📩 Enviar email si se confirma una cita
        if status_value == "scheduled" and previous_status != "scheduled":
            try:
                send_appointment_confirmation(appointment)
            except Exception as e:
                print("Error enviando correo:", e)

        serializer = self.get_serializer(appointment)
        return Response(serializer.data)

# Cobrar cita
class ChargeAppointmentView(APIView):
    permission_classes = [IsAdminOrSuperuser]

    def post(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, id=appointment_id)
        appointment.status = 'completed'
        appointment.save()
        serializer = AppointmentSerializer(appointment)
        return Response(serializer.data, status=200)

# Promociones
class PromotionSettingsView(generics.RetrieveAPIView):
    queryset = PromotionSettings.objects.filter(active=True)
    serializer_class = PromotionSettingsSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        return self.queryset.first()

# Manicuristas
class ManicuristListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        manicurists = EmployeeProfile.objects.filter(available=True)
        serializer = EmployeeBasicSerializer(manicurists, many=True)
        return Response(serializer.data)


# Citas por manicurista y fecha
@api_view(['GET'])
#@permission_classes([IsAuthenticated])
def appointments_by_manicurist(request):
    manicurist_id = request.GET.get('manicurist')
    date_str = request.GET.get('date')

    if not manicurist_id or not date_str:
        return Response({'error': 'Faltan parámetros'}, status=400)

    manicurist = get_object_or_404(EmployeeProfile, id=manicurist_id)

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return Response({'error': 'Formato de fecha inválido'}, status=400)

    citas = Appointment.objects.filter(employee=manicurist, date=date_obj).select_related('client', 'service')

    # Si quieres devolver campos legibles para el frontend
    data = [{
        "id": cita.id,
        "client_name": f"{cita.client.first_name} {cita.client.last_name}",
        "service_name": cita.service.name,
        "time": cita.time.strftime("%H:%M"),
        "status": cita.status,
        "total_price": cita.total_price
    } for cita in citas]

    return Response(data)


# Disponibilidad de manicurista
class AvailableSlotsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, employee_id):
        try:
            employee = EmployeeProfile.objects.get(id=employee_id, available=True)
        except EmployeeProfile.DoesNotExist:
            return Response({"error": "Manicurista no encontrada"}, status=404)

        now = datetime.now()
        days_ahead = 7
        slots = []

        days_map = {
            "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
            "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6
        }

        working_days_str = employee.working_days.lower()
        available_days = [idx for name, idx in days_map.items() if name in working_days_str]

        for day_offset in range(days_ahead):
            day = now + timedelta(days=day_offset)
            if day.weekday() not in available_days:
                continue

            start_dt = datetime.combine(day.date(), employee.start_time)
            end_dt = datetime.combine(day.date(), employee.end_time)
            current = start_dt

            while current + timedelta(hours=1) <= end_dt:
                overlapping = Appointment.objects.filter(
                    employee=employee,
                    date=day.date(),
                    time__gte=current.time(),
                    time__lt=(current + timedelta(hours=1)).time(),
                    status='scheduled'
                ).exists()

                if not overlapping and current > now:
                    slots.append({
                        "start": current.isoformat(),
                        "end": (current + timedelta(hours=1)).isoformat()
                    })
                current += timedelta(hours=1)

        return Response(slots)

class EmployeeAvailableSlotsView(APIView):
    def get(self, request, employee_id):
        date_str = request.GET.get('date')
        if not date_str:
            return Response({"error": "Debe proporcionar ?date=YYYY-MM-DD"}, status=400)

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
            employee = EmployeeProfile.objects.get(id=employee_id)
        except EmployeeProfile.DoesNotExist:
            return Response({"error": "Manicurista no encontrada"}, status=404)
        except ValueError:
            return Response({"error": "Formato de fecha inválido"}, status=400)

        if not employee.start_time or not employee.end_time:
            return Response({"error": "La manicurista no tiene horario configurado"}, status=400)

        # Generar rango de horarios (por hora)
        start_dt = datetime.combine(date, employee.start_time)
        end_dt = datetime.combine(date, employee.end_time)
        delta = timedelta(hours=1)

        available_slots = []
        current = start_dt
        while current < end_dt:
            available_slots.append(current.strftime("%H:%M"))
            current += delta

        # Obtener citas ocupadas en esa fecha
        taken_times = Appointment.objects.filter(
            employee=employee,
            date=date,
            status__in=['scheduled', 'completed']
        ).values_list('time', flat=True)

        # Convertir a strings iguales para comparar
        taken_str = [t.strftime("%H:%M") for t in taken_times]

        free_slots = [s for s in available_slots if s not in taken_str]

        return Response({
            "employee": f"{employee.user.first_name} {employee.user.last_name}",
            "employee_id": str(employee.id),
            "date": date_str,
            "available_slots": free_slots,
            "occupied_slots": taken_str,
            "updated_at": datetime.now().isoformat()
        })

# Páginas HTML
def available_slots_page(request):
    return render(request, 'appointments/available_slots.html')

def about_view(request):
    return render(request, 'appointments/about.html')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    user = request.user
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    })



def available_view(request):
    return render(request, "appointments/available_slots.html")

# -------------------------------
# LOGIN API (para fetch/JS)
# -------------------------------

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@ensure_csrf_cookie
def api_login_view(request):
    """
    Permite que el frontend (fetch) haga login y obtenga cookie de sesión válida
    """
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return Response({"message": "Login exitoso", "user": user.username})
    else:
        return Response({"error": "Credenciales inválidas"}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_auth(request):
    return Response({
        "auth": True,
        "user": request.user.username,
        "id": request.user.id
    })

@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response({"ok": True})


@login_required
def edit_appointment(request, appointment_id):
    """
    Renderiza la página para ver/editar/completar una cita.
    Se inyectan datos básicos de la cita en el template para que el JS los use.
    """
    # appointment_id se espera como UUID (según tu urls anteriores)
    appointment = get_object_or_404(Appointment, id=appointment_id)

    # permisos: solo staff/admin o la persona que creó la cita?
    # aquí permitimos ver si es staff/superuser o si es el cliente mismo
    user = request.user
    if not (user.is_staff or user.is_superuser or appointment.client == user):
        return redirect("/api/appointments/available-view/")

    context = {
        "appointment_id": str(appointment.id),
        "client_name": f"{appointment.client.first_name} {appointment.client.last_name}",
        "client_id": appointment.client.id,
        #"original_service_id": getattr(appointment.service.id, 'hex', None) if hasattr(appointment.service, 'id') else getattr(appointment.service, 'id', None) or None,
        # fallback: if service is FK, we can just pass the id
        # ---------- SERVICIOS ----------
        "service_manos_id": appointment.service_manos.id if appointment.service_manos else None,
        "service_manos_name": appointment.service_manos.name if appointment.service_manos else "",

        "service_pies_id": appointment.service_pies.id if appointment.service_pies else None,
        "service_pies_name": appointment.service_pies.name if appointment.service_pies else "",

        "appointment_date": appointment.date.strftime("%Y-%m-%d"),
        "appointment_time": appointment.time.strftime("%H:%M"),
    }
    return render(request, "appointments/edit_appointment.html", context)

logger = logging.getLogger(__name__)

@login_required
def create_appointment(request):
    try:
        logger.info(f"📩 BODY recibido: {request.body}")
        data = json.loads(request.body)

        logger.info(f"""
        ✅ Nueva Cita
        - User: {request.user}
        - Employee: {data.get('employee')}
        - Service: {data.get('service')}
        - Date: {data.get('date')}
        - Time: {data.get('time')}
        - Notes: {data.get('notes')}
        """)

        # ... tu lógica de guardado

        return JsonResponse({"ok": True})

    except Exception as e:
        logger.error(f"❌ Error creando cita: {str(e)}", exc_info=True)
        return JsonResponse({"error": "Error interno"}, status=500)
    
@login_required
def my_profile(request):
    u = request.user
    return JsonResponse({
        "username": u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "email": u.email,
        "date_joined": u.date_joined.strftime("%Y-%m-%d")
    })

@login_required
def my_appointments(request):
    appointments = Appointment.objects.filter(client=request.user).select_related('employee__user', 'service_manos', 'service_pies').order_by('-date', '-time')

    data = []
    for a in appointments:

        servicios = []

        if a.service_manos:
            servicios.append({
                "id": str(a.service_manos.id),
                "name": a.service_manos.name,
                "price": a.service_manos.price
            })

        if a.service_pies:
            servicios.append({
                "id": str(a.service_pies.id),
                "name": a.service_pies.name,
                "price": a.service_pies.price
            })

        data.append({
            "id": str(a.id),
            "date": a.date.strftime("%Y-%m-%d"),
            "time": a.time.strftime("%H:%M"),
            "services": servicios,
            "price": (
                (a.service_manos.price if a.service_manos else 0) +
                (a.service_pies.price if a.service_pies else 0)
            ),
            "status": a.status,
            "employee_id": str(a.employee.id) if a.employee else None,
            "employee_name": a.employee.user.get_full_name() if a.employee and a.employee.user else "Sin asignar",
        })

    return JsonResponse(data, safe=False)


@csrf_exempt
def cancel_appointment(request, id):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    try:
        # Si es admin, puede cancelar cualquier cita
        if request.user.is_staff:
            appt = Appointment.objects.get(id=id)
        else:
            # Usuario normal solo puede cancelar sus propias citas
            appt = Appointment.objects.get(id=id, client=request.user)

        appt.status = "cancelled"
        appt.save()

        return JsonResponse({"success": True, "status": appt.status})

    except Appointment.DoesNotExist:
        return JsonResponse({"error": "Cita no encontrada"}, status=404)
    
@csrf_exempt
def reschedule_appointment(request, id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            appt = Appointment.objects.get(id=id, client=request.user)

            # Convertir valores enviados como string a objetos date y time
            from datetime import datetime

            new_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
            new_time = datetime.strptime(data["time"], "%H:%M").time()

            # Si también envías employee_id, actualizarlo
            if "employee_id" in data and data["employee_id"]:
                from appointments.models import EmployeeProfile
                new_employee = EmployeeProfile.objects.get(id=data["employee_id"])
                appt.employee = new_employee

            appt.date = new_date
            appt.time = new_time
            appt.status = "scheduled"
            appt.save()

            return JsonResponse({"success": True, "status": appt.status})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
        

def admin_only(view_func):
    return user_passes_test(
        lambda u: u.is_authenticated and (u.is_superuser or getattr(u, "role", "") == "admin")
    )(view_func)

def admin_panel(request):
    return render(request, "appointments/admin_panel.html")

@admin_only
def ventas_rapidas(request):
    return render(request, "appointments/ventas_rapidas.html")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def appointments_list(request):

    manicurist = request.GET.get("manicurist")  # employee_id
    date = request.GET.get("date")


    qs = Appointment.objects.filter(status="scheduled").select_related(
        "client", "employee__user", "service"
    )

    data = []
    for a in qs:

        servicios = []

        if a.service_manos:
            servicios.append({
                "id": str(a.service_manos.id),
                "name": a.service_manos.name,
                "price": a.service_manos.price
            })

        if a.service_pies:
            servicios.append({
                "id": str(a.service_pies.id),
                "name": a.service_pies.name,
                "price": a.service_pies.price
            })

    if manicurist:
        qs = qs.filter(employee_id=manicurist)

    if date:
        qs = qs.filter(date=date)

    data = [
        {
            "id": str(a.id),
            "client_name": f"{a.client.first_name} {a.client.last_name}" if a.client else "Sin cliente",
            "services": servicios,
            "time": a.time.strftime("%H:%M"),
            "date": str(a.date),
            "manicurist": a.employee.user.get_full_name() if a.employee else "—",
            "status": a.status,
            "total_price": str(a.total_price) if a.total_price else None,
        }
        for a in qs.order_by("date", "time")
    ]

    return Response(data)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_scheduled_appointments(request):

    qs = Appointment.objects.filter(status="scheduled").select_related(
        "client", "employee__user", "service_manos", "service_pies"
    ).order_by("date", "time")

    data = []
    for a in qs:

        servicios = []

        if a.service_manos:
            servicios.append({
                "id": str(a.service_manos.id),
                "name": a.service_manos.name,
                "price": a.service_manos.price
            })

        if a.service_pies:
            servicios.append({
                "id": str(a.service_pies.id),
                "name": a.service_pies.name,
                "price": a.service_pies.price
            })

    data = [
        {
            "id": str(a.id),
            "date": str(a.date),
            "time": a.time.strftime("%H:%M"),
            "client_name": f"{a.client.first_name} {a.client.last_name}" if a.client else "Sin cliente",
            "services": servicios,
            "manicurist_name": a.employee.user.get_full_name() if a.employee else "—",
            "total_price": str(a.total_price) if a.total_price else None,
            "status": a.status,
        }
        for a in qs
    ]

    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scheduled_appointments_filtered(request):
    manicurist_id = request.GET.get("manicurist")
    date = request.GET.get("date")

    qs = Appointment.objects.filter(status="scheduled").select_related(
        "client", "employee__user", "service"
    )

    data = []
    for a in qs:

        servicios = []

        if a.service_manos:
            servicios.append({
                "id": str(a.service_manos.id),
                "name": a.service_manos.name,
                "price": a.service_manos.price
            })

        if a.service_pies:
            servicios.append({
                "id": str(a.service_pies.id),
                "name": a.service_pies.name,
                "price": a.service_pies.price
            })

    if manicurist_id:
        qs = qs.filter(employee_id=manicurist_id)

    if date:
        qs = qs.filter(date=date)

    qs = qs.order_by("date", "time")

    data = [
        {
            "id": str(a.id),
            "date": str(a.date),
            "time": a.time.strftime("%H:%M"),
            "client_name": f"{a.client.first_name} {a.client.last_name}" if a.client else "Sin cliente",
            "services": servicios,
            "manicurist_name": a.employee.user.get_full_name() if a.employee else "—",
            "total_price": str(a.total_price) if a.total_price else None,
            "status": a.status,
        }
        for a in qs
    ]

    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manicurist_list(request):
    manicurists = EmployeeProfile.objects.filter(available=True).select_related("user")

    data = [
        {
            "id": str(m.id),
            "name": m.user.get_full_name(),
        }
        for m in manicurists
    ]

    return Response(data)


@csrf_exempt
@login_required
def create_appointment_intent(request):
    """
    Recibe payload del frontend con:
    { employee, service_manos, service_pies, date, time, notes }
    Crea registro Appointment con deposit_paid=False y status='pending'
    Crea PaymentIntent en Stripe y devuelve client_secret y appointment_id
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)
    try:
        data = json.loads(request.body)
        user = request.user

        employee = EmployeeProfile.objects.get(id=data.get("employee"))
        service_manos = Service.objects.filter(id=data.get("service_manos")).first()
        service_pies  = Service.objects.filter(id=data.get("service_pies")).first()

        # calcular total
        total = Decimal('0')
        if service_manos: total += service_manos.price
        if service_pies:  total += service_pies.price

        # anticipo fijo al 20% (ajustable)
        deposit_amount = (total * Decimal('0.20')).quantize(Decimal('0.01'))

        # crear la cita "pending" — no confirmada hasta pagar
        appointment = Appointment.objects.create(
            client=user,
            employee=employee,
            service_manos=service_manos,
            service_pies=service_pies,
            date=data.get("date"),
            time=data.get("time"),
            total_price=total,
            deposit_amount=deposit_amount,
            requires_deposit=True,
            deposit_paid=False,
            status='pending'
        )

        # metadata opcional con id para luego reconectar
        metadata = {"appointment_id": str(appointment.id)}

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
    
@csrf_exempt
def mercadopago_webhook(request):
    data = json.loads(request.body)

    payment_id = data["data"]["id"]

    payment = sdk.payment().get(payment_id)
    status = payment["response"]["status"]

    if status == "approved":
        appointment_id = payment["response"]["external_reference"]

        appointment = Appointment.objects.get(id=appointment_id)
        appointment.deposit_paid = True
        appointment.payment_reference = payment_id
        appointment.status = "scheduled"
        appointment.save()

    return JsonResponse({"ok": True})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_pending_appointment(request):
    data = request.data

    appointment = Appointment.objects.create(
        client=request.user,
        employee_id=data["employee"],
        service_manos_id=data.get("service_manos"),
        service_pies_id=data.get("service_pies"),
        date=data["date"],
        time=data["time"],
        duration_hours=data["duration_hours"],
        status="pending_payment",
        deposit_paid=False,
    )

    return Response({
        "appointment_id": appointment.id,
        "status": appointment.status
    })

class AppointmentListView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(client=self.request.user)