from django.urls import include, path

urlpatterns = [
    path("organization/", include("company.urls.org")),
    path("company/", include("company.urls.org")),
]
