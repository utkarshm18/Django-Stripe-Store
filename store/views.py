import stripe
from stripe._error import InvalidRequestError, StripeError, SignatureVerificationError
import uuid
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import json

from .models import Product, Order, OrderItem

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


def home(request):
    """Main page showing products and orders."""
    products = Product.objects.all()
    
    # Check for success message first
    payment_success = request.GET.get('payment') == 'success'
    order_id = request.GET.get('order_id')
    
    # Filter orders by user if authenticated
    if request.user.is_authenticated:
        orders_query = Order.objects.filter(user=request.user, status='paid')
    else:
        # For anonymous users, show orders from session (optional - can be empty)
        orders_query = Order.objects.none()
    
    # If we have a success order_id, make sure it's marked as paid (backup mechanism)
    if order_id:
        try:
            order = Order.objects.get(id=order_id)
            if order.status != 'paid':
                # Try to verify with Stripe and update
                if order.stripe_session_id:
                    try:
                        session = stripe.checkout.Session.retrieve(order.stripe_session_id)
                        if session.payment_status == 'paid':
                            order.status = 'paid'
                            order.stripe_payment_intent_id = session.payment_intent
                            order.save()
                            print(f"DEBUG: Updated order {order_id} to paid on home page load")
                    except Exception as e:
                        print(f"DEBUG: Could not verify order {order_id} with Stripe: {e}")
        except Order.DoesNotExist:
            pass
    
    # Backup: Check and update any pending orders that have been paid
    # This ensures orders appear even if success view didn't run
    if request.user.is_authenticated:
        pending_orders = Order.objects.filter(user=request.user, status='pending', stripe_session_id__isnull=False)
    else:
        pending_orders = Order.objects.none()
    for pending_order in pending_orders[:5]:  # Check last 5 pending orders
        try:
            session = stripe.checkout.Session.retrieve(pending_order.stripe_session_id)
            if session.payment_status == 'paid':
                pending_order.status = 'paid'
                pending_order.stripe_payment_intent_id = session.payment_intent
                pending_order.save()
                print(f"DEBUG: Auto-updated pending order {pending_order.id} to paid on home page")
        except Exception as e:
            # Skip if can't retrieve session
            pass
    
    # Get paid orders, ordered by most recent first
    orders = orders_query.select_related().prefetch_related('items__product').order_by('-created_at')[:10]
    
    # Get the order details for success message
    success_order = None
    if payment_success and order_id:
        try:
            success_order = Order.objects.prefetch_related('items__product').get(
                id=order_id, 
                status='paid'
            )
            print(f"DEBUG: Success order found: {success_order.id} with {success_order.items.count()} items")
        except Order.DoesNotExist:
            print(f"DEBUG: Order {order_id} not found or not paid")
            # Try to find it anyway (might have just been updated)
            try:
                success_order = Order.objects.prefetch_related('items__product').get(id=order_id)
                if success_order.status != 'paid':
                    success_order.status = 'paid'
                    success_order.save()
                    print(f"DEBUG: Updated order {order_id} to paid")
            except Order.DoesNotExist:
                pass
    
    context = {
        'products': products,
        'orders': orders,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'payment_success': payment_success,
        'order_id': order_id,
        'success_order': success_order,
    }
    return render(request, 'store/home.html', context)


