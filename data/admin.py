from django.contrib import admin

from .models import (
    AWSRole,
    AzureOAuthToken,
    BillingRecord,
    BillingSummary,
    CloudAccount,
    GoogleOAuthToken,
)

# Register your models here.
admin.register(CloudAccount)
admin.register(BillingRecord)
admin.register(BillingSummary)
admin.register(GoogleOAuthToken)
admin.register(AzureOAuthToken)
admin.register(AWSRole)
