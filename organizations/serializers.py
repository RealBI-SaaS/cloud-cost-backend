from rest_framework import serializers

from .models import Company, CompanyMembership, Invitation


class CompanyMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyMembership
        fields = ["role"]


class CompanySerializer(serializers.ModelSerializer):
    membership = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = "__all__"
        read_only_fields = ["id", "membership", "created_at", "updated_at"]

    def get_membership(self, company):
        user = self.context["request"].user
        try:
            # membership = CompanyMembership.objects.get(user=user)
            membership = CompanyMembership.objects.filter(user=user).first()
            return CompanyMembershipSerializer(membership).data
        except CompanyMembership.DoesNotExist:
            return None


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = [
            "id",
            "company",
            "invitee_email",
            "role",
            "token",
            "expires_at",
        ]
