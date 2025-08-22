import os
from urllib.parse import urlencode

import requests
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import redirect, render
from dotenv import load_dotenv
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()
from .serializers import GoogleOAuthErrorSerializer, UserSerializer

load_dotenv()
#
# # Environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
SUCCESS_REDIRECT_URL = os.getenv("GOOGLE_SUCCESS_REDIRECT_URL")
LOGIN_FROM_REDIRECT_URL = os.getenv("GOOGLE_LOGIN_FROM_REDIRECT_URL")


def api_documentation(request):
    return render(request, "index.html")


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="code",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="The authorization code returned by Google OAuth2 after user login.",
            required=False,
        ),
        OpenApiParameter(
            name="state",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Optional OAuth state parameter for CSRF protection.",
            required=False,
        ),
    ],
    responses={
        302: None,  # success redirect
        400: GoogleOAuthErrorSerializer,
        500: GoogleOAuthErrorSerializer,
    },
    summary="Google OAuth2 Callback",
    description=(
        "Handles the callback from Google OAuth2 after a user signs in.\n\n"
        "- Exchanges the authorization `code` for access/refresh tokens\n"
        "- Retrieves Google profile info (email, name)\n"
        "- Creates or retrieves the corresponding user in the system\n"
        "- Issues JWT access and refresh tokens\n"
        "- Redirects to the frontend with tokens appended as query parameters\n\n"
        "**Success:** 302 redirect to `SUCCESS_REDIRECT_URL?access=...&refresh=...`\n\n"
        "**Failure:** Returns JSON with error details"
    ),
)
@api_view(["GET"])
def google_oauth_callback(request):
    code = request.GET.get("code")
    if not code:
        return redirect(LOGIN_FROM_REDIRECT_URL)

    try:
        # Exchange auth code for tokens
        token_endpoint = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        response = requests.post(token_endpoint, data=data)
        tokens = response.json()

        if response.status_code != 200:
            return JsonResponse(
                {"error": "Failed to exchange auth code", "response": response.json()},
                status=400,
            )

        # Get user info from Google
        access_token = tokens["access_token"]
        userinfo_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}

        userinfo_response = requests.get(userinfo_endpoint, headers=headers)
        user_data = userinfo_response.json()

        # Get or create user
        user, created = User.objects.get_or_create(
            email=user_data["email"],
            defaults={
                "first_name": user_data.get("given_name", ""),
                "last_name": user_data.get("family_name", ""),
                "is_google_user": True,
                "is_email_verified": True,
                "is_active": True,
            },
        )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Create redirect URL with tokens as parameters
        params = {"access": access_token, "refresh": refresh_token}
        redirect_url = f"{SUCCESS_REDIRECT_URL}?{urlencode(params)}"

        return redirect(redirect_url)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Return the logged-in user"""
        return self.request.user
