from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer
from rest_framework import serializers

from .models import Company


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = "__all__"


class UserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = get_user_model()
        fields = ("id", "email", "password")


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "created_at", "updated_at"]


#
# class CompanyMembershipSerializer(serializers.ModelSerializer):
#     company = CompanySerializer(read_only=True)
#     company_id = serializers.UUIDField(write_only=True, required=False)
#     company_name = serializers.CharField(write_only=True, required=False)
#     user_id = serializers.UUIDField(read_only=True)
#
#     class Meta:
#         model = CompanyMember
#         fields = [
#             "id",
#             "company",
#             "company_id",
#             "company_name",
#             "user_id",
#             "role",
#             "created_at",
#             "updated_at",
#         ]
#         read_only_fields = ["id", "created_at", "updated_at", "role"]
#
#     def validate(self, data):
#         """
#         Validate that either company_id or company_name is provided, but not both.
#         """
#         company_id = data.get("company_id")
#         company_name = data.get("company_name")
#
#         if not company_id and not company_name:
#             raise serializers.ValidationError(
#                 "Either company_id or company_name must be provided"
#             )
#         if company_id and company_name:
#             raise serializers.ValidationError(
#                 "Cannot provide both company_id and company_name"
#             )
#
#         return data
