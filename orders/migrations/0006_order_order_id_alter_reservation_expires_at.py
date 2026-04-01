import random
import string
import orders.models
from django.utils import timezone
from django.db import migrations, models

def backfill_order_ids(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    date_str = timezone.now().strftime("%Y%m%d")
    
    for order in Order.objects.filter(order_id__isnull=True):
        while True:
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            new_id = f"GH-{date_str}-{random_str}"
            if not Order.objects.filter(order_id=new_id).exists():
                order.order_id = new_id
                order.save(update_fields=['order_id'])
                break


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0005_alter_reservation_expires_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='order_id',
            field=models.CharField(blank=True, editable=False, max_length=30, null=True, unique=True),
        ),
        migrations.RunPython(backfill_order_ids, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='reservation',
            name='expires_at',
            field=models.DateTimeField(default=orders.models.get_default_expiry),
        ),
    ]
