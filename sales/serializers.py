from rest_framework import serializers
from .models import Sale, SaleItem
from products.models import Product
from appointments.models import Appointment


class SaleItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="product",
        allow_null=True,
        required=False
    )

    class Meta:
        model = SaleItem
        fields = ['id', 'product_id', 'quantity', 'subtotal']


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)
    # allow string UUID in payload; we'll accept it and convert in create()
    appointment = serializers.CharField(required=False, allow_null=True)
    
    class Meta:
        model = Sale
        fields = ['id', 'client', 'appointment', 'date', 'payment_method', 'total', 'notes', 'items']
        read_only_fields = ['client', 'date']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        appointment_uuid = validated_data.pop('appointment', None)

        # ✅ Convertir UUID → Appointment instance
        appointment_instance = None
        if appointment_uuid:
            try:
                appointment_instance = Appointment.objects.get(id=appointment_uuid)
            except Appointment.DoesNotExist:
                raise serializers.ValidationError({"appointment": "La cita no existe."})

        # ✅ crear venta con la instancia correcta
        sale = Sale.objects.create(
            appointment=appointment_instance,
            **validated_data
        )

        # ✅ crear los items
        for item in items_data:
            appt_for_item = item.get('appointment', None)
            if appt_for_item and isinstance(appt_for_item, str):
                try:
                    item['appointment'] = Appointment.objects.get(id=appt_for_item)
                except Appointment.DoesNotExist:
                    item['appointment'] = None
            SaleItem.objects.create(sale=sale, **item)

        # ✅ marcar cita como completada
        if appointment_instance:
            appointment_instance.status = "completed"
            appointment_instance.save()

        return sale
