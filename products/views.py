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
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from .serializers import (
    ProductImageSerializer, 
    ProductSerializer,ProductCreateUpdateSerializer, 
    CategorySerializer, ProductImageCreateSerializer
)
from .models import Category, Product, ProductImage, Brand, HSCode, ProductGroup
from utils.apiResponse import api_response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
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
from django.db.models import Q

class GetProductsByCategory(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    pagination_class = PageNumberPagination

    def get(self, request):
        try:
            # Parse category query params
            category_names = [name.strip() for name in request.query_params.get('category', '').split(',')]
            # if category namea is empty
            if not any(category_names):
                return api_response(
                    success=False,
                    data=None,
                    error="No category provided",
                    message="Please provide a category",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Create a cache key that is consistent and includes the page number
            categories_key = "_".join(sorted(category_names))
            page_number = request.query_params.get('page', 1)
            cache_key = f"products_by_category_{categories_key}_page_{page_number}"

            # Check cache first
            cached_data = cache.get(cache_key)
            if cached_data:
                return api_response(
                    success=True,
                    data=cached_data,
                    message="Products retrieved successfully",
                    status_code=status.HTTP_200_OK
                )

            # Build dynamic query for category names
            query = Q()
            for name in category_names:
                query |= Q(category__name__icontains=name)
            products = Product.objects.filter(query).order_by('item_no')  # consistent ordering using item_no as primary key

            # Paginate queryset
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(products, request)
            serializer = ProductSerializer(page, many=True)
            data = paginator.get_paginated_response(serializer.data).data

            # Cache the serialized paginated response, not the queryset
            cache.set(cache_key, data, timeout=60 * 60)  # cache for 1 hour

            return api_response(
                success=True,
                data=data,
                message="Products retrieved successfully",
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Internal Server Error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@receiver([post_save, post_delete], sender=Product)
def invalidate_product_related_caches(sender, **kwargs):
    # Only available in django-redis cache backend
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern("products_by_category_*")
        cache.delete_pattern("products_list_page_*")
        cache.delete_pattern("filter_products_*")
        cache.delete_pattern("search_products_*")
    elif hasattr(cache, 'clear'):
        cache.clear()

@receiver([post_save, post_delete], sender=Category)
def invalidate_category_caches(sender, **kwargs):
    # cache invalidation for GetCategoriesView
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern("categories_list_all*")
    elif hasattr(cache, 'clear'):
        cache.clear()

@receiver([post_save, post_delete], sender=ProductGroup)
def invalidate_product_group_caches(sender, **kwargs):
    # cache invalidation for GetProductGroups
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern("product_groups_all*")
    elif hasattr(cache, 'clear'):
        cache.clear()

class GetCategoriesView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            cache_key = "categories_list_all"
            cached_data = cache.get(cache_key)
            if cached_data:
                return api_response(
                    success=True,
                    data=cached_data,
                    message="Categories retrieved successfully",
                    status_code=status.HTTP_200_OK
                )

            categories = Category.objects.all()
            serializer = CategorySerializer(categories, many=True)
            data = serializer.data
            
            cache.set(cache_key, data, timeout=60 * 60)  # cache categories for 1 hour

            return api_response(
                success=True,
                data=data,
                message="Categories retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Internal Server Error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
    queryset = Product.objects.order_by('-created_at')

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateUpdateSerializer
        return ProductSerializer
    
    def list(self, request, *args, **kwargs):
        page_number = request.query_params.get('page', 1)
        cache_key = f"products_list_page_{page_number}"
        
        cached_data = cache.get(cache_key)
        if cached_data:
            return api_response(
                success=True,
                data=cached_data,
                message="Products retrieved successfully",
                status_code=status.HTTP_200_OK
            )

        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = self.get_paginated_response(serializer.data).data
        else:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

        # cache generic product list for 5 min
        cache.set(cache_key, data, timeout=60 * 5)

        return api_response(
            success=True,
            data=data,
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

class FilterProduct(APIView):
    """
    General product filter endpoint supporting multiple filter criteria.
    
    Query Parameters:
    - search: Search by item_no or category name (string)
    - category: Filter by category ID or name (string/int)
    - brand: Filter by brand ID or name (string/int)
    - product_group: Filter by product group ID or name (string/int)
    - hs_code: Filter by HS code (string, comma-separated for multiple)
    - min_price: Minimum price (decimal)
    - max_price: Maximum price (decimal)
    - in_stock: Filter by stock availability (true/false)
    - sort_by: Sort field (created_at, gross_price, item_no) (default: -created_at)
    - page: Page number for pagination (default: 1)
    
    Example: /api/products/filter/?category=1&min_price=100&max_price=5000&sort_by=-gross_price
    """
    
    permission_classes = [permissions.AllowAny]
    pagination_class = PageNumberPagination

    def get(self, request):
        try:
            # Generate deterministic cache key based on query params
            params_dict = dict(request.query_params)
            # Standardize by sorting keys so that same filters give same key
            sorted_params = tuple(sorted((k, tuple(sorted(v))) for k, v in params_dict.items()))
            import hashlib
            params_hash = hashlib.md5(str(sorted_params).encode('utf-8')).hexdigest()
            page_number = request.query_params.get('page', 1)
            cache_key = f"filter_products_hash_{params_hash}_page_{page_number}"

            cached_data = cache.get(cache_key)
            if cached_data:
                return api_response(
                    success=True,
                    data=cached_data,
                    message="Products filtered successfully",
                    status_code=status.HTTP_200_OK
                )

            queryset = Product.objects.all()
            
            # Search filter
            search_query = request.query_params.get('search', '').strip()
            if search_query:
                queryset = queryset.filter(
                    item_no__icontains=search_query
                ) | queryset.filter(
                    category__name__icontains=search_query
                )
            
            # Category filter
            category_param = request.query_params.get('category', '').strip()
            if category_param:
                try:
                    # Try as ID first
                    category_id = int(category_param)
                    queryset = queryset.filter(category_id=category_id)
                except ValueError:
                    # Fall back to name
                    queryset = queryset.filter(category__name__icontains=category_param)
            
            # Brand filter
            brand_param = request.query_params.get('brand', '').strip()
            if brand_param:
                try:
                    brand_id = int(brand_param)
                    queryset = queryset.filter(brand_id=brand_id)
                except ValueError:
                    queryset = queryset.filter(brand__name__icontains=brand_param)
            
            # Product Group filter
            product_group_param = request.query_params.get('product_group', '').strip()
            if product_group_param:
                try:
                    group_id = int(product_group_param)
                    queryset = queryset.filter(product_group_id=group_id)
                except ValueError:
                    queryset = queryset.filter(product_group__name__icontains=product_group_param)
            
            # HS Code filter (supports comma-separated values)
            hs_code_param = request.query_params.get('hs_code', '').strip()
            if hs_code_param:
                hs_codes = [code.strip() for code in hs_code_param.split(',') if code.strip()]
                if hs_codes:
                    queryset = queryset.filter(hs_code__code__in=hs_codes)

            # OEM filter  (to be added later)
            # oem_param = request.query_params.get('oem', '').strip()
            # if oem_param:
            #     queryset = queryset.filter(oem__icontains=oem_param)
            
            # Price range filter
            min_price = request.query_params.get('min_price', '').strip()
            max_price = request.query_params.get('max_price', '').strip()
            
            if min_price:
                try:
                    queryset = queryset.filter(gross_price__gte=float(min_price))
                except ValueError:
                    pass
            
            if max_price:
                try:
                    queryset = queryset.filter(gross_price__lte=float(max_price))
                except ValueError:
                    pass
            
            # Stock availability filter
            in_stock_param = request.query_params.get('in_stock', '').strip().lower()
            if in_stock_param in ['true', '1', 'yes']:
                queryset = queryset.filter(inventory_qty__gt=0)
            elif in_stock_param in ['false', '0', 'no']:
                queryset = queryset.filter(inventory_qty=0)
            
            # Sorting
            # if sort_by is not provide use -created_at
            sort_by = request.query_params.get('sort_by', '-created_at').strip()
            allowed_sort_fields = ['created_at', 
                                   '-created_at', 
                                   'gross_price', 
                                   '-gross_price', 
                                   'item_no', 
                                   '-item_no']
            if sort_by in allowed_sort_fields:
                queryset = queryset.order_by(sort_by)
            else:
                queryset = queryset.order_by('-created_at')
            
            # Pagination
            paginator = self.pagination_class()
            paginated_products = paginator.paginate_queryset(queryset, request)
            
            serializer = ProductSerializer(paginated_products, many=True)
            data = paginator.get_paginated_response(serializer.data).data
            
            # Cache generic product filter for 5 min
            cache.set(cache_key, data, timeout=60 * 5)

            return api_response(
                success=True,
                data=data,
                message="Products filtered successfully",
                status_code=status.HTTP_200_OK
            )
        
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error filtering products",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GetProductReviewsView(APIView):
    permission_classes = [IsVerifiedUser]

    def post(self, request):
        product_id = request.data.get('item_no')

        if not product_id:
            return api_response(
                success=False,
                data=None,
                error="Missing product ID",
                message="Product ID is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Get product or return 404
        product = get_object_or_404(Product, item_no=product_id)

        # Paginate reviews for this product
        reviews_queryset = product.reviews.all().order_by('-created_at')
        paginator = PageNumberPagination()
        paginated_reviews = paginator.paginate_queryset(reviews_queryset, request)
        serializer = ReviewsSerializer(paginated_reviews, many=True)
        data = paginator.get_paginated_response(serializer.data).data

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
        cache_key = "product_groups_all"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return api_response(
                success=True,
                data=cached_data,
                message="Product groups retrieved successfully",
                status_code=status.HTTP_200_OK
            )

        groups = ProductGroup.objects.all()
        serializer = ProductGroupSerializer(groups, many=True)
        data = serializer.data
        
        cache.set(cache_key, data, timeout=60 * 60)
        
        return api_response(
            success=True,
            data=data,
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
            
        page_number = request.query_params.get('page', 1)
        cache_key = f"search_products_{query}_page_{page_number}"

        cached_data = cache.get(cache_key)
        if cached_data:
            return api_response(
                success=True,
                data=cached_data,
                message="search results successfully returned",
                status_code=status.HTTP_200_OK
            )
        
        products = Product.objects.filter(
            item_no__icontains=query
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(products, request)

        serializer = ProductSerializer(page, many=True)
        data = paginator.get_paginated_response(serializer.data).data
        
        # cache searches for 5 min
        cache.set(cache_key, data, timeout=60 * 5)
        
        return api_response(
            success=True,
            data=data,
            message="search results successfully returned",
            status_code=status.HTTP_200_OK
        )


 