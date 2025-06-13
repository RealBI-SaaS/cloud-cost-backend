from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AcceptInvitationView,
    AllCompaniesViewSet,
    CompanyViewSet,
    DeleteInvitationView,
    InviteUserView,
    ListInvitationsView,
    NavigationViewSet,
    OrganizationViewSet,
    RemoveMemberView,
    UpdateMembershipRoleView,
    UserGroupViewSet,
    company_color_scheme,
)

# Create a router and register our ViewSets with it.
router = DefaultRouter()
router.register(r"organization", OrganizationViewSet, basename="organization")
router.register(r"company", CompanyViewSet, basename="company")
router.register(r"all-companies", AllCompaniesViewSet, basename="all-companies")
router.register(r"user-group", UserGroupViewSet, basename="user-groups")
# router.register(
#     r"<uuid:organization_id>/navigation", NavigationViewSet, basename="navigation"
# )

router.register(
    r"(?P<organization_id>[^/.]+)/navigation",
    NavigationViewSet,
    basename="navigation",
)
user_group_create = UserGroupViewSet.as_view({"post": "create"})

urlpatterns = [
    path("", include(router.urls)),
    # path(
    #     "navigation/<uuid:organization_id>/",
    #     NavigationViewSet.as_view({"get": "list"}),
    #     name="navigation-list",
    # ),
    # from this
    # path(
    #     "<uuid:organization_id>/navigation/",
    #     NavigationViewSet.as_view({"get": "list"}),
    # ),
    # path(
    #     "navigation/",
    #     NavigationViewSet.as_view({"post": "create"}),
    # ),
    # path(
    #     "navigation/<uuid:pk>/",
    #     NavigationViewSet.as_view({"patch": "partial_update", "delete": "destroy"}),
    # ),
    # to this
    # path(
    #     "<uuid:organization_id>/navigation/",
    #     NavigationViewSet.as_view({"get": "list", "post": "create"}),
    #     name="navigation-list",
    # ),
    # path(
    #     "/navigation/<uuid:pk>/",
    #     NavigationViewSet.as_view(
    #         {"get": "retrieve", "patch": "update", "delete": "destroy"}
    #     ),
    #     name="navigation-detail",
    # ),
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
    path(
        "<uuid:org_id>/user-group/",
        user_group_create,
        name="usergroup-create",
    ),
    # get, patch company_color_scheme
    path(
        "<uuid:comp_id>/colorscheme/", company_color_scheme, name="company-color-scheme"
    ),
]
