from rest_framework import serializers

from .models import Invitation, Navigation, Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"
        read_only = "owners"


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ["id", "organization", "invitee_email", "role", "token", "expires_at"]


class NavigationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Navigation
        fields = ["id", "label", "icon", "organization", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

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
