from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import Organization, OrganizationMembership
from .serializers import OrganizationSerializer


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
                {"id": m.user.id, "username": m.user.username, "role": m.role}
                for m in members
            ]
        )
