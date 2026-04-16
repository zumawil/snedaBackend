from django.db import migrations

def backfill_statuses(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    # Map legacy statuses to 'paid'
    # These strings were removed from the OrderStatus enum but may exist in the DB
    legacy_statuses = ['shipped', 'delivered', 'fulfilled']
    
    # We use update() for efficiency and atomicity
    # This finds all orders with legacy statuses and sets them to 'paid'
    Order.objects.filter(status__in=legacy_statuses).update(status='paid')

class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0010_remove_order_pickup_location_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_statuses, reverse_code=migrations.RunPython.noop),
    ]
