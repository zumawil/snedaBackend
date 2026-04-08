
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import CartItem, Cart
from .serializer import (
    CartItemSerializer, CartItemCreateSerializer,
    CartSerializer
)
from rest_framework import status
from rest_framework import generics
from users.permissions import IsVerifiedUser
from dotenv import load_dotenv
from utils.apiResponse import api_response
from services.checkout_service import CheckoutService
from products.models import Product

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

load_dotenv()

logger = logging.getLogger(__name__)

#  get user cart
class CartView(APIView):

    permission_classes = [IsVerifiedUser]

    @swagger_auto_schema(
        operation_description="Get the current user's cart",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Cart retrieved successfully",
                schema=CartSerializer()
            ),
            401: openapi.Response(description="Unauthorized - Authentication required"),
            500: openapi.Response(description="Internal server error")
        }
    )
    def get(self, request):
        try:
            cart, created = Cart.objects.get_or_create(user=request.user)
            serializer = CartSerializer(cart)
            return api_response(
                success=True,
                data=serializer.data,
                message="Cart retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error retrieving cart",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CartItemListCreateView(generics.ListCreateAPIView):

    permission_classes = [IsVerifiedUser]

    @swagger_auto_schema(
        operation_description="Get all cart items or create a new cart item",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Cart items retrieved successfully",
                schema=CartItemSerializer(many=True)
            ),
            201: openapi.Response(
                description="Cart item created successfully",
                schema=CartItemSerializer()
            ),
            400: openapi.Response(description="Bad request - Validation failed"),
            401: openapi.Response(description="Unauthorized - Authentication required")
        }
    )
    def get_queryset(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart.items.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CartItemCreateSerializer
        return CartItemSerializer
        
    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        serializer.save(cart=cart)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            success=True,
            data=serializer.data,
            message="Cart items retrieved successfully",
            status_code=status.HTTP_200_OK
        )
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return api_response(
                success=True,
                data=serializer.data,
                message="Cart item created successfully",
                status_code=status.HTTP_201_CREATED
            )
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsVerifiedUser]
    serializer_class = CartItemSerializer

    @swagger_auto_schema(
        operation_description="Get, update, or delete a specific cart item",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Cart item retrieved successfully",
                schema=CartItemSerializer()
            ),
            204: openapi.Response(description="Cart item deleted successfully"),
            400: openapi.Response(description="Bad request - Validation failed"),
            401: openapi.Response(description="Unauthorized - Authentication required"),
            404: openapi.Response(description="Cart item not found")
        }
    )
    def get_queryset(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart.items.all()
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            success=True,
            data=serializer.data,
            message="Cart item retrieved successfully",
            status_code=status.HTTP_200_OK
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                data=serializer.data,
                message="Cart item updated successfully",
                status_code=status.HTTP_200_OK
            )
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return api_response(
            success=True,
            data=None,
            message="Cart item deleted successfully",
            status_code=status.HTTP_204_NO_CONTENT
        )

