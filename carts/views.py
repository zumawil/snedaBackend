import logging
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import CartItem, Cart
from .serializer import CartItemSerializer, CartSerializer
from orders.serailizer import OrderSerializer
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


class CartView(APIView):

    permission_classes = [IsVerifiedUser]

    def get(self, request):
        try:
            cart, created = Cart.objects.get_or_create(user=request.user)
            serializer = CartSerializer(cart)
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CartItemListCreateView(generics.ListCreateAPIView):

    permission_classes = [IsVerifiedUser]
    serializer_class = CartItemSerializer

    def get_queryset(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart.items.all()
    # create the cartItem for the user cart
    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        serializer.save(cart=cart)

class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsVerifiedUser]
    serializer_class = CartItemSerializer
    
    def get_queryset(self):
        # only allow items belonging to the current user's cart
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart.items.all()

from orders.models import Order, OrderItem

class CheckoutView(APIView):
    permission_classes = [IsVerifiedUser]

    @transaction.atomic()
    def post(self, request):

        # idempotency_key id generated from the frontend
        idempotency_key = request.data.get('X-Idempotency-Key') or request.headers.get('X-Idempotency-Key')
        if not idempotency_key:
            return Response({"error": "Idempotency key required"}, status=status.HTTP_400_BAD_REQUEST)

        attempt = CheckoutAttempt.objects.filter(key=idempotency_key).first()
        # check if there was an order attempt
        if attempt:
            order_serializer = OrderSerializer(attempt.order)
            response_data = {"order": order_serializer.data, "detail": "Order already processed"}
            # Include payment if exists
            payment = Payment.objects.filter(order=attempt.order).first()
            # check if payment was already created and is not processed for retries
            if payment and payment.is_processed:
                # payment is processed return data
                response_data['payment'] = PaymentSerializer(payment).data
            return Response(response_data, status=status.HTTP_200_OK)

        # continue with order
        try:
            cart = Cart.objects.select_related('user').prefetch_related(
                'items__product'
            ).get(user=request.user)
            
            items = cart.items.all()
        
            if not items.exists():
                return Response(
                    {"detail": "Cart is empty. Please add items before checkout."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create order
            order = Order.objects.create(user=request.user)

            for item in items:
            
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                )

            # Calculate total
            amount = sum([item.price * item.quantity for item in order.items.all()])

            address = request.data.get('address')
            pickup = True if request.data.get('pickup', '').lower() == 'true' else False

            # Create shipping record and get tracking number
            tracking_number = create_shipping(order, address, pickup)
            logger.info(f"Shipping created with tracking number: {tracking_number}")

            # Bill user using their email
            data = bill_user(amount, request.user.email)

            payment = None
            if data.get('status') == True:
                # Create payment record
                payment = Payment.objects.create(
                    order=order,
                    amount=amount,
                    method='card',  # Assuming card for Paystack
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

            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Cart.DoesNotExist:
            return Response(
                {"detail": "Cart not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
             
from products.models import Product

class AddToCartView(APIView):

    permission_classes = [IsVerifiedUser]

    def post(self, request, product_pk):
        cart, created = Cart.objects.get_or_create(user=request.user)

        try:
            product = Product.objects.get(pk=product_pk)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # check if the cart item is already created in the cart
        cart_item, created = CartItem.objects.get_or_create(
            defaults={'quantity': 1},
            product=product,
            cart=cart
        )
        
        # if the cart item already exists
        if not created:
            cart_item.quantity += 1
            cart_item.save()
        
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_200_OK)
       

