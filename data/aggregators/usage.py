from collections import defaultdict

from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce, TruncDay, TruncMonth

from company.models import Organization
from data.models import BillingRecord, CloudAccount


# for ever?
def get_usage_by_service_and_day(organization_id, since, until):
    response = {}
    organization = Organization.objects.get(pk=organization_id)

    cloud_account_ids = list(
        CloudAccount.objects.filter(organization=organization).values_list(
            "id", flat=True
        )
    )
    for cloud_account_id in cloud_account_ids:
        response[str(cloud_account_id)] = (
            list(
                BillingRecord.objects.filter(
                    cloud_account_id=cloud_account_id,
                    usage_start__date__gte=since,
                    usage_start__date__lte=until,
                )
                .annotate(day=TruncDay("usage_start"))
                .values("service_name", "day")
                .annotate(total_usage=Sum("usage_amount"))
                .order_by("day")
            ),
        )

    return response


def get_monthly_service_totals(organization_id, since, until):
    response = {}
    organization = Organization.objects.get(pk=organization_id)

    cloud_account_ids = list(
        CloudAccount.objects.filter(organization=organization).values_list(
            "id", flat=True
        )
    )
    for cloud_account_id in cloud_account_ids:
        queryset = (
            BillingRecord.objects.filter(
                cloud_account_id=cloud_account_id,
                usage_start__date__gte=since,
                usage_start__date__lte=until,
            )
            .annotate(month=TruncMonth("usage_start"))
            .values("service_name", "month", "currency")
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
                    "currency": row["currency"],
                    "month": row["month"],
                    "total_usage": float(row["total_usage"]),
                    "total_cost": float(row["total_cost"]),
                }
            )
        response[str(cloud_account_id)] = (
            [{"service_name": k, "monthly": v} for k, v in grouped.items()],
        )

    return response
