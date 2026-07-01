"""
Travel Shop blueprint.

Routes:
  GET  /shop/                    — product listing (filter by category)
  GET  /shop/product/<id>        — product detail + size picker
  POST /shop/cart/add            — add item to session cart
  POST /shop/cart/update         — update quantity
  POST /shop/cart/remove         — remove item
  GET  /shop/cart                — view cart
  GET  /shop/checkout            — checkout form
  POST /shop/checkout            — place order → ShopOrder in DB
  GET  /shop/confirmation/<code> — order confirmation

Cart is stored in Flask session as:
  session['shop_cart'] = [
      {'product_id': 1, 'size': 'M', 'quantity': 2},
      ...
  ]
"""

import uuid
import logging
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, g
)

from app import db
from app.models import Product, ShopOrder, ShopOrderItem
from app.services.auth import get_current_user, login_required

logger = logging.getLogger('snaptravels.shop')

shop_bp = Blueprint('shop', __name__, url_prefix='/shop')

CATEGORIES = [
    ('clothing',    'Travel Clothing', 'bi-person-arms-up'),
    ('bags',        'Bags & Luggage',  'bi-briefcase'),
    ('accessories', 'Accessories',     'bi-plug'),
    ('footwear',    'Footwear',        'bi-bootstrap'),
]


# ── Cart helpers ────────────────────────────────────────────────────────────

def _get_cart():
    return session.get('shop_cart', [])

def _save_cart(cart):
    session['shop_cart'] = cart
    session.modified = True

def _cart_count():
    return sum(item['quantity'] for item in _get_cart())

def _cart_total(cart):
    total = 0.0
    for item in cart:
        p = Product.query.get(item['product_id'])
        if p:
            total += p.price * item['quantity']
    return round(total, 2)

def _enrich_cart(cart):
    """Attach product objects to cart items."""
    enriched = []
    for item in cart:
        p = Product.query.get(item['product_id'])
        if p:
            enriched.append({**item, 'product': p})
    return enriched

def _gen_order_code():
    return 'SH-' + uuid.uuid4().hex[:8].upper()


# ── Context processor — inject cart count into all shop templates ───────────

@shop_bp.context_processor
def inject_cart_count():
    return {'cart_count': _cart_count()}


# ── Routes ──────────────────────────────────────────────────────────────────

@shop_bp.route('/')
def index():
    category = request.args.get('category', 'all')
    sort     = request.args.get('sort', 'popular')

    q = Product.query.filter_by(in_stock=True)
    if category != 'all':
        q = q.filter_by(category=category)

    if sort == 'price_asc':
        q = q.order_by(Product.price.asc())
    elif sort == 'price_desc':
        q = q.order_by(Product.price.desc())
    elif sort == 'newest':
        q = q.order_by(Product.created_at.desc())
    else:  # popular
        q = q.order_by(Product.review_count.desc())

    products = q.all()

    # Category counts for filter pills
    cat_counts = {}
    for cat, _, _ in CATEGORIES:
        cat_counts[cat] = Product.query.filter_by(category=cat, in_stock=True).count()

    return render_template(
        'shop/index.html',
        products=products,
        categories=CATEGORIES,
        cat_counts=cat_counts,
        active_category=category,
        active_sort=sort,
        total_count=Product.query.filter_by(in_stock=True).count(),
    )


@shop_bp.route('/product/<int:product_id>')
def product(product_id):
    p = Product.query.get_or_404(product_id)
    # Related: same category, exclude current
    related = (Product.query
               .filter_by(category=p.category, in_stock=True)
               .filter(Product.id != p.id)
               .order_by(Product.review_count.desc())
               .limit(4).all())
    return render_template('shop/product.html', product=p, related=related)


