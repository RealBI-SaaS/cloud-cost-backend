import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

# from rest_framework.permissions import IsAdminUser
from .models import (
    Company,
    Invitation,
    Navigation,
    Organization,
    OrganizationMembership,
)
from .serializers import (
    CompanySerializer,
    InvitationSerializer,
    NavigationSerializer,
    OrganizationSerializer,
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
        # TODO: use the role from the organization-membership while listing orgs
        if self.request.user.is_staff:
            return Organization.objects.all()
        return Organization.objects.filter(
            organizationmembership__user=self.request.user
        ).distinct()

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

        organizations = Organization.objects.filter(company=company)
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

    def post(self, request, org_id):
        email = request.data.get("email")

        if not email:
            return Response(
                {"error": "Invitee email is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            org_uuid = uuid.UUID(str(org_id), version=4)  # Ensures a valid UUID
        except ValueError:
            return Response(
                {"error": "Invalid organization ID format. Must be a valid UUID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # print(org_id)
            organization = Organization.objects.get(id=org_id)

            # Ensure the request user is an owner or admin
            if (
                request.user not in organization.owners.all()
                and request.user not in organization.members.all()
            ):
                return Response(
                    {"error": "You don't have permission to invite users"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            role = request.data.get("role", "member")  # Default to member
            invitation = Invitation.create_invitation(
                organization, request.user, email, role
            )

            # Send an email with the invitation token (you need an email backend configured)
            invite_link = (
                f"{settings.FRONTEND_BASE_URL}/accept-invitation/{invitation.token}/"
            )
            send_mail(
                "You're invited to join an organization!",
                f"Click here to accept the invitation: {invite_link}",
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
        try:
            # print(token)
            invitation = Invitation.objects.get(token=token)

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
