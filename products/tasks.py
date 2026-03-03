from django_q.tasks import async_task
from products.models import Product
from orders.models import Order

def update_inventory(order_id):
    order = Order.objects.get(id=order_id)
    for item in order.items.all():  # Assuming related_name='items' on OrderItem
        product = item.product
        product.stock -= item.quantity
        product.save()