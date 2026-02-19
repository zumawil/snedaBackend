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

        def parse_decimal(value, default=Decimal('0.00')):
            if not value or str(value).strip() == '':
                return default
            try:
                clean_value = str(value).replace(',', '.').strip()
                return Decimal(clean_value)
            except (InvalidOperation, ValueError):
                return default

        def parse_int(value, default=None):
            """Returns None for non-numeric values like UNKNOWN, BOX0004, PCS, etc."""
            if not value or str(value).strip() == '':
                return default
            try:
                clean_value = str(value).replace(' ', '').strip()
                # Reject obviously non-numeric strings
                return int(float(clean_value))
            except (ValueError, TypeError):
                return default  # Return None for UNKNOWN, BOX0004, PCS, etc.

        with open(csv_file, newline='', encoding='utf-8-sig') as f:
            # Auto-detect delimiter
            sample = f.read(2048)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = ','  # fallback

            self.stdout.write(f"Detected delimiter: '{delimiter}'")

            reader = csv.DictReader(f, delimiter=delimiter)

            # Strip whitespace from headers
            reader.fieldnames = [
                field.strip() if field else field for field in reader.fieldnames
            ]

            self.stdout.write(f"Headers found: {reader.fieldnames}")

            count = 0
            updated = 0
            skipped = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Strip whitespace from all values
                    row = {
                        k.strip() if k else k: v.strip() if isinstance(v, str) else v
                        for k, v in row.items()
                    }

                    # Check if ItemNo exists (required field)
                    item_no = row.get('ItemNo') or row.get('Item No') or row.get('item_no')
                    if not item_no or item_no.strip() == '':
                        skipped += 1
                        errors.append(f"Row {row_num}: Missing ItemNo — row data: {dict(list(row.items())[:3])}")
                        continue

                    item_no = item_no.strip()

                    with transaction.atomic():
                        # ProductGroup
                        product_group_name = row.get('ProductGroup') or row.get('Product Group') or 'Unknown'
                        product_group, _ = ProductGroup.objects.get_or_create(
                            name=product_group_name.strip()
                        )

                        # HSCode
                        hs_code_value = row.get('HSCode') or row.get('HS Code') or '0000 0000'
                        hs_code, _ = HSCode.objects.get_or_create(
                            code=hs_code_value.strip()
                        )

                        # Brand (from 'Group' column in DATA1)
                        brand_name = row.get('Group') or row.get('Brand') or 'Unknown'
                        brand, _ = Brand.objects.get_or_create(
                            name=brand_name.strip()
                        )

                        # Category (from 'Description' column)
                        category_name = row.get('Description') or 'No Category'
                        category, _ = Category.objects.get_or_create(
                            name=category_name.strip()
                        )

                        # Parse dimensions and weight
                        height = parse_decimal(row.get('Height'))
                        width = parse_decimal(row.get('Width'))
                        length = parse_decimal(row.get('Length'))
                        weight = parse_decimal(row.get('Weight'))

                        # Parse quantities — BoxQTY can be UNKNOWN/BOX0004/PCS so returns None
                        box_qty = parse_int(row.get('BoxQTY') or row.get('Box QTY'))
                        inventory_qty = parse_int(row.get('InventoryQTY') or row.get('Inventory QTY'), default=0)
                        gross_price = parse_decimal(row.get('Grossprice') or row.get('Gross Price'))

                        # in_stock based on inventory_qty
                        in_stock = 1 if inventory_qty and inventory_qty > 0 else 0

                        # GTIN
                        gtin = row.get('GTIN') or row.get('gtin') or None
                        if gtin:
                            gtin = gtin.strip() or None

                        # Availability from DATA2 (optional — only present if merging)
                        availability = parse_int(
                            row.get('Availability') or row.get('availability'),
                            default=0
                        )
                        if availability:
                            in_stock = availability

                        product, created = Product.objects.update_or_create(
                            item_no=item_no,
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
                                'inventory_qty': inventory_qty or 0,
                                'gross_price': gross_price,
                                'in_stock': in_stock,
                            }
                        )

                        if created:
                            count += 1
                            self.stdout.write(f"  Created: {item_no}")
                        else:
                            updated += 1
                            self.stdout.write(f"  Updated: {item_no}")

                except Exception as e:
                    skipped += 1
                    errors.append(f"Row {row_num} ({item_no if 'item_no' in locals() else 'unknown'}): {str(e)}")
                    continue

            # Summary
            self.stdout.write(self.style.SUCCESS(f"\n{'='*50}"))
            self.stdout.write(self.style.SUCCESS(f"Import completed!"))
            self.stdout.write(self.style.SUCCESS(f"{'='*50}"))
            self.stdout.write(self.style.SUCCESS(f"Products created: {count}"))
            self.stdout.write(self.style.SUCCESS(f"Products updated: {updated}"))
            self.stdout.write(self.style.WARNING(f"Rows skipped:     {skipped}"))

            if errors:
                self.stdout.write(self.style.ERROR(f"\nErrors encountered:"))
                for error in errors[:10]:
                    self.stdout.write(self.style.ERROR(f"  - {error}"))
                if len(errors) > 10:
                    self.stdout.write(self.style.ERROR(f"  ... and {len(errors) - 10} more errors"))