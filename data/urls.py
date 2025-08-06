from django.urls import path

from .views import google_oauth_get_token

urlpatterns = [
    path(
        "google/callback/",
        google_oauth_get_token,
        name="google_oauth_callback",
    ),
    # path(
    #     "google/get-data/",
    #     google_get_data,
    #     name="google_oauth_callback",
    # ),
]
