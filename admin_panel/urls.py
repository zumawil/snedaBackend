from django.urls import path
from .views import (
    # Dashboard
    DashboardStatsView,
    
    # Order Management
    AdminOrderListView,
    AdminOrderDetailView,
    AdminUpdateOrderStatusView,
    AdminOrderApproveView,
    AdminOrderRejectView,
    AdminOrderCancelView,
    
    # Product Management
    AdminProductListView,
    AdminProductCreateView,
    AdminProductDetailView,
    # AdminToggleProductStatusView,  # Commented out - Product model lacks is_active field
    AdminProductStockUpdateView,
    AdminProductImageView,
    
    # Shipping Management
    AdminShippingListView,
    AdminShippingDetailView,
    AdminUpdateShippingStatusView,
    
    # User Management
    AdminUserListView,
    AdminUserDetailView,
    AdminSearchUsersView,
    AdminAssignUserRoleView,
    ToggleUserStatusView,
    
    # Notification Management
    AdminCreateNotificationView,
)

urlpatterns = [
    # Dashboard
    path('stats/', DashboardStatsView.as_view(), name='admin-dashboard-stats'),
    
    # Order Management
    path('orders/', AdminOrderListView.as_view(), name='admin-orders-list'),
    path('orders/<int:pk>/', AdminOrderDetailView.as_view(), name='admin-order-detail'),
    path('orders/<int:pk>/status/', AdminUpdateOrderStatusView.as_view(), name='admin-order-update-status'),
    path('orders/<int:pk>/approve/', AdminOrderApproveView.as_view(), name='admin-order-approve'),
    path('orders/<int:pk>/reject/', AdminOrderRejectView.as_view(), name='admin-order-reject'),
    path('orders/<int:pk>/cancel/', AdminOrderCancelView.as_view(), name='admin-order-cancel'),
    
    # Product Management
    path('products/', AdminProductListView.as_view(), name='admin-products-list'),
    path('products/create/', AdminProductCreateView.as_view(), name='admin-product-create'),
    path('products/<int:pk>/', AdminProductDetailView.as_view(), name='admin-product-detail'),
    # path('products/<int:pk>/toggle-status/', AdminToggleProductStatusView.as_view(), name='admin-product-toggle-status'),  # Commented out
    path('products/<int:pk>/stock/', AdminProductStockUpdateView.as_view(), name='admin-product-stock'),
    path('product-images/', AdminProductImageView.as_view(), name='admin-product-images'),
    
    # Shipping Management
    path('shippings/', AdminShippingListView.as_view(), name='admin-shippings-list'),
    path('shippings/<int:pk>/', AdminShippingDetailView.as_view(), name='admin-shipping-detail'),
    path('shippings/<int:order_id>/status/', AdminUpdateShippingStatusView.as_view(), name='admin-shipping-status'),
    
    # User Management
    path('users/', AdminUserListView.as_view(), name='admin-users-list'),
    path('users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('users/search/', AdminSearchUsersView.as_view(), name='admin-users-search'),
    path('users/<int:pk>/role/', AdminAssignUserRoleView.as_view(), name='admin-user-role'),
    path('users/<int:pk>/toggle-status/', ToggleUserStatusView.as_view(), name='admin-user-toggle-status'),
    
    # Notification Management
    path('notifications/create/', AdminCreateNotificationView.as_view(), name='admin-notification-create'),
]
