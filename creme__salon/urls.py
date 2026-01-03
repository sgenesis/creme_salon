"""
URL configuration for creme__salon project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from sales.views import SaleViewSet
from django.http import JsonResponse
from django.contrib.auth import views as auth_views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    
)

def health(request):
    return JsonResponse({"status": "ok"})

router = DefaultRouter()
router.register(r'sales', SaleViewSet, basename='sales')

urlpatterns = [
    path("", health),
    path('admin/', admin.site.urls),

    # ✅ Rutas JWT

    path('panel/users/', include('users.urls')),

    
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('api/sales/', include('sales.urls')),

    path('api/', include(router.urls)),

    path('api/users/', include('users.urls')),
    path('api/employees/', include('employees.urls')),
    path('api/appointments/', include('appointments.urls')),
    path('api/products/', include('products.urls')),
    path('api/billing/', include('billing.urls')),
    

    path('dashboard/', TemplateView.as_view(template_name="dashboard.html")),
    path('auth/', include('social_django.urls', namespace='social')),
    path('api/payments/', include('payments.urls')),

    # 🔑 PASSWORD RESET FLOW
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='password_reset.html',
            email_template_name='password_reset_email.html',
            subject_template_name='password_reset_subject.txt',
            success_url='/password-reset/done/'
        ),
        name='password_reset'
    ),

    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='password_reset_done.html'
        ),
        name='password_reset_done'
    ),

    path(
        'password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='password_reset_confirm.html',
            success_url='/password-reset-complete/'
        ),
        name='password_reset_confirm'
    ),
    
]
