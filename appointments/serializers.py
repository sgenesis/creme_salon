from datetime import datetime, timedelta
from rest_framework import serializers
from .models import Service, Appointment, PromotionSettings
from employees.models import EmployeeProfile
from users.serializers import CustomUser, UserSerializer

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'


class AppointmentSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(read_only=True)
    client_name = serializers.ReadOnlyField(source='client.username')
    employee_name = serializers.ReadOnlyField(source='employee.user.username')
    service_manos_name = serializers.ReadOnlyField(source='service_manos.name')
    service_pies_name = serializers.ReadOnlyField(source='service_pies.name')
    deposit_required = serializers.BooleanField(default=True)
    deposit_amount = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    deposit_paid = serializers.BooleanField(default=False)
    payment_reference = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Appointment
        fields = [
            "__all__"
        ]

    def get_duration_text(self, obj):
        hours = float(obj.duration_hours)
        return "1 hora" if hours == 1 else f"{hours} horas"

    def validate(self, data):
        employee = data['employee']
        date = data['date']
        time = data['time']

        service_manos = data.get("service_manos")
        service_pies = data.get("service_pies")

        if not service_manos and not service_pies:
            raise serializers.ValidationError("Debes seleccionar al menos un servicio (manos o pies).")
        
        duration = 0
        if service_manos:
            duration += float(service_manos.duration_hours)
        if service_pies:
            duration += float(service_pies.duration_hours)

        end_time = (datetime.combine(date, time) + timedelta(hours=duration)).time()

        # 🗓️ Mapa de días a español
        day_map = {
            'monday': 'lunes',
            'tuesday': 'martes',
            'wednesday': 'miércoles',
            'thursday': 'jueves',
            'friday': 'viernes',
            'saturday': 'sábado',
            'sunday': 'domingo',
        }

        weekday = day_map[date.strftime("%A").lower()]
        working_days_text = employee.working_days.lower().strip()

        # 🔍 Verifica si es un rango tipo "lunes a sábado"
        valid_days = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']

        def dias_en_rango(rango):
            """Convierte 'lunes a sábado' en ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado']"""
            partes = rango.split(' a ')
            if len(partes) == 2 and partes[0] in valid_days and partes[1] in valid_days:
                start = valid_days.index(partes[0])
                end = valid_days.index(partes[1])
                if start <= end:
                    return valid_days[start:end + 1]
            # Si no es rango válido, devuelve el texto tal cual
            return [rango]

        # Generar lista de días laborales
        if ' a ' in working_days_text:
            working_days = dias_en_rango(working_days_text)
        else:
            working_days = [d.strip() for d in working_days_text.split(',')]

        # 🕓 Validar si trabaja ese día
        if weekday not in working_days:
            raise serializers.ValidationError({
                "non_field_errors": [f"La manicurista no trabaja los {weekday}s."]
            })

        # 🕑 Validar horario
        if time < employee.start_time or time >= employee.end_time:
            raise serializers.ValidationError({
                "non_field_errors": ["La cita está fuera del horario laboral."]
            })

        # 🧍‍♀️ Validar disponibilidad general
        if hasattr(employee, 'available') and not employee.available:
            raise serializers.ValidationError({
                "non_field_errors": ["La manicurista no está disponible actualmente."]
            })

        # 🔁 Validar que no haya otra cita en ese horario
        existing_appointment = Appointment.objects.filter(
            employee=employee,
            date=date,
            time=time,
            status__in=['scheduled', 'completed']
        ).exists()

        if existing_appointment:
            raise serializers.ValidationError({
                "non_field_errors": ["Ese horario ya está ocupado."]
            })
        
        if data.get("deposit_required") and not data.get("deposit_paid"):
            raise serializers.ValidationError({
                "payment": "Debes pagar el anticipo para confirmar la cita."
        })

        return data


    def create(self, validated_data):
        """
        Calcula automáticamente el precio total y crea la cita.
        """
        service_manos = validated_data.get("service_manos")
        service_pies = validated_data.get("service_pies")

        total_price = 0
        duration = 0

        if service_manos:
            total_price += float(service_manos.price)
            duration += float(service_manos.duration_hours)
        if service_pies:
            total_price += float(service_pies.price)
            duration += float(service_pies.duration_hours)

        validated_data["total_price"] = total_price
        #validated_data["duration_hours"] = duration

        validated_data["deposit_required"] = True
        validated_data["deposit_amount"] = round(total_price * 0.20, 2)

        return super().create(validated_data)


class PromotionSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionSettings
        fields = '__all__'

class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class AvailableSlotSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()

class EmployeeBasicSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = ['id', 'user', 'bio', 'available', 'specialties', 'working_days', 'start_time', 'end_time']



class EmployeeBasicSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)  # ✅ usar serializer, no modelo

    class Meta:
        model = EmployeeProfile
        fields = ['id', 'user', 'bio', 'available', 'specialties', 'working_days', 'start_time', 'end_time']


class AppointmentListSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.full_name", read_only=True)
    manicurist_name = serializers.CharField(source="manicurist.user.first_name", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "date",
            "start_time",
            "end_time",
            "status",
            "service",
            "client_name",
            "manicurist",
            "manicurist_name",
        ],
        read_only_fields = ["client"]

class AppointmentSimpleSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    manicurist_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'date', 'time', 'status',
            'service_name', 'client_name', 'manicurist_name',
            'total_price'
        ]