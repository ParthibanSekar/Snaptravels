"""
Activities & Experiences blueprint.
Browse and book city tours, adventure sports, cultural experiences.
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.models import Activity, Review, Booking, BookingItem, Notification
from app.services.auth import login_required, get_current_user
from app import db
from datetime import datetime
import uuid
from app.services.sanitize import sanitize_str, sanitize_booking_customer

activities_bp = Blueprint('activities', __name__, url_prefix='/activities')

CATEGORIES = ['Adventure', 'Cultural', 'Food', 'Wellness', 'Sightseeing', 'Water Sports', 'Wildlife']


@activities_bp.route('/', methods=['GET', 'POST'])
def listing():
    city = request.args.get('city', '').strip()
    category = request.args.get('category', '').strip()
    sort = request.args.get('sort', 'popular')

    query = Activity.query.filter_by(active=True)
    if city:
        query = query.filter(Activity.city.ilike(f'%{city}%'))
    if category:
        query = query.filter_by(category=category)

    if sort == 'price_low':
        query = query.order_by(Activity.price_per_person.asc())
    elif sort == 'price_high':
        query = query.order_by(Activity.price_per_person.desc())
    elif sort == 'rating':
        query = query.order_by(Activity.rating.desc())
    else:
        query = query.order_by(Activity.review_count.desc(), Activity.rating.desc())

    activities = query.all()

    # All available cities for the city filter
    cities = db.session.query(Activity.city).distinct().order_by(Activity.city.asc()).all()
    cities = [c[0] for c in cities]

    user = get_current_user()
    return render_template('activities.html', activities=activities,
                           city=city, category=category, sort=sort,
                           categories=CATEGORIES, cities=cities, user=user)


@activities_bp.route('/<int:activity_id>')
def detail(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    reviews = Review.query.filter_by(review_type='ACTIVITY', ref_id=activity_id)\
                          .order_by(Review.created_at.desc()).limit(10).all()
    avg_rating = None
    if reviews:
        avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1)

    # Track recently viewed
    if 'user_id' in session:
        from app.models import RecentlyViewed
        try:
            existing = RecentlyViewed.query.filter_by(
                user_id=session['user_id'], item_type='ACTIVITY', ref_id=activity_id
            ).first()
            if existing:
                existing.viewed_at = datetime.utcnow()
            else:
                rv = RecentlyViewed(user_id=session['user_id'], item_type='ACTIVITY',
                                    ref_id=activity_id, title=activity.name)
                db.session.add(rv)
            db.session.commit()
        except Exception:
            db.session.rollback()

    user = get_current_user()
    return render_template('activity_detail.html', activity=activity, reviews=reviews,
                           avg_rating=avg_rating, user=user)


@activities_bp.route('/<int:activity_id>/book', methods=['POST'])
@login_required
def book(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    persons = int(request.form.get('persons', 1))
    activity_date = request.form.get('activity_date', '')
    _raw = {
        'customer_name':  request.form.get('customer_name', ''),
        'customer_email': request.form.get('customer_email', ''),
        'customer_phone': request.form.get('customer_phone', ''),
    }
    _clean, _errs = sanitize_booking_customer(_raw, phone_required=False)
    if _errs:
        flash('Invalid input: ' + '; '.join(_errs.values()), 'danger')
        return redirect(request.referrer or url_for('activities.activities_home'))
    customer_name  = _clean['customer_name']
    customer_email = _clean['customer_email']
    customer_phone = _clean.get('customer_phone', '')
    special_requests = request.form.get('special_requests', '').strip()

    if not customer_name or not customer_email:
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('activities.detail', activity_id=activity_id))

    if persons < activity.min_persons or persons > activity.max_persons:
        flash(f'Group size must be between {activity.min_persons} and {activity.max_persons}.', 'warning')
        return redirect(url_for('activities.detail', activity_id=activity_id))

    total = round(activity.price_per_person * persons, 2)
    payment_method = request.form.get('payment_method', 'card').strip() or 'card'
    booking_code = f"ST-ACT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

    bk = Booking(
        user_id=session['user_id'],
        booking_code=booking_code,
        total_amount=total,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        payment_method=payment_method,
        status='CONFIRMED',
    )
    db.session.add(bk)
    db.session.flush()

    item = BookingItem(
        booking_id=bk.id,
        type='ACTIVITY',
        ref_id=activity.id,
        title=f"{activity.name} — {activity.city}",
        amount=total,
    )
    item.details = {
        'activity_name': activity.name,
        'city': activity.city,
        'category': activity.category,
        'duration_hours': activity.duration_hours,
        'persons': persons,
        'activity_date': activity_date,
        'price_per_person': activity.price_per_person,
        'special_requests': special_requests,
    }
    db.session.add(item)

    # Update review count (fake engagement)
    activity.review_count = (activity.review_count or 0) + 1

    notif = Notification(
        user_id=session['user_id'], type='BOOKING',
        title='Activity Booked!',
        message=f"{activity.name} in {activity.city} — {persons} person(s). Code: {booking_code}",
        link=url_for('public.booking_confirmation', booking_id=bk.id),
    )
    db.session.add(notif)
    db.session.commit()

    flash(f'Activity booked! Code: {booking_code}', 'success')
    return redirect(url_for('public.booking_confirmation', booking_id=bk.id))
