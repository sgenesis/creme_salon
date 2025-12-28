from rest_framework import generics, permissions
from .models import EmployeeProfile
from .serializers import EmployeeProfileSerializer

class EmployeeListView(generics.ListAPIView):
    queryset = EmployeeProfile.objects.all()
    serializer_class = EmployeeProfileSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class EmployeeDetailView(generics.RetrieveAPIView):
    queryset = EmployeeProfile.objects.all()
    serializer_class = EmployeeProfileSerializer
    permission_classes = [permissions.AllowAny]
