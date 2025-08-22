from django.urls import path

from .views import UserDetailView, google_oauth_callback

urlpatterns = [
    path(
        "google/oauth2/callback/",
        google_oauth_callback,
        name="google_oauth_callback",
    ),
    path("user/", UserDetailView.as_view(), name="user-detail"),
]
