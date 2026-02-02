from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

from users.models import CustomUser
from products.models import Product
from orders.models import Order
from payments.models import Payment
from users.permissions import IsAdminUser
from utils.apiResponse import api_response

from orders.serializers import OrderDetailSerializer
from products.serializers import ProductSerializer
from users.serializers import UserSerializer
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.pagination import PageNumberPagination

# class StandardResultsSetPagination(PageNumberPagination):
#     page_size = 10
#     page_size_query_param = 'page_size'
#     max_page_size = 1000

class DashboardStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            # Stats calculations
            today = timezone.now().date()
            # get revenue for today
            total_revenue = Payment.objects.filter(status='success', date_created=today).aggregate(Sum('amount'))['amount__sum'] or 0
            total_orders = Order.objects.filter(created_at=today).count()
            total_pending_orders = Order.objects.filter(shipping__status='pending').count()
            total_products = Product.objects.count()
            total_users = CustomUser.objects.count()

            # Growth (this month vs last month) - simple version
            now = timezone.now()
            this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_end = this_month_start - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            this_month_revenue = Payment.objects.filter(
                status='success', 
                date_created__gte=this_month_start
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            
            last_month_revenue = Payment.objects.filter(
                status='success', 
                date_created__gte=last_month_start,
                date_created__lt=this_month_start
            ).aggregate(Sum('amount'))['amount__sum'] or 0

            revenue_growth = 0
            if last_month_revenue > 0:
                revenue_growth = ((this_month_revenue - last_month_revenue) / last_month_revenue) * 100

            # Recent Orders
            recent_orders = Order.objects.order_by('-created_at')[:5]
            recent_orders_serializer = OrderDetailSerializer(recent_orders, many=True)

            data = {
                "stats": {
                    "total_revenue_for_today": float(total_revenue),
                    "total_orders": total_orders,
                    "total_products": total_products,
                    'total_pending_orders': total_pending_orders,
                    "total_users": total_users,
                    "revenue_growth": round(revenue_growth, 2),
                    "this_month_revenue": float(this_month_revenue)
                },
                "recent_orders": recent_orders_serializer.data
            }

            return api_response(
                success=True,
                data=data,
                message="Dashboard statistics retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                data=None,
                error=str(e),
                message="Error retrieving dashboard statistics",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AdminOrderListView(APIView):
    permission_classes = []
    pagination_class = PageNumberPagination

    def get(self, request):
        try:
            orders = Order.objects.all().order_by('-created_at')
            paginator = self.pagination_class()
            result_page = paginator.paginate_queryset(orders, request)
            serializer = OrderDetailSerializer(result_page, many=True)
            data = paginator.get_paginated_response(serializer.data).data

            return api_response(
                success=True,
                data=data,
                message="All orders retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error retrieving orders",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AdminProductListView(APIView):
    permission_classes = [IsAdminUser]
    pagination_class = PageNumberPagination

    def get(self, request):
        try:
            products = Product.objects.all().order_by('-item_no')
            paginator = self.pagination_class()
            result_page = paginator.paginate_queryset(products, request)
            serializer = ProductSerializer(result_page, many=True)
            data = paginator.get_paginated_response(serializer.data).data

            return api_response(
                success=True,
                data=data,
                message="All products retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error retrieving products",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AdminUserListView(APIView):
    permission_classes = [IsAdminUser]
    pagination_class = PageNumberPagination

    def get(self, request):
        try:
            users = CustomUser.objects.all().order_by('-date_joined')
            paginator = self.pagination_class()
            result_page = paginator.paginate_queryset(users, request)
            serializer = UserSerializer(result_page, many=True)
            data = paginator.get_paginated_response(serializer.data).data
            return api_response(
                success=True,
                data=data,
                message="All users retrieved successfully",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error retrieving users",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ToggleUserStatusView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            user = get_object_or_404(CustomUser, pk=pk)
            if user.is_superuser:
                return api_response(
                    success=False,
                    message="Cannot toggle status of a superuser",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            user.is_active = not user.is_active
            user.save()
            
            return api_response(
                success=True,
                data={"is_active": user.is_active},
                message=f"User status updated to {'active' if user.is_active else 'inactive'}",
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                error=str(e),
                message="Error updating user status",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

