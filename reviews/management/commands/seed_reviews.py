import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from products.models import Product
from reviews.models import Reviews


User = get_user_model()


LOREM_SNIPPETS = [
    "Great product, exactly as described.",
    "Decent quality for the price.",
    "Exceeded my expectations, will buy again.",
    "Not quite what I expected, but it works.",
    "Fantastic build quality and fast delivery.",
    "Average experience, nothing special.",
    "I am very satisfied with this purchase.",
    "The product arrived late but works fine.",
    "Highly recommended for everyday use.",
    "Would not recommend; quality could be better.",
]


class Command(BaseCommand):
    help = "Seed the database with dummy product reviews."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Total number of reviews to create (default: 100).",
        )
        parser.add_argument(
            "--per-product-max",
            type=int,
            default=10,
            help="Maximum reviews per product (soft cap, default: 10).",
        )
        parser.add_argument(
            "--ensure-min-per-product",
            type=int,
            default=0,
            help=(
                "Ensure at least this many reviews exist for every product "
                "(0 disables this behavior, default: 0)."
            ),
        )

    def handle(self, *args, **options):
        total_count = options["count"]
        per_product_max = options["per_product_max"]
        ensure_min_per_product = options["ensure_min_per_product"]

        products = list(Product.objects.all())
        users = list(User.objects.all())

        if not products:
            self.stdout.write(self.style.ERROR("No products found. Aborting."))
            return

        if not users:
            self.stdout.write(self.style.ERROR("No users found. Aborting."))
            return

        created = 0

        @transaction.atomic
        def ensure_minimum_reviews_per_product():
            nonlocal created
            if ensure_min_per_product <= 0:
                return

            self.stdout.write(
                f"Ensuring at least {ensure_min_per_product} review(s) per product..."
            )
            for product in products:
                existing_count = Reviews.objects.filter(product=product).count()
                needed = max(0, ensure_min_per_product - existing_count)
                for _ in range(needed):
                    user = random.choice(users)
                    review = Reviews.objects.create(
                        user=user,
                        product=product,
                        rating=random.randint(1, 5),
                        content=random.choice(LOREM_SNIPPETS),
                    )
                    created += 1
                    self.stdout.write(
                        f"  Created review {review.id} for product {product.item_no} by {user}"
                    )

        @transaction.atomic
        def create_additional_batch():
            nonlocal created
            if total_count <= 0:
                return

            self.stdout.write(
                f"Creating up to {total_count} additional dummy reviews "
                f"({len(products)} products, {len(users)} users)..."
            )

            for _ in range(total_count):
                product = random.choice(products)
                user = random.choice(users)

                # Optional cap per product
                if (
                    per_product_max is not None
                    and Reviews.objects.filter(product=product).count() >= per_product_max
                ):
                    continue

                review = Reviews.objects.create(
                    user=user,
                    product=product,
                    rating=random.randint(1, 5),
                    content=random.choice(LOREM_SNIPPETS),
                )
                created += 1
                self.stdout.write(
                    f"  Created review {review.id} for product {product.item_no} by {user}"
                )

        ensure_minimum_reviews_per_product()
        create_additional_batch()

        self.stdout.write(self.style.SUCCESS(f"Dummy reviews created: {created}"))

