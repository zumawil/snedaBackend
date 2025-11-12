from django.shortcuts import render
from .serailizer import OrderItemSerializer, OrderSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Order, OrderItem

# Create your views here.

class OrderView(APIView):

    def get(self, request, pk=None):
        try:
            if pk:
                # Get specific order
                order = get_object_or_404(Order, pk=pk, user=request.user)
                serializer = OrderSerializer(order)
                return Response(
                    serializer.data, 
                    status=status.HTTP_200_OK
                )
            else:
                # List all orders for user
                orders = Order.objects.filter(user=request.user)
                serializer = OrderSerializer(orders, many=True)
                return Response(
                    serializer.data,
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OrderItemView(APIView):

    def get(self, request, pk=None):
        try:
            if pk:
                # Get specific order item
                order_item = get_object_or_404(OrderItem, pk=pk, order__user=request.user)
                serializer = OrderItemSerializer(order_item)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                # List all order items for user
                order_items = OrderItem.objects.filter(order__user=request.user)
                serializer = OrderItemSerializer(order_items, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        serializer = OrderItemSerializer(data=request.data)
        if serializer.is_valid():
            # Ensure the order belongs to the user
            order = serializer.validated_data['order']
            if order.user != request.user:
                return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            order_item = get_object_or_404(OrderItem, pk=pk, order__user=request.user)
            serializer = OrderItemSerializer(order_item, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            order_item = get_object_or_404(OrderItem, pk=pk, order__user=request.user)
            order_item.delete()
            return Response({'message': 'OrderItem deleted'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)