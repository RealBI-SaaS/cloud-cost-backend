from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, NotificationRead
from .serializers import NotificationReadSerializer, NotificationSerializer


@extend_schema(
    summary="List Notifications",
    description=(
        "Returns all notifications for the authenticated user.\n\n"
        "- Each notification includes its read/unread status.\n"
        "- Results are ordered by creation time (newest first)."
    ),
    responses={200: NotificationSerializer(many=True)},
)
class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(readers=user).order_by("-created_at")


@extend_schema(
    summary="Mark Notification as Read/Unread",
    description=(
        "Update the read status of a specific notification for the authenticated user.\n\n"
        '- Pass `{ "is_read": true/True/1 }` to mark as read.\n'
        '- Pass `{ "is_read": false/False/0 }` to mark as unread.\n'
    ),
    request=NotificationReadSerializer,
    responses={
        200: NotificationReadSerializer,
        404: OpenApiResponse(
            description="Notification not found or not assigned to user."
        ),
    },
)
class NotificationReadUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        user = request.user
        notification = get_object_or_404(Notification, pk=pk, readers=user)

        notif_read, created = NotificationRead.objects.get_or_create(
            notification=notification, user=user
        )

        is_read = request.data.get("is_read", True)
        if isinstance(is_read, str):
            if is_read.lower() in ("true", "1"):
                is_read = True
            elif is_read.lower() in ("false", "0"):
                is_read = False
            else:
                return Response(
                    {"detail": "Invalid value for is_read"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif not isinstance(is_read, bool):
            return Response(
                {"detail": "Invalid value for is_read"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        notif_read.is_read = is_read
        if notif_read.is_read:
            notif_read.read_at = timezone.now()
        notif_read.save()

        return Response(
            NotificationReadSerializer(notif_read).data, status=status.HTTP_200_OK
        )


# from django.utils import timezone
# from .models import Notification, NotificationRead
#
# def create_notification(org, title, message, link=None):
#     # 1. Create the notification object
#     notif = Notification.objects.create(
#         organization=org,
#         title=title,
#         message=message,
#         link=link  # optional attribute we'll add in the model
#     )
#
#     # 2. Figure out who should receive it
#     recipients = list(org.admins.all()) + [org.company.owner]
#
#     # 3. For each recipient, create a NotificationRead entry
#     for user in recipients:
#         NotificationRead.objects.create(
#             notification=notif,
#             user=user,
#             is_read=False,
#             read_at=None
#         )
#     return notif
