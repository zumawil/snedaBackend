from django.shortcuts import render
from .serializers import ReviewsSerializer
from rest_framework.generics import ListCreateAPIView, RetrieveDestroyAPIView
from users.permissions import IsAdminUser, IsVerifiedUser
from products.models import Product
from .models import Reviews
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

    
class ReviewDetailView(RetrieveDestroyAPIView):
    serializer_class = ReviewsSerializer
    permission_classes = [IsVerifiedUser]

    def get_queryset(self):
        return Reviews.objects.filter(user=self.request.user)
    