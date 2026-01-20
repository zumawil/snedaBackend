import csv
from decimal import Decimal
from django.core.management.base import BaseCommand
from products.models import Product, ProductGroup, HSCode, Brand, ProductDescription

class Command(BaseCommand):
    help = "Populate products from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help="Path to the CSV file")

    def handle(self, *args, **options):
        csv_file = options['csv_file']

        with open(csv_file, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            count = 0

            for row in reader:
                # --- Get or create related objects ---
                product_group, _ = ProductGroup.objects.get_or_create(name=row.get('ProductGroup', 'Unknown'))
                hs_code, _ = HSCode.objects.get_or_create(code=row.get('HSCode', '0000 0000'))
                brand, _ = Brand.objects.get_or_create(name=row.get('Group', 'Unknown'))
                description, _ = ProductDescription.objects.get_or_create(description=row.get('Description', 'No Description'))

                # --- Parse numeric fields safely ---
                def parse_decimal(value, default=Decimal('0.00')):
                    try:
                        return Decimal(str(value).replace(',', '.'))
                    except:
                        return default

                height = parse_decimal(row.get('Height'))
                width = parse_decimal(row.get('Width'))
                length = parse_decimal(row.get('Length'))
                weight = parse_decimal(row.get('Weight'))
                gross_price = parse_decimal(row.get('Grossprice'))

                def parse_int(value, default=0):
                    try:
                        return int(value)
                    except:
                        return default

                box_qty = parse_int(row.get('BoxQTY'))
                inventory_qty = parse_int(row.get('InventoryQTY'))
                in_stock = inventory_qty  # you can also set logic here if needed

                # --- Create the product if it doesn't exist ---
                product, created = Product.objects.get_or_create(
                    item_no=row['ItemNo'],
                    defaults={
                        'product_group': product_group,
                        'description': description,
                        'hs_code': hs_code,
                        'gtin': row.get('GTIN') or None,
                        'height': height,
                        'width': width,
                        'length': length,
                        'weight': weight,
                        'box_qty': box_qty,
                        'inventory_qty': inventory_qty,
                        'gross_price': gross_price,
                        'brand': brand,
                        'in_stock': in_stock,
                    }
                )

                if created:
                    count += 1

            self.stdout.write(self.style.SUCCESS(f"{count} products added successfully!"))
