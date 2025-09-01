from django.urls import include, path
from rest_framework.routers import DefaultRouter

from company.views.company import (
    AllCompaniesViewSet,
    CompanyViewSet,
)

# Create a router and register our ViewSets with it.
router = DefaultRouter()
router.register(r"", CompanyViewSet, basename="company")
router.register(r"all-companies", AllCompaniesViewSet, basename="all-companies")

urlpatterns = [
    path("", include(router.urls)),
]
