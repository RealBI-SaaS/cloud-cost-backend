import datetime
import json

import boto3


def main():
    # Create a Cost Explorer client (uses ~/.aws credentials by default)
    client = boto3.client("ce", region_name="us-east-1")

    # Define time range: last 7 days
    end = datetime.date.today()
    start = end - datetime.timedelta(days=7)

    # Call AWS Cost Explorer
    response = client.get_cost_and_usage(
        TimePeriod={
            "Start": start.strftime("%Y-%m-%d"),
            "End": end.strftime("%Y-%m-%d"),
        },
        Granularity="DAILY",  # DAILY or MONTHLY
        Metrics=["BlendedCost", "UsageQuantity"],
        GroupBy=[
            {"Type": "DIMENSION", "Key": "SERVICE"},
        ],
    )

    # Pretty-print the response structure
    print(json.dumps(response, indent=2, default=str))


if __name__ == "__main__":
    main()
