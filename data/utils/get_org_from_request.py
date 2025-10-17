import uuid

from rest_framework.exceptions import NotFound, ValidationError

from company.models import Organization


def get_organization(self):
    """
    Retrieve the company from the request's query param or URL kwarg.
    """
    organization_id = self.kwargs.get(
        "organization_id"
    ) or self.request.query_params.get("organization_id")

    if not organization_id:
        raise ValidationError({"organization_id": "This field is required."})

    try:
        uuid.UUID(str(organization_id), version=4)
    except ValueError:
        raise ValidationError(
            {"organization_id": "Invalid Organization ID format. Must be a valid UUID."}
        )

    try:
        return Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        raise NotFound({"organization_id": "Organization not found."})
