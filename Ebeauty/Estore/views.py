from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Cart, CartItem, Order, User  # Import User from your app model (not django.contrib.auth.models)
from django.contrib.auth import get_user_model  # Import get_user_model instead of django.contrib.auth.models.User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import re
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.db.models.signals import post_save
from django.dispatch import receiver
from .forms import OrderForm
from django.shortcuts import get_object_or_404
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from io import BytesIO
from django.http import HttpResponse
from django.core.mail import EmailMessage
from django_daraja.mpesa.core import MpesaClient
from django.http import JsonResponse
from .forms import OrderForm
from django.contrib import messages

User = get_user_model()

# User Verification and Login
def login_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse('homepage'))
        else:
            return render(request, "login.html", {"message": "Invalid username or password!"})
    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]

        if password != confirmation:
            return render(request, "register.html", {"message": "Passwords must match."})

        if User.objects.filter(email=email).exists():
            return render(request, "register.html", {"message": "Email is already registered."})

        if not validate_password_strength(password):
            return render(request, "register.html", {
                "message": "Password must be at least 8 characters long, contain at least one letter, one number, and one special character."
            })

        try:
            user = User.objects.create_user(username, email, password)
        except IntegrityError:
            return render(request, "register.html", {"message": "Username is already taken."})

        return redirect(reverse("login"))
    return render(request, "register.html")


def validate_password_strength(password):
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True


# Home Page
def homepage(request):
    products = Product.objects.all()
    return render(request, 'homepage.html', {'products': products})


# Product Detail
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'product_detail.html', {'product': product})


@receiver(post_save, sender=get_user_model())
def create_cart_for_user(sender, instance, created, **kwargs):
    if created:
        Cart.objects.create(user=instance)

# Add to Cart
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)

    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    messages.success(
        request,
        f"{cart_item.quantity} x '{product.name}' added to your cart successfully!"
    )

    return redirect('homepage')



@login_required
def cart(request):
    # Get or create a cart for the user
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Retrieve cart items and total price
    cart_items = cart.cart_items.all()  # Use the related_name 'cart_items'
    total_price = cart.total_price()  # Calculate total price using the model method

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total_price': total_price
    })


# Remove from Cart
@login_required
def remove_from_cart(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
    cart_item.delete()
    return redirect('cart')


# Checkout
@login_required
def checkout(request):
    cart = Cart.objects.filter(user=request.user).first()
    if not cart or not cart.cart_items.exists():
        return redirect('cart')

    total_price = cart.total_price()
    return render(request, 'checkout.html', {'cart': cart, 'total_price': total_price})


# Simulated Mpesa Payment
@csrf_exempt
@login_required
def mpesa_payment(request):
    context = {}
    cart = Cart.objects.filter(user=request.user).first()

    # Ensure the user is logged in
    if not request.user.is_authenticated:
        return redirect('login')

    # Check if the user's cart is valid
    if not cart or not cart.cart_items.exists():
        return redirect('cart')  # Redirect to cart if it's empty

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Save delivery details
            delivery = form.save(commit=False)
            delivery.user = request.user
            delivery.save()

            # Create a new order
            order = Order.objects.create(
                user=request.user,
                total_price=cart.total_price(),
                status='pending',
            )

            # Add cart items to the order
            for item in cart.cart_items.all():
                order.cart_items.add(item)

            # Prepare item details before clearing the cart
            item_details = ""
            for cart_item in order.cart_items.all():
                item_name = cart_item.product.name  # Product name
                item_quantity = cart_item.quantity  # Quantity ordered
                item_price = cart_item.product.price  # Price per item
                item_total = item_price * item_quantity  # Total for this item

                # Append item details
                item_details += f" - {item_name} (x{item_quantity}) - Ksh {item_total:.2f}\n"

            # Clear the cart after preparing item details
            cart.cart_items.all().delete()

            # Prepare for MPesa STK Push
            cl = MpesaClient()
            phone_number = delivery.phone_number
            amount = int(order.total_price)
            account_reference = "OrderPayment"
            transaction_desc = f"Payment for Order #{order.id} by {request.user.username}"
            callback_url = 'https://api.darajambili.com/express-payment'

            try:
                # Initiate MPesa STK Push
                cl.stk_push(phone_number, amount, account_reference, transaction_desc, callback_url)

                # Prepare receipt email
               # Prepare receipt email for the user and the admin
                receipt_message = (
                    f"Dear {delivery.full_name},\n\n"
                    f"Thank you for your order and payment. Below are the details:\n\n"
                    f"Order Details:\n"
                    f"========================\n"
                    f"Order ID: {order.id}\n"
                    f"Delivery Location: {delivery.delivery_location}\n\n"
                    f"Items:\n"
                    f"{item_details}"
                    f"========================\n"
                    f"Total Price: Ksh {order.total_price:.2f}\n"
                    f"Thank you for shopping with us!\n"
                    f"We will deliver your order to: {delivery.delivery_location}."
                )

                # Send email to both the user and the admin
                recipient_list = [request.user.email, settings.EMAIL_HOST_USER]  # Add the admin's email here

                send_mail(
                    subject="Order Confirmation",
                    message=receipt_message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=recipient_list,  # Both user and admin will receive the email
                    fail_silently=False,
                )
                context['result'] = "Payment initiated! A confirmation email has been sent to you."
            except Exception as e:
                context['result'] = f"Error during payment initiation: {e}"

        else:
            context['result'] = "Invalid delivery details. Please try again."
    else:
        form = OrderForm()

    context.update({
        'form': form,
        'cart': cart,
    })
    return render(request, 'mpesa_payment.html', context)



def stk_push_callback(request):
    data = request.body
    return HttpResponse("STK push callback received")


# Payment Success
@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'payment_success.html', {'order': order})

# About Us view
def about(request):
    return render(request, 'about.html')

def index(request):
    return render(request, 'index.html')


def contact_us(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        if not (name and email and subject and message):
            return JsonResponse({'success': False, 'message': 'All fields are required.'})

        # Construct email message
        full_message = (
            f"Message from {name} ({email}):\n\n"
            f"Subject: {subject}\n\n"
            f"Message:\n{message}"
        )

        try:
            # Send email to your email address
            send_mail(
                f"New Contact Us Message: {subject}",
                full_message,
                settings.EMAIL_HOST_USER,  # Sender email (configured in settings)
                [settings.EMAIL_HOST_USER],  # Your email address
                fail_silently=False,
            )
            return JsonResponse({'success': True, 'message': 'Your message has been sent successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f"An error occurred: {e}"})

    return render(request, 'contact.html')