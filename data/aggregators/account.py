from django.db.models import Sum
from django.utils.timezone import now

from company.models import Organization
from data.models import BillingRecord, CloudAccount


def get_account_totals(organization_id, since, until):
    today = now().date()
    response = {}
    organization = Organization.objects.get(pk=organization_id)

    cloud_account_ids = list(
        CloudAccount.objects.filter(organization=organization).values_list(
            "id", flat=True
        )
    )
    for cloud_account_id in cloud_account_ids:
        qs = BillingRecord.objects.filter(cloud_account_id=cloud_account_id)

        total_today = (
            qs.filter(usage_start__date=today).aggregate(total=Sum("cost"))["total"]
            or 0
        )

        total_period = (
            qs.filter(
                usage_start__date__gte=since, usage_start__date__lte=until
            ).aggregate(total=Sum("cost"))["total"]
            or 0
        )
        response[str(cloud_account_id)] = {
            "currency": qs[0].currency if qs and qs[0].currency else "USD",
            "total_today": total_today,
            "total_period": total_period,
        }

    return response
