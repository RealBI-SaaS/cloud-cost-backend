# Aggregate daily costs
from django.db.models import Sum
from django.db.models.functions import TruncDate

from data.models import BillingRecord, BillingSummary


def update_billing_summary(cloud_account, start_date, end_date):
    aggregates = (
        BillingRecord.objects.filter(
            cloud_account=cloud_account,
            usage_start__gte=start_date,
            usage_end__lte=end_date,
        )
        .values("service_name", date_field=TruncDate("usage_start"))
        .annotate(total_cost=Sum("cost"))
    )
    for row in aggregates:
        BillingSummary.objects.update_or_create(
            cloud_account=cloud_account,
            date=row["date_field"],
            service_category=row["service_name"],
            defaults={"total_cost": row["total_cost"], "currency": "USD"},
        )
