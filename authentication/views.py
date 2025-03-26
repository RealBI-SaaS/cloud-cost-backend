import os
from urllib.parse import urlencode

#
import requests
from django.contrib.auth import get_user_model

# from django.conf import settings
# from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import redirect, render
from dotenv import load_dotenv

# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.status import (
#     HTTP_200_OK,
#     HTTP_201_CREATED,
#     HTTP_400_BAD_REQUEST,
#     HTTP_404_NOT_FOUND,
#     HTTP_500_INTERNAL_SERVER_ERROR,
# )
# from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

#
# from core.email_utils import send_verification_email, verify_email_token
#


User = get_user_model()
# from .serializers import CompanyMembershipSerializer, UserSerializer
#
# # Load environment variables at module level

load_dotenv()
#
# # Environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
SUCCESS_REDIRECT_URL = os.getenv("SUCCESS_REDIRECT_URL", "http://localhost:5173/home")
LOGIN_FROM_REDIRECT_URL = os.getenv(
    "LOGIN_FROM_REDIRECT_URL", "http://localhost:5173/login"
)
FRONTEND_URL = os.getenv("FRONTEND_URL")


#
# # Create your views here.
#
#
def api_documentation(request):
    return render(request, "index.html")


#


def google_oauth_callback(request):
    code = request.GET.get("code")
    if not code:
        # return JsonResponse({"error": "Authorization code not provided"}, status=400)
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


#
# class RegisterView(APIView):
#     http_method_names = ["post"]
#
#     def post(self, request, *args, **kwargs):
#         serializer = UserSerializer(data=self.request.data)
#         if serializer.is_valid():
#             data = serializer.validated_data
#             user = get_user_model().objects.create(**data)
#             user.set_password(data["password"])
#             user.save()
#
#             # Generate JWT tokens
#             refresh = RefreshToken.for_user(user)
#             access_token = str(refresh.access_token)
#             refresh_token = str(refresh)
#
#             # Send welcome email with verification link
#             # verification_url = f"{FRONTEND_URL}/verify-email/{user.id}"
#             send_verification_email(user, request)
#
#             return Response(
#                 {"access_token": access_token, "refresh_token": refresh_token},
#                 status=HTTP_201_CREATED,
#             )
#         return Response(status=HTTP_400_BAD_REQUEST, data={"errors": serializer.errors})
#
#
# class CompanyMembershipView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def get(self, request, *args, **kwargs):
#         """
#         Get all companies that the authenticated user is a member of.
#         Returns a list of companies with the user's role in each company.
#         """
#         try:
#             company_memberships = CompanyMember.objects.filter(user=request.user)
#             response_data = []
#
#             for membership in company_memberships:
#                 response_data.append(
#                     {
#                         "company_id": str(membership.company.id),
#                         "company_name": membership.company.name,
#                         "role": membership.role,
#                     }
#                 )
#
#             return Response(response_data, status=HTTP_200_OK)
#
#         except Exception as e:
#             return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
#
#     def post(self, request, *args, **kwargs):
#         """
#         Add a user to an existing company or create a new company and add the user.
#
#         Request body should contain:
#         - company_id (optional): UUID of existing company
#         - company_name (required if company_id not provided): Name for new company
#         - role (optional): Role of the user in the company (defaults to "member")
#         """
#         try:
#             serializer = CompanyMembershipSerializer(data=request.data)
#             if not serializer.is_valid():
#                 return Response(
#                     {"errors": serializer.errors}, status=HTTP_400_BAD_REQUEST
#                 )
#
#             data = serializer.validated_data
#             user = request.user
#             company_id = data.get("company_id")
#             company_name = data.get("company_name")
#
#             # If company_id is provided, try to get existing company
#             if company_id:
#                 try:
#                     company = Company.objects.get(id=company_id)
#                     role = "member"
#                 except Company.DoesNotExist:
#                     return Response(
#                         {"error": "Company not found"}, status=HTTP_404_NOT_FOUND
#                     )
#             # Otherwise create a new company
#             else:
#                 company = Company.objects.create(name=company_name)
#                 role = "owner"
#
#             # Create company membership or update if it already exists
#             company_member, created = CompanyMember.objects.update_or_create(
#                 user=user, company=company, defaults={"role": role}
#             )
#
#             # Serialize the response
#             response_serializer = CompanyMembershipSerializer(company_member)
#             return Response(
#                 response_serializer.data,
#                 status=HTTP_201_CREATED if created else HTTP_200_OK,
#             )
#
#         except Exception as e:
#             return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
#
#
# @api_view(["GET"])
# def test_mail(request):
#     try:
#         subject = "Hi natty, Dinn"
#         message = " it means a world to us "
#         email_from = settings.EMAIL_HOST_USER
#         recipient_list = [
#             "nutzaccs@gmail.com",
#         ]
#         send_mail(subject, message, email_from, recipient_list)
#         return Response({"success": "email sent"}, status=200)
#     except Exception as e:
#         return Response({"error": str(e)}, status=500)
#
#
# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_user(request):
#     try:
#         user = request.user
#         return Response(
#             {
#                 "userId": str(user.id),
#                 "email": user.email,
#                 "firstName": user.first_name,
#                 "lastName": user.last_name,
#                 "isGoogleUser": user.is_google_user,
#                 "isEmailVerified": user.is_email_verified,
#             }
#         )
#     except Exception as e:
#         return Response({"error": str(e)}, status=500)
#
#
# @api_view(["GET"])
# def verify_email(request, uidb64, token):
#     """
#     Verify user's email address.
#     """
#     user = verify_email_token(uidb64, token)
#     if user:
#         print("user verified")
#         user.is_email_verified = True
#         user.save()
#         return Response({"message": "Email verified successfully"}, status=HTTP_200_OK)
#     return Response(
#         {"error": "Invalid or expired verification link"}, status=HTTP_400_BAD_REQUEST
#     )
#
#
# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def resend_verification_email(request):
#     """
#     Resend verification email to authenticated user.
#     """
#     try:
#         if send_verification_email(request.user, request):
#             return Response(
#                 {"message": "Verification email sent successfully"}, status=HTTP_200_OK
#             )
#         return Response(
#             {"error": "Failed to send verification email"},
#             status=HTTP_500_INTERNAL_SERVER_ERROR,
#         )
#     except Exception as e:
#         return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
