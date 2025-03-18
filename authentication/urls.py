from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)   

urlpatterns = [
    path('google/oauth2/callback/', views.google_oauth_callback, name='google_oauth_callback'),
    path("user/", views.get_user, name='fetch_user'),
    # path("create-user/", views.create_user, name='create_user'),
    path('create-user/', views.RegisterView.as_view(), name='register'),

     # jwt urls 
    path('jwt/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('jwt/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('jwt/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

]


