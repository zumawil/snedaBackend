from django.contrib import admin
from .models import Order, OrderItem, Reservation

class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'status', 'total_amount', 'marked_for_review', 'created_at')
    list_filter = ('marked_for_review', 'status', 'created_at')
    search_fields = ('order_id', 'user__email')

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(Reservation)
