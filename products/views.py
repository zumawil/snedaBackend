from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import authentication
from rest_framework import status
from rest_framework import generics

from .serializers import ProductImageSerializer, ProductSerializer, CategorySerializer
from .models import Category, Product, ProductImage
# Create your views here.

# cart api
class CategoryView(APIView):
    
    def get(self, request):
        
        categories = Category.objects.all()
        try:
            serializer = CategorySerializer(categories, many=True)

            return Response(
                serializer.data, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error":e},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

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

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):

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