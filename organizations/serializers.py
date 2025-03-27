from rest_framework import serializers

from organizations.models import Organization

from .models import Invitation, Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"
        read_only = "owners"


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ["id", "organization", "invitee_email", "role", "token", "expires_at"]
