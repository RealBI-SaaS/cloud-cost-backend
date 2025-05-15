import uuid
from datetime import timedelta

from django.db import models
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from authentication.models import CustomUser


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    # one to many to user
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    # many to many to organization
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
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

    # owners = models.ManyToManyField(
    #     CustomUser, blank=True, related_name="owned_organizations"
    # )
    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    """Manages users and roles within an organization"""

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
        ordering = ["joined_at"]
        unique_together = ("user", "organization")  # Prevent duplicate memberships

    def __str__(self):
        return f"{self.user.email} - {self.organization.name} ({self.role})"


class Invitation(models.Model):
    """Handles invitations to join an organization"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    invited_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="sent_invitations"
    )
    invitee_email = models.EmailField()
    role = models.CharField(
        max_length=10, choices=OrganizationMembership.ROLE_CHOICES, default="member"
    )
    token = models.CharField(max_length=50, unique=True)  # For verifying invites
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
        ordering = ["created_at"]
        unique_together = ("organization", "invitee_email")  # Prevent duplicate invites

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


class Navigation(models.Model):
    """Model representing an organizations' Nnavigation"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=100, unique=False)
    icon = models.CharField(max_length=20, unique=False, null=True, blank=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="navigations"
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="sub_navigations",
        help_text="If set, this navigation is a sub-navigation of the selected navigation.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("label", "organization")
        ordering = ["label"]

    def __str__(self):
        return self.label
