from django.urls import include, path
from rest_framework.routers import DefaultRouter

from company.views.org import (
    AcceptInvitationView,
    DeleteInvitationView,
    InviteUserView,
    ListInvitationsView,
    OrganizationViewSet,
    RemoveMemberView,
    UpdateMembershipRoleView,
)

router = DefaultRouter()
router.register(r"", OrganizationViewSet, basename="organization")


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
    path(
        "invitations/revoke/<uuid:id>/",
        DeleteInvitationView.as_view(),
        name="revoke-invitations",
    ),
    # PATCH to update role
    path(
        "<uuid:org_id>/members/<uuid:user_id>/role/", UpdateMembershipRoleView.as_view()
    ),
    # DELETE to remove a member
    path("<uuid:org_id>/members/<uuid:user_id>/", RemoveMemberView.as_view()),
]
