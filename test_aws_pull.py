import json
from datetime import date

import boto3

# Alternative: Use the existing utility function
# from data.aws_utils import get_costexplorer_client_from_role


def main():
    # --- ASSUME ROLE ---
    sts = boto3.client("sts")
    creds = sts.assume_role(
        RoleArn="arn:aws:iam::430118811292:role/NumlockBillingAccessRoletestdemo",
        RoleSessionName="TenantDataPull",
        ExternalId="ext-14d0b4f4-1680-4999-ac98-31b4863e4875",
    )["Credentials"]
    print(creds)

    # --- CREATE SESSION WITH TEMP CREDENTIALS ---
    session = boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )

    # --- CREATE COST EXPLORER CLIENT FROM SESSION ---
    client = session.client("ce")

    # Alternative approach using existing utility:
    # client, creds = get_costexplorer_client_from_role(
    #     "arn:aws:iam::767397678516:role/NumlockBillingAccessRoledemo",
    #     external_id="ext-834dfa0a-fdf0-4188-83a0-aaeb307b378d"
    # )

    # --- DEFINE TIME RANGE ---
    today = date.today()
    january = today.replace(month=1, day=1)
    start_date = january.strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    granularity = "DAILY"
    metrics = ["BlendedCost", "UsageQuantity"]
    group_by = [
        {"Type": "DIMENSION", "Key": "SERVICE"},
        {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"},
    ]

    # --- CALL AWS COST EXPLORER ---
    response = client.get_cost_and_usage(
        TimePeriod={"Start": start_date, "End": end_date},
        Granularity=granularity,
        Metrics=metrics,
        GroupBy=group_by,
    )

    # --- PREPARE DEBUG INFO ---
    debug_data = {
        "start_date": start_date,
        "end_date": end_date,
        "granularity": granularity,
        "metrics": metrics,
        "group_by": group_by,
        "response": response,
    }

    # for result in response.get("ResultsByTime", []):
    #     for group in result.get("Groups", []):
    #         print(group["Keys"])

    # --- WRITE TO JSON FILE ---
    with open("ce_debug.json", "w") as f:
        json.dump(debug_data, f, indent=2, default=str)

    print("Data written to ce_debug.json")


if __name__ == "__main__":
    main()
