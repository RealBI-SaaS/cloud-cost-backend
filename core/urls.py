"""
URL configuration for the core project.

The ``urlpatterns`` list routes URLs to views.
For more information, see the Django docs:
https://docs.djangoproject.com/en/5.1/topics/http/urls/

"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from authentication.views.user import api_documentation

urlpatterns = (
    [
        path("admin/", admin.site.urls),
        path("myauth/", include("authentication.urls")),
        path("data/", include("data.urls")),
        # company urls
        path("company/", include("company.urls.company")),
        path("organization/", include("company.urls.org")),
        re_path(r"^auth/", include("djoser.urls")),
        re_path(r"^auth/", include("djoser.urls.jwt")),
        path("", api_documentation, name="api-documentation"),
        # swagger docs
        path("schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "swagger/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path(
            "redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
        ),
    ]
    + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
)


# admin page
admin.site.site_header = "NumLK Admin"
admin.site.site_title = "NumLK Admin Portal"
admin.site.index_title = "Welcome to NumLK System Admin Portal"
