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
        # Retrieve the product based on the name provided in the request data
        product = Product.objects.get(name=self.request.data.get('product'))
        user = self.request.user

        # Check if the user has already reviewed this product
        product_reviews = product.reviews.filter(user=user)
        if product_reviews.exists():
            raise ValidationError("You can't have two reviews under one product")

        # Initialize a flag to track if the user is allowed to review
        can_review = False

        # Check if the user has purchased the product and the order was delivered
        for order in user.orders.all():
            # Get order items for this product in the current order
            order_items = order.items.filter(product=product)
            if order_items.exists():  # Check if the product was in this order
                # Verify if the order status is 'delivered' to allow review
                if order.status == 'delivered':
                    can_review = True
                    break  # No need to check further orders

        # If the user is not allowed to review, raise a validation error
        if not can_review:
            raise ValidationError("You can only review products you have purchased and received (order status: delivered).")

        # Proceed with creating the review
        return super().perform_create(serializer)
    
class ReviewDetailView(RetrieveDestroyAPIView):
    serializer_class = ReviewsSerializer
    permission_classes = [IsVerifiedUser]

    def get_queryset(self):
        return Reviews.objects.filter(user=self.request.user)
    