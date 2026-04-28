"""
Holiday Packages blueprint.
Handles listing, detail view, and booking of packaged holidays.
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from app.models import Package, PromoCode, Review, Wishlist, Booking, BookingItem
from app.forms import PackageBookingForm, ReviewForm
from app.services.auth import login_required, get_current_user
from app import db
from datetime import datetime
import uuid

packages_bp = Blueprint('packages', __name__, url_prefix='/packages')


@packages_bp.route('/')
def listing():
    destination = request.args.get('destination', '').strip()
    tag = request.args.get('tag', '').strip()

    query = Package.query.filter_by(active=True)
    if destination:
        query = query.filter(Package.destination.ilike(f'%{destination}%'))
    if tag:
        query = query.filter_by(tag=tag)

    packages = query.order_by(Package.base_price.asc()).all()
    user = get_current_user()

    # Gather all tags for filter pills
    tags = db.session.query(Package.tag).filter(Package.tag.isnot(None)).distinct().all()
    tags = [t[0] for t in tags]

    return render_template('packages.html', packages=packages, user=user,
                           tags=tags, active_tag=tag, destination=destination)


@packages_bp.route('/<slug>')
def detail(slug):
    pkg = Package.query.filter_by(slug=slug, active=True).first_or_404()
    reviews = Review.query.filter_by(review_type='PACKAGE', ref_id=pkg.id)\
                          .order_by(Review.created_at.desc()).limit(10).all()
    avg_rating = None
    if reviews:
        avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1)

    review_form = ReviewForm()
    booking_form = PackageBookingForm()

    # Check wishlist
    in_wishlist = False
    if 'user_id' in session:
        w = Wishlist.query.filter_by(
            user_id=session['user_id'], item_type='PACKAGE', ref_id=pkg.id
        ).first()
        in_wishlist = bool(w)

    user = get_current_user()
    return render_template('package_detail.html', pkg=pkg, reviews=reviews,
                           avg_rating=avg_rating, review_form=review_form,
                           booking_form=booking_form, in_wishlist=in_wishlist,
                           user=user)


@packages_bp.route('/<slug>/book', methods=['POST'])
@login_required
def book(slug):
    pkg = Package.query.filter_by(slug=slug, active=True).first_or_404()
    form = PackageBookingForm()
    user = get_current_user()

    if not form.validate_on_submit():
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('packages.detail', slug=slug))

    persons = form.persons.data or 2
    total = pkg.base_price * persons

    # Apply promo code if provided
    discount = 0.0
    promo_label = ''
    code_str = (form.promo_code.data or '').strip().upper()
    if code_str:
        promo = PromoCode.query.filter_by(code=code_str).first()
        if promo:
            valid, msg = promo.is_valid(total)
            if valid:
                discount = promo.compute_discount(total)
                promo.used_count += 1
                promo_label = f' (promo: {code_str})'
            else:
                flash(f'Promo code: {msg}', 'warning')
        else:
            flash('Promo code not found.', 'warning')

    final_amount = total - discount
    payment_method = request.form.get('payment_method', 'card').strip() or 'card'
    booking_code = f"ST-PKG-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

    booking = Booking(
        user_id=session['user_id'],
        booking_code=booking_code,
        total_amount=final_amount,
        customer_name=form.customer_name.data,
        customer_email=form.customer_email.data,
        customer_phone=form.customer_phone.data,
        payment_method=payment_method,
        status='CONFIRMED',
    )
    db.session.add(booking)
    db.session.flush()

    item = BookingItem(
        booking_id=booking.id,
        type='PACKAGE',
        ref_id=pkg.id,
        title=pkg.name,
        amount=final_amount,
    )
    item.details = {
        'destination': pkg.destination,
        'duration_nights': pkg.duration_nights,
        'persons': persons,
        'travel_date': form.travel_date.data.isoformat() if form.travel_date.data else None,
        'discount': discount,
        'promo': code_str or None,
        'special_requests': form.special_requests.data or '',
    }
    db.session.add(item)
    db.session.commit()

    flash(f'Package booked! Your booking code is {booking_code}{promo_label}', 'success')
    return redirect(url_for('public.booking_confirmation', booking_id=booking.id))


@packages_bp.route('/<int:pkg_id>/review', methods=['POST'])
@login_required
def submit_review(pkg_id):
    pkg = Package.query.get_or_404(pkg_id)
    form = ReviewForm()
    if form.validate_on_submit():
        # Check for existing review
        existing = Review.query.filter_by(
            user_id=session['user_id'], review_type='PACKAGE', ref_id=pkg_id
        ).first()
        if existing:
            flash('You have already reviewed this package.', 'info')
        else:
            rev = Review(
                user_id=session['user_id'],
                review_type='PACKAGE',
                ref_id=pkg_id,
                rating=int(form.rating.data),
                title=form.title.data,
                comment=form.comment.data,
            )
            db.session.add(rev)
            db.session.commit()
            flash('Thank you for your review!', 'success')
    return redirect(url_for('packages.detail', slug=pkg.slug))


@packages_bp.route('/api/apply-promo', methods=['POST'])
def apply_promo_api():
    """AJAX endpoint for real-time promo code validation."""
    data = request.get_json() or {}
    code = (data.get('code') or '').strip().upper()
    amount = float(data.get('amount') or 0)

    if not code:
        return jsonify({'valid': False, 'message': 'Enter a promo code.'})

    promo = PromoCode.query.filter_by(code=code).first()
    if not promo:
        return jsonify({'valid': False, 'message': 'Code not found.'})

    valid, msg = promo.is_valid(amount)
    if not valid:
        return jsonify({'valid': False, 'message': msg})

    discount = promo.compute_discount(amount)
    return jsonify({
        'valid': True,
        'message': promo.description or 'Promo applied!',
        'discount': discount,
        'final': round(amount - discount, 2),
        'discount_type': promo.discount_type,
        'discount_value': promo.discount_value,
    })
