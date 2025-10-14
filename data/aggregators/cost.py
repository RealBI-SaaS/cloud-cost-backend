from django.db.models import Sum
from django.db.models.functions import TruncDay

# from datetime import timedelta
# from .utils import parse_date_range
from ..models import BillingRecord  # adjust import path if needed


def get_cost_by_service(cloud_account_id, since, until):
    return list(
        BillingRecord.objects.filter(
            cloud_account_id=cloud_account_id,
            usage_start__date__gte=since,
            usage_start__date__lte=until,
        )
        .values("service_name")
        .annotate(total_cost=Sum("cost"))
        .order_by("-total_cost")
    )


def get_cost_by_region(cloud_account_id, since, until):
    return list(
        BillingRecord.objects.filter(
            cloud_account_id=cloud_account_id,
            usage_start__date__gte=since,
            usage_start__date__lte=until,
        )
        .values("region")
        .annotate(total_cost=Sum("cost"))
        .order_by("-total_cost")
    )


def get_daily_costs(cloud_account_id, since, until):
    return list(
        BillingRecord.objects.filter(
            cloud_account_id=cloud_account_id,
            usage_start__date__gte=since,
            usage_start__date__lte=until,
        )
        .annotate(day=TruncDay("usage_start"))
        .values("day")
        .annotate(total_cost=Sum("cost"))
        .order_by("day")
    )
