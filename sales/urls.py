from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SaleViewSet, 
    sales_by_client, 
    sales_report, sale_ticket, 
    sales_history, sales_dashboard, sales_export_excel,
    daily_cut,
    daily_cut_view
    )


urlpatterns = [
    
    path('dashboard/', sales_dashboard, name="sales_dashboard"),                         
    path('client/<int:client_id>/', sales_by_client),
    path('report/', sales_report),
    path('<int:sale_id>/ticket/', sale_ticket),                
    path('history/', sales_history, name="sales_history"),
    path('export-excel/', sales_export_excel),
    path('daily-cut/', daily_cut, name="daily_cut"),
    path('daily-cut/view/', daily_cut_view, name="daily_cut_view"),


    
]

