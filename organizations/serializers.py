from rest_framework import serializers

from .models import Company, Invitation, Navigation, Organization

#
# class OrganizationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Organization
#         fields = "__all__"
#         # read_only = "owners"
#
#


class OrganizationSerializer(serializers.ModelSerializer):
    role = serializers.CharField(read_only=True)

    class Meta:
        model = Organization
        fields = "__all__"  # includes model fields
        extra_fields = ["role", "company_name"]  # manually annotated field

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if hasattr(instance, "role"):
            rep["role"] = instance.role
        if hasattr(instance, "company_name"):
            rep["company_name"] = instance.company_name
        return rep


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"
        read_only_fields = ["id", "owner", "created_at", "updated_at"]


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ["id", "organization", "invitee_email", "role", "token", "expires_at"]


class NavigationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Navigation
        fields = [
            "id",
            "label",
            "icon",
            "organization",
            "parent",
            "created_at",
            "updated_at",
            "sub_navigations",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "sub_navigations"]

    def validate(self, data):
        """Ensure label uniqueness within an organization, only on creation."""
        request_method = self.context["request"].method

        # Only enforce label uniqueness on POST (i.e., create)
        if request_method == "POST":
            organization = data.get("organization")
            label = data.get("label")

            if Navigation.objects.filter(
                organization=organization, label=label
            ).exists():
                raise serializers.ValidationError(
                    {
                        "label": "This navigation label already exists in the organization."
                    }
                )

        return data

    def get_sub_navigations(self, obj):
        # Only one level of nesting as requested
        children = obj.sub_navigations.all()
        return NavigationChildSerializer(children, many=True).data


class NavigationChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = Navigation
        fields = [
            "id",
            "label",
            "icon",
            "organization",
            "parent",
            "created_at",
            "updated_at",
        ]