@require_http_methods(["POST"])
def create_checkout_session(request):
    """Create a Stripe Checkout session for the order."""
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
        request_idempotency_key = data.get('idempotency_key')  # From frontend
        
        if not items:
            return JsonResponse({'error': 'No items provided'}, status=400)
        
        # Validate items and calculate total
        line_items = []
        total_amount = Decimal('0.00')
        order_items_data = []
        
        for item in items:
            product_id = item.get('product_id')
            quantity = int(item.get('quantity', 0))
            
            if quantity <= 0:
                continue
            
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return JsonResponse({'error': f'Product {product_id} not found'}, status=400)
            
            item_total = product.price * quantity
            total_amount += item_total
            
            # Add to Stripe line items
            line_items.append({
                'price_data': {
                    'currency': 'inr',
                    'product_data': {
                        'name': product.name,
                        'description': product.description[:500],  # Stripe limit
                    },
                    'unit_amount': int(product.price * 100),  # Convert to paise (INR smallest unit)
                },
                'quantity': quantity,
            })
            
            order_items_data.append({
                'product': product,
                'quantity': quantity,
                'price': product.price,
            })
        
        if not line_items:
            return JsonResponse({'error': 'No valid items'}, status=400)
        
        # Generate or use provided idempotency key to prevent double charges
        if request_idempotency_key:
            idempotency_key = request_idempotency_key
        else:
            idempotency_key = str(uuid.uuid4())
        
        # Check if an order with this idempotency key already exists
        existing_order = Order.objects.filter(idempotency_key=idempotency_key).first()
        if existing_order:
            # Return existing session if it's still pending
            if existing_order.status == 'pending' and existing_order.stripe_session_id:
                return JsonResponse({
                    'sessionId': existing_order.stripe_session_id,
                    'order_id': existing_order.id,
                    'existing': True,
                })
            # If order is already paid, return error to prevent duplicate
            elif existing_order.status == 'paid':
                return JsonResponse({
                    'error': 'This order has already been completed',
                    'order_id': existing_order.id,
                }, status=400)
        
        # Additional protection: Check for recent duplicate requests from same session
        # (within last 5 seconds with same items)
        from datetime import timedelta
        recent_cutoff = timezone.now() - timedelta(seconds=5)
        recent_orders = Order.objects.filter(
            created_at__gte=recent_cutoff,
            total_amount=total_amount,
            status='pending'
        )
        
        # Check if any recent order has the same items
        for recent_order in recent_orders:
            recent_items = set((item.product.id, item.quantity) for item in recent_order.items.all())
            current_items = set((item['product'].id, item['quantity']) for item in order_items_data)
            if recent_items == current_items:
                # Duplicate request detected
                if recent_order.stripe_session_id:
                    return JsonResponse({
                        'sessionId': recent_order.stripe_session_id,
                        'order_id': recent_order.id,
                        'existing': True,
                    })
        
        # Create order in database first (pending status)
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                status='pending',
                total_amount=total_amount,
                idempotency_key=idempotency_key,
            )
            
            for item_data in order_items_data:
                OrderItem.objects.create(
                    order=order,
                    product=item_data['product'],
                    quantity=item_data['quantity'],
                    price=item_data['price'],
                )
            
            # Create Stripe Checkout Session with idempotency
            try:
                # Use idempotency key for Stripe API call to prevent duplicate charges
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=line_items,
                    mode='payment',
                    success_url=request.build_absolute_uri('/success?session_id={CHECKOUT_SESSION_ID}'),
                    cancel_url=request.build_absolute_uri('/cancel'),
                    metadata={
                        'order_id': str(order.id),
                        'idempotency_key': idempotency_key,
                    },
                    # Stripe idempotency (if supported in your Stripe version)
                    # idempotency_key=idempotency_key,  # Uncomment if your Stripe version supports this
                )
                
                # Update order with session ID
                order.stripe_session_id = checkout_session.id
                order.save()
                
                return JsonResponse({
                    'sessionId': checkout_session.id,
                    'order_id': order.id,
                })
                
            except StripeError as e:
                # If Stripe fails, mark order as failed
                order.status = 'failed'
                order.save()
                return JsonResponse({'error': str(e)}, status=400)
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def success(request):
    """Handle successful payment redirect from Stripe."""
    session_id = request.GET.get('session_id')
    
    if not session_id:
        print("DEBUG: No session_id in request")
        return redirect('home')
    
    # Check if session_id is the placeholder (shouldn't happen, but handle it)
    if session_id == '{CHECKOUT_SESSION_ID}' or '{CHECKOUT_SESSION_ID}' in session_id:
        print("Warning: Received placeholder session_id, redirecting to home")
        return redirect('home')
    
    print(f"DEBUG: Processing success for session_id: {session_id}")
    
    try:
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        print(f"DEBUG: Session retrieved - payment_status: {session.payment_status}, metadata: {session.metadata}")
        
        # Always try to update order if payment is paid, regardless of current status
        if session.payment_status == 'paid':
            # Find the order and lock it to prevent race conditions
            with transaction.atomic():
                # Try to find order by session_id first (check both pending and any status)
                order = Order.objects.select_for_update().filter(
                    stripe_session_id=session_id
                ).first()
                
                # If not found, try to find by order_id from metadata
                if not order and session.metadata:
                    order_id = session.metadata.get('order_id')
                    print(f"DEBUG: Trying to find order by metadata order_id: {order_id}")
                    if order_id:
                        order = Order.objects.select_for_update().filter(
                            id=order_id
                        ).first()
                
                if order:
                    print(f"DEBUG: Found order {order.id}, current status: {order.status}")
                    # Only update if not already paid (prevent duplicate updates on refresh)
                    if order.status != 'paid':
                        order.status = 'paid'
                        order.stripe_payment_intent_id = session.payment_intent
                        order.save()
                        print(f"DEBUG: Updated order {order.id} to paid status")
                    else:
                        print(f"DEBUG: Order {order.id} already paid, skipping update")
                    # Redirect with success message
                    from django.urls import reverse
                    redirect_url = reverse('home') + f'?payment=success&order_id={order.id}'
                    print(f"DEBUG: Redirecting to: {redirect_url}")
                    return redirect(redirect_url)
                else:
                    print(f"DEBUG: No order found for session_id: {session_id}")
                    # Try to find any order with this session_id regardless of status
                    fallback_order = Order.objects.filter(stripe_session_id=session_id).first()
                    if fallback_order:
                        print(f"DEBUG: Found fallback order {fallback_order.id} with status {fallback_order.status}")
                        fallback_order.status = 'paid'
                        fallback_order.stripe_payment_intent_id = session.payment_intent
                        fallback_order.save()
                        from django.urls import reverse
                        redirect_url = reverse('home') + f'?payment=success&order_id={fallback_order.id}'
                        print(f"DEBUG: Redirecting to: {redirect_url}")
                        return redirect(redirect_url)
                    else:
                        # Last resort: try to find by metadata order_id without status check
                        if session.metadata:
                            order_id = session.metadata.get('order_id')
                            if order_id:
                                print(f"DEBUG: Last resort - trying to find order {order_id} by ID only")
                                last_resort_order = Order.objects.filter(id=order_id).first()
                                if last_resort_order:
                                    print(f"DEBUG: Found last resort order {last_resort_order.id}")
                                    last_resort_order.status = 'paid'
                                    last_resort_order.stripe_payment_intent_id = session.payment_intent
                                    if not last_resort_order.stripe_session_id:
                                        last_resort_order.stripe_session_id = session_id
                                    last_resort_order.save()
                                    from django.urls import reverse
                                    redirect_url = reverse('home') + f'?payment=success&order_id={last_resort_order.id}'
                                    return redirect(redirect_url)
        
        # If payment not confirmed, redirect anyway (webhook will handle it)
        print(f"DEBUG: Payment status is {session.payment_status}, redirecting to home")
        return redirect('home')
    
    except InvalidRequestError as e:
        # Invalid session ID (e.g., placeholder or doesn't exist)
        print(f"ERROR: Invalid Stripe session ID: {session_id}, error: {e}")
        return redirect('home')
    except StripeError as e:
        # Other Stripe errors
        print(f"ERROR: Stripe error in success view: {e}")
        return redirect('home')
    except Exception as e:
        # Catch any other unexpected errors
        print(f"ERROR: Unexpected error in success view: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return redirect('home')


def cancel(request):
    """Handle cancelled payment."""
    return redirect('home')


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhook events for additional security."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    if not settings.STRIPE_WEBHOOK_SECRET:
        # Webhook secret not configured, skip webhook verification
        return HttpResponse(status=200)
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except SignatureVerificationError:
        return HttpResponse(status=400)
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session.get('metadata', {}).get('order_id')
        
        if order_id:
            try:
                with transaction.atomic():
                    order = Order.objects.select_for_update().filter(
                        id=order_id,
                        status='pending'
                    ).first()
                    
                    if order:
                        order.status = 'paid'
                        order.stripe_payment_intent_id = session.get('payment_intent')
                        order.save()
            except Order.DoesNotExist:
                pass
    
    return HttpResponse(status=200)


def register(request):
    """User registration view."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'store/register.html', {'form': form})


def user_login(request):
    """User login view."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {username}!')
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'store/login.html')


def user_logout(request):
    """User logout view."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')

