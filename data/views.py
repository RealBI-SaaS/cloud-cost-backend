import os
import uuid
from datetime import timedelta

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from dotenv import load_dotenv
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from company.models import Organization
from company.permissions import IsOrgAdminOrOwnerOrReadOnly
from data.models import CustomExpense, CustomExpenseVendor
from data.serializers import CustomExpenseSerializer, CustomExpenseVendorSerializer

from .aggregators.account import get_account_totals
from .aggregators.cost import (
    get_cost_by_region,
    get_cost_by_service,
    get_cost_summary_by_service,
    get_daily_costs,
)
from .aggregators.usage import get_monthly_service_totals, get_usage_by_service_and_day
from .aggregators.utils import parse_date_range

# from .aws_utils import fetch_cost_and_usage, get_tenant_aws_client
from .integration_helpers.aws import (
    fetch_cost_and_usage,
    get_account_aws_client,
    save_billing_data_efficient,
)
from .models import BillingRecord, CloudAccount
from .serializers import (
    CloudAccountSerializer,
    CostByRegionSerializer,
    CostByServiceSerializer,
    CostSummaryByAccountSerializer,
    CostSummaryByOrgRequestSerializer,
    CostSummaryByOrgSerializer,
    CostSummaryByServiceSerializer,
    DailyCostSerializer,
    MonthlyServiceTotalsSerializer,
    UsageByServiceDaySerializer,
)
from .utils.get_org_from_request import get_organization

load_dotenv()

GOOGLE_DATA_CLIENT_ID = os.getenv("GOOGLE_DATA_CLIENT_ID")
GOOGLE_DATA_CLIENT_SECRET = os.getenv("GOOGLE_DATA_CLIENT_SECRET")


class CloudAccountViewSet(viewsets.ModelViewSet):
    serializer_class = CloudAccountSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgAdminOrOwnerOrReadOnly]
    http_method_names = ["get", "put", "patch", "delete"]

    def get_organization(self):
        return self.get_organization()

    def get_queryset(self):
        organization = self.get_organization()
        return CloudAccount.objects.filter(organization=organization)

    # dont use this method, create a specific account instead: AWS, GCP ...
    def perform_create(self, serializer):
        organization = self.get_organization()
        serializer.save(organization=organization)


class CustomExpenseVendorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomExpenseVendor.objects.all().order_by("name")
    serializer_class = CustomExpenseVendorSerializer
    permission_classes = [permissions.IsAuthenticated]


class CustomExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = CustomExpenseSerializer
    # permission_classes = [permissions.IsAuthenticated, IsOrgAdminOrOwnerOrReadOnly]

    def get_organization(self):
        return get_organization(self)

    def get_queryset(self):
        organization = self.get_organization()
        return CustomExpense.objects.filter(organization=organization)

    def perform_create(self, serializer):
        organization = self.get_organization()
        serializer.save(organization=organization)


@extend_schema(
    responses=DailyCostSerializer(many=True),
    description=(
        "Returns daily total costs for all cloud accounts in the given organization. "
        # "Optionally accepts `days`, `since`, and `until` query parameters."
    ),
    summary="Daily Costs",
)
@api_view(["GET"])
def billing_daily_costs(request, organization_id):
    start_date, end_date, error = parse_date_range(request)
    if error:
        return error

    data = get_daily_costs(
        organization_id,
        # cloud_account_id,
        start_date,
        end_date,
    )

    return Response({"range": {"start": start_date, "end": end_date}, "results": data})


@extend_schema(
    responses=CostByServiceSerializer(many=True),
    description="Returns total cost aggregated by service for all accounts in the given organization.",
    summary="Cost by Service",
)
@api_view(["GET"])
def billing_cost_by_service(request, organization_id):
    start_date, end_date, error = parse_date_range(request)
    if error:
        return error

    data = get_cost_by_service(organization_id, start_date, end_date)

    return Response({"range": {"start": start_date, "end": end_date}, "results": data})


@extend_schema(
    responses=CostByRegionSerializer(many=True),
    description="Returns total cost aggregated by region.",
    summary="Cost by Region",
)
@api_view(["GET"])
def billing_cost_by_region(request, organization_id):
    start_date, end_date, error = parse_date_range(request)
    if error:
        return error

    data = get_cost_by_region(organization_id, start_date, end_date)

    return Response({"range": {"start": start_date, "end": end_date}, "results": data})


@extend_schema(
    responses=UsageByServiceDaySerializer(many=True),
    description="Returns daily usage aggregated by service for all accounts in the given organization.",
    summary="Usage by Service & Day",
)
@api_view(["GET"])
def billing_usage_service_day(request, organization_id):
    start_date, end_date, error = parse_date_range(request)
    if error:
        return error

    data = get_usage_by_service_and_day(organization_id, start_date, end_date)

    return Response({"range": {"start": start_date, "end": end_date}, "results": data})


