from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AcceptInvitationView,
    InviteUserView,
    ListInvitationsView,
    NavigationViewSet,
    OrganizationViewSet,
)

# Create a router and register our ViewSets with it.
router = DefaultRouter()
router.register(r"organization", OrganizationViewSet, basename="organization")
router.register(r"navigation", NavigationViewSet, basename="navigation")


urlpatterns = [
    path("", include(router.urls)),
    path(
        "<str:org_id>/invite/",
        InviteUserView.as_view(),
        name="invite_user",
    ),
    path(
        "invitations/accept/<str:token>/",
        AcceptInvitationView.as_view(),
        name="accept_invitation",
    ),
    path(
        "<uuid:org_id>/invitations/",
        ListInvitationsView.as_view(),
        name="list-invitations",
    ),
]
