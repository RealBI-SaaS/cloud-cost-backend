from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)   

urlpatterns = [
    path('google/oauth2/callback/', views.google_oauth_callback, name='google_oauth_callback'),
    path("user/", views.get_user),

     # jwt urls 
    path('jwt/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('j/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

]


