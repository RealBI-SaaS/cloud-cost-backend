import boto3
from botocore.exceptions import ClientError
from django.db import transaction
from django.http import JsonResponse

from ..models import BillingRecord
from ..utils.sanitize_cur_report_name import sanitize_report_name


def get_account_aws_client(
    cloud_account, client_type="ce", role_session_name="TenantDataPull"
):
    # TODO: look into this val
    sts = boto3.client("sts")
    role_vals = cloud_account.aws_role_values
    creds = sts.assume_role(
        RoleArn=role_vals.role_arn,
        RoleSessionName=role_session_name,
        ExternalId=role_vals.external_id,
    )["Credentials"]

    return boto3.client(
        client_type,
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )


def test_aws_access(cloud_account):
    """
    Check if the given cloud_account has access to Cost Explorer (ce)
    and Cost & Usage Reports (cur).
    """
    results = {"ce": False, "cur": False}

    # --- Cost Explorer ---
    try:
        ce = get_account_aws_client(cloud_account, client_type="ce")
        ce.get_cost_and_usage(
            TimePeriod={"Start": "2023-01-01", "End": "2023-01-02"},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
        )
        results["ce"] = True
    except ClientError as e:
        if e.response["Error"]["Code"] != "AccessDeniedException":
            raise

    # --- CUR ---
    try:
        cur = get_account_aws_client(cloud_account, client_type="cur")
        cur.describe_report_definitions()
        results["cur"] = True
    except ClientError as e:
        if e.response["Error"]["Code"] != "AccessDeniedException":
            raise

    print(results)
    return results


def fetch_cost_and_usage(client, start_date, end_date):
    results = []
    next_token = None

    while True:
        kwargs = {
            "TimePeriod": {
                "Start": start_date.strftime("%Y-%m-%d"),
                "End": end_date.strftime("%Y-%m-%d"),
            },
            "Granularity": "DAILY",
            "Metrics": ["UnblendedCost", "UsageQuantity"],
            "GroupBy": [
                {"Type": "DIMENSION", "Key": "SERVICE"},
                {"Type": "DIMENSION", "Key": "USAGE_TYPE"},
            ],
        }
        if next_token:
            kwargs["NextPageToken"] = next_token

        response = client.get_cost_and_usage(**kwargs)
        results.extend(response.get("ResultsByTime", []))

        next_token = response.get("NextPageToken")
        if not next_token:
            break

    return {"ResultsByTime": results}


def create_cur_report(cur_client, cloud_account, bucket_name):
    prefix = str(cloud_account.id)
    report_name = sanitize_report_name(cloud_account.account_name)

    try:
        # 3. Create CUR report
        response = cur_client.put_report_definition(
            ReportDefinition={
                "ReportName": report_name,
                "TimeUnit": "DAILY",
                "Format": "textORcsv",  # CSV
                "Compression": "ZIP",  # ZIP or GZIP only
                "AdditionalSchemaElements": ["RESOURCES"],
                "S3Bucket": bucket_name,
                "S3Prefix": prefix,
                "S3Region": "us-west-2",  # must match your bucket region
                "RefreshClosedReports": True,
                "ReportVersioning": "CREATE_NEW_REPORT",
            }
        )
        # If no exception, AWS accepted the request
        result = {
            "status": "success",
            "message": f"CUR report '{report_name}' created in s3://{bucket_name}/{prefix}/",
            "aws_response": response,
        }
        print(result)
        return JsonResponse(result)

    except ClientError as e:
        result = {
            "status": "error",
            "error_code": e.response["Error"]["Code"],
            "error_message": e.response["Error"]["Message"],
            "request_id": e.response["ResponseMetadata"]["RequestId"],
        }

        print(result)

        return JsonResponse(result)


# def create_focus_export(client, account_id, bucket_name):
#     # client = boto3.client("billing")
#
#     try:
#         response = client.create_export(
#             Name=f"focus-{account_id}",
#             DataQuery={
#                 "Table": "focus-1.0",
#                 "Fields": [
#                     "bill_billing_entity",
#                     "line_item_usage_amount",
#                     "product_product_name",
#                 ],  # choose columns
#             },
#             DestinationConfiguration={
#                 "S3Destination": {
#                     "Bucket": bucket_name,
#                     "Prefix": f"focus/{account_id}",
#                     "Region": "us-west-2",
#                 }
#             },
#             RefreshCadence="DAILY",
#         )
#
#         return {
#             "status": "success",
#             "message": "FOCUS export created successfully",
#             "aws_response": response,
#         }
#
#     except ClientError as e:
#         return {
#             "status": "error",
#             "error_code": e.response["Error"]["Code"],
#             "error_message": e.response["Error"]["Message"],
#             "request_id": e.response["ResponseMetadata"]["RequestId"],
#         }


