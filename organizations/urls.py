from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AcceptInvitationView, InviteUserView, OrganizationViewSet

# Create a router and register our ViewSets with it.
router = DefaultRouter()
router.register(r"organization", OrganizationViewSet, basename="organization")


urlpatterns = [
    path("", include(router.urls)),
    path(
        "members/<str:org_id>/invite/",
        InviteUserView.as_view(),
        name="invite_user",
    ),
    path(
        "invitations/accept/<str:token>/",
        AcceptInvitationView.as_view(),
        name="accept_invitation",
    ),
]
