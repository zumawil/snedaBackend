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

# cart api
class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser, IsVerifiedUser]

    def get_queryset(self):
        # calculate produt count for all the categories in the table
        return Category.objects.annotate(products_count=Count('products'))

class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser, IsVerifiedUser]
    
   
class ProductListView(APIView):
    
    def get(self, request):
        
        products = Product.objects.all()
        try:
            serializer = ProductSerializer(products, many=True)

            return Response(
                serializer.data, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error":e},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):

    permission_classes = [IsAdminUser, IsVerifiedUser]

    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class ProductImageView(APIView):
    def get(self, request):
        
        productImages = ProductImage.objects.all()
        try:
            serializer = ProductImageSerializer(productImages, many=True)

            return Response(
                serializer.data, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error":e},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )