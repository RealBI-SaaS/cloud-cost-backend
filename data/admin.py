from django.contrib import admin

from .models import (
    AWSRole,
    AzureOAuthToken,
    BillingRecord,
    CloudAccount,
    GoogleOAuthToken,
)

# Register your models here.
admin.site.register(CloudAccount)
admin.site.register(BillingRecord)
admin.site.register(GoogleOAuthToken)
admin.site.register(AzureOAuthToken)
admin.site.register(AWSRole)
