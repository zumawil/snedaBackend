from . import views
from django.urls import path

urlpatterns = [
    path('categories/', views.CategoryView.as_view(), name='categories'),
    path('products/', views.ProductListView.as_view(), name='products'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('product-images/', views.ProductImageView.as_view(), name='product-images'),
]