from django.urls import path
from .views import (
    DashboardStatsView,
    AdminOrderListView,
    AdminProductListView,
    AdminUserListView,
    ToggleUserStatusView
)

urlpatterns = [
    path('stats/', DashboardStatsView.as_view(), name='admin-dashboard-stats'),
    path('orders/', AdminOrderListView.as_view(), name='admin-orders-list'),
    path('products/', AdminProductListView.as_view(), name='admin-products-list'),
    path('users/', AdminUserListView.as_view(), name='admin-users-list'),
    path('users/<int:pk>/toggle-status/', ToggleUserStatusView.as_view(), name='admin-user-toggle-status'),
]
