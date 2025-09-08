from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from company.models import Company, Organization
from company.serializers.company import CompanySerializer
from company.serializers.org import OrganizationSerializer


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
        # FIX: since queryset already filters it out no need to verify
        if company.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("You are not allowed to update this company.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Allow only the owner to delete the company"""
        company = self.get_object()
        # FIX: since queryset already filters it out no need to verify
        if company.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("You are not allowed to delete this company.")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["get"], url_path="organizations")
    def organizations(self, request, pk=None):
        """
        Get all organizations for a specific company (by company ID) for admins.
        Its purpose is not for user functionalities but rather for admin settings, use base organization endpoints for fetching users' organizations.
        """
        company = get_object_or_404(Company, id=pk)
        # TODO: recheck this priviledge control
        if (
            # OrganizationMembership.objects.filter(company=company, user=request.user)
            not request.user.is_staff
        ):
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
