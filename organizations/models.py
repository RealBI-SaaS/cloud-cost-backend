import uuid
from datetime import timedelta

from django.db import models
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from authentication.models import CustomUser


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)

    # logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)
    # one to many to user
    # owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    # many to many to organization
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.name


# class CompanyColorScheme(models.Model):
#     company = models.OneToOneField(
#         Company, on_delete=models.CASCADE, related_name="color_scheme"
#     )
#
#     primary = models.CharField(max_length=7, blank=True, null=True)
#     sidebar_accent = models.CharField(max_length=7, blank=True, null=True)
#     borders = models.CharField(max_length=7, blank=True, null=True)
#     form_input_background = models.CharField(max_length=7, blank=True, null=True)
#     sidebar_background = models.CharField(max_length=7, blank=True, null=True)
#     sidebar_font_color = models.CharField(max_length=7, blank=True, null=True)
#
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#

# class Organization(models.Model):
#     """Model representing an organization"""
#
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     name = models.CharField(max_length=255, unique=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     company = models.ForeignKey(Company, on_delete=models.CASCADE)
#
# owners = models.ManyToManyField(
#     CustomUser, blank=True, related_name="owned_organizations"
# )
# class Meta:
#     ordering = ["name"]
#
# def __str__(self) -> str:
#     return f"{self.name}"
#

# class UserGroup(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     name = models.CharField(max_length=255, unique=True)
#     organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
#     users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="user_groups")
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     def __str__(self) -> str:
#         return f"{self.name}"
#


class CompanyMembership(models.Model):
    """Manages users and roles within an organization"""

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("member", "Member"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["joined_at"]
        # Prevent duplicate memberships
        unique_together = ("user", "company")

    def __str__(self):
        return f"{self.user.email} - {self.company.name} ({self.role})"


class Invitation(models.Model):
    """Handles invitations to join an organization"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    invited_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="sent_invitations"
    )
    invitee_email = models.EmailField()
    role = models.CharField(
        max_length=10, choices=CompanyMembership.ROLE_CHOICES, default="member"
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
    # user_groups = models.ManyToManyField(
    #     "UserGroup", related_name="invitations", blank=True
    # )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["created_at"]
        # Prevent duplicate invites
        unique_together = ("company", "invitee_email")

    def __str__(self):
        return f"Invite to {self.invitee_email} for {self.company.name} ({self.role})"

    @classmethod
    def create_invitation(cls, company, invited_by, email, role="member"):
        token = get_random_string(32)
        expires_at = now() + timedelta(days=7)  # 7-day expiration
        return cls.objects.create(
            company=company,
            invited_by=invited_by,
            invitee_email=email,
            role=role,
            token=token,
            expires_at=expires_at,
        )


#
# class Navigation(models.Model):
#     """Model representing an organizations' Nnavigation"""
#
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     label = models.CharField(max_length=100, unique=False)
#     icon = models.CharField(max_length=20, unique=False, null=True, blank=True)
#     organization = models.ForeignKey(
#         Organization, on_delete=models.CASCADE, related_name="navigations"
#     )
#     user_groups = models.ManyToManyField(
#         "UserGroup", related_name="navigations", blank=True
#     )
#     order = models.PositiveIntegerField(default=0, help_text="Custom order")
#     parent = models.ForeignKey(
#         "self",
#         null=True,
#         blank=True,
#         on_delete=models.CASCADE,
#         related_name="sub_navigations",
#         help_text="If set, this navigation is a sub-navigation of the selected navigation.",
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     class Meta:
#         unique_together = ("label", "organization")
#         ordering = ["parent_id", "order", "label"]
#
#     def __str__(self):
#         return self.label
