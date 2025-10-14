from django.db.models import Sum
from django.utils.timezone import now

from ..models import BillingRecord  # adjust import path


def get_account_totals(cloud_account_ids, since, until):
    today = now().date()
    start_month = today.replace(day=1)

    if not isinstance(cloud_account_ids, (list, tuple)):
        cloud_account_ids = [cloud_account_ids]

    qs = BillingRecord.objects.filter(cloud_account_id__in=cloud_account_ids)

    # if since:
    #     start_date = since
    # elif days is not None:
    #     start_date = today - timedelta(days=days)
    # else:
    #     start_date = start_month

    total_today = (
        qs.filter(usage_start__date=today).aggregate(total=Sum("cost"))["total"] or 0
    )

    total_period = (
        qs.filter(usage_start__date__gte=since, usage_start__date__lte=until).aggregate(
            total=Sum("cost")
        )["total"]
        or 0
    )

    return total_period, total_today
