import uuid

from django.db import models

from authentication.models import CustomUser


class Organization(models.Model):
    """Model representing an organization"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owners = models.ManyToManyField(
        CustomUser, blank=True, related_name="owned_organizations"
    )

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
        unique_together = ("user", "organization")  # Prevent duplicate memberships

    def __str__(self):
        return f"{self.user.username} - {self.organization.name} ({self.role})"


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

    def __str__(self):
        return (
            f"Invite to {self.invitee_email} for {self.organization.name} ({self.role})"
        )
