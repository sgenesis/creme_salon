from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CreateDepositPreferenceView, mercadopago_webhook, CheckDepositStatusView

urlpatterns = [
    
    path("create-preference/", CreateDepositPreferenceView.as_view()),
    path("webhook/", mercadopago_webhook),
    path("payments/check-deposit/<uuid:appointment_id>/", CheckDepositStatusView.as_view()),


]