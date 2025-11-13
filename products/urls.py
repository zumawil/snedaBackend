from . import views
from django.urls import path

urlpatterns = [
    path('categories/', views.CategoryListCreateView.as_view(), name='categories'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category-detail'),
    path('products/', views.ProductListView.as_view(), name='products'), # list all products
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'), # get a product by id
    path('product-images/', views.ProductImageView.as_view(), name='product-images'), # list all product images
    path ('products/create/', views.ProductCreateView.as_view(), name='product-create'), # create a new product
]