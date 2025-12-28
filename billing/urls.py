from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    
    CashStatusAPIView,
    CashOpenAPIView,
    CashCloseAPIView,
    CashDayReportAPIView
)


urlpatterns = [
    
    path("status/", CashStatusAPIView.as_view(), name="cash-status"),
    path("open/", CashOpenAPIView.as_view(), name="cash-open"),
    path("close/", CashCloseAPIView.as_view(), name="cash-close"),
    path("report/", CashDayReportAPIView.as_view(), name="cash-report"),

]
