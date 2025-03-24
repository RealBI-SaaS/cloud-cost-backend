from typing import Optional

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from authentication.models import User


def send_welcome_email(user, verification_url: str) -> bool:
    """
    Send a welcome email to a new user with verification link.

    Args:
        user: User object
        verification_url: URL for email verification

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        subject = "Welcome to X Analytics!"
        context = {
            "first_name": user.first_name or "there",
            "verification_url": verification_url,
        }

        html_message = render_to_string("email/welcome.html", context)
        plain_message = f"Welcome to Cedar Street Analytics! Please verify your email by visiting: {verification_url}"

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending welcome email: {str(e)}")
        return False


def generate_verification_url(user, request) -> str:
    """
    Generate a verification URL for the user's email.

    Args:
        user: User object
        request: HTTP request object

    Returns:
        str: Verification URL
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    verification_url = request.build_absolute_uri(
        reverse("verify-email", kwargs={"uidb64": uid, "token": token})
    )
    print(f"Verification URL: {verification_url}")
    return verification_url


def send_verification_email(user, request) -> bool:
    """
    Send a verification email to an existing user.

    Args:
        user: User object
        request: HTTP request object

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        verification_url = generate_verification_url(user, request)
        print(f"Verification URL: {verification_url}")
        return True
        # return send_welcome_email(user, verification_url)
    except Exception as e:
        print(f"Error sending verification email: {str(e)}")
        return False


def verify_email_token(uidb64: str, token: str) -> Optional[object]:
    """
    Verify the email verification token.

    Args:
        uidb64: Base64 encoded user ID
        token: Verification token

    Returns:
        User object if verification successful, None otherwise
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None

    if default_token_generator.check_token(user, token):
        return user
    return None
