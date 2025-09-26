import os
import uuid
from collections import defaultdict
from datetime import timedelta

from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce, TruncDay, TruncMonth
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

        # is_member = OrganizationMembership.objects.filter(
        #     user=self.request.user, organization=organization
        # ).exists()
        # if not is_member:
        #     raise PermissionDenied("You do not have access to this company.")

        return organization

    def get_queryset(self):
        organization = self.get_organization()
        return CloudAccount.objects.filter(organization=organization)

    # dont use this method, create a specific account instead: AWS, GCP ...
    def perform_create(self, serializer):
        organization = self.get_organization()
        serializer.save(organization=organization)


def get_daily_costs(cloud_account_id):
    queryset = (
        BillingRecord.objects.filter(cloud_account_id=cloud_account_id)
        .annotate(day=TruncDay("usage_start"))
        .values("day")
        .annotate(total_cost=Sum("cost"))
        .order_by("day")
    )
    # Convert queryset to list/dict for JSON serialization
    return list(queryset)


def get_cost_by_service(cloud_account_id):
    queryset = (
        BillingRecord.objects.filter(cloud_account_id=cloud_account_id)
        .values("service_name")
        .annotate(total_cost=Sum("cost"))
        .order_by("-total_cost")
    )
    return list(queryset)


def get_cost_by_region(cloud_account_id):
    queryset = (
        BillingRecord.objects.filter(cloud_account_id=cloud_account_id)
        .values("region")
        .annotate(total_cost=Sum("cost"))
        .order_by("-total_cost")
    )
    return list(queryset)


def get_usage_by_service_and_day(cloud_account_id):
    queryset = (
        BillingRecord.objects.filter(cloud_account_id=cloud_account_id)
        .annotate(day=TruncDay("usage_start"))
        .values("service_name", "day")
        .annotate(total_usage=Sum("usage_amount"))
        .order_by("day")
    )
    return list(queryset)


def get_account_totals(cloud_account_ids):
    """
    Accepts either:
    - a single cloud_account_id (int/UUID)
    - or a list of cloud_account_ids
    Returns: total_month, total_today
    """

    today = now().date()
    start_month = today.replace(day=1)

    # Normalize input to a list
    if not isinstance(cloud_account_ids, (list, tuple)):
        cloud_account_ids = [cloud_account_ids]

    # Get all BillingRecords for the accounts
    qs = BillingRecord.objects.filter(cloud_account_id__in=cloud_account_ids)

    # Total today
    total_today = (
        qs.filter(usage_start__date=today).aggregate(total=Sum("cost"))["total"] or 0
    )

    # Total this month (from first day of month to today)
    total_month = (
        qs.filter(usage_start__date__gte=start_month).aggregate(total=Sum("cost"))[
            "total"
        ]
        or 0
    )

    return total_month, total_today


def get_monthly_service_totals(cloud_account_id):
    queryset = (
        BillingRecord.objects.filter(cloud_account_id=cloud_account_id)
        .annotate(month=TruncMonth("usage_start"))
        .values("service_name", "month")
        .annotate(
            total_usage=Coalesce(
                Sum("usage_amount"), Value(0, output_field=DecimalField())
            ),
            total_cost=Coalesce(Sum("cost"), Value(0, output_field=DecimalField())),
        )
        .order_by("service_name", "month")
    )

    # Group months under each service
    grouped = defaultdict(list)
    for row in queryset:
        grouped[row["service_name"]].append(
            {
                "month": row["month"],
                "total_usage": float(row["total_usage"]),
                "total_cost": float(row["total_cost"]),
            }
        )

    result = [{"service_name": k, "monthly": v} for k, v in grouped.items()]
    return result


# TODO: add permissions.IsAuthenticated
@extend_schema(
    responses=DailyCostSerializer(many=True),
    description="Returns daily total costs for the given Cloud Account.",
    summary="Daily Costs",
)
@api_view(["GET"])
def billing_daily_costs(request, cloud_account_id):
    data = get_daily_costs(cloud_account_id)
    return Response(data)


@extend_schema(
    responses=CostByServiceSerializer(many=True),
    description="Returns total cost aggregated by service for the given Cloud Account.",
    summary="Cost by Service",
)
@api_view(["GET"])
def billing_cost_by_service(request, cloud_account_id):
    data = get_cost_by_service(cloud_account_id)
    return Response(data)


@extend_schema(
    responses=CostByRegionSerializer(many=True),
    description="Returns total cost aggregated by region.",
    summary="Cost by Region",
)
@api_view(["GET"])
def billing_cost_by_region(request, cloud_account_id):
    data = get_cost_by_region(cloud_account_id)
    return Response(data)


@extend_schema(
    responses=UsageByServiceDaySerializer(many=True),
    description="Returns daily usage aggregated by service for the given Cloud Account.",
    summary="Usage by Service & Day",
)
@api_view(["GET"])
def billing_cost_by_service_day(request, cloud_account_id):
    data = get_usage_by_service_and_day(cloud_account_id)
    return Response(data)


@extend_schema(
    responses=CostSummaryByServiceSerializer,
    description="Returns today's and this month's costs, grouped by service.",
    summary="Service Cost Summary",
)
@api_view(["GET"])
def cost_summary_by_service(request, cloud_account_id):
    today = now().date()

    start_month = today.replace(day=1)

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
            "today": {i["service_name"]: i["total_cost"] for i in today_totals},
            "this_month": {i["service_name"]: i["total_cost"] for i in month_totals},
        }
    )


@extend_schema(
    responses=CostSummaryByAccountSerializer,
    description="Returns total costs for today and for the current month for a specifc integrated account.",
    summary="Account Cost Summary",
)
@api_view(["GET"])
def cost_summary_by_account(request, cloud_account_id):
    # cloud_account = CloudAccount.objects.get(id=cloud_account_id)
    total_month, total_today = get_account_totals(cloud_account_id)

    cost_request_counter.labels(type="cost-summary-by-account").inc()

    return Response({"total_month": total_month, "total_today": total_today})


@extend_schema(
    request=CostSummaryByOrgRequestSerializer,
    responses=CostSummaryByOrgSerializer,
    description=(
        "Returns total costs for today and for the current month "
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

        total_month, total_today = get_account_totals(cloud_account_ids)

        res[org_id] = {
            "total_month": total_month,
            "total_today": total_today,
        }

    return Response(res)


@extend_schema(
    responses=MonthlyServiceTotalsSerializer(many=True),
    description="Returns monthly usage and cost aggregated by service.",
    summary="Monthly Service Totals",
)
@api_view(["GET"])
def billing_monthly_service_total(request, cloud_account_id):
    data = get_monthly_service_totals(cloud_account_id)
    cost_request_counter.labels(type="monthly-service-total").inc()
    return Response(data)


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
    # TODO: such optimization
    # cloud_accounts = list(
    #         CloudAccount.objects.filter(organization=org).values_list("id", "vendor")
    #     )
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
