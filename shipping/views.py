from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Shipping
from .serializers import ShippingSerializer
from rest_framework import status
from django.shortcuts import get_object_or_404
from users.permissions import IsVerifiedUser, IsAdminUser
from utils.apiResponse import api_response

# Create your views here.
class ShippingStatusView(APIView):
    """
    get shipping status
    """

    permission_classes = [IsVerifiedUser]

    def get(self, request, order_id):
        order_pk = order_id
        shipping = get_object_or_404(Shipping, order__id=order_pk)
        if not shipping:
            return api_response(
                success=False,
                data=None,
                error="Shipping not found",
                message="Shipping not found for this order",
                status_code=status.HTTP_404_NOT_FOUND
            )
        serializer = ShippingSerializer(shipping)

        return api_response(
            success=True,
            data={"shipping": serializer.data},
            message="Shipping details retrieved successfully",
            status_code=status.HTTP_200_OK
        )

class UpdateShippingStatusView(APIView):
    # only admin users can update shipping status
    """
    update shipping status for an order
    only verified admins are allowed 
    """
    permission_classes = [IsAdminUser,IsVerifiedUser]

    def put(self, request, order_id):
        order_pk = order_id
        shipping = get_object_or_404(Shipping, order__id=order_pk)
        if not shipping:
            return api_response(
                success=False,
                data=None,
                error="Shipping not found",
                message="Shipping not found for this order",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ShippingSerializer(shipping, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                data={"shipping": serializer.data},
                message="Shipping status updated successfully",
                status_code=status.HTTP_200_OK
            )
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message="Invalid shipping data",
            status_code=status.HTTP_400_BAD_REQUEST
        )

# track shipping by tracking number
class TrackShippingView(APIView):


    permission_classes = [IsVerifiedUser]

    def get(self, request, tracking_number):
        shipping = get_object_or_404(Shipping, tracking_number=tracking_number)
        if not shipping:
            return api_response(
                success=False,
                data=None,
                error="Shipping not found",
                message="Shipping not found for this tracking number",
                status_code=status.HTTP_404_NOT_FOUND
            )
        serializer = ShippingSerializer(shipping)

        return api_response(
            success=True,
            data={"shipping": serializer.data},
            message="Shipping tracking information retrieved successfully",
            status_code=status.HTTP_200_OK
        )
    

