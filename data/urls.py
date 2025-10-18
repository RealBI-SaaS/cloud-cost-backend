from django.urls import path
from rest_framework.routers import DefaultRouter

from .integration_views.aws import aws_register_role_view
from .integration_views.azure import (
    azure_oauth_callback_view,
    fetch_azure_billing_view,
    start_azure_auth_view,
)
from .integration_views.gcp import (
    fetch_google_projects_and_billing_view,
    google_oauth_callback_view,
    start_google_auth_view,
)
from .views import (
    CloudAccountViewSet,
    CustomExpenseVendorViewSet,
    CustomExpenseViewSet,
    ExportOrgnizationBillingCSV,
    billing_cost_by_region,
    billing_cost_by_service,
    billing_daily_costs,
    billing_monthly_service_total,
    billing_usage_service_day,
    cost_summary_by_account,
    cost_summary_by_orgs,
    cost_summary_by_service,
    refresh_billing_data,
)

router = DefaultRouter()
router.register(
    r"organizations/(?P<organization_id>[^/.]+)/cloud-accounts",
    CloudAccountViewSet,
    basename="organization-cloudaccounts",
)

router.register(
    r"organizations/(?P<organization_id>[^/.]+)/custom-expense-vendors",
    CustomExpenseVendorViewSet,
    basename="custom-expense-vendor",
)
router.register(
    r"organizations/(?P<organization_id>[^/.]+)/custom-expense",
    CustomExpenseViewSet,
    basename="custom-expense",
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
        "google/oauth/start/<uuid:organization_id>/<str:account_name>",
        start_google_auth_view,
        name="google_oauth_start",
    ),
    # azure
    path(
        "azure/oauth/start/<uuid:organization_id>/<str:account_name>",
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
    # path(
    #     "test",
    #     test,
    #     name="test",
    # ),
    path(
        "cost/daily/<uuid:organization_id>/",
        billing_daily_costs,
        name="billing_daily_costs",
    ),
    path(
        "cost/region/<uuid:organization_id>/",
        billing_cost_by_region,
        name="billing_cost_by_region",
    ),
    path(
        "usage/service-day/<uuid:organization_id>/",
        billing_usage_service_day,
        name="billing_cost_bay_service_day",
    ),
    path(
        "cost/service/<uuid:organization_id>/",
        billing_cost_by_service,
        name="billing_cost_by_service",
    ),
    path(
        "cost-summary/service/<uuid:organization_id>/",
        cost_summary_by_service,
        name="cost-summary-by-service",
    ),
    path(
        "cost-summary/account/<uuid:organization_id>/",
        cost_summary_by_account,
        name="cost-summary-by-account",
    ),
    path(
        "cost-summary/service-monthly/<uuid:organization_id>/",
        billing_monthly_service_total,
        name="cost-monthly-summary-by-service",
    ),
    path(
        "cost-summary/orgs/",
        cost_summary_by_orgs,
        name="cost-monthly-daily-summary-by-organization",
    ),
    # utils
    path(
        "manage/org/<uuid:organization_id>/refresh/",
        refresh_billing_data,
        name="refresh-billing-data",
    ),
    # exporter
    path(
        "org/<uuid:organization_id>/export-billing-csv/",
        ExportOrgnizationBillingCSV.as_view(),
        name="export-organization-billing-csv",
    ),
    *router.urls,
]
