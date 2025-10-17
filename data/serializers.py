from rest_framework import serializers

from .models import CloudAccount, CustomExpense, CustomExpenseVendor


class CloudAccountSerializer(serializers.ModelSerializer):
    # ?
    # organization = serializers.UUIDField(source="organization.id", read_only=True)
    organization = serializers.UUIDField(source="organization_id", read_only=True)

    class Meta:
        model = CloudAccount
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "organization",
            "account_id",
            "vendor",
        )


# cost views


class DailyCostSerializer(serializers.Serializer):
    day = serializers.DateField()
    total_cost = serializers.DecimalField(max_digits=20, decimal_places=2)


class CostByServiceSerializer(serializers.Serializer):
    service_name = serializers.CharField()
    total_cost = serializers.DecimalField(max_digits=20, decimal_places=2)


class CostByRegionSerializer(serializers.Serializer):
    region = serializers.CharField(allow_blank=True)
    total_cost = serializers.DecimalField(max_digits=20, decimal_places=2)


class UsageByServiceDaySerializer(serializers.Serializer):
    service_name = serializers.CharField()
    day = serializers.DateField()
    total_usage = serializers.DecimalField(max_digits=20, decimal_places=2)


class CostSummaryByServiceSerializer(serializers.Serializer):
    today = serializers.DictField(
        child=serializers.DecimalField(max_digits=20, decimal_places=2)
    )
    this_month = serializers.DictField(
        child=serializers.DecimalField(max_digits=20, decimal_places=2)
    )


class CostSummaryByAccountSerializer(serializers.Serializer):
    total_month = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_today = serializers.DecimalField(max_digits=20, decimal_places=2)


class CostSummaryByOrgRequestSerializer(serializers.Serializer):
    org_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of organization UUIDs to fetch cost summary for",
    )


class RangeSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()


class CostSummaryByOrgSerializer(serializers.Serializer):
    """
    Serializer for multiple orgs' cost summary.
    Includes range info and nested org→account→summary mapping.
    """

    range = RangeSerializer()

    # Dynamic dict of org IDs → dict of account IDs → CostSummaryByAccountSerializer
    results = serializers.DictField(
        child=serializers.DictField(child=CostSummaryByAccountSerializer()),
        help_text="Mapping of org_id → account_id → cost summary data",
    )


class MonthlyServiceTotalsEntrySerializer(serializers.Serializer):
    month = serializers.DateField()
    total_usage = serializers.FloatField()
    total_cost = serializers.FloatField()


class MonthlyServiceTotalsSerializer(serializers.Serializer):
    service_name = serializers.CharField()
    monthly = MonthlyServiceTotalsEntrySerializer(many=True)


class CustomExpenseVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomExpenseVendor
        fields = ["id", "name", "website", "logo", "description"]


class CustomExpenseSerializer(serializers.ModelSerializer):
    vendor = CustomExpenseVendorSerializer(read_only=True)
    vendor_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomExpenseVendor.objects.all(),
        source="vendor",
        write_only=True,
        required=False,
    )

    class Meta:
        model = CustomExpense
        fields = [
            "id",
            "vendor",
            "vendor_id",
            "custom_name",
            "amount",
            "currency",
            "frequency",
            "created_at",
        ]

    def validate(self, attrs):
        vendor = attrs.get("vendor")
        custom_name = attrs.get("custom_name")

        if not vendor and not custom_name:
            raise serializers.ValidationError(
                "You must provide either a vendor_id or a custom_name."
            )

        return attrs

    def create(self, validated_data):
        # If a vendor is provided, ignore custom_name
        if validated_data.get("vendor"):
            validated_data["custom_name"] = None
        return CustomExpense.objects.create(**validated_data)
