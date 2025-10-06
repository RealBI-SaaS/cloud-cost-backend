from rest_framework import serializers

from .models import Notification, NotificationRead


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["id", "title", "message", "link", "type", "created_at", "is_read"]

    def get_is_read(self, obj):
        user = self.context["request"].user
        read_obj = NotificationRead.objects.filter(notification=obj, user=user).first()
        return read_obj.is_read if read_obj else False


class NotificationReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationRead
        fields = ["id", "is_read", "read_at"]
        read_only_fields = ["id", "read_at"]
