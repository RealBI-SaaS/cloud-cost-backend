import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils.timezone import now
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Invitation, Organization, OrganizationMembership
from .serializers import InvitationSerializer, OrganizationSerializer

User = get_user_model()


class OrganizationViewSet(viewsets.ModelViewSet):
    """Handles CRUD operations for organizations"""

    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Retrieve only organizations where the user is a member"""
        return Organization.objects.filter(
            organizationmembership__user=self.request.user
        ).distinct()

    def perform_create(self, serializer):
        """Create an organization and make the requesting user the owner"""
        organization = serializer.save()
        organization.owners.add(self.request.user)  # Add user as owner
        OrganizationMembership.objects.create(
            user=self.request.user, organization=organization, role="owner"
        )

    def update(self, request, *args, **kwargs):
        """Allow only owners to update"""
        organization = self.get_object()
        if self.request.user not in organization.owners.all():
            raise PermissionDenied("You are not allowed to update this organization.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Allow only owners to delete"""
        organization = self.get_object()
        if self.request.user not in organization.owners.all():
            raise PermissionDenied("You are not allowed to delete this organization.")
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
            print(org_id)
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
            print(token)
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
