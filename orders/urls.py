from django.urls import path
from . import views

urlpatterns = [
    path('order/<int:pk>/', views.OrderView.as_view(), name='orders'),
    path('order-items/', views.OrderItemView.as_view(), name='order-item-list'),
    path('order-items/<int:pk>/', views.OrderItemView.as_view(), name='order-item-detail'),
    path('orders/<int:pk>/', views.OrderView.as_view(), name='order-detail'),
]