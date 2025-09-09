from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers


@extend_schema_serializer(component_name="CustomUser")
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_google_user",
        )
        read_only_fields = ["is_staff", "is_google_user"]


class UserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = get_user_model()
        fields = ("id", "email", "password", "first_name", "last_name")


class GoogleOAuthErrorSerializer(serializers.Serializer):
    error = serializers.CharField()
    response = serializers.DictField(required=False)


# magic link serializers: 1. for request 2. for validation
class MagicLinkRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class MagicLinkVerifySerializer(serializers.Serializer):
    token = serializers.CharField()


# ot code serializers
class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
