from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import CartItem, Cart
from .serializer import CartItemSerializer, CartSerializer
from orders.serailizer import OrderSerializer
from rest_framework import status
from django.shortcuts import get_object_or_404
# Create your views here.

class CartView(APIView):

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


class CartItemView(APIView):

    def get(self, request, pk):
        try:
            cart_item = get_object_or_404(CartItem, cart__user=request.user, pk=pk)
            serializer = CartItemSerializer(cart_item)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def delete(self, request, pk):
        try:
            item = get_object_or_404(CartItem, pk=pk)
            item.delete()
            return Response({"info": "item deleted"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    
    # def post(self, request):
    #     serializer = CartItemSerializer(data=request.data)
    #     if serializer.is_valid():
    #         cart, created = Cart.objects.get_or_create(user=request.user)
    #         item = serializer.save(cart=cart)
    #         return Response(
    #             CartItemSerializer(item).data,
    #             status=status.HTTP_201_CREATED
    #         )
    #     else:
    #         return Response(
    #             serializer.errors,
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    # def put(self, request, pk):
    #     try:
    #         item = get_object_or_404(CartItem, cart__user=request.user, pk=pk)
    #         serializer = CartItemSerializer(item, data=request.data)
    #         if serializer.is_valid():
    #             serializer.save()
    #             return Response(serializer.data, status=status.HTTP_200_OK)
    #         else:
    #             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    #     except Exception as e:
    #         return Response(
    #             {'error': str(e)},
    #             status=status.HTTP_500_INTERNAL_SERVER_ERROR
    #         )

from orders.models import Order, OrderItem

class CheckoutView(APIView):

    def post(self, request):
        try:
            cart = Cart.objects.get(user=request.user)
            items = cart.items.all()
            
            if not items.exists():
                return Response(
                    {"detail": "Cart is empty. Please add items before checkout."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # create order for user doing checkout
            order = Order.objects.create(user=request.user)
            for item in items:
                order_item = OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                )
            # clear the cart
            cart.items.all().delete()
            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Cart.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
from products.models import Product

class AddToCartView(APIView):

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
       

