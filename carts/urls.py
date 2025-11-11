from . import views
from django.urls import path

urlpatterns = [
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart-items/', views.CartItemView.as_view(), name='cart-item-list'),  # GET (list), POST
    path('cart-items/<int:pk>/', views.CartItemView.as_view(), name='cart-item-detail'),  # GET (detail), PUT, DELETE
    path('checkout/', views.CheckoutView.as_view(), name='checkout' ),
    path('add-to-cart/<int:product_pk>/', views.AddToCartView.as_view(), name='add-to-cart'),
]