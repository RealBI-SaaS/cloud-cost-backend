# aws_views.py
import boto3
from botocore.exceptions import ClientError
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from organizations.models import Company

from .models import AWSRole, CloudAccount

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


def aws_callback_view(request):
    # In practice this might be a POST endpoint where tenant sends you their RoleArn + ExternalId
    role_arn = request.POST["role_arn"]
    external_id = request.POST["external_id"]
    company_id = request.POST["company_id"]
    print(role_arn, external_id, company_id)

    # company = Company.objects.get(id=company_id)
    # company.aws_role_arn = role_arn
    # company.aws_external_id = external_id
    # company.save()
    #
    return JsonResponse({"status": "AWS integration saved"})


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def aws_register_role_view(request):
#     # In practice this might be a POST endpoint where tenant sends you their RoleArn + ExternalId
#     # print(request.POST)
#     # print(request.data)
#     role_arn = request.data["role_arn"]
#     external_id = request.data["external_id"]
#     company_id = request.data["company_id"]
#     connection_name = request.data["name"]
#     print(role_arn, external_id, company_id, connection_name)
#     company = Company.objects.get(id=company_id)
#     cloud_account = CloudAccount.objects.create(
#         company=company,
#         vendor="AWS",
#         account_name=connection_name,  # name it later from API
#         account_id="temp",  # will update in fetch view
#     )
#     AWSRole.objects.create(
#         cloud_account=cloud_account, external_id=external_id, role_arn=role_arn
#     )
#
#     # company = Company.objects.get(id=company_id)
#     # company.aws_role_arn = role_arn
#     # company.aws_external_id = external_id
#     # company.save()
#     #
#     return JsonResponse({"status": "AWS integration saved"})


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

    return Response(
        {"message": "AWS Role registered successfully"}, status=status.HTTP_201_CREATED
    )


def get_tenant_aws_client(company, service="s3"):
    sts = boto3.client("sts")
    creds = sts.assume_role(
        RoleArn=company.aws_role_arn,
        RoleSessionName="TenantDataPull",
        ExternalId=company.aws_external_id,
    )["Credentials"]

    return boto3.client(
        service,
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )
