import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import F
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from company.models import (
    Invitation,
    Organization,
    OrganizationMembership,
)
from company.serializers.company import CompanySerializer
from company.serializers.org import (
    InvitationSerializer,
    InviteUserSerializer,
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
        # TODO: optimize with serializers
        if self.request.user.is_staff:
            return (
                Organization.objects.select_related("company").annotate(
                    company_name=F("company__name"),
                )
            ).distinct()
        return (
            (
                Organization.objects.filter(
                    organizationmembership__user=self.request.user
                )
            )
            .annotate(
                role=F("organizationmembership__role"),
                company_name=F("company__name"),
            )
            .distinct()
        )

    def perform_create(self, serializer):
        """Create a new Organization"""
        company = serializer.validated_data["company"]

        if company.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied(
                "You can only create organizations for companies you own."
            )

        organization = serializer.save()
        OrganizationMembership.objects.create(
            user=self.request.user, organization=organization, role="owner"
        )

    def update(self, request, *args, **kwargs):
        organization = self.get_object()
        if (
            not self._has_role(request.user, organization, ["owner", "admin"])
            and not request.user.is_staff
        ):
            raise PermissionDenied("You are not allowed to update this organization.")
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a specific Organization",
    )
    def destroy(self, request, *args, **kwargs):
        organization = self.get_object()
        if (
            not self._has_role(request.user, organization, ["owner"])
            and not request.user.is_staff
        ):
            raise PermissionDenied("Only owners can delete the organization.")
        return super().destroy(request, *args, **kwargs)

    # override views for docs
    @extend_schema(
        summary="List organizations",
        description="Retrieve a list of all organizations for staff and only those you are a member of for non-staff users.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create organization",
        description="Create a new organization with the given data.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

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

<<<<<<< HEAD
    @extend_schema(
        responses=inline_serializer(
            name="CompanyWithOwnership",
            fields={
                "id": serializers.UUIDField(),
                "name": serializers.CharField(),
                "theme": serializers.CharField(),
                "created_at": serializers.DateTimeField(),
                "updated_at": serializers.DateTimeField(),
                "owner": serializers.UUIDField(),
                "is_owner": serializers.BooleanField(),
            },
        )
    )
=======
>>>>>>> de1d7d5 ([feat]: comp info for an org)
    @action(detail=True, methods=["get"])
    def company(self, request, pk=None):
        """Get the company info of this organization including user's ownership data"""
        organization = self.get_object()
        company = organization.company

        is_owner = company.owner == request.user or request.user.is_staff

        serializer = CompanySerializer(company, context={"request": request})
        data = serializer.data
        data["is_owner"] = is_owner

        return Response(data)


# TODO: make sure to only allow admins and owners
class InviteUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = InviteUserSerializer

    def _has_role(self, user, organization, allowed_roles):
        return OrganizationMembership.objects.filter(
            user=user, organization=organization, role__in=allowed_roles
        ).exists()

    @extend_schema(
        summary="Invite a user to an organization.",
        description="Expects email and an optional role whick defaults to 'member' if ignored.",
    )
    def post(self, request, org_id):
        email = request.data.get("email")
        role = request.data.get("role", "member")

        if not email:
            return Response(
                {"error": "Invitee email is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            uuid.UUID(str(org_id), version=4)
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

            html_message = render_to_string(
                "email/invitation.html",
                {
                    "organization": organization,
                    "role": role,
                    "invite_link": invite_link,
                },
            )

            send_mail(
                subject=f"You're Invited to Join {organization} on Realbi!",
                message="",  # Plain text fallback can go here if you want
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
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

    def get(self, request, token):
        try:
            invitation = Invitation.objects.get(token=token)
            if not request.user.email == invitation.invitee_email:
                return Response(
                    {
                        "error": "Wrong user claiming invitation, signin with the invited email."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

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
            _, created = OrganizationMembership.objects.get_or_create(
                user=user,
                organization=invitation.organization,
                defaults={"role": invitation.role},
            )

            if not created:
                return Response(
                    {"error": "User is already a member of this organization"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # NOTE: Delete invitation after acceptance
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

    @extend_schema(
        summary="Delete a specific invitation",
    )
    def delete(self, request, id):
        try:
            invitation = Invitation.objects.get(id=id)

            # TODO: refactor permission
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

    @extend_schema(
        summary="list invitations in an organization.",
    )
    def get(self, request, org_id):
        """
        Retrieve all invitations for a given organization.
        """
        invitations = Invitation.objects.filter(organization_id=org_id)
        serializer = InvitationSerializer(invitations, many=True)
        return Response(serializer.data, status=200)


class UpdateMembershipRoleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Update role of an organization member.",
    )
    def patch(self, request, org_id, user_id):
        try:
            organization = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response(
                {"error": "Organization not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # TODO: refactor this, simple fix
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

        # FIX: This too
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
