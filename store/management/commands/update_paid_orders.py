from django.core.management.base import BaseCommand
import stripe
from django.conf import settings
from store.models import Order

stripe.api_key = settings.STRIPE_SECRET_KEY


class Command(BaseCommand):
    help = 'Update pending orders to paid status by checking Stripe sessions'

    def handle(self, *args, **options):
        pending_orders = Order.objects.filter(status='pending')
        
        if not pending_orders.exists():
            self.stdout.write(self.style.SUCCESS('No pending orders found.'))
            return
        
        self.stdout.write(f'Found {pending_orders.count()} pending order(s). Checking Stripe...')
        
        updated_count = 0
        for order in pending_orders:
            if not order.stripe_session_id:
                self.stdout.write(self.style.WARNING(f'Order {order.id} has no session_id, skipping.'))
                continue
            
            try:
                session = stripe.checkout.Session.retrieve(order.stripe_session_id)
                
                if session.payment_status == 'paid':
                    order.status = 'paid'
                    order.stripe_payment_intent_id = session.payment_intent
                    order.save()
                    self.stdout.write(self.style.SUCCESS(f'Updated order {order.id} to paid'))
                    updated_count += 1
                else:
                    self.stdout.write(f'  Order {order.id} payment status: {session.payment_status}')
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error checking order {order.id}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'\nUpdated {updated_count} order(s) to paid status.'))

