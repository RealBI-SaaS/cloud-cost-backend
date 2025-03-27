from django.urls import path

from .views import UserDetailView, google_oauth_callback

urlpatterns = [
    path(
        "google/oauth2/callback/",
        google_oauth_callback,
        name="google_oauth_callback",
    ),
    path("user/", UserDetailView.as_view(), name="user-detail"),
    # path("company/", views.CompanyMembershipView.as_view(), name="company_memberships"),
    # path("user/", views.get_user, name="fetch_user"),
    # path("create-user/", views.create_user, name='create_user'),
    # path("create-user/", views.RegisterView.as_view(), name="register"),
    # path("test-mail/", views.test_mail, name="test_mail"),
    # Email verification URLs
    # path(
    #     "verify-email/<str:uidb64>/<str:token>/",
    #     views.verify_email,
    #     name="verify-email",
    # ),
    # path(
    #     "resend-verification/",
    #     views.resend_verification_email,
    #     name="resend-verification",
    # ),
    # jwt urls
    # path("jwt/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    # path("jwt/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # path("jwt/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]
