import os
import uuid
from collections import defaultdict

from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce, TruncDay, TruncMonth
from django.utils.timezone import now
from dotenv import load_dotenv
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from company.models import Company, CompanyMembership

from .models import (
    BillingRecord,
    CloudAccount,
    Company,
)
from .serializers import (
    CloudAccountSerializer,
)

# from .services.bigquery_client import fetch_billing_data_from_bq
# from .services.ingestion import ingest_billing_data

load_dotenv()

GOOGLE_DATA_CLIENT_ID = os.getenv("GOOGLE_DATA_CLIENT_ID")
GOOGLE_DATA_CLIENT_SECRET = os.getenv("GOOGLE_DATA_CLIENT_SECRET")


class CloudAccountViewSet(viewsets.ModelViewSet):
    serializer_class = CloudAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_company(self):
        """
        Retrieve the company from the request's query param or URL kwarg.
        """
        company_id = self.kwargs.get("company_id") or self.request.query_params.get(
            "company_id"
        )
        if not company_id:
            raise ValidationError({"company_id": "This field is required."})
        try:
            company_id_uuid = uuid.UUID(str(company_id), version=4)
        except ValueError:
            return Response(
                {"error": "Invalid company ID format. Must be a valid UUID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            raise ValidationError({"company_id": "Invalid company ID."})

        is_member = CompanyMembership.objects.filter(
            user=self.request.user, company=company
        ).exists()
        if not is_member:
            raise PermissionDenied("You do not have access to this company.")

        return company

    def get_queryset(self):
        company = self.get_company()
        return CloudAccount.objects.filter(company=company)

    def perform_create(self, serializer):
        company = self.get_company()
        serializer.save(company=company).save(company=user_company)


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


def get_account_totals(cloud_account_id):
    qs = CloudAccount.objects.get(id=cloud_account_id).billing_records
    # qs = BillingRecord.objects.filter(cloud_account=cloud_account_id)
    today = now().date()

    # FIX: only current month, no month setting
    start_month = today.replace(day=1)

    # First day of next month
    # if start_month.month == 12:
    #     next_month = start_month.replace(year=start_month.year + 1, month=1)
    # else:
    #     next_month = start_month.replace(month=start_month.month + 1)

    # total today
    total_today = (
        qs.filter(usage_start__date=today).aggregate(total=Sum("cost"))["total"] or 0
    )

    # total this month (from start_month inclusive to next_month exclusive)
    total_month = (
        qs.filter(usage_start__date__gte=start_month).aggregate(total=Sum("cost"))[
            "total"
        ]
        or 0
    )

    return total_month, total_today


# def get_monthly_service_totals(cloud_account_id):
#     queryset = (
#         BillingRecord.objects.filter(cloud_account_id=cloud_account_id)
#         .annotate(month=TruncMonth("usage_start"))
#         .values("service_name", "month")
#         .annotate(
#             total_usage=Sum("usage_amount"),
#             total_cost=Sum("cost"),
#         )
#         .order_by("month", "service_name")
#     )
#     return list(queryset)


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
@api_view(["GET"])
def billing_daily_costs(request, cloud_account_id):
    data = get_daily_costs(cloud_account_id)
    return Response(data)


@api_view(["GET"])
def billing_cost_by_service(request, cloud_account_id):
    data = get_cost_by_service(cloud_account_id)
    return Response(data)


@api_view(["GET"])
def billing_cost_by_region(request, cloud_account_id):
    data = get_cost_by_region(cloud_account_id)
    return Response(data)


@api_view(["GET"])
def billing_cost_by_service_day(request, cloud_account_id):
    data = get_usage_by_service_and_day(cloud_account_id)
    return Response(data)


@api_view(["GET"])
def cost_summary_by_service(request, cloud_account_id):
    today = now().date()

    # FIX: only current month, no month setting
    start_month = today.replace(day=1)

    qs = CloudAccount.objects.get(id=cloud_account_id).billing_records
    # print(qs, start_month)

    # qs = qs.billing_records
    #
    # print(qs)
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

    return Response(
        {
            "today": {i["service_name"]: i["total_cost"] for i in today_totals},
            "this_month": {i["service_name"]: i["total_cost"] for i in month_totals},
        }
    )


@api_view(["GET"])
def cost_summary_by_account(request, cloud_account_id):
    # cloud_account = CloudAccount.objects.get(id=cloud_account_id)
    total_month, total_today = get_account_totals(cloud_account_id)

    return Response({"total_month": total_month, "total_today": total_today})


@api_view(["GET"])
def billing_monthly_service_total(request, cloud_account_id):
    data = get_monthly_service_totals(cloud_account_id)
    return Response(data)
