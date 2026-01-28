import logging
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import CartItem, Cart
from .serializer import (
    CartItemSerializer, CartItemCreateSerializer,
    CartSerializer, CheckoutSerializer, CheckoutResponseSerializer
)
from orders.serializers import OrderSerializer
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework import generics
from users.permissions import IsVerifiedUser, IsAdminUser
from django.db import transaction
from django.db.models import F
from shipping.models import Shipping
from shipping.generate_shipping_number import generate_tracking_number
from .models import CheckoutAttempt
import requests
from dotenv import load_dotenv
import os
from payments.models import Payment
from payments.serializers import PaymentSerializer
from utils.apiResponse import api_response

load_dotenv()

logger = logging.getLogger(__name__)
# Create your views here.

# helper functions
def create_shipping(order, address, pickup=False):
    """
    Create a shipping record for an order.
    
    Args:
        order: The Order instance
        address: Shipping address string
        pickup: Boolean indicating if it's a pickup order
        
    Returns:
        str: The generated tracking number
    """
    tracking_number = generate_tracking_number()
    Shipping.objects.create(
        order=order,
        status="pending",
        tracking_number=tracking_number,
        address=address,
        pickup=pickup
    )
    return tracking_number


from decimal import Decimal, ROUND_HALF_UP

# convert cedis to pesewas for paystack
def to_pesewas(amount):
    """Convert amount to pesewas (smallest currency unit for GHS)."""
    return int((Decimal(amount) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def bill_user(amount, email):
    """
    Initialize a Paystack payment transaction.
    
    Args:
        amount: The amount to charge (in GHS)
        email: Customer's email address
        
    Returns:
        dict: Paystack API response
    """
    amount = to_pesewas(amount)
    
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    url = "https://api.paystack.co/transaction/initialize"

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "email": email,
        "amount": amount,   # amount in pesewas (₵50.00 = 5000)
        "currency": "GHS",  # GHS works with Paystack
        "callback_url": f"{os.getenv('APP_URL')}payments/callback/"
    }

    response = requests.post(url, json=data, headers=headers)

    return response.json()

#  get user cart
class CartView(APIView):

    permission_classes = [IsVerifiedUser]

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
    
    def get_queryset(self):
        # only allow items belonging to the current user's cart
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

from orders.models import Order, OrderItem

class CheckoutView(APIView):
    permission_classes = [IsVerifiedUser]

    def post(self, request):

        # idempotency_key id generated from the frontend
        idempotency_key = request.data.get('X-Idempotency-Key') or request.headers.get('X-Idempotency-Key')
        if not idempotency_key:
            return api_response(
                success=False,
                data=None,
                error="Idempotency key required",
                message="Idempotency key is required for checkout",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        attempt = CheckoutAttempt.objects.filter(key=idempotency_key).first()
        # check if there was an order attempt
        if attempt:
            order_serializer = OrderSerializer(attempt.order)
            response_data = {"order": order_serializer.data, "detail": "payment order already created"}
            # Include payment if exists
            payment = Payment.objects.filter(order=attempt.order).first()
            # check if payment was already created and is not processed for retries
            if payment and payment.is_processed:
                # payment is processed return data
                response_data['payment'] = PaymentSerializer(payment).data
            return api_response(
                success=True,
                data=response_data,
                message="Payment order already created",
                status_code=status.HTTP_200_OK
            )

        # continue with  
        try:
            cart = Cart.objects.select_related('user').prefetch_related(
                'items__product'
            ).get(user=request.user)
            
            items = cart.items.all()
        
            if not items.exists():
                return api_response(
                    success=False,
                    data=None,
                    error="Cart is empty",
                    message="Cart is empty. Please add items before checkout.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Create order and reserve stock atomically
            with transaction.atomic():
                order = Order.objects.create(user=request.user)
                for item in items:
                    # Try to reserve stock atomically
                    updated = Product.objects.filter(
                        pk=item.product.pk,
                        inventory_qty__gte=item.quantity  # Ensure sufficient stock
                    ).update(inventory_qty=F('inventory_qty') - item.quantity)
                    
                    if updated == 0:
                        # Stock insufficient - rollback this transaction
                        # Refresh product data for error message
                        current_stock = Product.objects.get(pk=item.product.pk).inventory_qty
                        raise Exception(f'Insufficient stock for product {item.product.item_no}. Available: {current_stock}, Requested: {item.quantity}')
                    
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.gross_price
                    )

            # Calculate total
            amount = sum([item.get_total_price() for item in order.items.all()])

            address = request.data.get('address')
            pickup = True if str(request.data.get('pickup', '')).lower() == 'true' else False

            # Create shipping record and get tracking number
            tracking_number = create_shipping(order, address, pickup)
            logger.info(f"Shipping created with tracking number: {tracking_number}")

            # Bill user using their email - do this outside of stock reservation transaction
            data = bill_user(amount, request.user.email)

            payment = None
            if data.get('status') == True:
                # Create payment record
                payment = Payment.objects.create(
                    order=order,
                    amount=amount,
                    status='pending',
                    paystack_reference=data['data']['reference']
                )

            order.total_amount = amount
            order.save()
            logger.info(f"Order {order.id} created during checkout for user {request.user.email}")

            # Clear cart
            cart.items.all().delete()

            CheckoutAttempt.objects.create(
                key = idempotency_key,
                order = order,
            )

            response_data = {
                'order': OrderSerializer(order).data,
            }

            if payment:
                response_data['payment'] = PaymentSerializer(payment).data
                response_data['payment_url'] = data['data']['authorization_url']

            return api_response(
                success=True,
                data=response_data,
                message="Checkout completed successfully",
                status_code=status.HTTP_201_CREATED
            )
            
        except Cart.DoesNotExist:
            return api_response(
                success=False,
                data=None,
                error="Cart not found",
                message="Cart not found for user",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error during checkout",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
             
from products.models import Product

class AddToCartView(APIView):

    permission_classes = [IsVerifiedUser]

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