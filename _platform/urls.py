from django.urls import path

from .views import NotificationListView, NotificationReadUpdateView

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path(
        "notifications/<uuid:pk>/read/",
        NotificationReadUpdateView.as_view(),
        name="notification-read",
    ),
]
