from django.contrib import admin

from .models import (
    AWSRole,
    AzureOAuthToken,
    BillingRecord,
    CloudAccount,
    GoogleOAuthToken,
)

# Register your models here.
admin.register(CloudAccount)
admin.register(BillingRecord)
admin.register(GoogleOAuthToken)
admin.register(AzureOAuthToken)
admin.register(AWSRole)
