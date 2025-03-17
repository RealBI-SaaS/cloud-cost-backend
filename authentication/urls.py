from django.urls import path
from . import views


urlpatterns = [
    path('google/oauth2/callback/', views.google_oauth_callback, name='google_oauth_callback'),
]
