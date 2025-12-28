from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    
)

from .views import (
    RegisterView, 
    UserListView, 
    UserProfileView, 
    PromotionStatusView, 
    register_page,
    CustomPasswordResetCompleteView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetDoneView,
    CustomPasswordResetView,
    debug_auth, 
    TokenInspectView,
    user_list,
    user_edit,
    user_delete
)

urlpatterns = [
    path('', user_list, name='user-list-html'),


    path('register/', RegisterView.as_view(), name='user-register'),
    path('list/', UserListView.as_view(), name='user-list'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('promotions/', PromotionStatusView.as_view(), name='promotion-status'),

    #vista administrador
    
    path('edit/<int:pk>/', user_edit, name='user-edit'),
    path('delete/<int:pk>/', user_delete, name='user-delete'),

    # 🔑 Endpoints JWT
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('register-form/', register_page, name='register-form'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("debug-auth/", debug_auth),

    #recuperación de contraseña
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    #debug
    path("token-inspect/", TokenInspectView.as_view()),
]

