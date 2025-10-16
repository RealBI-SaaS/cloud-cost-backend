
Cloud Account Cost & Usage APIs Summary
======================================

This endpoints allow retrieving aggregated billing and usage data for cloud accounts and organizations.
Most endpoints support **date framing**, allowing you to specify custom reporting periods using query parameters.

Date Framing
------------

Endpoints that support date framing accept the following optional query parameters:

.. code-block:: http

    GET /cost-summary/account/<uuid:cloud_account_id>/?days=7
    GET /cost-summary/account/<uuid:cloud_account_id>/?since=2025-09-15&until=2025-09-22

- **days** — number of days back from today.
- **since** — start date (``YYYY-MM-DD``) for the data range.
- **until** — end date (``YYYY-MM-DD``) for the data range.

---

- All framed responses include a ``range`` field showing the effective start and end dates.
- All framed responses requested with ``organization_id`` will have the ``cloud account`` IDs as the key to its respective data. Example:

  .. code-block:: json
    {"f65f4b29-912b-4706-8246-6c3c45505432": data}

---

Endpoints
---------

1. Detail Info Views - Provide semi-summerized, detailed info
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1. billing_daily_costs**

- **URL:** ``cost/daily/<uuid:organization_id>/``
- **Description:** Returns total daily cost for all cloud accounts of an organization.
- **Supports:** Date framing
- **Response:**

  .. code-block:: json

      {[
            {
                "day": "2025-10-02T00:00:00Z",
                "total_cost": 0.4398
            },
            {
                "day": "2025-10-03T00:00:00Z",
                "total_cost": 0.4398
      }]}

**2. billing_cost_by_service**

- **URL:** ``cost/service/<uuid:organization_id>/``
- **Description:** Returns total cost aggregated by service.
- **Supports:** Date framing
- **Response:**

  .. code-block:: json

      [
        {
          "service_name": "Amazon Elastic Compute Cloud - Compute",
          "total_cost": 2.506
        },
        {
          "service_name": "Amazon Virtual Private Cloud",
          "total_cost": 1.075
        }
      ]


**3. billing_cost_by_region**

- **URL:** ``cost/region/<uuid:organization_id>/``
- **Description:** Returns total cost aggregated by region.
- **Supports:** Date framing
- **Response:**

  .. code-block:: json

      [
        {
          "region": null,
          "total_cost": 3.9476
        }
      ]


**4. billing_usage_service_day**

- **URL:** ``usage/service-day/<uuid:organization_id>/``
- **Description:** Returns daily usage aggregated by service for a given account.
- **Supports:** Date framing
- **Response:**

  .. code-block:: json

      [
        {
          "service_name": "EC2 - Other",
          "day": "2025-01-01T00:00:00Z",
          "total_usage": 0.522123
        },
        {
          "service_name": "Amazon Elastic Compute Cloud - Compute",
          "day": "2025-01-01T00:00:00Z",
          "total_usage": 24.016832
        }
      ]

---

2. Summary Info Views
~~~~~~~~~~~~~~~~~~~~~

**5. billing_monthly_service_total**

- **URL:** ``cost-summary/service-monthly/<uuid:organization_id>/``
- **Description:** Returns monthly cost and usage by service for a cloud account.
- **Supports:** Date framing
- **Response:**

  .. code-block:: json

      [
        {
          "service_name": "Amazon Elastic Compute Cloud - Compute",
          "monthly": [
            {
              "month": "2025-10-01T00:00:00Z",
              "total_usage": 216.435914,
              "total_cost": 2.506
            }
          ]
        }
      ]


**6. cost_summary_by_service**

- **URL:** ``cost-summary/service/<uuid:organization_id>/``
- **Description:** Returns today’s and month-to-date totals per service.
- **Supports:** Date framing
- **Response:**

  .. code-block:: json

      {
        "today": {},
        "this_month": {
          "Amazon Elastic Compute Cloud - Compute": 2.506,
          "Amazon Simple Storage Service": 0.0003,
          "Amazon Virtual Private Cloud": 1.075,
          "EC2 - Other": 0.3563,
          "AWS Cost Explorer": 0.01
        }
      }


**7. cost_summary_by_account**

- **URL:** ``cost-summary/account/<uuid:organization_id>/``
- **Description:** Returns total cost for today and for a given period (defaults to month-to-date).
- **Supports:** Date framing
- **Response:**

  .. code-block:: json

      {
        "total_today": 0,
        "total_period": 3.9476
      }


**8. cost_summary_by_orgs**

- **URL:** ``cost-summary/orgs/``
- **Description:** Returns total costs for today and month-to-date for one or more organizations.
- **Supports:** Date framing
- **Docs:** https://ceres.pythonanywhere.com/swagger/#/data/data_cost_summary_orgs_create
- **Response:**

  .. code-block:: json

      {
        "org_id": {
          "total_month": "2.32",
          "total_today": "34.223"
        }
      }

---

