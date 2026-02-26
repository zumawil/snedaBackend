from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework import status
from rest_framework.permissions import AllowAny
from .models import Reviews
from .serializers import ReviewsSerializer
from utils.apiResponse import api_response
from users.permissions import IsVerifiedUser

class ReviewListCreateView(ListCreateAPIView): 
    """
    List and create reviews.
    returns paginated list of reviews.
    Optionally filter by product via ?product=<item_no>.
    """
    
    serializer_class = ReviewsSerializer
    permission_classes = [IsVerifiedUser]  

    def get_queryset(self):
        """
        Optionally filter by product via ?product=<item_no>.
        Optimize with select_related if serializer touches user/product fields.
        """
        qs = Reviews.objects.select_related("product", "user").all()
        product_item_no = self.request.query_params.get("product")
        if product_item_no:
            qs = qs.filter(product__item_no=product_item_no)
        return qs

def list(self, request, *args, **kwargs): 
    """
    List reviews.
    Optionally filter by product via ?product=<item_no>.
    """
    page = self.paginate_queryset(self.get_queryset())
    if page is not None:
        serializer = self.get_serializer(page, many=True)
        paginated_response = self.get_paginated_response(serializer.data)

        return api_response(
            success=True,
            data=paginated_response.data,
            message="Reviews retrieved successfully",
            status_code=paginated_response.status_code,
        )

    serializer = self.get_serializer(queryset, many=True)

    return api_response(
        success=True,
        data=serializer.data,
        message="Reviews retrieved successfully",
        status_code=status.HTTP_200_OK,
    )

class ReviewDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = ReviewsSerializer
    permission_classes = [AllowAny]
    lookup_field = "product__item_no"
    lookup_url_kwarg = "item_no"

    def get_queryset(self):
        # Scope to the requesting user's reviews if that's your rule; adjust as needed.
        return Reviews.objects.filter(user=self.request.user).select_related("product", "user")

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