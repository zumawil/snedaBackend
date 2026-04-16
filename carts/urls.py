from . import views
from django.urls import path

urlpatterns = [
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart-items/', views.CartItemListCreateView.as_view(), name='cart-item-list'),  # GET cart items
    path('cart-items/<int:pk>/', views.CartItemDetailView.as_view(), name='cart-item-detail'),  # GET (detail), PUT, DELETE
    path('checkout/', views.CheckoutView.as_view(), name='checkout' ),
    path('checkout/pickup/', views.PickupCheckoutView.as_view(), name='checkout-pickup'),
    path('clear-cart/', views.ClearCartView.as_view(), name='clear-cart'),
    # path('add-to-cart/<str:product_pk>/', views.AddToCartView.as_view(), name='add-to-cart'),
    # path('remove-from-cart/<str:product_pk>/', views.RemoveProductFromCartView.as_view(), name='remove-from-cart'),
    # path('decrement-product-quantity-in-cart/<str:product_pk>/', views.DecreMentProductQuantityInCartView.as_view(), name='decrement-product-quantity-in-cart'),
    # path('increment-product-quantity-in-cart/<str:product_pk>/', views.IncrementProductQuantityInCartView.as_view(), name='increment-product-quantity-in-cart'),
    # path('get-cart-count/', views.GetCartCountView.as_view(), name='get-cart-count')
]