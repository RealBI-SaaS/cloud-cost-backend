import random
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import OneTimeCredential
from authentication.serializers import (
    MagicLinkRequestSerializer,
    MagicLinkVerifySerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
)
from authentication.utils.hash import hash_code, verify_code
from core.throttles import OTPRequestThrottle, OTPVerifyThrottle

# magic link valid lifetime (minutes)
MAGIC_LINK_LIFETIME = 1
OTC_LIFETIME = 1

User = get_user_model()


class MagicLinkRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPRequestThrottle]

    @extend_schema(
        request=MagicLinkRequestSerializer,
        responses={200: {"description": "Magic link sent"}},
    )
    def post(self, request):
        serializer = MagicLinkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Return success to prevent email enumeration
            return Response(
                {"detail": "If an account exists, a link has been sent."},
                status=status.HTTP_200_OK,
            )

        # Delete old tokens for this user
        OneTimeCredential.objects.filter(user=user, type="magic_link").delete()

        token = uuid.uuid4().hex

        expiry = timezone.now() + timedelta(minutes=MAGIC_LINK_LIFETIME)
        _ = OneTimeCredential.objects.create(
            user=user,
            secret=token,
            type="magic_link",
            expires_at=expiry,
        )

        link = f"{settings.FRONTEND_BASE_URL}/magiclink-activation/?token={token}"

        html_message = render_to_string(
            "email/otp/magic_link.html",
            {
                "link": link,
                "lifetime": OTC_LIFETIME,
            },
        )

        send_mail(
            subject="Your Magic Login Link On NumLK",
            message=f"Click here to log in: {link}, It ecpires in {MAGIC_LINK_LIFETIME} minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,
        )

        return Response(
            {"detail": "If an account exists, a link has been sent."},
            status=status.HTTP_200_OK,
        )


class MagicLinkVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyThrottle]

    @extend_schema(
        request=MagicLinkVerifySerializer,
        responses={
            200: {
                "description": "JWT tokens",
                "examples": {
                    "access": "jwt_access_token",
                    "refresh": "jwt_refresh_token",
                },
            },
            400: {"description": "Invalid or expired token"},
        },
    )
    def post(self, request):
        serializer = MagicLinkVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        try:
            otc = OneTimeCredential.objects.get(secret=token, type="magic_link")
        except OneTimeCredential.DoesNotExist:
            return Response(
                {"detail": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otc.is_expired():
            otc.delete()
            return Response(
                {"detail": "Token has expired."}, status=status.HTTP_400_BAD_REQUEST
            )

        user = otc.user

        # Delete token after use
        otc.delete()

        # Issue JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )


# otc


class OTPRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPRequestThrottle]

    @extend_schema(
        request=OTPRequestSerializer, responses={200: {"description": "OTP sent"}}
    )
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "If an account exists, an OTP has been sent."},
                status=status.HTTP_200_OK,
            )

        OneTimeCredential.objects.filter(user=user, type="otp").delete()

        # Generate 6-digit OTP
        code = f"{random.randint(0, 999999):06d}"

        expiry = timezone.now() + timedelta(minutes=OTC_LIFETIME)
        OneTimeCredential.objects.create(
            user=user,
            secret=hash_code(code),
            type="otp",
            expires_at=expiry,
        )

        html_message = render_to_string(
            "email/otp/otc.html",
            {
                "code": code,
                "lifetime": OTC_LIFETIME,
            },
        )

        send_mail(
            subject="Your Login Code For NumLK",
            message=f"Your OTP code is {code}. It expires in {OTC_LIFETIME} minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,
        )

        return Response(
            {"detail": "If an account exists, an OTP has been sent."},
            status=status.HTTP_200_OK,
        )


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyThrottle]

    @extend_schema(
        request=OTPVerifySerializer,
        responses={
            200: {
                "description": "JWT tokens",
                "examples": {
                    "access": "jwt_access_token",
                    "refresh": "jwt_refresh_token",
                },
            },
            400: {"description": "Invalid code or expired"},
        },
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "User doesn't exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            otc = OneTimeCredential.objects.get(user=user, type="otp")
        except OneTimeCredential.DoesNotExist:
            return Response(
                {"detail": "Invalid code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otc.is_expired():
            otc.delete()
            return Response(
                {"detail": "Code has expired."}, status=status.HTTP_400_BAD_REQUEST
            )

        if not verify_code(code, otc.secret):
            return Response(
                {"detail": "Invalid code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otc.delete()

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )
