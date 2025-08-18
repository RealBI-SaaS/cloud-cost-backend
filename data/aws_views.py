# aws_views.py

import boto3
from botocore.exceptions import ClientError
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from company.models import Company

from .models import AWSRole, BillingRecord, CloudAccount

#
# def aws_start_auth_view(request, company_id):
#     # In AWS there's no redirect flow like OAuth — you send instructions
#     company = Company.objects.get(id=company_id)
#     return JsonResponse(
#         {
#             "instructions": "Create an IAM Role in your AWS account that trusts our AWS account ID: 111111111111. Use ExternalId: XYZ123",
#             "arn_format": "arn:aws:iam::<YOUR_ACCOUNT_ID>:role/<RoleName>",
#         }
#     )


# def aws_callback_view(request):
#     # In practice this might be a POST endpoint where tenant sends you their RoleArn + ExternalId
#     role_arn = request.POST["role_arn"]
#     external_id = request.POST["external_id"]
#     company_id = request.POST["company_id"]
#     print(role_arn, external_id, company_id)
#
# company = Company.objects.get(id=company_id)
# company.aws_role_arn = role_arn
# company.aws_external_id = external_id
# company.save()
#
# return JsonResponse({"status": "AWS integration saved"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def aws_register_role_view(request):
    role_arn = request.data["role_arn"]
    external_id = request.data["external_id"]
    company_id = request.data["company_id"]
    connection_name = request.data["name"]

    # Step 1: Validate AWS credentials before saving
    if len(role_arn) < 20 or not role_arn.startswith("arn:aws:iam::"):
        return Response(
            {"error": "RoleArn looks invalid"}, status=status.HTTP_400_BAD_REQUEST
        )
    sts_client = boto3.client("sts", region_name="us-east-1")  # Region can be changed
    try:
        sts_client.assume_role(
            RoleArn=role_arn, RoleSessionName="TestSession", ExternalId=external_id
        )
    except ClientError as e:
        return Response(
            {"error": f"Invalid AWS credentials: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Step 2: Only save if credentials are valid
    company = Company.objects.get(id=company_id)
    cloud_account = CloudAccount.objects.create(
        company=company,
        vendor="AWS",
        account_name=connection_name,
        account_id="temp",
    )
    AWSRole.objects.create(
        cloud_account=cloud_account, external_id=external_id, role_arn=role_arn
    )

    # TODO:test here and fetch/ingest data later
    ingest_aws_billing(cloud_account, "2025-04-01", "2025-06-01")

    return Response(
        {"message": "AWS Role registered successfully"}, status=status.HTTP_201_CREATED
    )


@api_view(["get"])
def test(request):
    ca = CloudAccount.objects.get(id="5674bae8-74e4-46b8-820e-d23f9102892b")

    # generate_billing_summaries(ca)

    # ingest_aws_billing(ca, "2025-04-01", "2025-06-01")


def get_tenant_aws_client(cloud_account):
    sts = boto3.client("sts")
    role_vals = cloud_account.aws_role_values
    creds = sts.assume_role(
        RoleArn=role_vals.role_arn,
        RoleSessionName="TenantDataPull",
        ExternalId=role_vals.external_id,
    )["Credentials"]

    return boto3.client(
        "ce",
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )


def fetch_cost_and_usage(client, start_date, end_date):
    response = client.get_cost_and_usage(
        TimePeriod={"Start": start_date, "End": end_date},
        Granularity="DAILY",  # or MONTHLY
        Metrics=["UnblendedCost", "UsageQuantity"],
        GroupBy=[
            {"Type": "DIMENSION", "Key": "SERVICE"},
            {"Type": "DIMENSION", "Key": "USAGE_TYPE"},
        ],
    )
    return response


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
    company = cloud_account.company
    client = get_tenant_aws_client(cloud_account)
    response = fetch_cost_and_usage(client, start_date, end_date)
    save_billing_data_efficient(cloud_account, response)
