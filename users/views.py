from rest_framework import generics, permissions
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from .models import CustomUser
from .serializers import UserSerializer, RegisterSerializer, PromotionStatusSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.urls import reverse_lazy
from rest_framework.decorators import api_view
from jwt import decode, ExpiredSignatureError, InvalidTokenError
from django.conf import settings

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
    
class PromotionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = PromotionStatusSerializer(request.user)
        return Response(serializer.data)



def register_page(request):
    return render(request, "register.html")

class CustomPasswordResetView(PasswordResetView):
    template_name = "password_reset.html"
    email_template_name = "password_reset_email.html"
    subject_template_name = "password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = "password_reset_done.html"


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "password_reset_complete.html"

@api_view(["GET"])
def debug_auth(request):
    return Response({
        "user": str(request.user),
        "authenticated": request.user.is_authenticated,
        "role": getattr(request.user, "role", "NO ROLE"),
        "auth_header": request.headers.get("Authorization"),
    })

class TokenInspectView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):

        # 1. intentar obtener token del header
        auth_header = request.headers.get("Authorization", None)
        token = None
        source = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            source = "Authorization Header"

        # 2. si no viene en header, revisar cookie
        if not token:
            cookie_token = request.COOKIES.get("jwt", None)
            if cookie_token:
                token = cookie_token
                source = "Cookie (jwt)"

        if not token:
            return Response({"error": "No token found", "source": None})

        # 3. Decodificar token sin verificar firma para ver payload
        try:
            payload = decode(token, options={"verify_signature": False})
        except Exception as e:
            return Response({"error": "Cannot decode token", "detail": str(e)})

        # 4. Validar token con firma y expiración
        jwt_auth = JWTAuthentication()
        try:
            validated = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated)
            status = "VALID ✅"
        except ExpiredSignatureError:
            user = None
            status = "EXPIRED ❌"
        except InvalidTokenError as e:
            user = None
            status = f"INVALID ❌ ({str(e)})"
        except Exception as e:
            user = None
            status = f"ERROR ❌ ({str(e)})"

        return Response({
            "token_source": source,
            "status": status,
            "payload": payload,
            "user": str(user) if user else None,
        })
    
# --- Página admin para gestionar usuarios (solo superuser/role admin) ---
@login_required
def admin_panel(request):
    # permitir solo superuser o role 'admin'
    if not (request.user.is_superuser or getattr(request.user, 'role', None) == 'admin'):
        return redirect('/api/appointments/available-view/')
    return render(request, "users/admin_panel.html")

# Solo administradores pueden acceder
is_admin = user_passes_test(lambda u: u.is_superuser or u.is_staff)

@is_admin
def user_list(request):
    users = CustomUser.objects.all()
    return render(request, 'users/user_list.html', {'users': users})

@api_view(['POST'])
@permission_classes([IsAdminUser])
def users_create(request):
    data = request.data.copy()
    pwd = data.pop('password', None)
    serializer = UserSerializer(data=data)
    if serializer.is_valid():
        user = serializer.save()
        if pwd:
            user.set_password(pwd)
            user.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# users/views_html.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from .models import CustomUser
from .forms import UserForm

# Solo administradores pueden acceder
is_admin = user_passes_test(lambda u: u.is_superuser or u.is_staff)

@is_admin
def user_list(request):
    users = CustomUser.objects.all()
    return render(request, '/users/list.html', {'users': users})


@is_admin
def user_edit(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    form = UserForm(request.POST or None, instance=user)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect('user-list-html')

    return render(request, 'users/user_form.html', {'form': form, 'user': user})


@is_admin
def user_delete(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)

    if request.method == "POST":
        user.delete()
        return redirect('user-list-html')

    return render(request, 'users/user_confirm_delete.html', {'user': user})
