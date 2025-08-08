import os
from urllib.parse import urlencode

import requests
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.timezone import now, timedelta
from dotenv import load_dotenv
from rest_framework.decorators import api_view

from authentication.models import CustomUser
from organizations.models import CompanyMembership

from .models import BillingRecord, CloudAccount, GoogleOAuthToken

load_dotenv()
#
# # Environment variables
GOOGLE_DATA_CLIENT_ID = os.getenv("GOOGLE_DATA_CLIENT_ID")
GOOGLE_DATA_CLIENT_SECRET = os.getenv("GOOGLE_DATA_CLIENT_SECRET")
GOOGLE_FAILED_DATA_PULL_REDIRECT_URL = os.getenv("GOOGLE_DATA_FAILED_REDIRECT_URI")
GOOGLE_DATA_REDIRECT_URL = os.getenv(
    "GOOGLE_DATA_REDIRECT_URL", "http://localhost:5173/home"
)
LOGIN_FROM_REDIRECT_URL = os.getenv(
    "LOGIN_FROM_REDIRECT_URL", "http://localhost:5173/login"
)


@api_view(["GET"])
def start_google_auth_view(request):
    params = {
        "client_id": GOOGLE_DATA_CLIENT_ID,
        "redirect_uri": "http://localhost:8000/data/google/callback/",
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/cloud-platform https://www.googleapis.com/auth/cloud-billing.readonly",
        "access_type": "offline",  # to get refresh_token
        "prompt": "consent",  # always ask for permission
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return redirect(url)


@api_view(["GET"])
def google_oauth_callback_view(request):
    try:
        code = request.GET.get("code")
        if not code:
            return redirect(GOOGLE_FAILED_DATA_PULL_REDIRECT_URL)
    except TypeError:
        return redirect(GOOGLE_FAILED_DATA_PULL_REDIRECT_URL)

    token_data = {
        "code": code,
        "client_id": GOOGLE_DATA_CLIENT_ID,
        "client_secret": GOOGLE_DATA_CLIENT_SECRET,
        "redirect_uri": "http://localhost:8000/data/google/callback/",
        "grant_type": "authorization_code",
    }

    response = requests.post("https://oauth2.googleapis.com/token", data=token_data)
    tokens = response.json()

    if response.status_code != 200:
        return JsonResponse(
            {"error": "Token exchange failed", "details": tokens}, status=400
        )

    # Extract token info
    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens["expires_in"]
    expires_at = now() + timedelta(seconds=expires_in)

    # Create or update CloudAccount and token
    # TODO: You should get or create based on company + project info
    # print(request.user)
    user_id = CustomUser.objects.filter(email="u1@numlock.com").first().id
    membership = CompanyMembership.objects.filter(
        user=user_id, role__in=["owner", "admin"]
    ).first()
    # CompanyMembership.objects.filter(user='1426bcda-4ddd-4180-806a-cc7e2ba79b75', role__in=['admin', 'owner']).first()

    company = membership.company
    # if membership:
    # else:
    #     print("ERRRR....")
    #
    cloud_account = CloudAccount.objects.create(
        company=company,
        vendor="GCP",
        account_name="Google Cloud",  # name it later from API
        account_id="temp",  # will update in fetch view
    )

    GoogleOAuthToken.objects.create(
        cloud_account=cloud_account,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        # scope=tokens.get("scope"),
        # token_type=tokens.get("token_type", "Bearer"),
        # id_token=tokens.get("id_token"),
    )

    return redirect(f"/data/google/fetch/?account_id={cloud_account.id}")


@api_view(["GET"])
def fetch_google_projects_and_billing_view(request):
    account_id = request.GET.get("account_id")
    cloud_account = CloudAccount.objects.get(id=account_id)
    token = cloud_account.google_oauth_token

    # Refresh token if expired
    if token.is_expired():
        token = refresh_google_token(
            token, GOOGLE_DATA_CLIENT_ID, GOOGLE_DATA_CLIENT_SECRET
        )

    headers = {"Authorization": f"Bearer {token.access_token}"}

    projects_resp = requests.get(
        "https://cloudresourcemanager.googleapis.com/v1/projects", headers=headers
    )
    projects = projects_resp.json().get("projects", [])

    for project in projects:
        billing_url = f"https://cloudbilling.googleapis.com/v1/projects/{project['projectId']}/billingInfo"
        billing_resp = requests.get(billing_url, headers=headers)
        billing_info = billing_resp.json()

        # Store to DB
        BillingRecord.objects.create(
            cloud_account=cloud_account,
            usage_start=now(),  # dummy, replace with actual usage window if available
            usage_end=now(),
            service_name="Google Billing",
            resource=project["projectId"],
            cost=0.0,  # Replace with real cost if available
            metadata=billing_info,
        )

    return JsonResponse({"success": True, "projects": projects})


def refresh_google_token(token: GoogleOAuthToken, client_id, client_secret):
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": token.refresh_token,
            "grant_type": "refresh_token",
        },
    )

    if response.status_code == 200:
        data = response.json()
        token.access_token = data["access_token"]
        token.expires_at = now() + timedelta(seconds=data["expires_in"])
        token.scope = data.get("scope", token.scope)
        token.token_type = data.get("token_type", token.token_type)
        token.id_token = data.get("id_token", token.id_token)
        token.save()
        return token
    else:
        raise Exception("Failed to refresh token", response.text)
