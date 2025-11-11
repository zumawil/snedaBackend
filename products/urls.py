from . import views
from django.urls import path

urlpatterns = [
    path('categories/', views.CategoryView.as_view(), name='categories'),
    path('products/', views.ProductView.as_view(), name='products'),
    path('product-images/', views.ProductImageView.as_view(), name='product-images'),
]