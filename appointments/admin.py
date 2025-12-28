from django.contrib import admin
from .models import Service, Appointment, PromotionSettings

admin.site.register(Service)
admin.site.register(Appointment)
admin.site.register(PromotionSettings)
