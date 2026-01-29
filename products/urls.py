from . import views
from django.urls import path

urlpatterns = [
    # path('categories/', views.CategoryListCreateView.as_view(), name='categories'), # list all categories and create a new category
    # path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category-detail'), # get a category by id
    path('products/', views.ProductListCreateView.as_view(), name='products'), # list all products creat product
    path('products/<str:pk>/', views.ProductDetailView.as_view(), name='product-detail'), # get a product by id
    path('product-images/', views.ProductImageListView.as_view(), name='product-images'), # list all product images
    path('product-images/<str:pk>/', views.ProductImageDetailView.as_view(), name='product-image-detail'), # get a product image by id
    path('product-reviews/', views.GetProductReviewsView.as_view(), name='get-product_reviews'),
    path('products-in-hs-code/', views.GetProductByHSCode.as_view(), name='get-products-in-hs-code'),
    path('products-price-range/', views.GetProductPriceRange.as_view(), name='get-products-price-range'),
    path('product-groups/', views.GetProductGroups.as_view(), name='get-product-groups'),
    path('product/search/', views.SearchProduct.as_view(), name='search product'),
]