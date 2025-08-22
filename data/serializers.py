from rest_framework import serializers

from .models import CloudAccount


class CloudAccountSerializer(serializers.ModelSerializer):
    company = serializers.UUIDField(source="company.id", read_only=True)

    class Meta:
        model = CloudAccount
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "company")


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


class MonthlyServiceTotalsEntrySerializer(serializers.Serializer):
    month = serializers.DateField()
    total_usage = serializers.FloatField()
    total_cost = serializers.FloatField()


class MonthlyServiceTotalsSerializer(serializers.Serializer):
    service_name = serializers.CharField()
    monthly = MonthlyServiceTotalsEntrySerializer(many=True)
