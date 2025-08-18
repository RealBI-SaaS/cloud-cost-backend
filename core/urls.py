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

from authentication.views import api_documentation

urlpatterns = (
    [
        path("admin/", admin.site.urls),
        path("myauth/", include("authentication.urls")),
        path("data/", include("data.urls")),
        path("company/", include("company.urls")),
        re_path(r"^auth/", include("djoser.urls")),
        re_path(r"^auth/", include("djoser.urls.jwt")),
        path("", api_documentation, name="api-documentation"),
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
admin.site.site_header = "RealBI Admin"
admin.site.site_title = "RealBI Admin Portal"
admin.site.index_title = "Welcome to RealBI System Admin Portal"
