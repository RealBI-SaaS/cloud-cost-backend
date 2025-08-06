import os

import requests
from django.http import JsonResponse
from django.shortcuts import redirect
from dotenv import load_dotenv

load_dotenv()
#
# # Environment variables
GOOGLE_DATA_CLIENT_ID = os.getenv("GOOGLE_DATA_CLIENT_ID")
GOOGLE_DATA_CLIENT_SECRET = os.getenv("GOOGLE_DATA_CLIENT_SECRET")
GOOGLE_FAILED_DATA_PULL_REDIRECT_URL = os.getenv("GOOGLE_DATA_REDIRECT_URI")
GOOGLE_DATA_REDIRECT_URL = os.getenv(
    "GOOGLE_DATA_REDIRECT_URL", "http://localhost:5173/home"
)
LOGIN_FROM_REDIRECT_URL = os.getenv(
    "LOGIN_FROM_REDIRECT_URL", "http://localhost:5173/login"
)

#
# def google_oauth_get_token(request):
#     code = request.GET.get("code")
#     print("here", code)
#     if not code:
#         # return JsonResponse({"error": "Authorization code not provided"}, status=400)
#         return redirect(GOOGLE_FAILED_DATA_PULL_REDIRECT_URL)
#
#     try:
#         # Exchange auth code for tokens
#         token_endpoint = "https://oauth2.googleapis.com/token"
#         data = {
#             "code": code,
#             "client_id": GOOGLE_DATA_CLIENT_ID,
#             "client_secret": GOOGLE_DATA_CLIENT_SECRET,
#             # "redirect_uri": GOOGLE_DATA_REDIRECT_URL,
#             "redirect_uri": "http://localhost:8000/data/google/callback/",
#             "grant_type": "authorization_code",
#         }
#
#         response = requests.post(token_endpoint, data=data)
#         tokens = response.json()
#
#         if response.status_code != 200:
#             return JsonResponse(
#                 {"error": "Failed to exchange auth code", "response": response.json()},
#                 status=400,
#             )
#
#         # Get user info from Google
#         access_token = tokens["access_token"]
#         # billing_info_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"
#
#         # billing_info_endpoint = (
#         #     f"https://cloudbilling.googleapis.com/v1/projects/{project_id}/billingInfo"
#         # )
#         headers = {"Authorization": f"Bearer {access_token}"}
#         resp = requests.get(
#             "https://cloudresourcemanager.googleapis.com/v1/projects", headers=headers
#         )
#
#         data = resp.json()
#         projects = data.get("projects", [])
#         for project in projects:
#             print(project["projectId"], project["name"])
#
#         # billing_info_response = requests.get(billing_info_endpoint, headers=headers)
#         # billing_info = billing_info_response.json()
#
#         # print(billing_info)
#
#         # Generate JWT tokens
#         # refresh = RefreshToken.for_user(user)
#         # access_token = str(refresh.access_token)
#         # refresh_token = str(refresh)
#
#         # Create redirect URL with tokens as parameters
#         # params = {"access": access_token, "refresh": refresh_token}
#         # redirect_url = f"{SUCCESS_REDIRECT_URL}?{urlencode(params)}"
#         #
#         # return redirect(redirect_url)
#         # return JsonResponse({"resp": str(billing_info)})
#
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)


def google_oauth_get_token(request):
    code = request.GET.get("code")
    if not code:
        return redirect(GOOGLE_FAILED_DATA_PULL_REDIRECT_URL)

    try:
        token_endpoint = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": GOOGLE_DATA_CLIENT_ID,
            "client_secret": GOOGLE_DATA_CLIENT_SECRET,
            "redirect_uri": "http://localhost:8000/data/google/callback/",
            "grant_type": "authorization_code",
        }

        response = requests.post(token_endpoint, data=data)
        tokens = response.json()

        if response.status_code != 200:
            return JsonResponse(
                {"error": "Failed to exchange auth code", "response": tokens},
                status=400,
            )

        access_token = tokens["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        resp = requests.get(
            "https://cloudresourcemanager.googleapis.com/v1/projects", headers=headers
        )
        if resp.status_code != 200:
            return JsonResponse(
                {"error": "Failed to list projects", "resp": resp.json()},
                status=resp.status_code,
            )

        data = resp.json()
        projects = data.get("projects", [])

        # You can now select one and redirect:
        if not projects:
            return JsonResponse({"error": "No accessible projects found"}, status=404)

        project_id = projects[0]["projectId"]
        for proj in projects:
            billing_url = f"https://cloudbilling.googleapis.com/v1/projects/{proj['projectId']}/billingInfo"
            r = requests.get(billing_url, headers=headers)
            print(r.json())

        # return redirect(
        #     f"{GOOGLE_SUCCESS_DATA_PULL_REDIRECT_URL}?project_id={project_id}"
        # )

        return JsonResponse({"succ": str(projects)}, status=200)

    except Exception as e:
        import traceback

        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
