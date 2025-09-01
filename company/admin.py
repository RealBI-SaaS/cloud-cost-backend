from django.contrib import admin

from .models import (
    Company,
    Invitation,
    Organization,
    OrganizationMembership,
)

admin.site.register(Company)
admin.site.register(Organization)
admin.site.register(Invitation)
# admin.site.register(Navigation)
admin.site.register(OrganizationMembership)
