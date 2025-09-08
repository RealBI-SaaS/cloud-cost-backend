from rest_framework import permissions

from .models import OrganizationMembership


class IsOrgAdminOrOwnerOrReadOnly(permissions.BasePermission):
    """
    Members can only read.
    Admins and Owners can create, update, and delete.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        organization = view.get_organization()

        try:
            membership = OrganizationMembership.objects.get(
                user=request.user, organization=organization
            )
        except OrganizationMembership.DoesNotExist:
            return False

        return membership.role in ["admin", "owner"]
