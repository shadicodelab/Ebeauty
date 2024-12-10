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
    if request.method == 'POST':
        cart = Cart.objects.filter(user=request.user).first()
        if not cart or not cart.cart_items.exists():
            return redirect('cart')

        total_price = cart.total_price()

        # Simulate payment processing
        payment_successful = True

        if payment_successful:
            order = Order.objects.create(user=request.user, total_price=total_price, status='paid')
            for item in cart.cart_items.all():
                order.cart_items.add(item)
            cart.cart_items.all().delete()
            return redirect('payment_success', order_id=order.id)

    return render(request, 'mpesa_payment.html')


def place_order(request):
    cart = Cart.objects.filter(user=request.user).first()  # Get the user's cart
    if cart:
        if request.method == 'POST':
            form = OrderForm(request.POST)
            if form.is_valid():
                order = form.save(commit=False)  # Save the form without committing yet
                order.user = request.user  # Set the user who placed the order
                order.save()  # Save the order to the database

                # After saving the order, redirect to a confirmation page or another step
                return redirect('homepage')  # Replace with the URL name you want

        else:
            form = OrderForm()  # Show the empty form if the request is GET

        return render(request, 'place_order.html', {'form': form, 'cart': cart})
    else:
        return redirect('cart')  # Redirect if no cart exists

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
