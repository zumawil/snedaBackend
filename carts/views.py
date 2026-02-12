import logging
import time
import os
import requests
from decimal import Decimal, ROUND_HALF_UP
from django.shortcuts import render
from django.utils import timezone
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
from dotenv import load_dotenv
from payments.models import Payment
from payments.serializers import PaymentSerializer
from utils.apiResponse import api_response
import json

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


# convert cedis to pesewas for paystack
def to_pesewas(amount):
    """Convert amount to pesewas (smallest currency unit for GHS)."""
    return int((Decimal(amount) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))



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
from products.models import Product

# user sends a payment intent here and idempotency is generated on the server
# class PaymentIntentView(APIView):
#     permission_classes = [IsVerifiedUser]

#     def post(self, request):
#         pass
        
# make a checkout

# chart the user
def bill_user(amount, email, order_id=None, retry_count=0):
    amount = to_pesewas(amount)
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    url = "https://api.paystack.co/transaction/initialize"
    
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    # Generate reference
    timestamp = int(time.time())
    if order_id:
        if retry_count > 0:
            reference = f"ORD-{order_id}-R{retry_count}-{timestamp}"
        else:
            reference = f"ORD-{order_id}-{timestamp}"
    else:
        reference = None
    
    data = {
        "email": email,
        "amount": amount,
        "currency": "GHS",
        "callback_url": f"{os.getenv('APP_URL')}payments/callback/"
    }
    
    if reference:
        data["reference"] = reference
        data["metadata"] = {
            "order_id": order_id,
            "retry_count": retry_count
        }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Paystack API error: {str(e)}")
        return {
            'status': False,
            'message': f'Network error: {str(e)}'
        }

# retruns the status of a transaction
def verify_transaction_status(reference):
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('status'):
            return data['data']['status']
        
        return 'unknown'
    except requests.exceptions.RequestException as e:
        logger.error(f"Error verifying transaction {reference}: {str(e)}")
        return 'unknown'


def handle_payment_retry(order_id, max_retries=3):
    try:
        order = Order.objects.get(id=order_id)
        # get last payment
        payment = Payment.objects.order_by('-date_created').filter(order=order).first()
    except Order.DoesNotExist:
        return {
            'success': False,
            'error': 'Order not found',
            'payment_url': None
        }
    except Payment.DoesNotExist:
        return {
            'success': False,
            'error': 'Payment not found',
            'payment_url': None
        }
    
    # Check if already at max retries
    current_retry_count = getattr(payment, 'retry_count', 0)
    if current_retry_count >= max_retries:
        return {
            'success': False,
            'error': f'Maximum retry attempts ({max_retries}) reached',
            'payment_url': None,
            'retry_count': current_retry_count
        }
    
    # Verify current payment status first
    # current_status = verify_transaction_status(payment.paystack_reference)
    current_status = 'failed'
    
    if current_status == 'success':
        # Payment already succeeded, update local record
        payment.is_processed = True
        payment.status = 'completed'
        payment.save()
        
        return {
            'success': True,
            'message': 'Payment already completed',
            'payment_url': None,
            'status': 'completed'
        }
    
    # if the payment is pending return the existing URL
    # to complete the payment
    if current_status == 'pending':
        # Payment still pending, return existing URL
        authorization_url = getattr(payment, 'authorization_url', None)
        return {
            'success': True,
            'message': 'Payment still pending. Please complete the existing payment.',
            'payment_url': authorization_url,
            'status': 'pending',
            'retry_count': current_retry_count
        }
    
    # Payment failed or abandoned - create new attempt
    new_retry_count = current_retry_count + 1

    print("payment status retrying because it failed", current_status)
    
    # Initialize new payment with Paystack
    paystack_response = bill_user(
        amount=payment.amount,
        email=order.user.email,
        order_id=order.id,
        retry_count=new_retry_count
    )
    
    if paystack_response.get('status'):
        # create new payment 
        new_payment = Payment.objects.create(
                    order=order,
                    amount=payment.amount,
                    status='pending',
                    paystack_reference=paystack_response['data']['reference'],
                    authorization_url=paystack_response['data']['authorization_url'],
                    retry_count=new_retry_count,
                    last_retry_at = timezone.now()
                )
        payment.status = 'failed'
        payment.save()
        
        logger.info(f"New Payment issued for order #{order_id}")
        
        return {
            'success': True,
            'message': f'New Payment issued for order #{order_id}',
            'payment_url': paystack_response['data']['authorization_url'],
            'reference': paystack_response['data']['reference'],
            'retry_count': new_retry_count,
            'status': 'pending'
        }
    else:
        # Paystack initialization failed
        error_message = paystack_response.get('message', 'Failed to initialize payment')
        logger.error(f"Payment retry failed for order {order_id}: {error_message}")
        
        return {
            'success': False,
            'error': error_message,
            'payment_url': None,
            'retry_count': current_retry_count
        }


