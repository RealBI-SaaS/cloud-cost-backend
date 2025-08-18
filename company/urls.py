from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AcceptInvitationView,
    CompanyViewSet,
    DeleteInvitationView,
    InviteUserView,
    ListInvitationsView,
    RemoveMemberView,
    UpdateMembershipRoleView,
)

# Create a router and register our ViewSets with it.
router = DefaultRouter()
router.register(r"", CompanyViewSet, basename="company")
urlpatterns = [
    path("", include(router.urls)),
    path(
        "<str:company_id>/invite/",
        InviteUserView.as_view(),
        name="invite_user",
    ),
    path(
        "invitations/accept/<str:token>/",
        AcceptInvitationView.as_view(),
        name="accept_invitation",
    ),
    path(
        "<uuid:company_id>/invitations/",
        ListInvitationsView.as_view(),
        name="list-invitations",
    ),
    path(
        "invitations/revoke/<uuid:id>/",
        DeleteInvitationView.as_view(),
        name="revoke-invitations",
    ),
    # PATCH to update role
    path(
        "<uuid:company_id>/members/<uuid:user_id>/role/",
        UpdateMembershipRoleView.as_view(),
    ),
    # DELETE to remove a member
    path("<uuid:company_id>/members/<uuid:user_id>/", RemoveMemberView.as_view()),
]
