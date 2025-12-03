from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import authentication
from rest_framework import status
from rest_framework import generics
from users.permissions import IsAdminUser, IsVerifiedUser
from django.db.models import Count
from rest_framework import permissions
from reviews.serializers import ReviewsSerializer
from django.shortcuts import get_object_or_404

from .serializers import ProductImageSerializer, ProductSerializer, CategorySerializer
from .models import Category, Product, ProductImage
from utils.apiResponse import api_response
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

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            success=True,
            data=serializer.data,
            message="Category retrieved successfully"
        )

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
    permission_classes = [IsVerifiedUser]
    queryset = ProductImage.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductImageCreateSerializer
        return ProductImageSerializer

class ProductListCreateView(generics.ListCreateAPIView):
    """
    List all products or create a new product.

    GET: Retrieve a list of all products with their images.
    POST: Create a new product (requires name, category, description, price, stock).
    """
    permission_classes = [IsVerifiedUser]
    queryset = Product.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateUpdateSerializer
        return ProductSerializer


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific product.

    GET: Retrieve product details.
    PUT/PATCH: Update product (Admin and Verified User required).
    DELETE: Delete product (Admin and Verified User required).
    """
    permission_classes = [IsVerifiedUser]
    queryset = Product.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductCreateUpdateSerializer
        return ProductSerializer


class GetProductReviewsView(APIView):
    permission_classes = [IsVerifiedUser]

    def post(self, request):
        product_id = request.data.get('product')

        if not product_id:
            return api_response(
                success=False,
                data=None,
                error="Missing product ID",
                message="Product ID is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Get product or return 404
        product = get_object_or_404(Product, id=product_id)

        # Serialize all reviews for this product
        reviews = ReviewsSerializer(product.reviews.all(), many=True)

        return api_response(
            success=True,
            data={"reviews": reviews.data},
            message="Product reviews retrieved successfully",
            status_code=status.HTTP_200_OK
        )
