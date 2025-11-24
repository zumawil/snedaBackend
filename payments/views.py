from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Payment
from .serializers import PaymentSerializer
from orders.models import Order
from users.permissions import IsVerifiedUser

# Create your views here.

class PaymentView(APIView):
    """
    Handle payments.

    GET /payments/: List all payments for the authenticated user.
    GET /payments/<pk>/: Retrieve details of a specific payment.
    POST /payments/: Initiate a new payment for an order.
    """

    permission_classes = [IsVerifiedUser]

    def get(self, request, pk=None):
        try:
            if pk:
                # Get specific payment
                payment = get_object_or_404(Payment, pk=pk, order__user=request.user)
                serializer = PaymentSerializer(payment)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                # List all payments for user
                payments = Payment.objects.filter(order__user=request.user)
                serializer = PaymentSerializer(payments, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """
        Initiate a payment for an order.
        Expects: order_id, amount, method
        """
        try:
            order_id = request.data.get('order_id')
            amount = request.data.get('amount')
            method = request.data.get('method')

            if not all([order_id, amount, method]):
                return Response({'error': 'order_id, amount, and method are required'}, status=status.HTTP_400_BAD_REQUEST)

            order = get_object_or_404(Order, pk=order_id, user=request.user)

            # Check if payment already exists for this order
            if Payment.objects.filter(order=order).exists():
                return Response({'error': 'Payment already initiated for this order'}, status=status.HTTP_400_BAD_REQUEST)

            payment = Payment.objects.create(
                order=order,
                amount=amount,
                method=method
            )

            serializer = PaymentSerializer(payment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
