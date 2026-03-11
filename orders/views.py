import logging
from django.shortcuts import render
from .serializers import (
    OrderItemSerializer, OrderItemCreateSerializer, OrderItemUpdateSerializer,
    OrderSerializer, OrderStatusUpdateSerializer, OrderDetailSerializer
)
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Order, OrderItem
from shipping.models import Shipping
from users.permissions import IsAdminUser, IsVerifiedUser
from django.db.models import F
from products.models import Product
from utils.apiResponse import api_response

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


logger = logging.getLogger(__name__)

# Create your views here.

class OrderView(APIView):

    """
    Handle user orders.

    GET /orders/: List all orders for the authenticated user.
    GET /orders/<pk>/: Retrieve details of a specific order.
    """

    permission_classes = [IsVerifiedUser]

    @swagger_auto_schema(
        operation_description="Get all orders for the authenticated user or a specific order by ID",
        security=['Bearer', 'Cookie'],
        manual_parameters=[
            openapi.Parameter('pk', openapi.IN_PATH, description="Order ID (optional)", type=openapi.TYPE_INTEGER)
        ],
        responses={
            200: openapi.Response(
                description="Orders retrieved successfully",
                schema=OrderSerializer(many=True)
            ),
            401: openapi.Response(description="Unauthorized - Authentication required"),
            404: openapi.Response(description="Order not found")
        }
    )
    def get(self, request, pk=None):
        try:
            if pk:
                order = get_object_or_404(Order, pk=pk, user=request.user)
                serializer = OrderSerializer(order)
                return api_response(
                    success=True,
                    data=serializer.data,
                    message="Order retrieved successfully",
                    status_code=status.HTTP_200_OK
                )
            else:
                orders = Order.objects.filter(user=request.user).order_by('-created_at')
                serializer = OrderSerializer(orders, many=True)
                return api_response(
                    success=True,
                    data=serializer.data,
                    message="Orders retrieved successfully",
                    status_code=status.HTTP_200_OK
                )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error retrieving orders",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OrderItemView(APIView):
    """
    Handle order items for authenticated users.
    
    Allows users to:
    - GET: List all order items or retrieve a specific order item by ID
    - POST: Create a new order item for an existing order
    - PUT: Update an existing order item
    - DELETE: Remove an order item from an order
    
    All operations require the order to belong to the authenticated user.
    """

    permission_classes = [IsVerifiedUser]

    @swagger_auto_schema(
        operation_description="Get all order items for the authenticated user or a specific order item by ID",
        security=['Bearer', 'Cookie'],
        manual_parameters=[
            openapi.Parameter('pk', openapi.IN_PATH, description="Order Item ID (optional)", type=openapi.TYPE_INTEGER)
        ],
        responses={
            200: openapi.Response(
                description="Order items retrieved successfully",
                schema=OrderItemSerializer(many=True)
            ),
            401: openapi.Response(description="Unauthorized - Authentication required"),
            404: openapi.Response(description="Order item not found")
        }
    )
    def get(self, request, pk=None):
        try:
            if pk:
                # Get specific order item
                order_item = get_object_or_404(OrderItem, pk=pk, order__user=request.user)
                serializer = OrderItemSerializer(order_item)
                return api_response(
                    success=True,
                    data=serializer.data,
                    message="Order item retrieved successfully",
                    status_code=status.HTTP_200_OK
                )
            else:
                # List all order items for user
                order_items = OrderItem.objects.filter(order__user=request.user)
                serializer = OrderItemSerializer(order_items, many=True)
                return api_response(
                    success=True,
                    data=serializer.data,
                    message="Order items retrieved successfully",
                    status_code=status.HTTP_200_OK
                )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error retrieving order items",
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(
        operation_description="Create a new order item for an existing order",
        security=['Bearer', 'Cookie'],
        request_body=OrderItemCreateSerializer,
        responses={
            201: openapi.Response(
                description="Order item created successfully",
                schema=OrderItemSerializer()
            ),
            400: openapi.Response(description="Bad request - Invalid data"),
            401: openapi.Response(description="Unauthorized - Authentication required"),
            403: openapi.Response(description="Forbidden - Cannot create item for another user's order")
        }
    )
    def post(self, request):
        serializer = OrderItemCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Ensure the order belongs to the user
            order = serializer.validated_data['order']
            if order.user != request.user:
                return api_response(
                    success=False,
                    data=None,
                    error="Unauthorized",
                    message="You cannot create order items for orders that don't belong to you",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            serializer.save()
            return api_response(
                success=True,
                data=serializer.data,
                message="Order item created successfully",
                status_code=status.HTTP_201_CREATED
            )
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message="Invalid order item data",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    @swagger_auto_schema(
        operation_description="Update an existing order item's quantity",
        security=['Bearer', 'Cookie'],
        request_body=OrderItemUpdateSerializer,
        manual_parameters=[
            openapi.Parameter('pk', openapi.IN_PATH, description="Order Item ID", type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={
            200: openapi.Response(
                description="Order item updated successfully",
                schema=OrderItemSerializer()
            ),
            400: openapi.Response(description="Bad request - Invalid data"),
            401: openapi.Response(description="Unauthorized - Authentication required"),
            404: openapi.Response(description="Order item not found")
        }
    )
    def put(self, request, pk):
        try:
            order_item = get_object_or_404(OrderItem, pk=pk, order__user=request.user)
            serializer = OrderItemUpdateSerializer(order_item, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return api_response(
                    success=True,
                    data=serializer.data,
                    message="Order item updated successfully",
                    status_code=status.HTTP_200_OK
                )
            return api_response(
                success=False,
                data=None,
                error="Validation failed",
                message="Invalid order item data",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error updating order item",
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(
        operation_description="Delete an order item from an order",
        security=['Bearer', 'Cookie'],
        manual_parameters=[
            openapi.Parameter('pk', openapi.IN_PATH, description="Order Item ID", type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={
            204: openapi.Response(description="Order item deleted successfully"),
            401: openapi.Response(description="Unauthorized - Authentication required"),
            404: openapi.Response(description="Order item not found")
        }
    )
    def delete(self, request, pk):
        try:
            order_item = get_object_or_404(OrderItem, pk=pk, order__user=request.user)
            order_item.delete()
            return api_response(
                success=True,
                data=None,
                message="Order item deleted successfully",
                status_code=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error deleting order item",
                status_code=status.HTTP_400_BAD_REQUEST
            )

class OrderCancelView(APIView):
    """
    Cancel a pending order.
    
    POST /orders/cancel/<pk>/: Cancel the specified order if its status is 'pending'.
    Only the order owner can cancel their order.
    Cancelling a pending order will:
    - Restore stock for each order item
    - Cancel any linked shipping record
    """
    permission_classes = [IsVerifiedUser]

    @swagger_auto_schema(
        operation_description="Cancel a pending order (owner only)",
        security=['Bearer', 'Cookie'],
        manual_parameters=[
            openapi.Parameter('pk', openapi.IN_PATH, description="Order ID", type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={
            200: openapi.Response(
                description="Order cancelled successfully",
                schema=OrderSerializer()
            ),
            400: openapi.Response(description="Bad request - Order cannot be cancelled in current state or already cancelled"),
            401: openapi.Response(description="Unauthorized - Authentication required"),
            404: openapi.Response(description="Order not found")
        }
    )
    def post(self, request, pk):
        try:
            order = get_object_or_404(Order, pk=pk, user=request.user)
            # use effective_status (shipping-derived when present) to decide
            current_status = order.effective_status
            if current_status == "pending":
                # Restore stock for each order item
                for item in order.items.all():
                    Product.objects.filter(
                        id=item.product.id
                    ).update(stock=F('stock') + item.quantity)
                # cancel any linked shipping record if present
                if hasattr(order, 'shipping') and order.shipping:
                    # logger.info(f"Cancelling shipping for order {order.id}")
                    order.shipping.status = 'cancelled'
                    order.shipping.save()
                    # logger.info(f"Shipping cancelled for order {order.id}")
                # nothing to write to Order model; shipping holds the state
                return api_response(
                    success=True,
                    data=None,
                    message="Order cancelled successfully",
                    status_code=status.HTTP_200_OK
                )
            elif current_status == 'cancelled':
                return api_response(
                    success=False,
                    data=None,
                    error="Already cancelled",
                    message="Order already cancelled",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            else:
                return api_response(
                    success=False,
                    data=None,
                    error="Cannot cancel",
                    message="Order can't be cancelled in its current state",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error cancelling order",
                status_code=status.HTTP_400_BAD_REQUEST
            )

class OrderDetailView(APIView):
    """
    Handle detailed order information for authenticated users.
    
    GET /orders/detail/: Retrieve detailed information about the authenticated user's orders.
    Returns order details including user information, payment status, and fulfillment status.
    """
    permission_classes = [IsVerifiedUser]

    @swagger_auto_schema(
        operation_description="Get detailed order information for the authenticated user",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Order details retrieved successfully",
                schema=OrderDetailSerializer(many=True)
            ),
            401: openapi.Response(description="Unauthorized - Authentication required"),
            400: openapi.Response(description="Bad request - Error retrieving order details")
        }
    )
    def get(self, request):
        try:
            orders = Order.objects.filter(user=request.user).order_by('-created_at')
            serializer = OrderDetailSerializer(orders, many=True)
            return api_response(
                success=True,
                data=serializer.data,
                message="Orders retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error retrieving order details",
                status_code=status.HTTP_400_BAD_REQUEST
            )

    