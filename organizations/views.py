import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import CustomUser

# from rest_framework.permissions import IsAdminUser
from .models import (
    Company,
    CompanyColorScheme,
    Invitation,
    Navigation,
    Organization,
    OrganizationMembership,
    UserGroup,
)
from .serializers import (
    CompanySerializer,
    InvitationSerializer,
    NavigationSerializer,
    OrganizationSerializer,
    UserGroupSerializer,
)

User = get_user_model()


class OrganizationViewSet(viewsets.ModelViewSet):
    """Handles CRUD operations for organizations"""

    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _has_role(self, user, organization, allowed_roles):
        return OrganizationMembership.objects.filter(
            user=user, organization=organization, role__in=allowed_roles
        ).exists()

    def get_queryset(self):
        """Retrieve only organizations where the user is a member"""
        # TODO: optimize with serializers
        if self.request.user.is_staff:
            # return Organization.objects.all()
            return (
                Organization.objects.select_related("company").annotate(  # optimization
                    company_name=F("company__name"),
                    # company_logo=F("company__logo"),
                )
            ).distinct()
        # return Organization.objects.filter(
        #     organizationmembership__user=self.request.user
        # ).distinct()

        return (
            (
                Organization.objects.filter(
                    organizationmembership__user=self.request.user
                )
            )
            .annotate(
                role=F("organizationmembership__role"),
                company_name=F("company__name"),
                # company_logo=F("company__logo"),
            )
            .distinct()
        )

    def perform_create(self, serializer):
        company = serializer.validated_data["company"]

        if company.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied(
                "You can only create organizations for companies you own."
            )

        organization = serializer.save()
        OrganizationMembership.objects.create(
            user=self.request.user, organization=organization, role="owner"
        )

    # def perform_create(self, serializer):
    #     """Create an organization and make the requesting user the owner"""
    #     organization = serializer.save()
    #     # TODO: handle the company relationship instead
    #     # organization.owners.add(self.request.user)  # Add user as owner
    #     OrganizationMembership.objects.create(
    #         user=self.request.user, organization=organization, role="owner"
    #     )

    def update(self, request, *args, **kwargs):
        organization = self.get_object()
        if (
            not self._has_role(request.user, organization, ["owner", "admin"])
            and not request.user.is_staff
        ):
            raise PermissionDenied("You are not allowed to update this organization.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        organization = self.get_object()
        if (
            not self._has_role(request.user, organization, ["owner"])
            and not request.user.is_staff
        ):
            raise PermissionDenied("Only owners can delete the organization.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        """Get all members of an organization with roles"""
        organization = self.get_object()
        members = OrganizationMembership.objects.filter(
            organization=organization
        ).select_related("user")
        return Response(
            [
                {
                    "id": m.user.id,
                    "email": m.user.email,
                    "first_name": m.user.first_name,
                    "last_name": m.user.last_name,
                    "role": m.role,
                }
                for m in members
            ]
        )


class CompanyViewSet(viewsets.ModelViewSet):
    """Handles CRUD operations for companies"""

    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return companies owned by the current user"""
        if self.request.user.is_staff:
            return Company.objects.all()
        return Company.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        """Set the owner of the company to the current user"""
        serializer.save(owner=self.request.user)

    def update(self, request, *args, **kwargs):
        """Allow only the owner to update the company"""
        company = self.get_object()
        if company.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("You are not allowed to update this company.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Allow only the owner to delete the company"""
        company = self.get_object()
        if company.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("You are not allowed to delete this company.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["get"], url_path="organizations")
    def organizations(self, request, pk=None):
        """
        Get all organizations for a specific company (by company ID).
        """
        company = get_object_or_404(Company, id=pk)
        if not request.user.is_staff:
            raise PermissionDenied(
                "You do not have access to this company's organizations."
            )

        organizations = (
            Organization.objects.filter(company=company)
            .select_related("company")
            .annotate(company_name=F("company__name"))
        )
        serializer = OrganizationSerializer(organizations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AllCompaniesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides a read-only list of all companies with search support.
    """

    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAdminUser]

    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ["name"]


class InviteUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _has_role(self, user, organization, allowed_roles):
        return OrganizationMembership.objects.filter(
            user=user, organization=organization, role__in=allowed_roles
        ).exists()

    def post(self, request, org_id):
        email = request.data.get("email")

        if not email:
            return Response(
                {"error": "Invitee email is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            org_uuid = uuid.UUID(str(org_id), version=4)
        except ValueError:
            return Response(
                {"error": "Invalid organization ID format. Must be a valid UUID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            organization = Organization.objects.get(id=org_id)

            if (
                not self._has_role(request.user, organization, ["admin", "owner"])
                and not request.user.is_staff
            ):
                return Response(
                    {"error": "You don't have permission to invite users"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            role = request.data.get("role", "member")

            existing_invite = Invitation.objects.filter(
                organization=organization, invitee_email=email, status="pending"
            ).first()

            if existing_invite:
                if existing_invite.role != role:
                    # Update the role, token, and expiration
                    existing_invite.role = role
                    existing_invite.token = get_random_string(32)
                    existing_invite.expires_at = now() + timedelta(days=7)
                    existing_invite.save()
                invitation = existing_invite
            else:
                invitation = Invitation.create_invitation(
                    organization, request.user, email, role
                )

            invite_link = (
                f"{settings.FRONTEND_BASE_URL}/accept-invitation/{invitation.token}/"
            )
            send_mail(
                "invitation on realbi",
                f"""You are invited to join {organization} as {role}.

                Click here to accept the invitation: {invite_link}""",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=True,
            )

            return Response(
                InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED
            )

        except Organization.DoesNotExist:
            return Response(
                {"error": "Organization not found"}, status=status.HTTP_404_NOT_FOUND
            )


class AcceptInvitationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, token):
        # TODO: protect against acceptance with uninvited user
        try:
            # print(token)
            invitation = Invitation.objects.get(token=token)
            print(invitation.invitee_email)

            # Check if the invitation is expired
            if invitation.expires_at < now():
                return Response(
                    {"error": "Invitation has expired"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if the user exists
            try:
                user = User.objects.get(email=invitation.invitee_email)
            except User.DoesNotExist:
                return Response(
                    {
                        "error": f"No active account found for this email {invitation.invitee_email}"
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Add user to organization
            # TODO: lookout for duplicate memberships with different roles
            membership, created = OrganizationMembership.objects.get_or_create(
                user=user,
                organization=invitation.organization,
                defaults={"role": invitation.role},
            )

            if not created:
                return Response(
                    {"error": "User is already a member of this organization"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Delete invitation after acceptance
            invitation.delete()

            return Response(
                {"message": "Invitation accepted successfully!"},
                status=status.HTTP_200_OK,
            )

        except Invitation.DoesNotExist:
            return Response(
                {"error": "Invalid invitation token"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class DeleteInvitationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, id):
        try:
            invitation = Invitation.objects.get(id=id)

            if (
                not OrganizationMembership.objects.filter(
                    user=request.user,
                    organization=invitation.organization,
                    role__in=["admin", "owner"],
                ).exists()
                and not request.user.is_staff
            ):
                return Response(
                    {"error": "You don't have permission to delete this invitation."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            invitation.delete()

            return Response(
                {"message": "Invitation deleted successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )

        except Invitation.DoesNotExist:
            return Response(
                {"error": "Invitation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


class ListInvitationsView(APIView):
    """
    View to list all invitations for an organization.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, org_id):
        """
        Retrieve all invitations for a given organization.
        """
        invitations = Invitation.objects.filter(organization_id=org_id)
        serializer = InvitationSerializer(invitations, many=True)
        return Response(serializer.data, status=200)


class NavigationViewSet(viewsets.ModelViewSet):
    """Handles CRUD operations for navigation"""

    serializer_class = NavigationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _has_role(self, user, organization, allowed_roles):
        return OrganizationMembership.objects.filter(
            user=user, organization=organization, role__in=allowed_roles
        ).exists()

    def get_queryset(self):
        """Retrieve only navigations belonging to the specified organization"""
        if self.action in ["update", "partial_update", "destroy"]:
            # Skip organization validation in get_queryset for PATCH & DELETE
            return Navigation.objects.all()
        organization_id = self.kwargs.get("organization_id")  # Extract from URL kwargs

        if not organization_id:
            raise ValidationError(
                {"organization": "Organization ID is required in the URL."}
            )
        if (
            not Organization.objects.filter(
                Q(id=organization_id)
                & (
                    Q(organizationmembership__user=self.request.user)
                    # | Q(owners=self.request.user)
                )
            ).exists()
            and not self.request.user.is_staff
        ):
            raise PermissionDenied(
                {"detail": "You are not a member of this organization."}
            )
        return Navigation.objects.filter(organization_id=organization_id)

    def perform_create(self, serializer):
        """Allow only organization owners to create navigation"""
        organization_id = self.request.data.get("organization")

        if not organization_id:
            raise ValidationError({"organization": "This field is required."})

        organization = get_object_or_404(Organization, id=organization_id)

        # Ensure the user is an OWNER of the organization

        if (
            not self._has_role(self.request.user, organization, ["owner", "admin"])
            and not self.request.user.is_staff
        ):
            raise PermissionDenied(
                "You are not allowed to create a navigation in this organization."
            )
        # if self.request.user not in organization.owners.all():
        #     raise PermissionDenied(
        #         "Only organization owners can create navigation items."
        #     )

        # Enforce unique labels within the organization
        label = self.request.data.get("label")
        if Navigation.objects.filter(organization=organization, label=label).exists():
            raise ValidationError(
                {"label": "This label already exists in the organization."}
            )

        serializer.save(organization=organization)

    def update(self, request, *args, **kwargs):
        """Allow only owners of the organization to update the navigation"""
        navigation = self.get_object()
        organization = navigation.organization

        if (
            not self._has_role(request.user, organization, ["owner", "admin"])
            and not request.user.is_staff
        ):
            raise PermissionDenied("You are not allowed to update this navigation.")
        #
        # if request.user not in organization.owners.all():
        #     raise PermissionDenied("You are not allowed to update this navigation.")

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Allow only owners of the organization to delete the navigation"""
        navigation = self.get_object()
        organization = navigation.organization
        if (
            not self._has_role(request.user, organization, ["owner", "admin"])
            and not request.user.is_staff
        ):
            raise PermissionDenied("You are not allowed to delete this navigation.")
        #
        # if request.user not in organization.owners.all():
        #     raise PermissionDenied("You are not allowed to delete this navigation.")
        #
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["patch"], url_path="reorder")
    def reorder_navigation(self, request, *args, **kwargs):
        """
        Reorders children under a single parent or top-level navigations.
        Request format:
        - For top-level:
            {
              "parent_id": null,
              "navigations": [{ "id": "<uuid>", "order": 0 }, ...]
            }
        - For child navigations:
            {
              "parent_id": "<uuid>",
              "navigations": [{ "id": "<uuid>", "order": 0 }, ...]
            }
        """
        parent_id = request.data.get("parent_id")
        navigations = request.data.get("navigations", [])

        if not isinstance(navigations, list):
            return Response({"detail": "navigations must be a list."}, status=400)

        organization_id = self.kwargs.get("organization_id")
        if not organization_id:
            return Response(
                {"detail": "organization_id is required in the URL."}, status=400
            )

        if (
            not Organization.objects.filter(
                Q(id=organization_id)
                & Q(organizationmembership__user=self.request.user)
            ).exists()
            and not self.request.user.is_staff
        ):
            raise PermissionDenied(
                {"detail": "You are not a member of this organization."}
            )

        with transaction.atomic():
            for item in navigations:
                nav_id = item.get("id")
                order = item.get("order")

                if nav_id is None or order is None:
                    continue  # Skip invalid items

                Navigation.objects.filter(
                    id=nav_id,
                    organization_id=organization_id,
                    parent_id=parent_id,  # Works for both null and UUID
                ).update(order=order)

        return Response({"status": "reordered"}, status=status.HTTP_200_OK)


class UpdateMembershipRoleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, org_id, user_id):
        try:
            organization = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response(
                {"error": "Organization not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if (
            not OrganizationMembership.objects.filter(
                user=request.user,
                organization=organization,
                role__in=["admin", "owner"],
            ).exists()
            and not request.user.is_staff
        ):
            return Response(
                {"error": "You don't have permission to update roles."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            membership = OrganizationMembership.objects.get(
                organization=organization, user__id=user_id
            )
        except OrganizationMembership.DoesNotExist:
            return Response(
                {"error": "Membership not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if membership.role == "owner":
            return Response(
                {"error": "Cannot change the role of the owner."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_role = request.data.get("role")
        if new_role not in dict(OrganizationMembership.ROLE_CHOICES):
            return Response(
                {"error": "Invalid role."}, status=status.HTTP_400_BAD_REQUEST
            )

        membership.role = new_role
        membership.save()

        return Response(
            {"message": "Role updated successfully."}, status=status.HTTP_200_OK
        )


class RemoveMemberView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, org_id, user_id):
        try:
            organization = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response(
                {"error": "Organization not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if (
            not OrganizationMembership.objects.filter(
                user=request.user,
                organization=organization,
                role__in=["admin", "owner"],
            ).exists()
            and not request.user.is_staff
        ):
            return Response(
                {"error": "You don't have permission to remove members."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            membership = OrganizationMembership.objects.get(
                organization=organization, user__id=user_id
            )
        except OrganizationMembership.DoesNotExist:
            return Response(
                {"error": "Membership not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if membership.role == "owner":
            return Response(
                {"error": "Cannot remove the organization owner."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership.delete()

        return Response(
            {"message": "Member removed successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )


@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def company_color_scheme(request, comp_id):
    company = Company.objects.get(id=comp_id)
    try:
        scheme = company.color_scheme
    except CompanyColorScheme.DoesNotExist:
        if request.method == "GET":
            return Response({"color_scheme": None})
        scheme = CompanyColorScheme.objects.create(company=company)

    if request.method == "PATCH":
        for field in [
            "primary",
            "sidebar_accent",
            "borders",
            "form_input_background",
            "sidebar_background",
            "sidebar_font_color",
        ]:
            if field in request.data:
                setattr(scheme, field, request.data[field])
        scheme.save()

    data = {
        "primary": scheme.primary,
        "sidebar_accent": scheme.sidebar_accent,
        "borders": scheme.borders,
        "form_input_background": scheme.form_input_background,
        "sidebar_background": scheme.sidebar_background,
        "sidebar_font_color": scheme.sidebar_font_color,
    }
    return Response({"color_scheme": data})


class UserGroupViewSet(viewsets.ModelViewSet):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer

    # TODO: add permission check here

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=False, methods=["get"], url_path="by-org/(?P<org_id>[^/.]+)")
    def by_organization(self, request, org_id=None):
        groups = self.queryset.filter(organization__id=org_id)
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_user(self, request, pk=None):
        group = self.get_object()
        user_id = request.data.get("user_id")
        try:
            user = CustomUser.objects.get(id=user_id)
            group.users.add(user)
            return Response({"status": "user added"})
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

    @action(detail=True, methods=["post"])
    def remove_user(self, request, pk=None):
        group = self.get_object()
        user_id = request.data.get("user_id")
        try:
            user = CustomUser.objects.get(id=user_id)
            group.users.remove(user)
            return Response({"status": "user removed"})
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
