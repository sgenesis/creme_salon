from django.contrib import admin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'username', 'role', 'phone', 'total_services',
        'has_free_service', 'services_for_promo', 'promo_system_active'
    )
    list_filter = ('role', 'promo_system_active', 'has_free_service')