@shop_bp.route('/cart/add', methods=['POST'])
def cart_add():
    product_id = int(request.form.get('product_id', 0))
    size       = request.form.get('size', '').strip() or None
    quantity   = max(1, int(request.form.get('quantity', 1)))

    p = Product.query.get(product_id)
    if not p:
        flash('Product not found.', 'danger')
        return redirect(url_for('shop.index'))

    # Size required for clothing and footwear
    if p.category in ('clothing', 'footwear') and not size:
        flash('Please select a size.', 'warning')
        return redirect(url_for('shop.product', product_id=product_id))

    cart = _get_cart()
    # Check if same product+size already in cart
    for item in cart:
        if item['product_id'] == product_id and item.get('size') == size:
            item['quantity'] = min(item['quantity'] + quantity, 10)
            _save_cart(cart)
            flash(f'"{p.name}" updated in your cart.', 'success')
            return redirect(url_for('shop.cart'))

    cart.append({'product_id': product_id, 'size': size, 'quantity': quantity})
    _save_cart(cart)
    flash(f'"{p.name}" added to cart!', 'success')
    return redirect(url_for('shop.cart'))


@shop_bp.route('/cart/update', methods=['POST'])
def cart_update():
    product_id = int(request.form.get('product_id', 0))
    size       = request.form.get('size') or None
    quantity   = int(request.form.get('quantity', 1))

    cart = _get_cart()
    for item in cart:
        if item['product_id'] == product_id and item.get('size') == size:
            if quantity < 1:
                cart.remove(item)
            else:
                item['quantity'] = min(quantity, 10)
            break
    _save_cart(cart)
    return redirect(url_for('shop.cart'))


@shop_bp.route('/cart/remove', methods=['POST'])
def cart_remove():
    product_id = int(request.form.get('product_id', 0))
    size       = request.form.get('size') or None
    cart = [i for i in _get_cart()
            if not (i['product_id'] == product_id and i.get('size') == size)]
    _save_cart(cart)
    flash('Item removed from cart.', 'info')
    return redirect(url_for('shop.cart'))


@shop_bp.route('/cart')
def cart():
    enriched = _enrich_cart(_get_cart())
    total    = sum(i['product'].price * i['quantity'] for i in enriched)
    shipping = 0 if total >= 999 else 99
    return render_template(
        'shop/cart.html',
        cart=enriched,
        subtotal=round(total, 2),
        shipping=shipping,
        grand_total=round(total + shipping, 2),
    )


@shop_bp.route('/checkout/guest', methods=['POST'])
def checkout_as_guest():
    """Set session flag to allow guest checkout, then redirect to checkout."""
    session['shop_guest_checkout'] = True
    session.modified = True
    return redirect(url_for('shop.checkout'))


@shop_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = _enrich_cart(_get_cart())
    if not cart:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('shop.index'))

    user = get_current_user()
    # Show login/guest gate if not logged in and not yet chosen guest
    if not user and not session.get('shop_guest_checkout'):
        return render_template('shop/checkout_gate.html', cart=cart)

    subtotal = sum(i['product'].price * i['quantity'] for i in cart)
    shipping = 0 if subtotal >= 999 else 99
    grand_total = round(subtotal + shipping, 2)
    user = get_current_user()

    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        email   = request.form.get('email', '').strip()
        phone   = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city    = request.form.get('city', '').strip()
        pincode = request.form.get('pincode', '').strip()
        state   = request.form.get('state', '').strip()
        payment = request.form.get('payment_method', 'card')

        errors = {}
        if not name:    errors['name']    = 'Name is required'
        if not email:   errors['email']   = 'Email is required'
        if not address: errors['address'] = 'Address is required'
        if not city:    errors['city']    = 'City is required'
        if not pincode: errors['pincode'] = 'PIN code is required'

        if errors:
            return render_template(
                'shop/checkout.html',
                cart=cart, subtotal=round(subtotal, 2),
                shipping=shipping, grand_total=grand_total,
                errors=errors, form=request.form,
            )

        full_address = f'{address}, {city}, {state} - {pincode}'
        order = ShopOrder(
            order_code       = _gen_order_code(),
            user_id          = user.id if user else None,
            customer_name    = name,
            customer_email   = email,
            customer_phone   = phone or None,
            shipping_address = full_address,
            total_amount     = grand_total,
            payment_method   = payment,
            status           = 'CONFIRMED',
        )
        db.session.add(order)
        db.session.flush()   # get order.id

        for item in cart:
            p = item['product']
            db.session.add(ShopOrderItem(
                order_id     = order.id,
                product_id   = p.id,
                product_name = p.name,
                size         = item.get('size'),
                quantity     = item['quantity'],
                unit_price   = p.price,
            ))

        db.session.commit()
        _save_cart([])   # clear cart
        session.pop('shop_guest_checkout', None)
        if not user:
            session['shop_guest_email'] = email  # so guest can view their orders
        logger.info(f'[SHOP] Order {order.order_code} placed — ₹{grand_total}')
        return redirect(url_for('shop.confirmation', code=order.order_code))

    return render_template(
        'shop/checkout.html',
        cart=cart,
        subtotal=round(subtotal, 2),
        shipping=shipping,
        grand_total=grand_total,
        errors={},
        form={},
        user=user,
    )


