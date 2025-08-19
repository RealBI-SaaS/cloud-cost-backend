from django.urls import path
from rest_framework.routers import DefaultRouter

from data.azure_views import azure_oauth_callback_view

from .aws_views import aws_register_role_view, test
from .azure_views import (
    fetch_azure_billing_view,
    start_azure_auth_view,
)
from .google_views import (
    fetch_google_projects_and_billing_view,
    google_oauth_callback_view,
    start_google_auth_view,
)
from .views import (
    CloudAccountViewSet,
    billing_cost_by_region,
    billing_cost_by_service,
    billing_cost_by_service_day,
    billing_daily_costs,
    billing_monthly_service_total,
    cost_summary_by_account,
    cost_summary_by_service,
)

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
        "google/oauth/start/<uuid:company_id>/<str:account_name>",
        start_google_auth_view,
        name="google_oauth_start",
    ),
    # azure
    path(
        "azure/oauth/start/<uuid:company_id>/<str:account_name>",
        start_azure_auth_view,
        name="azure_oauth_start",
    ),
    path(
        "azure/oauth/callback/", azure_oauth_callback_view, name="azure_oauth_callback"
    ),
    # AWS
    # path("aws/callback/", aws_callback_view, name="aws_callback"),
    path("aws/register-role/", aws_register_role_view, name="aws_add_role"),
    path(
        "azure/fetch/",
        fetch_azure_billing_view,
        name="azure_data_fetch",
    ),
    path(
        "test",
        test,
        name="test",
    ),
    path(
        "cost/daily/<uuid:cloud_account_id>/",
        billing_daily_costs,
        name="billing_daily_costs",
    ),
    path(
        "cost/region/<uuid:cloud_account_id>/",
        billing_cost_by_region,
        name="billing_cost_by_region",
    ),
    path(
        "cost/service-day/<uuid:cloud_account_id>/",
        billing_cost_by_service_day,
        name="billing_cost_bay_service_day",
    ),
    path(
        "cost/service/<uuid:cloud_account_id>/",
        billing_cost_by_service,
        name="billing_cost_by_service",
    ),
    path(
        "cost-summary/service/<uuid:cloud_account_id>/",
        cost_summary_by_service,
        name="cost-summary-by-service",
    ),
    path(
        "cost-summary/account/<uuid:cloud_account_id>/",
        cost_summary_by_account,
        name="cost-summary-by-account",
    ),
    path(
        "cost-summary/monthly-service/<uuid:cloud_account_id>/",
        billing_monthly_service_total,
        name="cost-monthly-summary-by-service",
    ),
    *router.urls,
]
