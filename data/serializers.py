from rest_framework import serializers

from .models import CloudAccount


class CloudAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudAccount
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "company")
