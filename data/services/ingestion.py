# Save raw data
from datetime import datetime
from decimal import Decimal

from data.models import BillingRecord

from .aggregation import update_billing_summary


def save_billing_records(cloud_account, raw_records):
    """Save raw billing data to the DB, avoid duplicates."""
    created_count = 0

    for item in raw_records:
        # Convert timestamps
        usage_start = datetime.fromisoformat(
            item["usage_start_time"].replace("Z", "+00:00")
        )
        usage_end = datetime.fromisoformat(
            item["usage_end_time"].replace("Z", "+00:00")
        )

        obj, created = BillingRecord.objects.update_or_create(
            cloud_account=cloud_account,
            usage_start=usage_start,
            usage_end=usage_end,
            service_name=item.get("service", ""),
            project_id=item.get("project"),
            region=item.get("region"),
            cost=Decimal(str(item.get("cost", 0))),
            defaults={
                "cost_type": item.get("cost_type", ""),
                "usage_amount": Decimal(str(item.get("usage_amount", 0)))
                if item.get("usage_amount")
                else None,
                "usage_unit": item.get("usage_unit"),
                "resource": item.get("resource_name"),
                "currency": item.get("currency", "USD"),
                "metadata": item,
            },
        )
        if created:
            created_count += 1

    return created_count


def ingest_billing_data(
    cloud_account, access_token, projects, start_date, end_date, get_billing_data_func
):
    """Main pipeline for ingestion."""
    total_created = 0

    for project in projects:
        project_id = project["projectId"]
        raw_records = get_billing_data_func(
            access_token, project_id, start_date, end_date
        )
        created_count = save_billing_records(cloud_account, raw_records)
        total_created += created_count

    # After all records are in, update summaries
    update_billing_summary(cloud_account, start_date, end_date)

    return total_created
