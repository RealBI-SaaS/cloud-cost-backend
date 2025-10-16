from django.db.models import Sum
from django.db.models.functions import TruncDay
from django.utils.timezone import now

from company.models import Organization
from data.models import CloudAccount

# from datetime import timedelta
# from .utils import parse_date_range
from ..models import BillingRecord  # adjust import path if needed


def get_cost_by_service(organization_id, since, until):
    response = {}
    organization = Organization.objects.get(pk=organization_id)

    cloud_account_ids = list(
        CloudAccount.objects.filter(organization=organization).values_list(
            "id", flat=True
        )
    )
    for cloud_account_id in cloud_account_ids:
        response[str(cloud_account_id)] = list(
            BillingRecord.objects.filter(
                cloud_account_id=cloud_account_id,
                usage_start__date__gte=since,
                usage_start__date__lte=until,
            )
            .values("currency", "service_name")
            .annotate(total_cost=Sum("cost"))
            .order_by("-total_cost")
        )
    return response


def get_cost_by_region(organization_id, since, until):
    response = {}
    organization = Organization.objects.get(pk=organization_id)

    cloud_account_ids = list(
        CloudAccount.objects.filter(organization=organization).values_list(
            "id", flat=True
        )
    )
    for cloud_account_id in cloud_account_ids:
        response[str(cloud_account_id)] = list(
            BillingRecord.objects.filter(
                cloud_account_id=cloud_account_id,
                usage_start__date__gte=since,
                usage_start__date__lte=until,
            )
            .values("currency", "region")
            .annotate(total_cost=Sum("cost"))
            .order_by("-total_cost")
        )

    return response


def get_daily_costs(organization_id, since, until):
    response = {}
    organization = Organization.objects.get(pk=organization_id)

    cloud_account_ids = list(
        CloudAccount.objects.filter(organization=organization).values_list(
            "id", flat=True
        )
    )
    for cloud_account_id in cloud_account_ids:
        response[str(cloud_account_id)] = list(
            BillingRecord.objects.filter(
                cloud_account_id=cloud_account_id,
                usage_start__date__gte=since,
                usage_start__date__lte=until,
            )
            .annotate(day=TruncDay("usage_start"))
            .values("currency", "day")
            .annotate(total_cost=Sum("cost"))
            .order_by("day")
        )
    return response


def get_cost_summary_by_service(organization_id, since, until):
    response = {}
    organization = Organization.objects.get(pk=organization_id)

    cloud_account_ids = list(
        CloudAccount.objects.filter(organization=organization).values_list(
            "id", flat=True
        )
    )

    today = now().date()

    for cloud_account_id in cloud_account_ids:
        qs = CloudAccount.objects.get(id=cloud_account_id).billing_records

        today_total = (
            qs.filter(usage_start__date=today)
            .values("service_name")
            .annotate(total_cost=Sum("cost"))
        )

        period_total = (
            qs.filter(usage_start__date__gte=since, usage_start__date__lte=until)
            .values("currency", "service_name")
            .annotate(total_cost=Sum("cost"))
        )

        response[str(cloud_account_id)] = {
            "total_today": today_total,
            "total_period": period_total,
        }
    return response
