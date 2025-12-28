from appointments import serializers
from .views import CashRegister

class CashRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashRegister
        fields = '__all__'
        read_only_fields = ['opened_at', 'closed_at', 'opened_by', 'closed_by', 'business_date']