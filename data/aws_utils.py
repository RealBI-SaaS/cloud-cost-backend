# aws_utils.py
import boto3
from botocore.config import Config


def assume_role(
    role_arn: str,
    external_id: str = None,
    session_name: str = "TenantSession",
    duration_seconds: int = 3600,
):
    sts = boto3.client("sts")
    assume_kwargs = {
        "RoleArn": role_arn,
        "RoleSessionName": session_name,
        "DurationSeconds": duration_seconds,
    }
    if external_id:
        assume_kwargs["ExternalId"] = external_id

    resp = sts.assume_role(**assume_kwargs)
    creds = resp["Credentials"]
    return {
        "aws_access_key_id": creds["AccessKeyId"],
        "aws_secret_access_key": creds["SecretAccessKey"],
        "aws_session_token": creds["SessionToken"],
        "expiration": creds["Expiration"],
    }


def get_costexplorer_client_from_role(role_arn, external_id=None, region="us-east-1"):
    creds = assume_role(role_arn, external_id=external_id)
    session = boto3.Session(
        aws_access_key_id=creds["aws_access_key_id"],
        aws_secret_access_key=creds["aws_secret_access_key"],
        aws_session_token=creds["aws_session_token"],
        region_name=region,
    )
    # Cost Explorer is global but boto3 expects a region; us-east-1 is safe
    return session.client("ce", config=Config(region_name=region)), creds
