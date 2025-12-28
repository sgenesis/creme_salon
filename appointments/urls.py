from django.urls import path
from .views import (
    custom_login_view,
    salon_dashboard,
    ServiceListView,
    ServiceListAdminView,
    AppointmentCreateView,
    AppointmentListView,
    AppointmentListAdminView,
    AppointmentDetailAdminView,
    ChargeAppointmentView,
    PromotionSettingsView,
    AvailableSlotsView,
    EmployeeAvailableSlotsView,
    available_slots_page,
    about_view,
    ManicuristListView,
    appointments_by_manicurist,
    current_user_view,
    available_view,
    api_login_view,
    test_auth,
    logout_view,
    edit_appointment,
    my_profile,
    my_appointments,
    cancel_appointment,
    reschedule_appointment,
    admin_panel,
    ventas_rapidas,
    appointments_list,
    all_scheduled_appointments,
    scheduled_appointments_filtered
)

urlpatterns = [
    # LOGIN
    path('login/', custom_login_view, name='login'),
    path('api-login/', api_login_view, name='api_login'),
    path('users/me/', current_user_view, name='current_user'),

    # DASHBOARD
    path('salon-dashboard/', salon_dashboard, name='salon_dashboard'),

    # SERVICIOS
    path('services/', ServiceListView.as_view(), name='service-list'),
    path('services-admin/', ServiceListAdminView.as_view(), name='service-list-admin'),

    # CITAS
    path('create/', AppointmentCreateView.as_view(), name='appointment-create'),
    path('appointments/list/', AppointmentListView.as_view(), name='appointment-list'),
    path('appointments/admin-list/', AppointmentListAdminView.as_view(), name='appointment-list-admin'),
    path('appointments/detail/<int:id>/', AppointmentDetailAdminView.as_view(), name='appointment-detail-admin'),
    path('appointments/charge/<uuid:appointment_id>/', ChargeAppointmentView.as_view(), name='charge_appointments'),
    path("appointments-list/", appointments_list, name="appointments-list"),

    # PROMOCIONES
    path('promotion/', PromotionSettingsView.as_view(), name='promotion-settings'),

    # MANICURISTAS
    path('manicurists/', ManicuristListView.as_view(), name='manicurist-list'),
    path('appointments-by-manicurist/', appointments_by_manicurist, name='appointments-by-manicurist'),

    # DISPONIBILIDAD
    path('available-slots/', AvailableSlotsView.as_view(), name='available-slots'),
    path('available-slots/<uuid:employee_id>/', AvailableSlotsView.as_view(), name='available-slots-by-employee'),
    path('available/<uuid:employee_id>/', EmployeeAvailableSlotsView.as_view(), name='employee-available-slots'),
    path('available-view/', available_view, name='available-slots-page'),

    # INFO GENERAL
    path('about/', about_view, name='about'),

    path('api/test-auth/', test_auth),
    path('logout/', logout_view),
    path("<uuid:appointment_id>/edit/", edit_appointment, name="edit_appointment"),

    #Perfil
    path('profile/', my_profile, name='my_profile'),
    path('my/', my_appointments, name='my_appointment'),

    #cancelar cita
    path("cancel/<uuid:id>/", cancel_appointment),
    path("reschedule/<uuid:id>/", reschedule_appointment),

    path("admin-panel/", admin_panel, name="admin_panel"),
    path("ventas-rapidas/", ventas_rapidas, name="ventas_rapidas"),

    path("all-scheduled/", all_scheduled_appointments, name="all-scheduled"),
    path("scheduled-filtered/", scheduled_appointments_filtered, name="scheduled-filtered"),

]
