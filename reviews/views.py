from django.shortcuts import render
from .serializers import ReviewsSerializer
from rest_framework.generics import ListCreateAPIView, RetrieveDestroyAPIView
from users.permissions import IsAdminUser, IsVerifiedUser
from products.models import Product
from .models import Reviews
from utils.apiResponse import api_response
# Create your views here.

from rest_framework.exceptions import ValidationError

class ReviewListCreateView(ListCreateAPIView):
    serializer_class = ReviewsSerializer
    permission_classes = [IsVerifiedUser]

    def get_queryset(self):
        return Reviews.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        product_id= self.request.data.get('product') # by id

        # Get product safely
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            raise ValidationError("Invalid product name.")

        user = self.request.user

        # Check if user already reviewed this product
        if product.reviews.filter(user=user).exists():
            raise ValidationError("You can't review a product twice.")

        # Check if user has delivered orders containing the product
        has_delivered_order = user.orders.filter(
            status='delivered',
            items__product=product
        ).exists()

        if not has_delivered_order:
            raise ValidationError(
                "You can only review products you have purchased and received."
            )

        # Save review with user and product
        serializer.save(user=user, product=product)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            success=True,
            data=serializer.data,
            message="Reviews retrieved successfully",
            status_code=status.HTTP_200_OK
        )
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return api_response(
                success=True,
                data=serializer.data,
                message="Review created successfully",
                status_code=status.HTTP_201_CREATED
            )
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    
class ReviewDetailView(RetrieveDestroyAPIView):
    serializer_class = ReviewsSerializer
    permission_classes = [IsVerifiedUser]

    def get_queryset(self):
        return Reviews.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            success=True,
            data=serializer.data,
            message="Review retrieved successfully",
            status_code=status.HTTP_200_OK
        )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return api_response(
            success=True,
            data=None,
            message="Review deleted successfully",
            status_code=status.HTTP_204_NO_CONTENT
        )
    