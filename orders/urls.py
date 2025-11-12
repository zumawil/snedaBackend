from django.urls import path
from . import views

urlpatterns = [
    path('orders/', views.OrderView.as_view(), name='order-list'),  # List all orders
    path('orders/<int:pk>/', views.OrderView.as_view(), name='order-detail'),  # Get specific order
    path('order-items/', views.OrderItemView.as_view(), name='order-item-list'),  # List/create order items
    path('order-items/<int:pk>/', views.OrderItemView.as_view(), name='order-item-detail'),  # Get/update/delete order item
]