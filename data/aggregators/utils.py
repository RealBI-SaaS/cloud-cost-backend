from datetime import datetime, timedelta

from django.utils.timezone import now
from rest_framework.response import Response


def parse_date_range(request, default_month_to_date=True):
    """
    Extracts and validates `days`, `since`, and `until` from query params.

    Returns:
      (start_date, end_date, error_response)
    """

    today = now().date()
    days = request.query_params.get("days")
    since = request.query_params.get("since")
    until = request.query_params.get("until")

    try:
        if days is not None:
            days = int(days)
        if since:
            since = datetime.strptime(since, "%Y-%m-%d").date()
        if until:
            until = datetime.strptime(until, "%Y-%m-%d").date()
    except ValueError:
        return (
            None,
            None,
            Response(
                {"error": "Invalid date format, use YYYY-MM-DD or integer for days."},
                status=400,
            ),
        )

    # Determine start date
    if since:
        start_date = since
    elif days is not None:
        start_date = today - timedelta(days=days)
    elif default_month_to_date:
        start_date = today.replace(day=1)
    else:
        start_date = today

    end_date = until or today

    if start_date > end_date:
        return (
            None,
            None,
            Response(
                {"error": "`since` or computed start_date cannot be after `until`."},
                status=400,
            ),
        )

    return start_date, end_date, None
