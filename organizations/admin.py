from django.contrib import admin

from .models import (
    Company,
    Invitation,
    Navigation,
    Organization,
    OrganizationMembership,
)

# Register your models here.

admin.site.register(Organization)
admin.site.register(OrganizationMembership)
admin.site.register(Invitation)
admin.site.register(Navigation)
admin.site.register(Company)
