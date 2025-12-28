from rest_framework import serializers
from .models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone', 'address', 'role', 'is_superuser', 'total_services', 'has_free_service']
        read_only_fields = ['id', 'total_services', 'has_free_service']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'phone']

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', '')
        )
        return user
    
class PromotionStatusSerializer(serializers.ModelSerializer):
    services_remaining = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'username',
            'role',
            'total_services',
            'services_for_promo',
            'has_free_service',
            'promo_system_active',
            'services_remaining',
        ]

    def get_services_remaining(self, obj):
        if not obj.promo_system_active:
            return None
        if obj.has_free_service:
            return 0
        return max(obj.services_for_promo - obj.total_services, 0)
