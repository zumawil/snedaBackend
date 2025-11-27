from django.urls import path
from . import views

urlpatterns = [
    path('payments/', views.PaymentView.as_view(), name='payment-list'),  # List all payments / initiate payment
    path('payments/<int:pk>/', views.PaymentView.as_view(), name='payment-detail'),  # Get specific payment
    path('payments/callback/', views.PaymentCallback.as_view(), name='payment-callback'),  # Paystack callback
    path('payment/webhook/', views.WebhookView.as_view(), name='payment-webhook'),
    path('payments/order/<int:order_id>/', views.GetPaymentByOrder.as_view(), name='get-payment-by-order'),
]