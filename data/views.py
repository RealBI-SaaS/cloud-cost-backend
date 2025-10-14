import os
import uuid
from datetime import timedelta

from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from dotenv import load_dotenv
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from company.models import Organization
from company.permissions import IsOrgAdminOrOwnerOrReadOnly

from .aggregators.account import get_account_totals
from .aggregators.cost import get_cost_by_region, get_cost_by_service, get_daily_costs
from .aggregators.usage import get_monthly_service_totals, get_usage_by_service_and_day
from .aggregators.utils import parse_date_range

# from .aws_utils import fetch_cost_and_usage, get_tenant_aws_client
from .integration_helpers.aws import (
    fetch_cost_and_usage,
    get_account_aws_client,
    save_billing_data_efficient,
)
from .metrics import cost_request_counter
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

load_dotenv()

GOOGLE_DATA_CLIENT_ID = os.getenv("GOOGLE_DATA_CLIENT_ID")
GOOGLE_DATA_CLIENT_SECRET = os.getenv("GOOGLE_DATA_CLIENT_SECRET")


class CloudAccountViewSet(viewsets.ModelViewSet):
    serializer_class = CloudAccountSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrgAdminOrOwnerOrReadOnly]
    http_method_names = ["get", "put", "patch", "delete"]

    def get_organization(self):
        """
        Retrieve the company from the request's query param or URL kwarg.
        """
        organization_id = self.kwargs.get(
            "organization_id"
        ) or self.request.query_params.get("organization_id")

        if not organization_id:
            raise ValidationError({"organization_id": "This field is required."})

        try:
            uuid.UUID(str(organization_id), version=4)
        except ValueError:
            raise ValidationError(
                {
                    "organization_id": "Invalid Organization ID format. Must be a valid UUID."
                }
            )

        try:
            return Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            raise NotFound({"organization_id": "Organization not found."})

    def get_queryset(self):
        organization = self.get_organization()
        return CloudAccount.objects.filter(organization=organization)

    # dont use this method, create a specific account instead: AWS, GCP ...
    def perform_create(self, serializer):
        organization = self.get_organization()
        serializer.save(organization=organization)


@extend_schema(
    responses=DailyCostSerializer(many=True),
    description=(
        "Returns daily total costs for the given Cloud Account. "
        # "Optionally accepts `days`, `since`, and `until` query parameters."
    ),
    summary="Daily Costs",
)
@api_view(["GET"])
def billing_daily_costs(request, cloud_account_id):
    start_date, end_date, error = parse_date_range(request)
    if error:
        return error

    data = get_daily_costs(
        cloud_account_id,
        start_date,
        end_date,
    )

    return Response({"range": {"start": start_date, "end": end_date}, "results": data})


@extend_schema(
    responses=CostByServiceSerializer(many=True),
    description="Returns total cost aggregated by service for the given Cloud Account.",
    summary="Cost by Service",
)
@api_view(["GET"])
def billing_cost_by_service(request, cloud_account_id):
    start_date, end_date, error = parse_date_range(request)
    if error:
        return error

    data = get_cost_by_service(cloud_account_id, start_date, end_date)

    return Response({"range": {"start": start_date, "end": end_date}, "results": data})


@extend_schema(
    responses=CostByRegionSerializer(many=True),
    description="Returns total cost aggregated by region.",
    summary="Cost by Region",
)
@api_view(["GET"])
def billing_cost_by_region(request, cloud_account_id):
    start_date, end_date, error = parse_date_range(request)
    if error:
        return error

    data = get_cost_by_region(cloud_account_id, start_date, end_date)

    return Response({"range": {"start": start_date, "end": end_date}, "results": data})


@extend_schema(
    responses=UsageByServiceDaySerializer(many=True),
    description="Returns daily usage aggregated by service for the given Cloud Account.",
    summary="Usage by Service & Day",
)
@api_view(["GET"])
def billing_usage_service_day(request, cloud_account_id):
    start_date, end_date, error = parse_date_range(request)
    if error:
        return error

    data = get_usage_by_service_and_day(cloud_account_id, start_date, end_date)

    return Response({"range": {"start": start_date, "end": end_date}, "results": data})


@extend_schema(
    responses=MonthlyServiceTotalsSerializer(many=True),
    description="Returns monthly usage and cost aggregated by service.",
    summary="Monthly Cost and Usage Service Totals",
)
@api_view(["GET"])
def billing_monthly_service_total(request, cloud_account_id):
    start_date, end_date, error = parse_date_range(request)
    if error:
        return error

    data = get_monthly_service_totals(cloud_account_id, start_date, end_date)

    return Response({"range": {"start": start_date, "end": end_date}, "results": data})


