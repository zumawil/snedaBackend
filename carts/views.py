
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

load_dotenv()

logger = logging.getLogger(__name__)

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

        
        result = CheckoutService.process_checkout(user, idempotency_key, address, pickup)

       
        return api_response(
            success=result.get('success', False),
            data=result.get('data'),
            message=result.get('message'),
            error=result.get('error'),
            status_code=result.get('status_code', status.HTTP_200_OK)
        )

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