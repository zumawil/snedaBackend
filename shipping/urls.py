from django.urls import path
from .views import ShippingStatusView, TrackShippingView
urlpatterns = [
    # takes order id and checks status of shipping associated with it
    path('status/<int:order_id>/', ShippingStatusView.as_view(), name='shipping_status'),
    # takes order id and updates shipping associated with it
    # path('update-status/<int:order_id>/', UpdateShippingStatusView.as_view(), name='update_shipping_status'),
    path('track-shipping/<str:tracking_number>/', TrackShippingView.as_view(), name='track_shipping'),
    
]