from django.contrib import admin

from .models import Notification, NotificationRead

admin.site.register(Notification)
admin.site.register(NotificationRead)
