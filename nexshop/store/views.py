import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Product, Category, Order, OrderItem


# ── Home / Product Listing ──────────────────────────────────────────────────
def home(request):
    categories = Category.objects.all()
    category_slug = request.GET.get('category')
    search = request.GET.get('q', '')

    products = Product.objects.filter(is_active=True)
    if category_slug:
        products = products.filter(category__slug=category_slug)
    if search:
        products = products.filter(name__icontains=search)

    return render(request, 'store/home.html', {
        'products': products,
        'categories': categories,
        'selected_category': category_slug,
        'search': search,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related = Product.objects.filter(category=product.category, is_active=True).exclude(id=product.id)[:4]
    return render(request, 'store/product_detail.html', {'product': product, 'related': related})


# ── Cart (session-based) ────────────────────────────────────────────────────
def cart_view(request):
    cart = request.session.get('cart', {})
    items = []
    total = 0
    for pid, qty in cart.items():
        try:
            p = Product.objects.get(id=pid)
            subtotal = p.price * qty
            total += subtotal
            items.append({'product': p, 'quantity': qty, 'subtotal': subtotal})
        except Product.DoesNotExist:
            pass
    return render(request, 'store/cart.html', {'items': items, 'total': total})


@require_POST
def add_to_cart(request, product_id):
    cart = request.session.get('cart', {})
    pid = str(product_id)
    cart[pid] = cart.get(pid, 0) + 1
    request.session['cart'] = cart
    return JsonResponse({'success': True, 'count': sum(cart.values())})


@require_POST
def update_cart(request, product_id):
    data = json.loads(request.body)
    qty = int(data.get('quantity', 1))
    cart = request.session.get('cart', {})
    pid = str(product_id)
    if qty <= 0:
        cart.pop(pid, None)
    else:
        cart[pid] = qty
    request.session['cart'] = cart
    return JsonResponse({'success': True, 'count': sum(cart.values())})


@require_POST
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    cart.pop(str(product_id), None)
    request.session['cart'] = cart
    return JsonResponse({'success': True, 'count': sum(cart.values())})


# ── Checkout & Orders ───────────────────────────────────────────────────────
@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('cart')

    items = []
    total = 0
    for pid, qty in cart.items():
        try:
            p = Product.objects.get(id=pid)
            subtotal = p.price * qty
            total += subtotal
            items.append({'product': p, 'quantity': qty, 'subtotal': subtotal})
        except Product.DoesNotExist:
            pass

    if request.method == 'POST':
        address = request.POST.get('address', '').strip()
        if not address:
            return render(request, 'store/checkout.html', {
                'items': items, 'total': total, 'error': 'Shipping address is required.'
            })

        order = Order.objects.create(
            user=request.user,
            total_price=total,
            shipping_address=address,
            status='confirmed',
        )
        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price=item['product'].price,
            )
        request.session['cart'] = {}
        return redirect('order_success', order_id=order.id)

    return render(request, 'store/checkout.html', {'items': items, 'total': total})


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/order_success.html', {'order': order})


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/my_orders.html', {'orders': orders})


# ── Auth ────────────────────────────────────────────────────────────────────
def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        if password1 != password2:
            error = 'Passwords do not match.'
        elif User.objects.filter(username=username).exists():
            error = 'Username already taken.'
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            login(request, user)
            return redirect('home')
    return render(request, 'store/register.html', {'error': error})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'home'))
        error = 'Invalid username or password.'
    return render(request, 'store/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('home')


def cart_count(request):
    cart = request.session.get('cart', {})
    return JsonResponse({'count': sum(cart.values())})
