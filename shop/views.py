from django.shortcuts import render

from django.shortcuts import render
from shop.models import Product
from .models import OrderItem, Order
def home(request):
    products = Product.objects.filter(is_active=True)
    return render(request, "shop/home.html", {"products": products})


def about_view(request):
    return render(request, "about.html")

    
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import SignupForm, LoginForm

def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Signup successful! 🎉")
            return redirect("home")
    else:
        form = SignupForm()
    return render(request, "auth/signup.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back {user.username}! 👋")
            return redirect("home")
    else:
        form = LoginForm()
    return render(request, "auth/login.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have logged out.")
    return redirect("home")

from django.shortcuts import get_object_or_404

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]

    context = {
        "product": product,
        "related_products": related_products,
    }
    return render(request, "shop/product_detail.html", context)



from django.shortcuts import render
from django.db.models import Q
from .models import Product, Category

def product_list(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.all()

    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort = request.GET.get('sort', '')

    # Search filter
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    # Category filter
    if category_id:
        products = products.filter(category__id=category_id)

    # Price filter
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Sorting
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'newest':
        products = products.order_by('-created_at')

    context = {
        "products": products,
        "categories": categories,
        "selected_category": category_id,
        "query": query,
        "min_price": min_price,
        "max_price": max_price,
        "sort": sort,
    }
    return render(request, "product_list.html", context)

from django.http import JsonResponse
from .cart import Cart
from django.shortcuts import redirect

def cart_view(request):
    cart = Cart(request)
    context = {
        "cart_items": cart.items(),
        "total": cart.total(),
    }
    return render(request, "cart.html", context)

def cart_add(request, product_id):
    cart = Cart(request)
    cart.add(product_id)
    return redirect(request.META.get('HTTP_REFERER'))

def cart_remove(request, product_id):
    cart = Cart(request)
    cart.remove(product_id)
    return redirect("cart")

def cart_update(request, product_id):
    quantity = int(request.POST.get("quantity", 1))
    cart = Cart(request)
    cart.update(product_id, quantity)
    return redirect("cart")


from .forms import CheckoutForm
from .cart import Cart
from django.contrib.auth.decorators import login_required

# @login_required
def checkout_view(request):
    cart = Cart(request)
    if not cart.items():
        return redirect("product_list")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()
            # Save order items
            for item in cart.items():
                OrderItem.objects.create(
                    order=order,
                    product=item["product"],
                    quantity=item["quantity"],
                    price=item["product"].price
                )
            cart.clear()
            messages.success(request, f"✅ Product purchase successful! Order ID: #{order.id}")
            return render(request, "checkout_success.html", {"order": order})
    else:
        form = CheckoutForm()
    return render(request, "checkout.html", {"form": form, "cart_items": cart.items(), "total": cart.total()})



# Cashfree Payment Integration
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .forms import CheckoutForm
from .cart import Cart
from .models import Order, OrderItem, Payment
import requests, json
from django.views.decorators.csrf import csrf_exempt
import hashlib
import hmac

@login_required
def checkout_view(request):
    cart = Cart(request)
    if not cart.items():
        messages.warning(request, "Your cart is empty!")
        return redirect("product_list")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()

            total_amount = cart.total()

            if total_amount <= 0:
                messages.error(request, "Cart is empty or invalid amount.")
                return redirect("cart")

            # Create order items
            for item in cart.items():
                OrderItem.objects.create(
                    order=order,
                    product=item["product"],
                    quantity=item["quantity"],
                    price=item["product"].price
                )

            # Create payment record
            payment = Payment.objects.create(order=order, amount=total_amount, status="INITIATED")
            cart.clear()

            # Redirect to payment page
            return redirect("cashfree_payment", order_id=order.id)
    else:
        form = CheckoutForm()

    return render(request, "checkout.html", {"form": form, "cart_items": cart.items(), "total": cart.total()})


@login_required
def cashfree_payment(request, order_id):
    """
    Generates Cashfree cftoken and redirects to checkout page
    """
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect("checkout")

    try:
        payment = order.payment
    except Payment.DoesNotExist:
        messages.error(request, "Payment record not found.")
        return redirect("checkout")

    # Generate cftoken from Cashfree API
    try:
        order_amount = float(payment.amount)
        payload = {
            "orderId": str(order.id),
            "orderAmount": "{0:.2f}".format(order_amount),
            "orderCurrency": "INR"
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Use Basic Auth with app_id:secret_key
        auth = (settings.CASHFREE_APP_ID, settings.CASHFREE_SECRET_KEY)
        
        response = requests.post(
            settings.CASHFREE_API_URL,
            json=payload,
            headers=headers,
            auth=auth,
            timeout=10
        )
        
        print(f"Cashfree API Response: {response.status_code} - {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK' and 'cftoken' in data:
                cftoken = data['cftoken']
                # Save token to Payment record
                payment.cftoken = cftoken
                payment.save()
                
                print(f"Token generated successfully: {cftoken[:20]}...")
                
                # Redirect to checkout page with token
                return redirect('cashfree_checkout', order_id=order.id)
            else:
                error_msg = data.get('message', 'Failed to generate token')
                print(f"Cashfree error: {error_msg}")
                messages.error(request, f"Payment Error: {error_msg}")
                return render(request, "payment_error.html", {"error": error_msg})
        else:
            error_msg = f"API Error: {response.status_code}"
            print(f"Cashfree API Error: {response.text}")
            messages.error(request, error_msg)
            return render(request, "payment_error.html", {"error": error_msg})
            
    except requests.exceptions.Timeout:
        error_msg = "Request timeout. Please try again."
        print(f"Cashfree timeout: {error_msg}")
        messages.error(request, error_msg)
        return render(request, "payment_error.html", {"error": error_msg})
    except requests.exceptions.RequestException as e:
        error_msg = f"Connection Error: {str(e)}"
        print(f"Cashfree request error: {error_msg}")
        messages.error(request, error_msg)
        return render(request, "payment_error.html", {"error": error_msg})
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"Cashfree error: {error_msg}")
        messages.error(request, error_msg)
        return redirect("checkout")


@login_required
def cashfree_checkout(request, order_id):
    """
    Redirects user to Cashfree checkout with proper token
    """
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        payment = order.payment
    except Order.DoesNotExist:
        return render(request, "payment_error.html", {"error": "Order not found."})
    except Payment.DoesNotExist:
        return render(request, "payment_error.html", {"error": "Payment record not found."})

    if not payment.cftoken:
        return render(request, "payment_error.html", {"error": "Payment token not found."})

    # Render HTML that auto-submits to Cashfree
    context = {
        "order_id": order.id,
        "order_amount": "{0:.2f}".format(float(payment.amount)),
        "cashfree_app_id": settings.CASHFREE_APP_ID,
        "customer_name": order.full_name,
        "customer_email": order.email,
        "customer_phone": getattr(request.user, 'phone', '9999999999') or '9999999999',
        "cftoken": payment.cftoken,
    }
    return render(request, "cashfree_checkout.html", context)


@csrf_exempt
def cashfree_payment_success(request):
    """
    Handles payment success callback from Cashfree
    """
    order_id = request.POST.get("orderId")
    tx_status = request.POST.get("txStatus")
    reference_id = request.POST.get("referenceId")
    signature = request.POST.get("signature")

    if not order_id:
        return render(request, "payment_error.html", {"error": "Order ID missing in callback."})

    try:
        order = Order.objects.get(id=order_id)
        payment = order.payment
    except Order.DoesNotExist:
        return render(request, "payment_error.html", {"error": "Order not found."})
    except Payment.DoesNotExist:
        return render(request, "payment_error.html", {"error": "Payment record not found."})

    # Verify signature for security
    message = f"{order_id}{float(payment.amount)}{tx_status}"
    computed_signature = hashlib.sha256(
        (message + settings.CASHFREE_SECRET_KEY).encode()
    ).hexdigest()

    if signature != computed_signature:
        messages.error(request, "Payment verification failed. Invalid signature.")
        return render(request, "payment_failed.html", {"order": order})

    if tx_status == "SUCCESS":
        order.is_paid = True
        order.save()
        payment.payment_id = reference_id
        payment.status = "SUCCESS"
        payment.save()
        
        messages.success(request, f"✅ Payment Successful! Order ID: #{order.id}")
        return render(request, "checkout_success.html", {"order": order})
    else:
        payment.status = "FAILED"
        payment.save()
        messages.error(request, "Payment failed. Please try again.")
        return render(request, "payment_failed.html", {"order": order})


@csrf_exempt
def cashfree_webhook(request):
    """
    Webhook endpoint for Cashfree to notify about payment status
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            order_id = data.get("orderId")
            tx_status = data.get("txStatus")
            reference_id = data.get("referenceId")
            
            order = Order.objects.get(id=order_id)
            payment = order.payment
            
            if tx_status == "SUCCESS":
                order.is_paid = True
                order.save()
                payment.payment_id = reference_id
                payment.status = "SUCCESS"
            else:
                payment.status = tx_status
            
            payment.save()
            return redirect("checkout_success", order_id=order.id)
        except Exception as e:
            print(f"Webhook error: {str(e)}")
            return render(request, "payment_error.html", {"error": str(e)})
    
    return render(request, "payment_error.html", {"error": "Invalid webhook request"})





from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Order

@login_required
def profile_view(request):
    user = request.user
    orders = user.order_set.all().order_by('-created_at')

    if request.method == "POST":
        user.first_name = request.POST.get("first_name", user.first_name)
        user.last_name = request.POST.get("last_name", user.last_name)
        user.email = request.POST.get("email", user.email)
        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect("profile")

    context = {
        "user": user,
        "orders": orders,
    }
    return render(request, "profile.html", context)

from django.shortcuts import render

from django.shortcuts import render, get_object_or_404
from .models import Category, Product

def category_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, is_active=True)
    context = {
        'slug': category.name,
        'products': products
    }
    return render(request, 'category.html', context)


def all_categories_view(request):
    categories = Category.objects.all()
    return render(request, 'categories.html', {'categories': categories})




from django.contrib.admin.views.decorators import staff_member_required
from .models import Product, Category, Order

@staff_member_required
def admin_dashboard(request):
    context = {
        "total_products": Product.objects.count(),
        "total_categories": Category.objects.count(),
        "total_orders": Order.objects.count(),
    }
    return render(request, "admin_dashboard.html", context)

from django.http import JsonResponse
from .models import Product
from django.db.models import Q

def api_search_products(request):
    query = request.GET.get('q', '')
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )[:10]
        results = []
        for product in products:
            results.append({
                'id': product.id,
                'name': product.name,
                'price': str(product.price),
                'slug': product.slug,
                'image': product.images.first().image.url if product.images.exists() else ''
            })
        return JsonResponse({'results': results})
    return JsonResponse({'results': []})


import csv, io
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Product, Category, ProductImage
from django.utils.text import slugify

def upload_products_csv(request):
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Please upload a CSV file")
            return redirect("upload_products")

        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        reader = csv.DictReader(io_string)

        for row in reader:
            # Category handle
            category, created = Category.objects.get_or_create(name=row["category"])

            # Product create/update
            product, created = Product.objects.update_or_create(
                sku=row["sku"],
                defaults={
                    "name": row["name"],
                    "description": row.get("description", ""),
                    "category": category,
                    "price": row["price"],
                    "discount_price": row.get("discount_price") or None,
                    "stock": row.get("stock") or 0,
                    "is_active": row.get("is_active", "True").lower() in ["true", "1"],
                    "slug": slugify(row["name"]),
                }
            )

            # Image add if provided
            if row.get("image"):
                ProductImage.objects.get_or_create(
                    product=product,
                    image=row["image"],  # Path: "products/filename.jpg"
                    defaults={"alt_text": row["name"]}
                )

        messages.success(request, "Products uploaded successfully ✅")
        return redirect("upload_products")

    return render(request, "upload_products.html")


# shop/views.py
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product

def buy_now(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # cart initialize
    cart = request.session.get('cart', {})

    # product ko add karna
    if str(product_id) in cart:
        cart[str(product_id)] += 1
    else:
        cart[str(product_id)] = 1

    # session update
    request.session['cart'] = cart

    # direct checkout page pe bhejna
    return redirect('checkout')


from django.shortcuts import render, redirect
from .models import Address, Order, OrderItem
from .forms import AddressForm
from .cart import get_cart_items

def checkout(request):
    if not request.user.is_authenticated:
        return redirect('login')

    cart_items = get_cart_items(request)
    total = sum(item['total_price'] for item in cart_items)

    # Fetch all saved addresses
    addresses = Address.objects.filter(user=request.user)

    selected_address = None
    if request.method == "POST":
        if 'select_address' in request.POST:
            selected_address = Address.objects.get(id=request.POST.get('address_id'))
        else:
            # Add new address
            form = AddressForm(request.POST)
            if form.is_valid():
                new_address = form.save(commit=False)
                new_address.user = request.user
                new_address.save()
                selected_address = new_address
            else:
                print(form.errors)
                form = AddressForm()

        if selected_address:
            order = Order.objects.create(
                user=request.user,
                address=selected_address,
                is_paid=False
            )
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    quantity=item['quantity'],
                    price=item['total_price']
                )
            request.session['cart'] = {}
            return redirect('order_success')
    else:
        form = AddressForm()

    return render(request, 'checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'total': total,
        'addresses': addresses
    })






from django.shortcuts import render
from django.db.models import Q
from .models import Product, Category

def product_list_view(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.all()

    query = request.GET.get('q', '')
    selected_category = request.GET.get('category', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort = request.GET.get('sort', '')

    # Filter by search query
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    # Filter by category
    if selected_category:
        products = products.filter(category_id=selected_category)

    # Filter by price range
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Sorting
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'newest':
        products = products.order_by('-created_at')

    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'selected_category': selected_category,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
    }
    return render(request, 'product_list.html', context)