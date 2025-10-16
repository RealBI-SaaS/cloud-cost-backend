# aws_views.py

import boto3
from botocore.exceptions import ClientError
from django.utils.timezone import now
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from company.models import Organization

from ..integration_helpers.aws import (
    create_cur_report,
    create_focus_export,
    get_account_aws_client,
    ingest_aws_billing,
)

# from .aws_utils import fetch_cost_and_usage, get_tenant_aws_client, save_billing_data
from ..models import AWSRole, CloudAccount

# boto3.set_stream_logger("botocore", level=logging.DEBUG)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def aws_register_role_view(request):
    role_arn = request.data["role_arn"]
    external_id = request.data["external_id"]
    organization_id = request.data["organization_id"]
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
    organization = Organization.objects.get(id=organization_id)
    cloud_account = CloudAccount.objects.create(
        organization=organization,
        vendor="AWS",
        account_name=connection_name,
        # FIX: use something else
        account_id=external_id,
    )
    AWSRole.objects.create(
        cloud_account=cloud_account, external_id=external_id, role_arn=role_arn
    )

    client = get_account_aws_client(cloud_account, "cur", "SetupCUR")
    today = now().date()

    january = today.replace(month=1, day=1)
    # TODO: make these two processes run async after response (use the connection testing helper )
    ingest_aws_billing(cloud_account, january, today)
    create_cur_report(
        client,
        cloud_account,
        "numlock-public-bucket-1",
    )
    # TODO:test here and fetch/ingest data later
    # ingest_aws_billing(cloud_account, "2025-04-01", "2025-06-01")

    return Response(
        {"message": "AWS Role registered successfully"}, status=status.HTTP_201_CREATED
    )


@api_view(["get"])
def test(request):
    ca = CloudAccount.objects.get(id="f65f4b29-912b-4706-8246-6c3c45505432")

    # res = create_cur_report(
    #     "arn:aws:iam::767397678516:role/NumlockBillingAccessRolecur",
    #     "ext-3f3c3d9f-4963-40a0-a7f7-2701154fa669",
    #     "test_cur_self",
    #     "numlock-public-bucket-1",
    #     "test_folder_1",
    # )

    client = get_account_aws_client(ca, "bcm-data-exports", "SetupCURFocus")
    res = create_focus_export(
        client,
        "f65f4b29-912b-4706-8246-6c3c45505432",
        "numlock-public-bucket-1",
    )

    print(res)
    return Response({"message": "test ran, check logs"}, status=status.HTTP_201_CREATED)

    # generate_billing_summaries(ca)

    # ingest_aws_billing(ca, "2025-04-01", "2025-06-01")