@shop_bp.route('/confirmation/<code>')
def confirmation(code):
    from flask import abort
    order = ShopOrder.query.filter_by(order_code=code).first_or_404()
    user  = get_current_user()
    guest_email = session.get('shop_guest_email')
    # Ownership check: logged-in user must own the order,
    # or guest must match the email stored in their session.
    is_owner = (
        (user and order.user_id == user.id) or
        (not user and order.user_id is None and guest_email and
         order.customer_email == guest_email)
    )
    if not is_owner:
        abort(403)
    return render_template('shop/confirmation.html', order=order, user=user)


@shop_bp.route('/orders')
def my_orders():
    user = get_current_user()
    if user:
        orders = (ShopOrder.query.filter_by(user_id=user.id)
                  .order_by(ShopOrder.created_at.desc()).all())
    else:
        # Guest: look up by session email if stored
        guest_email = session.get('shop_guest_email')
        orders = (ShopOrder.query.filter_by(customer_email=guest_email).all()
                  if guest_email else [])
    return render_template('shop/my_orders.html', orders=orders, user=user)


@shop_bp.route('/order/<code>/cancel', methods=['POST'])
def cancel_order(code):
    order = ShopOrder.query.filter_by(order_code=code).first_or_404()
    user  = get_current_user()
    # Allow if owner or guest (guest checked via email in session)
    is_owner = (user and order.user_id == user.id) or \
               (not order.user_id and session.get('shop_guest_email') == order.customer_email)
    if not is_owner:
        flash('You are not authorised to cancel this order.', 'danger')
        return redirect(url_for('shop.my_orders'))
    if order.status != 'CONFIRMED':
        flash('This order cannot be cancelled.', 'warning')
        return redirect(url_for('shop.my_orders'))

    reason = request.form.get('reason', '').strip() or 'Cancelled by customer'
    order.status        = 'CANCELLED'
    order.cancel_reason = reason
    order.actioned_at   = datetime.utcnow()
    # Restore stock
    for item in order.items:
        p = Product.query.get(item.product_id)
        if p:
            p.stock_qty = (p.stock_qty or 0) + item.quantity
    db.session.commit()
    flash(f'Order {code} has been cancelled.', 'success')
    return redirect(url_for('shop.my_orders'))


@shop_bp.route('/order/<code>/return', methods=['POST'])
def return_order(code):
    order = ShopOrder.query.filter_by(order_code=code).first_or_404()
    user  = get_current_user()
    is_owner = (user and order.user_id == user.id) or \
               (not order.user_id and session.get('shop_guest_email') == order.customer_email)
    if not is_owner:
        flash('You are not authorised to return this order.', 'danger')
        return redirect(url_for('shop.my_orders'))
    if order.status != 'CONFIRMED':
        flash('Only confirmed orders can be returned.', 'warning')
        return redirect(url_for('shop.my_orders'))

    reason = request.form.get('reason', '').strip() or 'Return requested by customer'
    order.status        = 'RETURN_REQUESTED'
    order.return_reason = reason
    order.actioned_at   = datetime.utcnow()
    db.session.commit()
    flash(f'Return request submitted for order {code}. We will process it within 3–5 days.', 'success')
    return redirect(url_for('shop.my_orders'))
