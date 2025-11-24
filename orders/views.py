import logging
from django.shortcuts import render
from .serailizer import OrderItemSerializer, OrderSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Order, OrderItem
from shipping.models import Shipping
from users.permissions import IsAdminUser, IsVerifiedUser

logger = logging.getLogger(__name__)

# Create your views here.

class OrderView(APIView):

    
    """
    Handle user orders.

    GET /orders/: List all orders for the authenticated user.
    GET /orders/<pk>/: Retrieve details of a specific order.
    """

    permission_classes = [IsVerifiedUser]

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
    """
    Handle order items.

    GET /order-items/: List all order items for the authenticated user.
    GET /order-items/<pk>/: Retrieve details of a specific order item.
    POST /order-items/: Create a new order item.
    PUT /order-items/<pk>/: Update a specific order item.
    DELETE /order-items/<pk>/: Delete a specific order item.
    """

    permission_classes = [IsVerifiedUser]

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


class OrderUpdateStatusView(APIView):
    """
    Update order status (Admin only).

    PATCH /orders/<pk>/status/: Update the status of a specific order.
    Requires admin permissions. Valid statuses: pending, shipped, delivered.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def patch(self, request, pk):
        try:
            # Admin can update any order, so we don't filter by user
            order = get_object_or_404(Order, pk=pk)
            
            # Only allow status field to be updated
            new_status = request.data.get('status')
            if not new_status:
                return Response(
                    {'error': 'Status field is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate status choice
            valid_statuses = ['pending', 'shipped', 'delivered', 'cancelled']
            if new_status not in valid_statuses:
                return Response(
                    {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update shipping.status (Shipping is the source of truth for order state)
            if hasattr(order, 'shipping') and order.shipping:
                logger.info(f"Updating shipping status for order {order.id} to {new_status}")
                order.shipping.status = new_status
                order.shipping.save()
                logger.info(f"Shipping status updated for order {order.id}")
            else:
                logger.warning(f"No shipping record found for order {order.id}")
                return Response(
                    {'error':"no shipping related to this order was found"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class OrderCancelView(APIView):
    """
    Cancel a pending order.

    POST /orders/<pk>/cancel/: Cancel the specified order if its status is 'pending'.
    Only the order owner can cancel their order.
    """
    permission_classes = [IsVerifiedUser]
    
    def post(self, request, pk):
        try:
            order = get_object_or_404(Order, pk=pk, user=request.user)
            # use effective_status (shipping-derived when present) to decide
            current_status = order.effective_status
            if current_status == "pending":
                # Restore stock for each order item
                for item in order.items.all():
                    item.product.stock += item.quantity
                    item.product.save()
                # cancel any linked shipping record if present
                if hasattr(order, 'shipping') and order.shipping:
                    logger.info(f"Cancelling shipping for order {order.id}")
                    order.shipping.status = 'cancelled'
                    order.shipping.save()
                    logger.info(f"Shipping cancelled for order {order.id}")
                # nothing to write to Order model; shipping holds the state
                return Response({'detail': 'Order cancelled'}, status=status.HTTP_200_OK)
            elif current_status == 'cancelled':
                return Response({'detail':'order already cancelled'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'detail':"order can't be cancelled"},  status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)