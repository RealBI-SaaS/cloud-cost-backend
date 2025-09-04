import os
from datetime import datetime, timedelta
from urllib.parse import urlencode

# from itsdangerous import URLSafeSerializer
# serializer = URLSafeSerializer(settings.SECRET_KEY, salt="google-oauth")
import requests
from django.core import signing
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.timezone import now, timedelta
from dotenv import load_dotenv
from rest_framework.decorators import api_view

from company.models import Organization

from .models import CloudAccount, GoogleOAuthToken

# from .services.google_api import get_gcp_billing_data, get_gcp_projects
from .services.ingestion import ingest_billing_data

load_dotenv()
#
# # Environment variables

FRONTEND_URL = os.getenv("FRONTEND_URL", "defaultdomain.com")
GOOGLE_DATA_CLIENT_ID = os.getenv("GOOGLE_DATA_CLIENT_ID")
GOOGLE_DATA_CLIENT_SECRET = os.getenv("GOOGLE_DATA_CLIENT_SECRET")
GOOGLE_FAILED_DATA_PULL_REDIRECT_URL = os.getenv("GOOGLE_DATA_FAILED_REDIRECT_URI")
GOOGLE_DATA_REDIRECT_URL = os.getenv("GOOGLE_DATA_REDIRECT_URL")
LOGIN_FROM_REDIRECT_URL = os.getenv("LOGIN_FROM_REDIRECT_URL")


@api_view(["GET"])
def start_google_auth_view(request, organization_id, account_name):
    # company_id = request.GET.get("company_id")
    # TODO: better/specific response
    if not organization_id or not account_name:
        return JsonResponse(
            {"error": "organization_id and account_name are required"}, status=400
        )
    # Sign the state to prevent tampering
    state_data = {"organization_id": str(organization_id), "account_name": account_name}
    state_signed = signing.dumps(state_data)
    # Sign the company_id so it can't be tampered with
    # state = serializer.dumps({"company_id": company_id})
    state = str(organization_id) + "," + str(account_name)
    params = {
        "client_id": GOOGLE_DATA_CLIENT_ID,
        "redirect_uri": GOOGLE_DATA_REDIRECT_URL,
        "response_type": "code",
        # "scope": "https://www.googleapis.com/auth/cloud-platform https://www.googleapis.com/auth/cloud-billing.readonly https://www.googleapis.com/auth/bigquery.readonly",
        "scope": "https://www.googleapis.com/auth/cloud-billing.readonly",
        "access_type": "offline",  # to get refresh_token
        "prompt": "consent",  # always ask for permission
        "state": state_signed,
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return redirect(url)


@api_view(["GET"])
def google_oauth_callback_view(request):
    code = request.GET.get("code")
    state_signed = request.GET.get("state")

    if not code or not state_signed:
        return redirect(GOOGLE_FAILED_DATA_PULL_REDIRECT_URL)

    try:
        # Verify and decode the signed state
        state_data = signing.loads(state_signed)
        organization_id = state_data["organization_id"]
        account_name = state_data["account_name"]
    except signing.BadSignature:
        return JsonResponse({"error": "Invalid state signature"}, status=400)
    token_data = {
        "code": code,
        "client_id": GOOGLE_DATA_CLIENT_ID,
        "client_secret": GOOGLE_DATA_CLIENT_SECRET,
        "redirect_uri": GOOGLE_DATA_REDIRECT_URL,
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

    organization = Organization.objects.get(id=organization_id)

    cloud_account = CloudAccount.objects.create(
        organization=organization,
        vendor="GCP",
        account_name=account_name,
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


#
# @api_view(["GET"])
# def fetch_google_projects_and_billing_view(request):
#     account_id = request.GET.get("account_id")
#     cloud_account = CloudAccount.objects.get(id=account_id)
#     token = cloud_account.google_oauth_token
#
#     # Refresh token if expired
#     if token.is_expired():
#         token = refresh_google_token(
#             token, GOOGLE_DATA_CLIENT_ID, GOOGLE_DATA_CLIENT_SECRET
#         )
#
#     headers = {"Authorization": f"Bearer {token.access_token}"}
#
#     projects_resp = requests.get(
#         "https://cloudresourcemanager.googleapis.com/v1/projects", headers=headers
#     )
#     projects = projects_resp.json().get("projects", [])
#
#     for project in projects:
#         billing_url = f"https://cloudbilling.googleapis.com/v1/projects/{project['projectId']}/billingInfo"
#         billing_resp = requests.get(billing_url, headers=headers)
#         billing_info = billing_resp.json()
#
#         # Store to DB
#         BillingRecord.objects.create(
#             cloud_account=cloud_account,
#             usage_start=now(),  # dummy, replace with actual usage window if available
#             usage_end=now(),
#             service_name="Google Billing",
#             resource=project["projectId"],
#             cost=0.0,  # Replace with real cost if available
#             metadata=billing_info,
#         )
#
#     # return JsonResponse({"success": True, "projects": projects})
#     return redirect(f"{FRONTEND_URL}/settings/organization/data")


def get_gcp_projects(access_token):
    url = "https://cloudbilling.googleapis.com/v1/billingAccounts"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json().get("billingAccounts", [])


def get_gcp_billing_data(access_token, project_id):
    url = f"https://cloudbilling.googleapis.com/v1/projects/{project_id}/billingInfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 404:
        # Project billing info not found
        return None
    resp.raise_for_status()
    return resp.json()


@api_view(["GET"])
def fetch_google_projects_and_billing_view(request):
    account_id = request.GET.get("account_id")

    # Get token & account

    cloud_account = CloudAccount.objects.get(id=account_id)
    token = cloud_account.google_oauth_token

    # Refresh token if expired
    if token.is_expired():
        token = refresh_google_token(
            token, GOOGLE_DATA_CLIENT_ID, GOOGLE_DATA_CLIENT_SECRET
        )

    # Define date range (last 30 days)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    # Step 1: Fetch projects
    projects = get_gcp_projects(token.access_token)

    # Step 2: Ingest all billing data
    created_count = ingest_billing_data(
        cloud_account=cloud_account,
        access_token=token.access_token,
        projects=projects,
        start_date=start_date,
        end_date=end_date,
        get_billing_data_func=get_gcp_billing_data,
    )

    # return Response({"status": "success", "records_created": created_count})

    return redirect(f"{FRONTEND_URL}/settings/organization/data")


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
