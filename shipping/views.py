from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Shipping
from .serializers import ShippingSerializer
from rest_framework import status
from django.shortcuts import get_object_or_404
from users.permissions import IsVerifiedUser, IsAdminUser

# Create your views here.
class ShippingStatusView(APIView):

    permission_classes = [IsVerifiedUser]

    def get(self, request, order_id):
        order_pk = order_id
        shipping = get_object_or_404(Shipping, order__id=order_pk)
        if not shipping:
            return Response({"error":"shipping not found for this order"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ShippingSerializer(shipping)

        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

# class UpdateShippingStatusView(APIView):
#     # only admin users can update shipping status
#     permission_classes = [IsAdminUser]

#     def put(self, request, order_id):
#         order_pk = order_id
#         shipping = get_object_or_404(Shipping, order__id=order_pk)
#         if not shipping:
#             return Response({"error":"shipping not found for this order"}, status=status.HTTP_404_NOT_FOUND)
        
#         serializer = ShippingSerializer(shipping, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"data": serializer.data}, status=status.HTTP_200_OK)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# track shipping by tracking number
class TrackShippingView(APIView):

    permission_classes = [IsVerifiedUser]

    def get(self, request, tracking_number):
        shipping = get_object_or_404(Shipping, tracking_number=tracking_number)
        if not shipping:
            return Response({"error":"shipping not found for this tracking number"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ShippingSerializer(shipping)

        return Response({"data": serializer.data}, status=status.HTTP_200_OK)
    