@extend_schema(
    responses=CostSummaryByServiceSerializer,
    description="Returns today's and last 30 days' costs, grouped by service.",
    summary="Service Cost Summary",
)
@api_view(["GET"])
def cost_summary_by_service(request, cloud_account_id):
    today = now().date()

    start_month = today.replace(day=1)
    # last_30_days = today - timedelta(days=30)

    qs = CloudAccount.objects.get(id=cloud_account_id).billing_records

    # today totals
    today_totals = (
        qs.filter(usage_start__date=today)
        .values("service_name")
        .annotate(total_cost=Sum("cost"))
    )

    # month totals
    month_totals = (
        qs.filter(usage_start__date__gte=start_month)
        .values("service_name")
        .annotate(total_cost=Sum("cost"))
    )

    cost_request_counter.labels(type="cost-summary-by-service").inc()

    return Response(
        {
            "results": {
                "today": {i["service_name"]: i["total_cost"] for i in today_totals},
                "this_month": {
                    i["service_name"]: i["total_cost"] for i in month_totals
                },
            }
        }
    )


@extend_schema(
    responses=CostSummaryByAccountSerializer,
    description=(
        "Returns total costs for today and for a given period (defaults to month-to-date) "
        "for a specific integrated account. Optionally accepts `days` or `since` query parameters."
    ),
    summary="Account Cost Summary",
)
@api_view(["GET"])
def cost_summary_by_account(request, cloud_account_id):
    """
    GET /cost-summary/account/<uuid:cloud_account_id>/?days=7
    GET /cost-summary/account/<uuid:cloud_account_id>/?since=2025-09-15
    """
    # Parse optional query params

    start_date, end_date, error = parse_date_range(request)
    if error:
        return error
    # days = request.query_params.get("days")
    # since = request.query_params.get("since")

    # Convert query params
    # if days is not None:
    #     try:
    #         days = int(days)
    #     except ValueError:
    #         return Response(
    #             {"error": "Invalid 'days' parameter, must be an integer."}, status=400
    #         )
    # elif since is not None:
    #     try:
    #         since = datetime.strptime(since, "%Y-%m-%d").date()
    #     except ValueError:
    #         return Response(
    #             {"error": "Invalid 'since' date format, use YYYY-MM-DD."}, status=400
    #         )
    #
    # Compute totals
    total_period, total_today = get_account_totals(
        cloud_account_id, since=start_date, until=end_date
    )
    # data = get_monthly_service_totals(
    #     [cloud_account_id],
    # since=start_date,
    # until=end_date,
    # )

    return Response(
        {
            "results": {
                "total_today": total_today,
                "total_period": total_period,
            },
            "range": {
                "start": start_date,
                "end": end_date,
            },
        }
    )


# NOTE: maybe kind of duplicate with the summary for cloud account, cost_summary_by_account
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

    GET /cost-summary/account/<uuid:cloud_account_id>/?days=7
    GET /cost-summary/account/<uuid:cloud_account_id>/?since=2025-09-15
    """
    start_date, end_date, error = parse_date_range(request)
    if error:
        return error
    # days = request.quer
    # Parse optional query params
    # days = request.query_params.get("days")
    # since = request.query_params.get("since")

    org_ids = request.data.get("org_ids", [])
    if not isinstance(org_ids, list):
        raise ValidationError({"org_ids": "Must be a list of UUIDs."})
    res = {}

    for org_id in org_ids:
        try:
            org_uuid = uuid.UUID(org_id)
        except ValueError:
            raise ValidationError({"org_id": f"Invalid UUID: {org_id}"})

        try:
            org = Organization.objects.get(pk=org_uuid)
        except Organization.DoesNotExist:
            raise ValidationError(
                {"organization_id": f"Invalid Organization {org_id} ID included."}
            )

        # Get all cloud accounts for this org
        # cloud_account_ids = org.cloud_accounts.values_list("id", flat=True)
        cloud_account_ids = list(
            CloudAccount.objects.filter(organization=org).values_list("id", flat=True)
        )

        total_period, total_today = get_account_totals(
            cloud_account_ids, since=start_date, until=end_date
        )
        # data = get_monthly_service_totals(
        #     cloud_account_ids,
        #     # since=start_date,
        #     # until=end_date,
        # )

        res[org_id] = {
            "results": {"total_today": total_today, "total_period": total_period},
            "range": {
                "start": start_date,
                "end": end_date,
            },
        }

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
