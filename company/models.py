import uuid
from datetime import timedelta

from django.db import models
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from authentication.models import CustomUser


class Company(models.Model):
    """Model representing a company - parent of orgnaizations"""

    THEME_CHOICES = [
        ("default", "Default"),
        ("simple", "Simple"),
        ("classic", "Classic"),
        ("amber-minimal", "Amber Minimal"),
        ("bold-tech", "Bold Tech"),
        ("caffeine", "Caffeine"),
        ("elegant-luxury", "Elegant Luxury"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    theme = models.CharField(
        max_length=50,
        choices=THEME_CHOICES,
        default="default",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # db_table = "organizations_company"
        ordering = ["created_at"]

    def __str__(self):
        return self.name


class Organization(models.Model):
    """Model representing an organization"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)

    class Meta:
        ordering = ["name"]
        unique_together = ["name", "company"]

    def __str__(self) -> str:
        return f"{self.name}"


class OrganizationMembership(models.Model):
    """Manages users and roles within an Organization"""

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("member", "Member"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # db_table = "organizations_companymemberships"
        ordering = ["joined_at"]
        # Prevent duplicate memberships
        unique_together = ("user", "organization")

    def __str__(self):
        return f"{self.user.email} - {self.organization.name} ({self.role})"


class Invitation(models.Model):
    """Handles invitations to join an Organization"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    invited_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="sent_invitations"
    )
    invitee_email = models.EmailField()
    role = models.CharField(
        max_length=10, choices=OrganizationMembership.ROLE_CHOICES, default="member"
    )
    token = models.CharField(max_length=50, unique=True)
    # TODO: don't really need status
    status = models.CharField(
        max_length=10,
        choices=[
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
        ],
        default="pending",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        # db_table = "organizations_invitation"
        ordering = ["created_at"]
        # Prevent duplicate invites
        unique_together = ("organization", "invitee_email")

    def __str__(self):
        return (
            f"Invite to {self.invitee_email} for {self.organization.name} ({self.role})"
        )

    @classmethod
    def create_invitation(cls, organization, invited_by, email, role="member"):
        token = get_random_string(32)
        expires_at = now() + timedelta(days=7)  # 7-day expiration
        return cls.objects.create(
            organization=organization,
            invited_by=invited_by,
            invitee_email=email,
            role=role,
            token=token,
            expires_at=expires_at,
        )
