from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

# from rest_framework.permissions import IsAdminUser
from .models import (
    Company,
    CompanyMembership,
    Invitation,
)
from .serializers import CompanySerializer, InvitationSerializer, InviteUserSerializer

User = get_user_model()


class CompanyViewSet(viewsets.ModelViewSet):
    """Handles CRUD operations for companies"""

    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        return {"request": self.request}

    def is_company_owner(self, company, user):
        if user.is_staff:
            return True
        return (
            CompanyMembership.objects.filter(
                company=company, user=user, role="owner"
            ).exists()
            or CompanyMembership.objects.filter(
                company=company, user=user, role="admin"
            ).exists()
        )

    def get_queryset(self):
        """Return companies owned by the current user"""
        if self.request.user.is_staff:
            return Company.objects.all()
        # return Company.objects.all()
        return Company.objects.filter(companymembership__user=self.request.user)

    def perform_create(self, serializer):
        """Create the company and add the current user as owner in CompanyMembership."""
        company = serializer.save()  # Save the company first

        CompanyMembership.objects.create(
            user=self.request.user, company=company, role="owner"
        )

        return company

    def update(self, request, *args, **kwargs):
        # print("EDDIT", *args, **kwargs)
        """Allow only company owners or staff to update"""
        company = self.get_object()
        if not self.is_company_owner(company, request.user):
            raise PermissionDenied("You are not allowed to update this company.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Allow only company owners or staff to delete"""
        company = self.get_object()
        if not self.is_company_owner(company, request.user):
            raise PermissionDenied("You are not allowed to delete this company.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        """Get all members of a company with roles"""
        company = self.get_object()
        members = CompanyMembership.objects.filter(company=company).select_related(
            "user"
        )
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


class AllCompaniesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides a read-only list of all companies with search support.
    """

    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAdminUser]

    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ["name"]


@extend_schema(
    request=InviteUserSerializer,
    # responses={201: OpenApiTypes.OBJECT},  # optional, or define a response serializer
    description="Invite a user to a company by email. Admin/Owner only.",
    summary="Invite User",
)
class InviteUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _has_role(self, user, company, allowed_roles):
        return CompanyMembership.objects.filter(
            user=user, company=company, role__in=allowed_roles
        ).exists()

    def post(self, request, company_id):
        # email = request.data.get("email")
        # role = request.data.get("role", "member")
        #
        # if not email:
        #     return Response(
        #         {"error": "Invitee email is missing"},
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )
        #
        # try:
        #     org_uuid = uuid.UUID(str(company_id), version=4)
        # except ValueError:
        #     return Response(
        #         {"error": "Invalid company ID format. Must be a valid UUID."},
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )

        serializer = InviteUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        role = serializer.validated_data.get("role", "member")

        try:
            company = Company.objects.get(id=company_id)

            if (
                not self._has_role(request.user, company, ["admin", "owner"])
                and not request.user.is_staff
            ):
                return Response(
                    {"error": "You don't have permission to invite users"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            existing_invite = Invitation.objects.filter(
                company=company, invitee_email=email, status="pending"
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
                    company, request.user, email, role
                )

                # assign user groups
            # if groups:
            #     invitation.user_groups.set(groups)

            invite_link = (
                f"{settings.FRONTEND_BASE_URL}/accept-invitation/{invitation.token}/"
            )

            html_message = render_to_string(
                "email/invitation.html",
                {
                    "company": company,
                    "role": role,
                    "invite_link": invite_link,
                },
            )

            send_mail(
                subject=f"You're Invited to Join {company} on Realbi!",
                message="",  # Plain text fallback can go here if you want
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=True,
            )
            return Response(
                InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED
            )

        except Company.DoesNotExist:
            return Response(
                {"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND
            )


class AcceptInvitationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, token):
        try:
            invitation = Invitation.objects.get(token=token)

            # TODO: protect against acceptance with uninvited user
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

            # TODO: lookout for duplicate memberships with different roles
            membership, created = CompanyMembership.objects.get_or_create(
                user=user,
                company=invitation.company,
                defaults={"role": invitation.role},
            )

            if not created:
                return Response(
                    {"error": "User is already a member of this company"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Add user to the invited user groups
            # for group in invitation.user_groups.all():
            #     group.users.add(user)

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
                not CompanyMembership.objects.filter(
                    user=request.user,
                    company=invitation.company,
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
    View to list all invitations for an company.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, company_id):
        """
        Retrieve all invitations for a given company.
        """
        invitations = Invitation.objects.filter(company_id=company_id)
        serializer = InvitationSerializer(invitations, many=True)
        return Response(serializer.data, status=200)


class UpdateMembershipRoleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, company_id, user_id):
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response(
                {"error": "Company not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if (
            not CompanyMembership.objects.filter(
                user=request.user,
                company=company,
                role__in=["admin", "owner"],
            ).exists()
            and not request.user.is_staff
        ):
            return Response(
                {"error": "You don't have permission to update roles."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            membership = CompanyMembership.objects.get(
                company=company, user__id=user_id
            )
        except CompanyMembership.DoesNotExist:
            return Response(
                {"error": "Membership not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if membership.role == "owner":
            return Response(
                {"error": "Cannot change the role of the owner."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_role = request.data.get("role")
        if new_role not in dict(CompanyMembership.ROLE_CHOICES):
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

    def delete(self, request, company_id, user_id):
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response(
                {"error": "Company not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if (
            not CompanyMembership.objects.filter(
                user=request.user,
                company=company,
                role__in=["admin", "owner"],
            ).exists()
            and not request.user.is_staff
        ):
            return Response(
                {"error": "You don't have permission to remove members."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            membership = CompanyMembership.objects.get(
                company=company, user__id=user_id
            )
        except CompanyMembership.DoesNotExist:
            return Response(
                {"error": "Membership not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if membership.role == "owner":
            return Response(
                {"error": "Cannot remove the company owner."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership.delete()

        return Response(
            {"message": "Member removed successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )
