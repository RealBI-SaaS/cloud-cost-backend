from django.urls import path

from .views.oauth import google_oauth_callback
from .views.passwordless import (
    MagicLinkRequestView,
    MagicLinkVerifyView,
    OTPRequestView,
    OTPVerifyView,
)
from .views.user import UserDetailView

urlpatterns = [
    path(
        "google/oauth2/callback/",
        google_oauth_callback,
        name="google_oauth_callback",
    ),
    path("user/", UserDetailView.as_view(), name="user-detail"),
    # magic links
    path(
        "passwordless/magic-link/request/",
        MagicLinkRequestView.as_view(),
        name="magic-link-request",
    ),
    path(
        "passwordless/magic-link/verify/",
        MagicLinkVerifyView.as_view(),
        name="magic-link-verify",
    ),
    # otc
    path("passwordless/otp/request/", OTPRequestView.as_view(), name="otp-request"),
    path("passwordless/otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),
]
