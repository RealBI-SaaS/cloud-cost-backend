from django.urls import path
from rest_framework.routers import DefaultRouter

from data.azure_views import azure_oauth_callback_view

from .aws_views import aws_callback_view, aws_register_role_view
from .azure_views import (
    fetch_azure_billing_view,
    start_azure_auth_view,
)
from .google_views import (
    fetch_google_projects_and_billing_view,
    google_oauth_callback_view,
    start_google_auth_view,
)
from .views import CloudAccountViewSet

router = DefaultRouter()
router.register(
    r"companies/(?P<company_id>[^/.]+)/cloud-accounts",
    CloudAccountViewSet,
    basename="company-cloudaccounts",
)


urlpatterns = [
    # google
    path(
        "google/fetch/",
        fetch_google_projects_and_billing_view,
        name="google_data_fetch",
    ),
    path(
        "google/callback/",
        google_oauth_callback_view,
        name="google_oauth_callback",
    ),
    path(
        "google/auth/",
        start_google_auth_view,
        name="google_oauth_start",
    ),
    # azure
    path(
        "azure/oauth/start/<uuid:company_id>/",
        start_azure_auth_view,
        name="azure_oauth_start",
    ),
    path(
        "azure/oauth/callback/", azure_oauth_callback_view, name="azure_oauth_callback"
    ),
    # AWS
    # path("aws/start/<uuid:company_id>/", aws_start_auth_view, name="aws_start_auth"),
    path("aws/callback/", aws_callback_view, name="aws_callback"),
    path("aws/register-role/", aws_register_role_view, name="aws_add_role"),
    # path(
    #     "azure/oauth/start/<int:company_id>/",
    #     start_azure_auth_view,
    #     name="azure_oauth_start",
    # ),
    # path(
    #     "azure/oauth/callback/", azure_oauth_callback_view, name="azure_oauth_callback"
    # ),
    path(
        "azure/fetch/",
        fetch_azure_billing_view,
        name="azure_data_fetch",
    ),
    *router.urls,
]