class CheckoutView(APIView):
    """
     create order from cart
     bills the user 
     and retries payment for a failed order
    """
    permission_classes = [IsVerifiedUser]

    @swagger_auto_schema(
        operation_description="Process checkout - create order from cart and initiate payment",
        security=['Bearer', 'Cookie'],
        manual_parameters=[
            openapi.Parameter('X-Idempotency-Key', openapi.IN_HEADER, description="Unique key to ensure idempotent checkout requests", type=openapi.TYPE_STRING, required=True)
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'address': openapi.Schema(type=openapi.TYPE_STRING, description="Delivery address"),
                'pickup': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Whether customer will pick up order"),
                'pickup_location': openapi.Schema(type=openapi.TYPE_STRING, description="Selected pickup branch location"),
                'order_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="Order ID for payment retry (optional)")
            }
        ),
        responses={
            200: openapi.Response(
                description="Checkout successful or payment retry processed",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "error": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(description="Bad request - Idempotency key required or validation failed"),
            401: openapi.Response(description="Unauthorized - Authentication required")
        }
    )
    def post(self, request):
        user = request.user
        
        # Payment Retry Flow
        order_id = request.data.get('order_id')
        if order_id:
            result = CheckoutService.handle_payment_retry(order_id, user)
            if result.get('success'):
                return api_response(
                    success=True,
                    data=result.get('data'),
                    message=result.get('message'),
                    status_code=status.HTTP_200_OK
                )
            else:
                 return api_response(
                    success=False,
                    data=result.get('data'),
                    error=result.get('error'),
                    message=result.get('message'),
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        # --- Normal Checkout Flow ---
        idempotency_key = request.data.get('X-Idempotency-Key') or request.headers.get('X-Idempotency-Key')
        if not idempotency_key:
            return api_response(
                success=False,
                data=None,
                error="Idempotency key required",
                message="Idempotency key is required for checkout",
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        address = request.data.get('address')
        pickup = str(request.data.get('pickup', '')).lower() == 'true'
        pickup_location = request.data.get('pickup_location')
        if pickup and not pickup_location:
            return api_response(
                success=False,
                data=None,
                error="Pickup location required",
                message="pickup_location is required when pickup is true",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        if not pickup:
            pickup_location = None
        else:
            address = None
        result = CheckoutService.process_checkout(user, idempotency_key, address, pickup, pickup_location)

        return api_response(
            success=result.get('success', False),
            data=result.get('data'),
            message=result.get('message'),
            error=result.get('error'),
            status_code=result.get('status_code', status.HTTP_200_OK)
        )

class AddToCartView(APIView):

    permission_classes = [IsVerifiedUser]

    @swagger_auto_schema(
        operation_description="Add a product to the cart",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Product added to cart successfully",
                schema=CartItemSerializer()
            ),
            404: openapi.Response(description="Product not found"),
            401: openapi.Response(description="Unauthorized - Authentication required")
        }
    )
    def post(self, request, product_pk):
        # create cart if it doesn't exist for user
        cart, created = Cart.objects.get_or_create(user=request.user)

        try:
            product = Product.objects.get(pk=product_pk)
        except Product.DoesNotExist:
            return api_response(
                success=False,
                data=None,
                error="Product not found",
                message="Product with the given ID does not exist",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error retrieving product",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if product.inventory_qty < 1:
            return api_response(
                success=False,
                data=None,
                error="Out of stock",
                message="Product is out of stock",
                status_code=status.HTTP_200_OK
            )

        # check if the cart item is already created in the cart
        cart_item, created = CartItem.objects.get_or_create(
            defaults={'quantity': 1},
            product=product,
            cart=cart
        )
        
        # if the cart item already exists
        if not created:
            '''
                 It compares the total available stock of the product 
                 against the new quantity the user would have if this 
                 add operation succeeds.
            '''
            if product.inventory_qty < cart_item.quantity + 1:
                return api_response(
                    success=False,
                    data=None,
                    error="Insufficient stock",
                    message="Not enough stock available for this product",
                    status_code=status.HTTP_200_OK
                )
            cart_item.quantity += 1
            cart_item.save()
        
        serializer = CartItemSerializer(cart_item)
        return api_response(
            success=True,
            data=serializer.data,
            message="Product added to cart successfully",
            status_code=status.HTTP_200_OK
        )
       
class RemoveProductFromCartView(APIView):

    permission_classes = [IsVerifiedUser]

    @swagger_auto_schema(
        operation_description="Remove a product from the cart",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Product removed from cart successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "error": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            404: openapi.Response(description="Product not found in cart"),
            401: openapi.Response(description="Unauthorized - Authentication required")
        }
    )
    def post(self, request, product_pk):
        try:
            cart = Cart.objects.get(user=request.user)
            # get the product in the cart item
            cart_item = CartItem.objects.get(cart=cart, product__pk=product_pk)
            cart_item.delete()

            return api_response(
                success=True,
                data=None,
                message="Product removed from cart successfully",
                status_code=status.HTTP_200_OK
            )
        except CartItem.DoesNotExist:
            return api_response(
                success=False,
                data=None,
                error="Product not found in cart",
                message="Product with the given ID does not exist in the cart",
                status_code=status.HTTP_404_NOT_FOUND
            )
# decrement product quantity in cart
class DecreMentProductQuantityInCartView(APIView):
    permission_classes = [IsVerifiedUser]

    @swagger_auto_schema(
        operation_description="Decrement product quantity in cart by 1",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Product quantity decremented successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "error": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            404: openapi.Response(description="Product not found in cart"),
            401: openapi.Response(description="Unauthorized - Authentication required")
        }
    )
    def post(self, request, product_pk):
        try:
            cart = Cart.objects.get(user=request.user)
            # get the product in the cart item
            cart_item = CartItem.objects.get(cart=cart, product__pk=product_pk)
            
            # remove the cart item from the cart if the quantity is 1
            if cart_item.quantity <= 1:
                cart_item.delete()
            else:
                cart_item.quantity -= 1
                cart_item.save()

            return api_response(
                success=True,
                data=None,
                message="Product quantity decremented successfully",
                status_code=status.HTTP_200_OK
            )
        except CartItem.DoesNotExist:
            return api_response(
                success=False,
                data=None,
                error="Product not found in cart",
                message="Product with the given ID does not exist in the cart",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
class IncrementProductQuantityInCartView(APIView):
    permission_classes = [IsVerifiedUser]

    @swagger_auto_schema(
        operation_description="Increment product quantity in cart by 1",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Product quantity incremented successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "error": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(description="Bad request - Insufficient stock"),
            404: openapi.Response(description="Product not found in cart"),
            401: openapi.Response(description="Unauthorized - Authentication required")
        }
    )
    def post(self, request, product_pk):
        try:
            cart = Cart.objects.get(user=request.user)
            # get the product in the cart item
            cart_item = CartItem.objects.get(cart=cart, product__pk=product_pk)
            product = cart_item.product

            new_quantity = cart_item.quantity + 1

            if new_quantity > product.inventory_qty:
                return api_response(
                    success=False,
                    data=None,
                    error="Insufficient stock",
                    message="Not enough stock available for this product",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            cart_item.quantity += 1
            cart_item.save()

            return api_response(
                success=True,
                data=None,
                message="Product quantity incremented successfully",
                status_code=status.HTTP_200_OK
            )
        except CartItem.DoesNotExist:
            return api_response(
                success=False,
                data=None,
                error="Product not found in cart",
                message="Product with the given ID does not exist in the cart",
                status_code=status.HTTP_404_NOT_FOUND
            )

# clear all cart
class ClearCartView(APIView):
    permission_classes = [IsVerifiedUser]

    @swagger_auto_schema(
        operation_description="Clear all items from the cart",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Cart cleared successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "error": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            404: openapi.Response(description="Cart not found"),
            401: openapi.Response(description="Unauthorized - Authentication required")
        }
    )
    def post(self, request):
        try:
            cart = Cart.objects.get(user=request.user)
            cart.items.all().delete()

            return api_response(
                success=True,
                data=None,
                message="Cart cleared successfully",
                status_code=status.HTTP_200_OK
            )
        except Cart.DoesNotExist:
            return api_response(
                success=False,
                data=None,
                error="Cart not found",
                message="Cart not found for user",
                status_code=status.HTTP_404_NOT_FOUND
            )

class GetCartCountView(APIView):
    permission_classes = [IsVerifiedUser]

    @swagger_auto_schema(
        operation_description="Get the number of items in the cart",
        security=['Bearer', 'Cookie'],
        responses={
            200: openapi.Response(
                description="Cart count retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "count": openapi.Schema(type=openapi.TYPE_INTEGER)
                            }
                        ),
                        "error": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized - Authentication required")
        }
    )
    def get(self, request):
        try:
            cart = Cart.objects.get(user=request.user)
            return api_response(
                success=True,
                data={"count": cart.items.count()},
                message="Cart count retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Cart.DoesNotExist:
            return api_response(
                success=True,
                data={"count": 0},
                message="Cart count retrieved successfully",
                status_code=status.HTTP_200_OK
            )