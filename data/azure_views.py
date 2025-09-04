import uuid
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.timezone import now, timedelta
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError

from company.models import Organization

from .models import AzureOAuthToken, BillingRecord, CloudAccount

AZURE_AUTH_BASE = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
AZURE_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


@api_view(["GET"])
def start_azure_auth_view(request, organization_id, account_name):
    state = str(organization_id) + "," + account_name
    if not organization_id:
        raise ValidationError({"organization_id": "This field is required."})

    params = {
        "client_id": settings.AZURE_DATA_CLIENT_ID,
        "redirect_uri": settings.AZURE_DATA_REDIRECT_URI,
        "response_type": "code",
        "response_mode": "query",
        "scope": "https://management.azure.com/.default offline_access",
        "state": state,  # Pass company ID through state
    }
    return redirect(f"{AZURE_AUTH_BASE}?{urlencode(params)}")


@api_view(["GET"])
def azure_oauth_callback_view(request):
    state = request.GET.get("state")
    organization_id, account_name = state.split(",")
    organization_id = uuid.UUID(organization_id)
    code = request.GET.get("code")

    token_data = {
        "client_id": settings.AZURE_DATA_CLIENT_ID,
        "client_secret": settings.AZURE_DATA_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.AZURE_DATA_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    response = requests.post(AZURE_TOKEN_URL, data=token_data)
    tokens = response.json()

    if response.status_code != 200:
        return JsonResponse(
            {"error": "Token exchange failed", "details": tokens}, status=400
        )

    # Link to CloudAccount
    # membership = CompanyMembership.objects.filter(
    #     company_id=company_id, role__in=["owner", "admin"]
    # ).first()
    organization = Organization.objects.get(id=organization_id)

    cloud_account = CloudAccount.objects.create(
        organization=organization,
        vendor="azure",
        account_name="Azure Account",
        account_id="unknown",  # You can fill this in after querying subscriptions
    )

    AzureOAuthToken.objects.update_or_create(
        cloud_account=cloud_account,
        defaults={
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "token_type": tokens.get("token_type"),
            "scope": tokens.get("scope"),
            "tenant_id": tokens.get("tenant_id", ""),  # Might need to fetch from /me
            "expires_at": now() + timedelta(seconds=tokens["expires_in"]),
        },
    )

    return redirect(f"/data/azure/fetch/?account_id={cloud_account.id}")


@api_view(["GET"])
def fetch_azure_billing_view(request):
    account_id = request.GET.get("account_id")
    cloud_account = CloudAccount.objects.get(id=account_id)
    token = cloud_account.azure_oauth_token

    # Refresh token if expired
    if token.is_expired():
        token = refresh_azure_token(token)

    headers = {"Authorization": f"Bearer {token.access_token}"}

    # Example: list subscriptions
    subs_resp = requests.get(
        "https://management.azure.com/subscriptions?api-version=2020-01-01",
        headers=headers,
    )
    subscriptions = subs_resp.json().get("value", [])

    for sub in subscriptions:
        # Fetch billing usage (Cost Management API)
        usage_url = f"https://management.azure.com/subscriptions/{sub['subscriptionId']}/providers/Microsoft.Consumption/usageDetails?api-version=2023-03-01"
        usage_resp = requests.get(usage_url, headers=headers)
        usage_data = usage_resp.json().get("value", [])

        for item in usage_data:
            BillingRecord.objects.create(
                cloud_account=cloud_account,
                usage_start=item.get("properties", {}).get("usageStart"),
                usage_end=item.get("properties", {}).get("usageEnd"),
                service_name=item.get("properties", {}).get("meterName"),
                resource=item.get("properties", {}).get("instanceName"),
                cost=item.get("properties", {}).get("cost", 0.0),
                currency=item.get("properties", {}).get("currency", "USD"),
                metadata=item,
            )

    return JsonResponse({"success": True, "subscriptions": subscriptions})


def refresh_azure_token(token: AzureOAuthToken):
    data = {
        "client_id": settings.AZURE_DATA_CLIENT_ID,
        "client_secret": settings.AZURE_DATA_CLIENT_SECRET,
        "refresh_token": token.refresh_token,
        "grant_type": "refresh_token",
        "scope": "https://management.azure.com/.default offline_access",
    }
    url = f"https://login.microsoftonline.com/{token.tenant_id}/oauth2/v2.0/token"

    response = requests.post(url, data=data)
    if response.status_code == 200:
        new_data = response.json()
        token.access_token = new_data["access_token"]
        token.expires_at = now() + timedelta(seconds=new_data["expires_in"])
        token.save()
        return token
    else:
        raise Exception("Failed to refresh Azure token", response.text)
