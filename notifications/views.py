from django.shortcuts import render
from .serializers import NotificationSerializer
from .models import Notification
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework import status
from utils.apiResponse import api_response
from users.permissions import IsVerifiedUser, IsAdminUser


class ListNotificationsView(APIView):

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        return api_response(
            success=True,
            data=serializer.data,
            message=f"Notifications for {request.user.first_name} {request.user.last_name}",
            status_code=status.HTTP_200_OK
        )


class GetNotificationView(APIView):

    def get(self, request, pk):
        try:
            notification = get_object_or_404(Notification, pk=pk, user=request.user)
            serializer = NotificationSerializer(notification)
            return api_response(
                success=True,
                data=serializer.data,
                message=f"Notification retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Http404:
            return api_response(
                success=False,
                data=None,
                error="Notification not found",
                message="No notification found with the given ID",
                status_code=status.HTTP_404_NOT_FOUND
            )


class MarkNotificationReadView(APIView):

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        serializer = NotificationSerializer(notification)
        return api_response(
            success=True,
            data=serializer.data,
            message="Notification marked as read",
            status_code=status.HTTP_200_OK
        )


class DeleteNotificationView(APIView):

    def delete(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.delete()
        return api_response(
            success=True,
            data=None,
            message="Notification deleted successfully",
            status_code=status.HTTP_204_NO_CONTENT
        )


class MarkAllNotificationsReadView(APIView):

    def patch(self, request):
        notifications = Notification.objects.filter(user=request.user, is_read=False)
        count = notifications.count()
        notifications.update(is_read=True)
        return api_response(
            success=True,
            data={'marked_read_count': count},
            message=f"Marked {count} notifications as read",
            status_code=status.HTTP_200_OK
        )


class UnreadNotificationCountView(APIView):

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return api_response(
            success=True,
            data={'unread_count': count},
            message="Unread notification count retrieved successfully",
            status_code=status.HTTP_200_OK
        )

# create a notification for a user
class CreateNotificationView(APIView):

    permission_classes = [IsAdminUser, IsVerifiedUser]

    def post(self, request):
        
        user_id = request.data.get('user_id')
        message = request.data.get('message')
        
        if not user_id or not message:
            return api_response(
                success=False,
                data=None,
                error="Missing required fields",
                message="user_id and message are required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        from users.models import CustomUser
        
        try:
            user = CustomUser.objects.get(id=user_id)
            notification = Notification.objects.create(
                user=user,
                message=message
            )
            serializer = NotificationSerializer(notification)
            return api_response(
                success=True,
                data=serializer.data,
                message="Notification created successfully",
                status_code=status.HTTP_201_CREATED
            )
        except CustomUser.DoesNotExist:
            return api_response(
                success=False,
                data=None,
                error="User not found",
                message="User not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

