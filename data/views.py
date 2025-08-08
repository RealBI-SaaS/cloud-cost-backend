from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError

from .models import CloudAccount, Company
from .serializers import CloudAccountSerializer


class CloudAccountViewSet(viewsets.ModelViewSet):
    serializer_class = CloudAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_company(self):
        """
        Retrieve the company from the request's query param or URL kwarg.
        """
        company_id = self.kwargs.get("company_id") or self.request.query_params.get(
            "company_id"
        )
        if not company_id:
            raise ValidationError({"company_id": "This field is required."})

        try:
            return Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            raise ValidationError({"company_id": "Invalid company ID."})

    def get_queryset(self):
        company = self.get_company()
        return CloudAccount.objects.filter(company=company)

    def perform_create(self, serializer):
        company = self.get_company()
        serializer.save(company=company).save(company=user_company)
