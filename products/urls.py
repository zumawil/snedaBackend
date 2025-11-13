from . import views
from django.urls import path

urlpatterns = [
    path('categories/', views.CategoryListCreateView.as_view(), name='categories'), # list all categories and create a new category
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category-detail'), # get a category by id
    path('products/', views.ProductListCreateView.as_view(), name='products'), # list all products creat product
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'), # get a product by id
    path('product-images/', views.ProductImageListView.as_view(), name='product-images'), # list all product images
    path('product-images/<int:pk>/', views.ProductImageDetailView.as_view(), name='product-image-detail'), # get a product image by id
]