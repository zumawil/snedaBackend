import csv
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product, ProductGroup, HSCode, Brand, Category

class Command(BaseCommand):
    help = "Populate products from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help="Path to the CSV file")

    def handle(self, *args, **options):
        csv_file = options['csv_file']

        with open(csv_file, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            
            # Strip whitespace from headers
            reader.fieldnames = [field.strip() if field else field for field in reader.fieldnames]
            
            count = 0
            skipped = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
                try:
                    # Strip whitespace from all values
                    row = {k.strip() if k else k: v.strip() if isinstance(v, str) else v 
                           for k, v in row.items()}
                    
                    # Check if ItemNo exists (required field)
                    item_no = row.get('ItemNo') or row.get('Item No') or row.get('item_no')
                    if not item_no:
                        skipped += 1
                        errors.append(f"Row {row_num}: Missing ItemNo")
                        continue

                    with transaction.atomic():
                        # --- Get or create related objects ---
                        
                        # ProductGroup (from 'ProductGroup' column)
                        product_group_name = row.get('ProductGroup') or row.get('Product Group') or 'Unknown'
                        product_group, _ = ProductGroup.objects.get_or_create(
                            name=product_group_name.strip()
                        )
                        
                        # HSCode (from 'HSCode' column)
                        hs_code_value = row.get('HSCode') or row.get('HS Code') or '0000 0000'
                        hs_code, _ = HSCode.objects.get_or_create(
                            code=hs_code_value.strip()
                        )
                        
                        # Brand (from 'Group' column)
                        brand_name = row.get('Group') or row.get('Brand') or 'Unknown'
                        brand, _ = Brand.objects.get_or_create(
                            name=brand_name.strip()
                        )
                        
                        # Category (from 'Description' column)
                        category_name = row.get('Description') or 'No Category'
                        category, _ = Category.objects.get_or_create(
                            name=category_name.strip()
                        )

                        # --- Parse numeric fields safely ---
                        def parse_decimal(value, default=Decimal('0.00')):
                            if not value or value == '':
                                return default
                            try:
                                # Replace comma with dot for European decimal format
                                clean_value = str(value).replace(',', '.').strip()
                                return Decimal(clean_value)
                            except (InvalidOperation, ValueError):
                                return default

                        def parse_int(value, default=0):
                            if not value or value == '':
                                return default
                            try:
                                # Remove any spaces and convert
                                clean_value = str(value).replace(' ', '').strip()
                                return int(float(clean_value))
                            except (ValueError, TypeError):
                                return default

                        # Parse dimensions and weight
                        height = parse_decimal(row.get('Height'))
                        width = parse_decimal(row.get('Width'))
                        length = parse_decimal(row.get('Length'))
                        weight = parse_decimal(row.get('Weight'))
                        
                        # Parse quantities and price
                        box_qty = parse_int(row.get('BoxQTY') or row.get('Box QTY'))
                        inventory_qty = parse_int(row.get('InventoryQTY') or row.get('Inventory QTY'))
                        gross_price = parse_decimal(row.get('Grossprice') or row.get('Gross Price'))
                        
                        # Set in_stock based on inventory_qty
                        in_stock = inventory_qty > 0

                        # Get GTIN (optional field)
                        gtin = row.get('GTIN') or row.get('gtin') or None
                        if gtin:
                            gtin = gtin.strip()
                            if gtin == '':
                                gtin = None

                        # --- Create or update the product ---
                        product, created = Product.objects.update_or_create(
                            item_no=item_no.strip(),
                            defaults={
                                'product_group': product_group,
                                'category': category,
                                'hs_code': hs_code,
                                'brand': brand,
                                'gtin': gtin,
                                'height': height,
                                'width': width,
                                'length': length,
                                'weight': weight,
                                'box_qty': box_qty,
                                'inventory_qty': inventory_qty,
                                'gross_price': gross_price,
                                'in_stock': in_stock,
                            }
                        )

                        if created:
                            count += 1
                            self.stdout.write(f"Created: {item_no}")
                        else:
                            self.stdout.write(f"Updated: {item_no}")

                except Exception as e:
                    skipped += 1
                    errors.append(f"Row {row_num} ({item_no if 'item_no' in locals() else 'unknown'}): {str(e)}")
                    continue

            # Print summary
            self.stdout.write(self.style.SUCCESS(f"\n{'='*50}"))
            self.stdout.write(self.style.SUCCESS(f"Import completed!"))
            self.stdout.write(self.style.SUCCESS(f"{'='*50}"))
            self.stdout.write(self.style.SUCCESS(f"Products created: {count}"))
            self.stdout.write(self.style.WARNING(f"Rows skipped: {skipped}"))
            
            if errors:
                self.stdout.write(self.style.ERROR(f"\nErrors encountered:"))
                for error in errors[:10]:  # Show first 10 errors
                    self.stdout.write(self.style.ERROR(f"  - {error}"))
                if len(errors) > 10:
                    self.stdout.write(self.style.ERROR(f"  ... and {len(errors) - 10} more errors"))