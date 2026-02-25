from django.urls import path
from . import views

urlpatterns = [
    path('reviews/', views.ReviewListCreateView.as_view(), name='review-list-create'),
    path('reviews/<str:item_no>/', views.ReviewDetailView.as_view(), name='review-detail'),
]
