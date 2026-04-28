"""
Reviews blueprint — handles POST /reviews and GET /hotel/<id> detail with reviews.
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from app.models import Hotel, Flight, Review, Wishlist, Booking, BookingItem
from app.forms import ReviewForm
from app.services.auth import login_required, get_current_user
from app import db
from sqlalchemy import func

reviews_bp = Blueprint('reviews', __name__)


# ---- Hotel detail with reviews ----
@reviews_bp.route('/hotels/<int:hotel_id>')
def hotel_detail(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    reviews = Review.query.filter_by(review_type='HOTEL', ref_id=hotel_id)\
                          .order_by(Review.created_at.desc()).limit(20).all()

    avg_rating = None
    rating_counts = {i: 0 for i in range(1, 6)}
    if reviews:
        avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1)
        for r in reviews:
            rating_counts[r.rating] = rating_counts.get(r.rating, 0) + 1

    form = ReviewForm()

    in_wishlist = False
    already_reviewed = False
    if 'user_id' in session:
        w = Wishlist.query.filter_by(
            user_id=session['user_id'], item_type='HOTEL', ref_id=hotel_id
        ).first()
        in_wishlist = bool(w)
        already_reviewed = bool(
            Review.query.filter_by(
                user_id=session['user_id'], review_type='HOTEL', ref_id=hotel_id
            ).first()
        )

    user = get_current_user()
    return render_template('hotel_detail.html', hotel=hotel, reviews=reviews,
                           avg_rating=avg_rating, rating_counts=rating_counts,
                           form=form, in_wishlist=in_wishlist,
                           already_reviewed=already_reviewed, user=user)


# ---- Submit review ----
@reviews_bp.route('/reviews/hotel/<int:hotel_id>', methods=['POST'])
@login_required
def submit_hotel_review(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    form = ReviewForm()
    if form.validate_on_submit():
        existing = Review.query.filter_by(
            user_id=session['user_id'], review_type='HOTEL', ref_id=hotel_id
        ).first()
        if existing:
            flash('You have already reviewed this hotel.', 'info')
        else:
            # Check if verified booking exists
            verified = bool(
                db.session.query(BookingItem)
                .join(Booking, Booking.id == BookingItem.booking_id)
                .filter(
                    Booking.user_id == session['user_id'],
                    BookingItem.type == 'HOTEL',
                    BookingItem.hotel_id == hotel_id,
                ).first()
            )
            rev = Review(
                user_id=session['user_id'],
                review_type='HOTEL',
                ref_id=hotel_id,
                rating=int(form.rating.data),
                title=form.title.data,
                comment=form.comment.data,
                verified_booking=verified,
            )
            db.session.add(rev)
            db.session.commit()
            flash('Thank you for your review!', 'success')
    return redirect(url_for('reviews.hotel_detail', hotel_id=hotel_id))


# ---- Wishlist toggle (AJAX) ----
@reviews_bp.route('/wishlist/toggle', methods=['POST'])
@login_required
def toggle_wishlist():
    data = request.get_json() or {}
    item_type = data.get('item_type', '').upper()
    ref_id = int(data.get('ref_id', 0))

    if item_type not in ('FLIGHT', 'HOTEL', 'PACKAGE', 'ACTIVITY') or not ref_id:
        return jsonify({'error': 'Invalid request'}), 400

    existing = Wishlist.query.filter_by(
        user_id=session['user_id'], item_type=item_type, ref_id=ref_id
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'wishlisted': False})
    else:
        w = Wishlist(user_id=session['user_id'], item_type=item_type, ref_id=ref_id)
        db.session.add(w)
        db.session.commit()
        return jsonify({'wishlisted': True})


# ---- Promo AJAX (shared across booking pages) ----
@reviews_bp.route('/promo/validate', methods=['POST'])
def validate_promo():
    from app.models import PromoCode
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
    })
