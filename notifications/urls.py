from django.urls import path
from .views import (
    ListNotificationsView,
    GetNotificationView,
    MarkNotificationReadView,
    DeleteNotificationView,
    MarkAllNotificationsReadView,
    UnreadNotificationCountView,
    CreateNotificationView
)

urlpatterns = [
    # Get all notifications for the current user
    path('', ListNotificationsView.as_view(), name='list_notifications'),
    
    # Get a specific notification by ID
    path('<int:pk>/', GetNotificationView.as_view(), name='get_notification'),
    
    # Mark a notification as read
    path('<int:pk>/read/', MarkNotificationReadView.as_view(), name='mark_notification_read'),
    
    # Delete a notification
    path('<int:pk>/delete/', DeleteNotificationView.as_view(), name='delete_notification'),
    
    # Mark all notifications as read
    path('mark-all-read/', MarkAllNotificationsReadView.as_view(), name='mark_all_read'),
    
    # Get unread notification count
    path('unread-count/', UnreadNotificationCountView.as_view(), name='unread_count'),
    
    # Create a new notification (for admin/system use)
    path('create/', CreateNotificationView.as_view(), name='create_notification'),
]