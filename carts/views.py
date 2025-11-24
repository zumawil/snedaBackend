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
# Create your views here.

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
            
            # Validate all items before processing
            for item in items:
                # warn if a product in the cart is out of stock
                if item.product.stock <= 0:
                    return Response(
                        {"detail": f"{item.product.name} is no longer available"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # warn if requested quantity exceeds available stock
                if item.product.stock < item.quantity:
                    return Response(
                        {"detail": f"Insufficient stock for {item.product.name}. Available: {item.product.stock}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Create order
            order = Order.objects.create(user=request.user)
            
            # Process items and update stock atomically
            for item in items:
                updated = Product.objects.filter(
                    id=item.product.id,
                    stock__gte=item.quantity # select product who have enough stock for quantity requested
                ).update(stock=F('stock') - item.quantity)
                
                if updated == 0:
                    raise Exception(f"Stock changed for {item.product.name}")
                
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                )
            
            # Calculate total
            amount = sum([item.price * item.quantity for item in order.items.all()])
            order.total_amount = amount
            order.save()

            address = request.data.get('address', '')
            pickup = request.data.get('pickup', False)
            tracking_number = generate_tracking_number()

            # create shipping (Shipping is the source of truth for order state)
            # shipping = Shipping.objects.create(
            #     address=address,
            #     pickup=pickup,
            #     status='pending',
            #     tracking_number=tracking_number,
            #     order=order
            # )
            
            # Clear cart
            cart.items.all().delete()
            
            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
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
       

