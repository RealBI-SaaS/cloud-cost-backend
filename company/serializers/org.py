from rest_framework import serializers

from company.models import Invitation, Organization


class OrganizationSerializer(serializers.ModelSerializer):
    role = serializers.CharField(read_only=True)

    class Meta:
        model = Organization
        fields = "__all__"
        extra_fields = ["role", "company_name"]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if hasattr(instance, "role"):
            rep["role"] = instance.role
        if hasattr(instance, "company_name"):
            rep["company_name"] = instance.company_name
        return rep


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = [
            "id",
            "organization",
            "invitee_email",
            "role",
            "token",
            "expires_at",
        ]


class InviteUserSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(
        choices=["admin", "member", "viewer"],  # adjust roles as needed
        default="member",
        required=False,
    )


# class InvitationSerializer(serializers.Serializer):
#     email = serializers.EmailField()
#     role = serializers.ChoiceField(choices=["member", "admin"], default="member")
#
# fields = ["role"]
