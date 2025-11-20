from django.core.management.base import BaseCommand
from store.models import Product


class Command(BaseCommand):
    help = 'Seeds the database with 3 fixed products'

    def handle(self, *args, **options):
        products_data = [
            {
                'name': 'Wireless Headphones',
                'description': 'Premium wireless headphones with noise cancellation and 30-hour battery life. Perfect for music lovers and professionals.',
                'price': 16599.00,  # ~$199.99 in INR (approx 83 INR per USD)
                'image_url': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500',
            },
            {
                'name': 'Smart Watch',
                'description': 'Feature-rich smartwatch with fitness tracking, heart rate monitor, and smartphone notifications. Water-resistant design.',
                'price': 24899.00,  # ~$299.99 in INR
                'image_url': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500',
            },
            {
                'name': 'Mouse',
                'description': 'Ergonomic wireless mouse with precision tracking and comfortable design. Perfect for productivity and gaming.',
                'price': 4149.00,  # ~$49.99 in INR
                'image_url': 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=500',
            },
        ]

        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults=product_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created product: {product.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Product already exists: {product.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('Successfully seeded products!')
        )

