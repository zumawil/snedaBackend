from django.shortcuts import render
from .serializers import ReviewsSerializer
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework import status
from rest_framework.permissions import AllowAny
from users.permissions import IsAdminUser, IsVerifiedUser
from products.models import Product
from .models import Reviews
from utils.apiResponse import api_response
# Create your views here.

from rest_framework.exceptions import ValidationError


class ReviewListCreateView(ListCreateAPIView):
    serializer_class = ReviewsSerializer
    permission_classes = [IsVerifiedUser]

    def get_permissions(self):
        """
        Allow anyone (including anonymous users) to read reviews,
        but require a verified user to create a review.
        """
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [AllowAny()]
        return [IsVerifiedUser()]

    def get_queryset(self):
        """
        - If ?product=<item_no> is provided, return all reviews for that product
        - Otherwise, return all reviews
        """
        product_item_no = self.request.query_params.get("product")
        queryset = Reviews.objects.all()
        if product_item_no:
            queryset = queryset.filter(product__item_no=product_item_no)
        return queryset.order_by("-date_created")

    def perform_create(self, serializer):
        product_id = self.request.data.get("product")  # by item_no

        # Get product safely by item_no
        try:
            product = Product.objects.get(item_no=product_id)
        except Product.DoesNotExist:
            raise ValidationError("Invalid product.")

        user = self.request.user

        # Check if user already reviewed this product
        if product.reviews.filter(user=user).exists():
            raise ValidationError("You can't review a product twice.")

        # Check if user has delivered orders containing the product
        has_delivered_order = user.orders.shipping.filter(
            status="delivered", order__items__product=product
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
            status_code=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return api_response(
                success=True,
                data=serializer.data,
                message="Review created successfully",
                status_code=status.HTTP_201_CREATED,
            )
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class ReviewDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = ReviewsSerializer
    permission_classes = [IsVerifiedUser]

    def get_queryset(self):
        """
        Users can only access their own reviews.
        If `item_no` is provided in the URL, we scope to that product.
        """
        queryset = Reviews.objects.filter(user=self.request.user)
        item_no = self.kwargs.get("item_no")
        if item_no:
            queryset = queryset.filter(product__item_no=item_no)
        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            success=True,
            data=serializer.data,
            message="Review retrieved successfully",
            status_code=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        # Always allow partial updates so product doesn't need to be re-sent
        kwargs["partial"] = True
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                data=serializer.data,
                message="Review updated successfully",
                status_code=status.HTTP_200_OK,
            )
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return api_response(
            success=True,
            data=None,
            message="Review deleted successfully",
            status_code=status.HTTP_204_NO_CONTENT,
        )
    