from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),  # done
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),  # done
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # done
    path('logout/', LogoutView.as_view(), name='logout'),  # done

    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),  # done
]
