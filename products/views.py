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
from django.db.models.functions import Lower

# for api view pagination
from rest_framework.pagination import PageNumberPagination


from .serializers import (
    ProductImageSerializer, 
    ProductSerializer,ProductCreateUpdateSerializer, 
    CategorySerializer, ProductImageCreateSerializer
)
from .models import Category, Product, ProductImage, Brand, HSCode, ProductGroup
from utils.apiResponse import api_response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
# Create your views here.

# Product API Views

# class CategoryListCreateView(generics.ListCreateAPIView):
#     """
#     List all categories or create a new category.

#     GET: Retrieve a list of all categories with product counts.
#     POST: Create a new category (Admin and Verified User required).
#     """
#     queryset = Category.objects.all()
#     serializer_class = CategorySerializer
#     permission_classes = [IsVerifiedUser]

#     def get_queryset(self):
#         # calculate produt count for all the categories in the table
#         return Category.objects.annotate(products_count=Count('products'))
    
#     def list(self, request, *args, **kwargs):
#         queryset = self.get_queryset()
#         serializer = self.get_serializer(queryset, many=True)
#         return api_response(
#             success=True,
#             data=serializer.data,
#             message="Categories retrieved successfully",
#             status_code=status.HTTP_200_OK
#         )
    
#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return api_response(
#                 success=True,
#                 data=serializer.data,
#                 message="Category created successfully",
#                 status_code=status.HTTP_201_CREATED
#             )
#         return api_response(
#             success=False,
#             data=None,
#             error="Validation failed",
#             message=serializer.errors,
#             status_code=status.HTTP_400_BAD_REQUEST
#         )

# class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
#     """
#     Retrieve, update, or delete a specific category.

#     GET: Retrieve category details.
#     PUT/PATCH: Update category (Admin and Verified User required).
#     DELETE: Delete category (Admin and Verified User required).
#     """
#     queryset = Category.objects.all()
#     serializer_class = CategorySerializer
#     permission_classes = [IsVerifiedUser]

#     def retrieve(self, request, *args, **kwargs):
#         instance = self.get_object()
#         serializer = self.get_serializer(instance)
#         return api_response(
#             success=True,
#             data=serializer.data,
#             message="Category retrieved successfully",
#             status_code=status.HTTP_200_OK
#         )
    
#     def update(self, request, *args, **kwargs):
#         partial = kwargs.pop('partial', False)
#         instance = self.get_object()
#         serializer = self.get_serializer(instance, data=request.data, partial=partial)
#         if serializer.is_valid():
#             serializer.save()
#             return api_response(
#                 success=True,
#                 data=serializer.data,
#                 message="Category updated successfully",
#                 status_code=status.HTTP_200_OK
#             )
#         return api_response(
#             success=False,
#             data=None,
#             error="Validation failed",
#             message=serializer.errors,
#             status_code=status.HTTP_400_BAD_REQUEST
#         )
    
#     def destroy(self, request, *args, **kwargs):
#         instance = self.get_object()
#         instance.delete()
#         return api_response(
#             success=True,
#             data=None,
#             message="Category deleted successfully",
#             status_code=status.HTTP_204_NO_CONTENT
#         )

