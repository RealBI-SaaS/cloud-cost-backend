from collections import defaultdict

from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce, TruncDay, TruncMonth

from ..models import BillingRecord  # adjust import path


# for ever?
def get_usage_by_service_and_day(cloud_account_id, since, until):
    queryset = (
        BillingRecord.objects.filter(
            cloud_account_id=cloud_account_id,
            usage_start__date__gte=since,
            usage_start__date__lte=until,
        )
        .annotate(day=TruncDay("usage_start"))
        .values("service_name", "day")
        .annotate(total_usage=Sum("usage_amount"))
        .order_by("day")
    )
    return list(queryset)


def get_monthly_service_totals(cloud_account_id, since, until):
    queryset = (
        BillingRecord.objects.filter(
            cloud_account_id=cloud_account_id,
            usage_start__date__gte=since,
            usage_start__date__lte=until,
        )
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

    grouped = defaultdict(list)
    for row in queryset:
        grouped[row["service_name"]].append(
            {
                "month": row["month"],
                "total_usage": float(row["total_usage"]),
                "total_cost": float(row["total_cost"]),
            }
        )

    return [{"service_name": k, "monthly": v} for k, v in grouped.items()]
