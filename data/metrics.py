from prometheus_client import Counter

# This counter will count the number of purchases
cost_request_counter = Counter(
    "cost_request_total",  # name (Prometheus convention)
    "Total number of request for cost data",  # description
    ["type"],
)
