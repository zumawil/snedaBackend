from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import authentication
from rest_framework import status
from rest_framework import generics
from users.permissions import IsAdminUser, IsVerifiedUser
from django.db.models import Count

from .serializers import ProductImageSerializer, ProductSerializer, CategorySerializer
from .models import Category, Product, ProductImage
# Create your views here.

# Product API Views

class CategoryListCreateView(generics.ListCreateAPIView):
    """
    List all categories or create a new category.

    GET: Retrieve a list of all categories with product counts.
    POST: Create a new category (Admin and Verified User required).
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [ IsVerifiedUser]

    def get_queryset(self):
        # calculate produt count for all the categories in the table
        return Category.objects.annotate(products_count=Count('products'))

class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific category.

    GET: Retrieve category details.
    PUT/PATCH: Update category (Admin and Verified User required).
    DELETE: Delete category (Admin and Verified User required).
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [ IsVerifiedUser]


class ProductImageListView(generics.ListCreateAPIView):
    """
    List all product images or create a new product image.

    GET: Retrieve a list of all product images.
    POST: Create a new product image (requires product ID and image file).
    """
    permission_classes = [ IsVerifiedUser]
    serializer_class = ProductImageSerializer
    queryset = ProductImage.objects.all()

class ProductImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific product image.

    GET: Retrieve product image details.
    PUT/PATCH: Update product image.
    DELETE: Delete product image.
    """
    permission_classes = [ IsVerifiedUser]

    serializer_class = ProductImageSerializer
    queryset = ProductImage.objects.all()

class ProductListCreateView(generics.ListCreateAPIView):
    """
    List all products or create a new product.

    GET: Retrieve a list of all products with their images.
    POST: Create a new product (requires name, category, description, price, stock).
    """
    permission_classes = [ IsVerifiedUser]

    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific product.

    GET: Retrieve product details.
    PUT/PATCH: Update product (Admin and Verified User required).
    DELETE: Delete product (Admin and Verified User required).
    """
    permission_classes = [ IsVerifiedUser]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


