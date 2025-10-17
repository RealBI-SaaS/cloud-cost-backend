from django.contrib import admin

from .models import (
    AWSRole,
    AzureOAuthToken,
    BillingRecord,
    CloudAccount,
    CustomExpense,
    CustomExpenseVendor,
    GoogleOAuthToken,
)

# Register your models here.
admin.site.register(CloudAccount)
admin.site.register(CustomExpense)
admin.site.register(CustomExpenseVendor)
admin.site.register(BillingRecord)
admin.site.register(GoogleOAuthToken)
admin.site.register(AzureOAuthToken)
admin.site.register(AWSRole)
