from rest_framework import serializers
from .models import EmployeeProfile
from users.serializers import UserSerializer
from users.models import CustomUser 

class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class EmployeeProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = ['id', 'user', 'bio', 'available', 'specialties', 'working_days', 'start_time', 'end_time']
