import uuid

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class NotificationTypes(models.TextChoices):
    SUCCESS = "success", "Success"
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    ERROR = "error", "Error"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # organization = models.ForeignKey(
    #     Organization, on_delete=models.CASCADE, related_name="notifications"
    # )
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.URLField(max_length=500, null=True, blank=True)
    type = models.CharField(
        max_length=10,
        choices=NotificationTypes.choices,
        default=NotificationTypes.INFO,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    readers = models.ManyToManyField(
        User, through="NotificationRead", related_name="notifications"
    )

    def __str__(self):
        return f"{self.type} - {self.title}"


class NotificationRead(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.user} - {self.notification.title}"