def create_focus_export(client, account_id, bucket_name, region="us-west-2"):
    # client = boto3.client("bcm-data-exports")  # correct service name

    try:
        response = client.create_export(
            Export={
                "Name": f"focus_{account_id}",
                "Description": f"FOCUS 1.0 export for account {account_id}",
                "DataQuery": {
                    "QueryStatement": "SELECT * FROM focus_v1",  # or a more precise SQL
                    "TableConfigurations": {
                        "FOCUS_1_0": {
                            # optional table property overrides (if supported)
                        }
                    },
                },
                "DestinationConfigurations": {
                    "S3Destination": {
                        "S3Bucket": bucket_name,
                        "S3Prefix": f"focus/{account_id}",
                        "S3Region": region,
                        "S3OutputConfigurations": {
                            "Format": "TEXT_OR_CSV",
                            "Compression": "GZIP",
                            "OutputType": "CUSTOM",
                            "Overwrite": "CREATE_NEW_REPORT",
                        },
                    }
                },
                "RefreshCadence": {"Frequency": "SYNCHRONOUS"},
            }
        )
        return {"status": "success", "aws_response": response.body}
    except ClientError as e:
        return {
            "status": "error",
            "error_code": e.response["Error"]["Code"],
            "error_message": e.response["Error"]["Message"],
            "request_id": e.response["ResponseMetadata"].get("RequestId"),
        }


def save_billing_data(cloud_account, cost_response):
    for result_by_time in cost_response.get("ResultsByTime", []):
        usage_start = result_by_time["TimePeriod"]["Start"]
        usage_end = result_by_time["TimePeriod"]["End"]

        for group in result_by_time.get("Groups", []):
            service_name = None
            usage_type = None

            # Extract keys: example ["Amazon Elastic Compute Cloud - Compute", "BoxUsage"]
            keys = group.get("Keys", [])
            if len(keys) >= 1:
                service_name = keys[0]
            if len(keys) >= 2:
                usage_type = keys[1]

            cost_amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            usage_amount = float(
                group["Metrics"].get("UsageQuantity", {}).get("Amount", 0)
            )

            # Save to BillingRecord
            BillingRecord.objects.create(
                cloud_account=cloud_account,
                usage_start=usage_start,
                usage_end=usage_end,
                service_name=service_name or "",
                cost_type=usage_type,
                usage_amount=usage_amount,
                usage_unit=None,  # AWS doesn’t always provide unit in this API response
                cost=cost_amount,
                currency="USD",  # Cost Explorer reports USD by default
            )

        # generate_billing_summaries(cloud_account)


def upsert_billing_record(data):
    """
    data: dict with all BillingRecord fields
    """

    defaults = {
        "cost": data["cost"],
        "currency": data.get("currency", "USD"),
        "usage_amount": data.get("usage_amount"),
        "usage_unit": data.get("usage_unit"),
        "metadata": data.get("metadata"),
    }

    obj, created = BillingRecord.objects.update_or_create(
        cloud_account=data["cloud_account"],
        usage_start=data["usage_start"],
        usage_end=data["usage_end"],
        service_name=data["service_name"],
        cost_type=data.get("cost_type"),
        resource=data.get("resource"),
        defaults=defaults,
    )
    return obj, created


def save_billing_data_efficient(cloud_account, cost_response):
    with transaction.atomic():
        for result_by_time in cost_response.get("ResultsByTime", []):
            usage_start = result_by_time["TimePeriod"]["Start"]
            usage_end = result_by_time["TimePeriod"]["End"]

            for group in result_by_time.get("Groups", []):
                keys = group.get("Keys", [])
                service_name = keys[0] if len(keys) > 0 else ""
                cost_type = keys[1] if len(keys) > 1 else None

                cost_amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                usage_amount = float(
                    group["Metrics"].get("UsageQuantity", {}).get("Amount", 0)
                )

                if cost_amount <= 0 and usage_amount <= 0:
                    continue  # skip zero cost & usage

                data = {
                    "cloud_account": cloud_account,
                    "usage_start": usage_start,
                    "usage_end": usage_end,
                    "service_name": service_name,
                    "cost_type": cost_type,
                    "usage_amount": usage_amount,
                    "usage_unit": None,
                    "cost": cost_amount,
                    "currency": "USD",
                    "resource": None,
                    "metadata": None,
                }
                upsert_billing_record(data)


def ingest_aws_billing(cloud_account, start_date, end_date):
    # Organization = cloud_account.organization
    client = get_account_aws_client(cloud_account, "ce", "TenantDataPull")
    response = fetch_cost_and_usage(client, start_date, end_date)
    save_billing_data_efficient(cloud_account, response)