class CheckoutView(APIView):
    """
    This view is used to create an order from the cart.
    It uses idempotency to prevent creating the same order multiple times.
    convert all cart items to order items
    and bills the user
    """
    permission_classes = [IsVerifiedUser]

    def post(self, request):
        # --- Payment Retry Flow ---
        # If order_id is provided, handle payment retry (no cart needed)
        order_id = request.data.get('order_id')
        if order_id:
            return self._handle_payment_retry(request, order_id)

        # --- Normal Checkout Flow ---
        # Get idempotency key from request
        idempotency_key = request.data.get('X-Idempotency-Key') or request.headers.get('X-Idempotency-Key')
        if not idempotency_key:
            return api_response(
                success=False,
                data=None,
                error="Idempotency key required",
                message="Idempotency key is required for checkout",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Phase 1: Check idempotency and reserve stock (in transaction)
            result = self._create_order_and_reserve_stock(request, idempotency_key)
            
            if isinstance(result, Response):
                return result
            
            order, amount = result
            
            # Phase 2: External calls (outside transaction)
            return self._process_payment_and_shipping(request, order, amount)
            
        except Cart.DoesNotExist:
            return api_response(
                success=False,
                data=None,
                error="Cart not found",
                message="Cart not found for user",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error during checkout: {str(e)}")
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error during checkout",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _create_order_and_reserve_stock(self, request, idempotency_key):
        """
        Phase 1: Atomically check idempotency, create order, and reserve stock.
        Returns: (order, amount) tuple or response dict if order already exists
        """
        with transaction.atomic():
            # lock rows to prevent race conditions
            attempt, created = CheckoutAttempt.objects.select_for_update().get_or_create(key=idempotency_key)

            # If this is a duplicate request, return the existing order
            if not created and attempt.order:
                return self._handle_existing_order(attempt)

            # Lock and fetch cart with items
            cart = Cart.objects.select_for_update().select_related('user').prefetch_related(
                'items__product'
            ).get(user=request.user)
            
            # Lock cart items to prevent modifications during checkout
            items = list(cart.items.select_for_update().all())
            
            if not items:
                raise Exception("Cart is empty. Please add items before checkout.")

            # Create order
            order = Order.objects.create(user=request.user)
            
            # Link order to checkout attempt for idempotency
            attempt.order = order
            attempt.save()

            # Reserve stock atomically for each item
            for item in items:
                # Lock the product row to prevent concurrent modifications
                product = Product.objects.select_for_update().get(pk=item.product.pk)
                
                # Check stock availability
                if product.inventory_qty < item.quantity:
                    current_stock = product.inventory_qty
                    raise Exception(
                        f'Insufficient stock for product {product.item_no}. '
                        f'Available: {current_stock}, Requested: {item.quantity}'
                    )
                
                # Decrement stock
                product.inventory_qty -= item.quantity
                product.save()
                
                # Create order item
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price=product.gross_price
                )

            # Calculate and save total amount
            amount = sum([item.get_total_price() for item in order.items.all()])
            order.total_amount = amount
            order.save()

            logger.info(f"Order {order.id} created during checkout for user {request.user.email}")
            
            return order, amount

    def _handle_existing_order(self, attempt):
        """
        Handle case where order already exists (duplicate idempotency key).
        Returns a response dict.
        """
        order_serializer = OrderSerializer(attempt.order)
        response_data = {
            "order": order_serializer.data,
            "detail": "Payment order already created"
        }
        
        # Check if payment exists and is processed
        payment = Payment.objects.filter(order=attempt.order).first()
        
        if payment and payment.is_processed:
            response_data['payment'] = PaymentSerializer(payment).data
            return api_response(
                success=True,
                data=response_data,
                message="Payment order already created and processed",
                status_code=status.HTTP_200_OK
            )
        else:
            # Payment exists but not processed - attempt retry
            retry_result = handle_payment_retry(attempt.order.id)
            
            response_data['payment'] = PaymentSerializer(payment).data
            response_data['retry_result'] = retry_result
            
            # Add payment URL if available from retry
            if retry_result.get('payment_url'):
                response_data['payment_url'] = retry_result['payment_url']
            
            message = retry_result.get('message', 'Payment order already created')
            
            return api_response(
                success=True,
                data=response_data,
                message=message,
                status_code=status.HTTP_200_OK
            )

    def _handle_payment_retry(self, request, order_id):
        """
        Handle payment retry for an existing order.
        Validates that the order belongs to the requesting user,
        checks the latest payment status, and either returns the
        existing payment URL or creates a new payment attempt.
        Does NOT touch the cart.
        """
        try:
            # Validate order exists and belongs to the requesting user
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return api_response(
                success=False,
                data=None,
                error="Order not found",
                message="Order not found or does not belong to you",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Get the latest payment for this order
        latest_payment = Payment.objects.filter(
            order=order
        ).order_by('-date_created').first()

        print(order)

        if not latest_payment:
            return api_response(
                success=False,
                data=None,
                error="No payment found",
                message="No payment record found for this order. Please initiate checkout first.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # If payment already succeeded and processed, no retry needed
        if latest_payment.status == 'success' and latest_payment.is_processed:
            return api_response(
                success=True,
                data={
                    'order': OrderSerializer(order).data,
                    'payment': PaymentSerializer(latest_payment).data,
                    'status': 'success'
                },
                message="Order is already paid",
                status_code=status.HTTP_200_OK
            )

        # Delegate to handle_payment_retry which:
        # - Verifies current status with Paystack API
        # - Returns existing URL if still pending
        # - Creates a new Payment record if failed/abandoned
        # - Respects max_retries
        retry_result = handle_payment_retry(
            order.id,
            max_retries=latest_payment.max_retries
        )

        # Build consistent response
        response_data = {
            'order': OrderSerializer(order).data,
            'payment_url': retry_result.get('payment_url'),
            'reference': retry_result.get('reference'),
            'retry_count': retry_result.get('retry_count', 0),
            'status': retry_result.get('status', 'unknown')
        }

        if retry_result.get('success'):
            return api_response(
                success=True,
                data=response_data,
                message=retry_result.get('message', 'Payment retry initialized'),
                status_code=status.HTTP_200_OK
            )
        else:
            return api_response(
                success=False,
                data=response_data,
                error=retry_result.get('error', 'Payment retry failed'),
                message=retry_result.get('error', 'Payment retry failed'),
                status_code=status.HTTP_400_BAD_REQUEST
            )

    def _process_payment_and_shipping(self, request, order, amount):
        """
        Phase 2: Process external payment and shipping (outside transaction).
        This prevents holding database locks during slow external API calls.
        """
        try:
            # Get shipping details
            address = request.data.get('address')
            pickup = str(request.data.get('pickup', '')).lower() == 'true'
            
            # Create shipping record and get tracking number
            tracking_number = create_shipping(order, address, pickup)
            logger.info(f"Shipping created with tracking number: {tracking_number}")

            # Initiate payment with external provider
            data = bill_user(amount, request.user.email, order_id=order.id, retry_count=0)

            payment = None
            if data.get('status') == True:
                # Create payment record
                payment = Payment.objects.create(
                    order=order,
                    amount=amount,
                    status='pending',
                    paystack_reference=data['data']['reference'],
                    authorization_url=data['data']['authorization_url']
                )
                logger.info(f"Payment created for order {order.id} with reference {data['data']['reference']}")

            # Prepare response
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
            
        except Exception as e:
            # Payment/shipping failed but order exists with reserved stock
            # You may want to implement a cleanup/cancellation strategy here
            self._cancel_order_and_restore_stock(order)
            logger.error(f"Payment/shipping failed for order {order.id}: {str(e)}")
            
            # Option 1: Return error and let user retry
            return api_response(
                success=False,
                data={'order_id': order.id},
                error=str(e),
                message="Order created but payment failed. Please contact support.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    def _cancel_order_and_restore_stock(self, order):
        """
            Cancel order and restore stock if payment fails.
        """
        with transaction.atomic():
            # Restore stock for each order item
            for order_item in order.items.select_for_update().all():
                product = Product.objects.select_for_update().get(pk=order_item.product.pk)
                product.inventory_qty += order_item.quantity
                product.save()
            
            # Mark order as cancelled
            order.status = 'cancelled'
            order.save()
            
            logger.info(f"Order {order.id} cancelled and stock restored")

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

class GetCartCountView(APIView):
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