from rest_framework import serializers

from .models import CloudAccount


class CloudAccountSerializer(serializers.ModelSerializer):
    # ?
    # organization = serializers.UUIDField(source="organization.id", read_only=True)
    organization = serializers.UUIDField(source="organization_id", read_only=True)

    class Meta:
        model = CloudAccount
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "organization")


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