@extend_schema(
    responses=MonthlyServiceTotalsSerializer(many=True),
    description="Returns monthly usage and cost aggregated by service.",
    summary="Monthly Cost and Usage Service Totals",
)
@api_view(["GET"])
def billing_monthly_service_total(request, organization_id):
    start_date, end_date, error = parse_date_range(request)
    if error:
        return error

    data = get_monthly_service_totals(organization_id, start_date, end_date)

    return Response({"range": {"start": start_date, "end": end_date}, "results": data})


@extend_schema(
    responses=CostSummaryByServiceSerializer,
    description="Returns today's and last 30 days' costs, grouped by service.",
    summary="Service Cost Summary",
)
@api_view(["GET"])
def cost_summary_by_service(request, organization_id):
    start_date, end_date, error = parse_date_range(request)
    if error:
        return error

    data = get_cost_summary_by_service(organization_id, start_date, end_date)

    return Response({"range": {"start": start_date, "end": end_date}, "results": data})


@extend_schema(
    responses=CostSummaryByAccountSerializer,
    description=(
        "Returns total costs for today and for a given period (defaults to month-to-date) "
        "for a specific integrated account. Optionally accepts `days` or `since` query parameters."
    ),
    summary="Account Cost Summary",
)
@api_view(["GET"])
def cost_summary_by_account(request, organization_id):
    start_date, end_date, error = parse_date_range(request)
    if error:
        return error
    data = get_account_totals(organization_id, since=start_date, until=end_date)

    return Response(
        {
            "results": data,
            "range": {
                "start": start_date,
                "end": end_date,
            },
        }
    )


@extend_schema(
    request=CostSummaryByOrgRequestSerializer,
    responses=CostSummaryByOrgSerializer,
    description=(
        "Returns total costs for today and for the current month-to-date by default."
        "Pass integer `days` `n` to fetch only upto `n` days or `since` for a specific start date in YYYY-MM-DD format."
        "for all integrated accounts in MULTIPLE organizations -- Supports querying multiple organizations."
    ),
    summary="Organization Cost Summary",
)
@api_view(["POST"])
def cost_summary_by_orgs(request):
    """
    Expects JSON body:
    {
        "org_ids": ["uuid1", "uuid2", "uuid3"]
    }

    """
    start_date, end_date, error = parse_date_range(request)
    if error:
        return error

    org_ids = request.data.get("org_ids", [])
    if not isinstance(org_ids, list):
        raise ValidationError({"org_ids": "Must be a list of UUIDs."})
    res = {
        "range": {
            "start": start_date,
            "end": end_date,
        },
    }

    for org_id in org_ids:
        try:
            org_uuid = uuid.UUID(org_id)
        except ValueError:
            raise ValidationError({"org_id": f"Invalid UUID: {org_id}"})

        data = get_account_totals(org_uuid, since=start_date, until=end_date)

        res[org_id] = data

    return Response(res)


# refresh data, currently only aws
@extend_schema(
    description=(
        "Refresh an org's cloud integrations' data. Triggers a call to the CSPs - currently only AWS supported."
    ),
    summary="Organization data Refresher",
)
@api_view(["GET"])
def refresh_billing_data(request, organization_id):
    org = get_object_or_404(Organization, id=organization_id)
    cloud_accounts = list(CloudAccount.objects.filter(organization=org))

    # Check vendor type
    for cloud_account in cloud_accounts:
        if cloud_account.vendor.lower() != "aws":
            return JsonResponse(
                {"success": False, "message": "Cloud account is not AWS."}, status=400
            )

        # Determine start date = last usage_end + 1 day, or default 30 days ago
        last_record = (
            BillingRecord.objects.filter(cloud_account=cloud_account)
            .order_by("-usage_end")
            .first()
        )
        if last_record:
            start_date = last_record.usage_end.date() + timedelta(days=1)
        else:
            start_date = now().date() - timedelta(days=30)

        end_date = now().date()

        if start_date >= end_date:
            return JsonResponse(
                {"success": True, "message": "Data is already up to date."}, status=200
            )

        try:
            # Get AWS Cost Explorer client
            client = get_account_aws_client(cloud_account)

            # Fetch new cost & usage data
            cost_response = fetch_cost_and_usage(client, start_date, end_date)

            # Save new records
            save_billing_data_efficient(cloud_account, cost_response)

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Billing data refreshed from {start_date} to {end_date}.",
                },
                status=200,
            )

        except Exception as e:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Error refreshing billing data: {str(e)}",
                },
                status=500,
            )
