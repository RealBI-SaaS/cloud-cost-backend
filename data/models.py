import uuid

from django.db import models
from django.utils.timezone import now

from organizations.models import Company


class CloudVendor(models.TextChoices):
    AWS = "AWS", "Amazon Web Services"
    GCP = "GCP", "Google Cloud Platform"
    AZURE = "AZURE", "Microsoft Azure"
    # Add more vendors if needed


class CloudAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="cloud_accounts"
    )
    vendor = models.CharField(max_length=10, choices=CloudVendor.choices)
    account_name = models.CharField(max_length=255)  # Display name
    account_id = models.CharField(
        max_length=255
    )  # e.g., AWS account ID, GCP project ID
    # credentials_info = models.JSONField(
    #     blank=True, null=True
    # )  # Store OAuth credentials, keys, etc. (encrypted in practice)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("vendor", "account_id")
        ordering = ["vendor", "account_name"]

    def __str__(self):
        return f"{self.vendor} - {self.account_name}"


class BillingRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cloud_account = models.ForeignKey(
        "CloudAccount", on_delete=models.CASCADE, related_name="billing_records"
    )

    usage_start = models.DateTimeField()
    usage_end = models.DateTimeField()
    service_name = models.CharField(max_length=255)
    resource = models.CharField(
        max_length=255, blank=True, null=True
    )  # e.g., instance ID, bucket name
    cost = models.DecimalField(max_digits=12, decimal_places=4)
    currency = models.CharField(max_length=10, default="USD")
    metadata = models.JSONField(blank=True, null=True)  # e.g., tags, region, etc.

    class Meta:
        indexes = [
            models.Index(fields=["usage_start", "usage_end"]),
        ]
        ordering = ["-usage_start"]

    def __str__(self):
        return (
            f"{self.cloud_account} - {self.service_name} - {self.cost} {self.currency}"
        )


# class AzureBillingRecord(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     cloud_account = models.ForeignKey("CloudAccount", on_delete=models.CASCADE)
#     usage_start = models.DateTimeField()
#     usage_end = models.DateTimeField()
#     service_name = models.CharField(max_length=255)
#     resource = models.CharField(max_length=255)  # e.g., subscription ID or resource group
#     cost = models.DecimalField(max_digits=12, decimal_places=2)
#     currency = models.CharField(max_length=10, default="USD")
#     metadata = models.JSONField(blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#

# Create your models here.


class GoogleOAuthToken(models.Model):
    cloud_account = models.OneToOneField(
        "CloudAccount", on_delete=models.CASCADE, related_name="google_oauth_token"
    )

    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()
    # scope = models.TextField(blank=True, null=True)
    # token_type = models.CharField(max_length=50, default="Bearer")
    # id_token = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_expired(self):
        return now() >= self.expires_at

    def __str__(self):
        return f"OAuth token for {self.cloud_account.account_name}"


class AzureOAuthToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cloud_account = models.OneToOneField(
        "CloudAccount", on_delete=models.CASCADE, related_name="azure_oauth_token"
    )
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_type = models.CharField(max_length=50)
    scope = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField()
    tenant_id = models.CharField(max_length=100)  # Important for token refresh
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_expired(self):
        return now() >= self.expires_at

    def __str__(self):
        return f"Azure token for {self.cloud_account.account_name}"