class ProductImageListView(generics.ListCreateAPIView):
    """
    List all product images or create a new product image.

    GET: Retrieve a list of all product images.
    POST: Create a new product image (supports bulk creation).
    """
    permission_classes = [IsVerifiedUser, IsAdminUser]
    serializer_class = ProductImageSerializer
    queryset = ProductImage.objects.all()


    def get_serializer(self, *args, **kwargs):
        if self.request.method == 'POST':
            # allow bulk creation of product images
            if isinstance(self.request.data, list):
                kwargs['many'] = True
            return ProductImageCreateSerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            success=True,
            data=serializer.data,
            message="Product images retrieved successfully",
            status_code=status.HTTP_200_OK
        )
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                data=serializer.data,
                message="Product image(s) created successfully",
                status_code=status.HTTP_201_CREATED
            )
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class ProductImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific product image.

    GET: Retrieve product image details.
    PUT/PATCH: Update product image.
    DELETE: Delete product image.
    """
    # permission_classes = [IsVerifiedUser]
    queryset = ProductImage.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductImageCreateSerializer
        return ProductImageSerializer

    def create(self, request, *args, **kwargs):
        print("recieveced data", request.data)
        serializer = self.get_serializer(data=request.data, many=True)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                data=serializer.data,
                message="Product image created successfully",
                status_code=status.HTTP_201_CREATED
            )
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            success=True,
            data=serializer.data,
            message="Product image retrieved successfully",
            status_code=status.HTTP_200_OK
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                data=serializer.data,
                message="Product image updated successfully",
                status_code=status.HTTP_200_OK
            )
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return api_response(
            success=True,
            data=None,
            message="Product image deleted successfully",
            status_code=status.HTTP_204_NO_CONTENT
        )

class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateUpdateSerializer
        return ProductSerializer
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = self.get_paginated_response(serializer.data).data
            return api_response(
                success=True,
                data=data,
                message="Products retrieved successfully",
                status_code=status.HTTP_200_OK
            )

        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            success=True,
            data=serializer.data,
            message="Products retrieved successfully",
            status_code=status.HTTP_200_OK
        )
    
    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        try:
            # Handle Product Group (Required, expects ID)
            product_group_id = data.get('product_group')
            if not product_group_id:
                return api_response(
                    success=False,
                    data=None,
                    error="Product group ID is required",
                    message="Product group ID is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            try:
                product_group = ProductGroup.objects.get(id=product_group_id)
                data['product_group'] = product_group.id
            except ProductGroup.DoesNotExist:
                return api_response(
                    success=False,
                    data=None,
                    error="Product group not found",
                    message="Product group not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Handle Category (expects name, creates if missing)
            category_name = data.get('category')
            if category_name:
                category, _ = Category.objects.get_or_create(name=category_name)
                data['category'] = category.id
            
            # Handle Brand (expects name, creates if missing)
            brand_name = data.get('brand')
            if brand_name:
                brand, _ = Brand.objects.get_or_create(name=brand_name)
                data['brand'] = brand.id

            # Handle HS Code (expects code, creates if missing)
            hs_code_value = data.get('hs_code')
            if hs_code_value:
                hs_code, _ = HSCode.objects.get_or_create(code=hs_code_value)
                data['hs_code'] = hs_code.id

            serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return api_response(
                    success=True,
                    data=serializer.data,
                    message="Product created successfully",
                    status_code=status.HTTP_201_CREATED
                )
                
            return api_response(
                success=False,
                data=None,
                error="Validation failed",
                message=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Internal Server Error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific product.

    GET: Retrieve product details.
    PUT/PATCH: Update product (Admin required).
    DELETE: Delete product (Admin required).
    """
    queryset = Product.objects.all()

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductCreateUpdateSerializer
        return ProductSerializer
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            success=True,
            data=serializer.data,
            message="Product retrieved successfully",
            status_code=status.HTTP_200_OK
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                data=serializer.data,
                message="Product updated successfully",
                status_code=status.HTTP_200_OK
            )
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return api_response(
            success=True,
            data=None,
            message="Product deleted successfully",
            status_code=status.HTTP_204_NO_CONTENT
        )


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
        data = self.get_paginated_response(reviews.data).data

        return api_response(
            success=True,
            data={"reviews": data},
            message="Product reviews retrieved successfully",
            status_code=status.HTTP_200_OK
        )

from .models import HSCode

class GetProductByHSCode(APIView):
    # permission_classes = [IsVerifiedUser]

    pagination = PageNumberPagination

    def get(self, request):
        hs_code = request.query_params.get('hs_code')

        try: 
            hs_codes = hs_code.split(',') 
        except:
            hs_codes = [hs_code]
        
        if not hs_codes:
            return api_response(
                success=False,
                data=None,
                error="Missing HS code/s",
                message="HS code/s is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        hs_code_products = Product.objects.filter(hs_code__code__in=hs_codes)
       
        if not hs_code_products.exists():
            return api_response(
                success=False,
                data=None,
                error="HS code/s not found",
                message="HS code/s not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        paginator = self.pagination()
        paginated_products = paginator.paginate_queryset(hs_code_products, request, view=self)
        
        # Serialize paginated products
        serializer = ProductSerializer(paginated_products,many=True)

        products_data = paginator.get_paginated_response(serializer.data).data

        return api_response(
            success=True,
            data=products_data,
            message="Products in category retrieved successfully",
            status_code=status.HTTP_200_OK
        )

class GetProductPriceRange(APIView):

    pagination = PageNumberPagination
   
    def get(self, request):
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')

        if not min_price or not max_price:
            return api_response(
                success=False,
                data=None,
                error="Missing price range",
                message="Price range is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Get products within the price range
        products = Product.objects.filter(gross_price__gte=min_price, gross_price__lte=max_price)
        
        if not products.exists():
            return api_response(
                success=False,
                data=None,
                error="No products found within the price range",
                message="No products found within the price range",
                status_code=status.HTTP_404_NOT_FOUND
            )

        paginator = self.pagination()
        paginated_products = paginator.paginate_queryset(products, request, view=self)
        serializer = ProductSerializer(paginated_products,many=True)
        products_data = paginator.get_paginated_response(serializer.data).data

        return api_response(
            success=True,
            data=products_data,
            message="Products within price range retrieved successfully",
            status_code=status.HTTP_200_OK
        )

from .serializers import ProductGroupSerializer
from .models import ProductGroup

class GetProductGroups(APIView):

    permission_classes = []
    authentication_classes = []

    def get(self, request):
        groups = ProductGroup.objects.all()
        serializer = ProductGroupSerializer(groups, many=True)
        return api_response(
            success=True,
            data=serializer.data,
            message="Product groups retrieved successfully",
            status_code=status.HTTP_200_OK
        )

# search for products
class SearchProduct(APIView):

    permissions_class = []
    authentication_class = []

    pagination_class = PageNumberPagination

    def get(self, request):
        query = request.query_params.get('q', '')

        if not query:
            return api_response(
                data=[],
                message="no query parameter provided",
                error=True,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        products = Product.objects.filter(
            item_no__icontains=query
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(products, request)

        serializer = ProductSerializer(page, many=True)
        data = paginator.get_paginated_response(serializer.data).data
        
        return api_response(
            success=True,
            data=data,
            message="search results successfully returned",
            status_code=status.HTTP_200_OK
        )


 