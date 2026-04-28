"""
Extended Admin blueprint — Phase 5.
Handles: hotel CRUD, activity CRUD, revenue dashboard, user management, refunds.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.models import (Hotel, Activity, User, Booking, BookingItem, Notification,
                        RoomType, HotelImage, RewardPoints, PointsTransaction, BlogPost,
                        SiteConfig)
from app.services.auth import roles_required, get_current_user
from app.services.audit import log_audit
from app import db
from datetime import datetime, timedelta
import json

admin_ext_bp = Blueprint('admin_ext', __name__, url_prefix='/admin')


def _safe_image_urls(raw: str) -> list[str]:
    """Parse newline-separated gallery URLs, keeping only safe http/https URLs.
    Rejects javascript:, data:, and any other dangerous schemes."""
    from urllib.parse import urlparse
    safe = []
    for line in raw.splitlines():
        url = line.strip()
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            continue          # reject javascript:, data:, etc.
        if not parsed.netloc:
            continue          # reject bare paths without a host
        safe.append(url)
    return safe


# ---- Hotel Management -------------------------------------------------------

@admin_ext_bp.route('/hotels')
@roles_required('admin')
def hotels():
    user = get_current_user()
    page = request.args.get('page', 1, type=int)
    hotels = Hotel.query.order_by(Hotel.id.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin_hotels.html', user=user, hotels=hotels)


@admin_ext_bp.route('/hotels/new', methods=['GET', 'POST'])
@roles_required('admin')
def new_hotel():
    user = get_current_user()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        city = request.form.get('city', '').strip()
        if not name or not city:
            flash('Name and city are required.', 'danger')
            return redirect(url_for('admin_ext.new_hotel'))

        hotel = Hotel(
            name=name, city=city,
            rating=float(request.form.get('rating', 4.0)),
            price_per_night=float(request.form.get('price_per_night', 5000)),
            description=request.form.get('description', ''),
            image_path=request.form.get('image_path', ''),
        )
        amenities_raw = request.form.get('amenities', '')
        hotel.amenities = [a.strip() for a in amenities_raw.split(',') if a.strip()]
        db.session.add(hotel)
        db.session.flush()
        # Gallery URLs — only http/https URLs accepted
        gallery_raw = request.form.get('gallery_urls', '')
        for order, url in enumerate(_safe_image_urls(gallery_raw)):
            db.session.add(HotelImage(hotel_id=hotel.id, image_url=url, sort_order=order))
        db.session.commit()
        log_audit('HOTEL_CREATE', target_type='HOTEL', target_id=hotel.id,
                  target_label=f'{name}, {hotel.city}',
                  detail=dict(price_per_night=hotel.price_per_night, rating=hotel.rating))
        flash(f'Hotel "{name}" added!', 'success')
        return redirect(url_for('admin_ext.hotels'))
    return render_template('admin_hotel_form.html', user=user, hotel=None)


@admin_ext_bp.route('/hotels/<int:hotel_id>/edit', methods=['GET', 'POST'])
@roles_required('admin')
def edit_hotel(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    user = get_current_user()
    if request.method == 'POST':
        hotel.name = request.form.get('name', hotel.name)
        hotel.city = request.form.get('city', hotel.city)
        hotel.rating = float(request.form.get('rating', hotel.rating))
        hotel.price_per_night = float(request.form.get('price_per_night', hotel.price_per_night))
        hotel.description = request.form.get('description', '')
        hotel.image_path = request.form.get('image_path', '')
        amenities_raw = request.form.get('amenities', '')
        hotel.amenities = [a.strip() for a in amenities_raw.split(',') if a.strip()]
        # Replace gallery images — only http/https URLs accepted
        gallery_raw = request.form.get('gallery_urls', '')
        HotelImage.query.filter_by(hotel_id=hotel.id).delete()
        for order, url in enumerate(_safe_image_urls(gallery_raw)):
            db.session.add(HotelImage(hotel_id=hotel.id, image_url=url, sort_order=order))
        db.session.commit()
        log_audit('HOTEL_EDIT', target_type='HOTEL', target_id=hotel_id,
                  target_label=f'{hotel.name}, {hotel.city}')
        flash('Hotel updated!', 'success')
        return redirect(url_for('admin_ext.hotels'))
    return render_template('admin_hotel_form.html', user=user, hotel=hotel)


@admin_ext_bp.route('/hotels/<int:hotel_id>/delete', methods=['POST'])
@roles_required('admin')
def delete_hotel(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    if hotel.booking_items:
        flash('Cannot delete hotel with existing bookings.', 'danger')
        return redirect(url_for('admin_ext.hotels'))
    label = f'{hotel.name}, {hotel.city}'
    db.session.delete(hotel)
    db.session.commit()
    log_audit('HOTEL_DELETE', target_type='HOTEL', target_id=hotel_id, target_label=label)
    flash('Hotel deleted.', 'success')
    return redirect(url_for('admin_ext.hotels'))


# ---- Activity Management ----------------------------------------------------

@admin_ext_bp.route('/activities')
@roles_required('admin')
def activities():
    user = get_current_user()
    page = request.args.get('page', 1, type=int)
    acts = Activity.query.order_by(Activity.id.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin_activities.html', user=user, activities=acts)


@admin_ext_bp.route('/activities/new', methods=['GET', 'POST'])
@roles_required('admin')
def new_activity():
    user = get_current_user()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        city = request.form.get('city', '').strip()
        if not name or not city:
            flash('Name and city are required.', 'danger')
            return redirect(url_for('admin_ext.new_activity'))
        act = Activity(
            name=name, city=city,
            category=request.form.get('category', 'Sightseeing'),
            description=request.form.get('description', ''),
            duration_hours=float(request.form.get('duration_hours', 3)),
            price_per_person=float(request.form.get('price_per_person', 999)),
            original_price=float(request.form.get('original_price')) if request.form.get('original_price') else None,
            max_persons=int(request.form.get('max_persons', 20)),
            min_persons=int(request.form.get('min_persons', 1)),
            rating=float(request.form.get('rating', 4.5)),
            active=bool(request.form.get('active', True)),
        )
        includes_raw = request.form.get('includes', '')
        act.includes = [i.strip() for i in includes_raw.split('\n') if i.strip()]
        db.session.add(act)
        db.session.commit()
        flash(f'Activity "{name}" added!', 'success')
        return redirect(url_for('admin_ext.activities'))
    categories = ['Adventure', 'Cultural', 'Food', 'Wellness', 'Sightseeing', 'Water Sports', 'Wildlife']
    return render_template('admin_activity_form.html', user=user, activity=None, categories=categories)


@admin_ext_bp.route('/activities/<int:act_id>/edit', methods=['GET', 'POST'])
@roles_required('admin')
def edit_activity(act_id):
    act = Activity.query.get_or_404(act_id)
    user = get_current_user()
    if request.method == 'POST':
        act.name = request.form.get('name', act.name)
        act.city = request.form.get('city', act.city)
        act.category = request.form.get('category', act.category)
        act.description = request.form.get('description', '')
        act.duration_hours = float(request.form.get('duration_hours', act.duration_hours))
        act.price_per_person = float(request.form.get('price_per_person', act.price_per_person))
        act.original_price = float(request.form.get('original_price')) if request.form.get('original_price') else None
        act.max_persons = int(request.form.get('max_persons', act.max_persons))
        act.min_persons = int(request.form.get('min_persons', act.min_persons))
        act.rating = float(request.form.get('rating', act.rating))
        act.active = bool(request.form.get('active'))
        includes_raw = request.form.get('includes', '')
        act.includes = [i.strip() for i in includes_raw.split('\n') if i.strip()]
        db.session.commit()
        flash('Activity updated!', 'success')
        return redirect(url_for('admin_ext.activities'))
    categories = ['Adventure', 'Cultural', 'Food', 'Wellness', 'Sightseeing', 'Water Sports', 'Wildlife']
    return render_template('admin_activity_form.html', user=user, activity=act, categories=categories)


@admin_ext_bp.route('/activities/<int:act_id>/delete', methods=['POST'])
@roles_required('admin')
def delete_activity(act_id):
    act = Activity.query.get_or_404(act_id)
    act.active = False
    db.session.commit()
    flash('Activity deactivated.', 'success')
    return redirect(url_for('admin_ext.activities'))


# ---- Revenue Dashboard ------------------------------------------------------

@admin_ext_bp.route('/revenue')
@roles_required('admin')
def revenue():
    user = get_current_user()
    # Total revenue
    total_revenue = db.session.query(db.func.sum(Booking.total_amount))\
        .filter_by(status='CONFIRMED').scalar() or 0
    # Monthly revenue (last 6 months)
    monthly = []
    for i in range(5, -1, -1):
        d = datetime.utcnow().replace(day=1) - timedelta(days=i * 30)
        month_start = d.replace(day=1, hour=0, minute=0, second=0)
        if i == 0:
            month_end = datetime.utcnow()
        else:
            next_m = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            month_end = next_m - timedelta(seconds=1)
        rev = db.session.query(db.func.sum(Booking.total_amount)).filter(
            Booking.status == 'CONFIRMED',
            Booking.created_at >= month_start,
            Booking.created_at <= month_end,
        ).scalar() or 0
        monthly.append({'month': month_start.strftime('%b %Y'), 'revenue': round(rev, 2)})

    # Bookings by type
    type_counts = db.session.query(BookingItem.type, db.func.count(BookingItem.id))\
        .group_by(BookingItem.type).all()
    type_data = {t: c for t, c in type_counts}

    # Top booked hotels
    top_hotels = db.session.query(Hotel.name, db.func.count(BookingItem.id).label('cnt'))\
        .join(BookingItem, BookingItem.hotel_id == Hotel.id)\
        .group_by(Hotel.id).order_by(db.text('cnt DESC')).limit(5).all()

    # Recent revenue bookings
    recent = Booking.query.filter_by(status='CONFIRMED')\
        .order_by(Booking.created_at.desc()).limit(10).all()

    total_users = User.query.count()
    total_bookings = Booking.query.count()
    confirmed = Booking.query.filter_by(status='CONFIRMED').count()
    cancelled = Booking.query.filter(Booking.status.in_(['CANCELLED', 'CANCELLATION_REQUESTED'])).count()

    return render_template('admin_revenue.html', user=user,
                           total_revenue=total_revenue, monthly=monthly,
                           type_data=type_data, top_hotels=top_hotels,
                           recent=recent, total_users=total_users,
                           total_bookings=total_bookings, confirmed=confirmed,
                           cancelled=cancelled)


# ---- User Management --------------------------------------------------------

@admin_ext_bp.route('/users')
@roles_required('admin')
def users():
    user = get_current_user()
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    query = User.query
    if q:
        query = query.filter(User.email.ilike(f'%{q}%'))
    users_paged = query.order_by(User.created_at.desc()).paginate(page=page, per_page=25, error_out=False)
    return render_template('admin_users.html', user=user, users=users_paged, q=q)


@admin_ext_bp.route('/users/<int:uid>/toggle-status', methods=['POST'])
@roles_required('admin')
def toggle_user_status(uid):
    target = User.query.get_or_404(uid)
    if target.id == session.get('user_id'):
        flash('You cannot disable your own account.', 'danger')
        return redirect(url_for('admin_ext.users'))
    prev_role = target.role
    target.role = 'disabled' if target.role == 'user' else 'user'
    db.session.commit()
    action = 'USER_DISABLE' if target.role == 'disabled' else 'USER_ENABLE'
    log_audit(action, target_type='USER', target_id=uid,
              target_label=target.email,
              detail=dict(from_role=prev_role, to_role=target.role))
    flash(f'User {target.email} {"disabled" if target.role == "disabled" else "re-enabled"}.', 'success')
    return redirect(url_for('admin_ext.users'))


@admin_ext_bp.route('/users/<int:uid>/verify-email', methods=['POST'])
@roles_required('admin')
def verify_user_email(uid):
    """Admin can manually mark a user's email as verified."""
    target = User.query.get_or_404(uid)
    if target.email_confirmed:
        flash(f'{target.email} is already verified.', 'info')
        return redirect(url_for('admin_ext.users'))
    target.email_confirmed = True
    target.confirmation_token = None
    db.session.commit()
    log_audit('USER_EMAIL_VERIFIED', target_type='USER', target_id=uid,
              target_label=target.email,
              detail=dict(method='admin_manual'))
    flash(f'Email verified for {target.email}.', 'success')
    return redirect(url_for('admin_ext.users'))


# ---- Refund / Cancellation Processing ---------------------------------------

@admin_ext_bp.route('/refunds')
@roles_required('admin')
def refunds():
    user = get_current_user()
    pending = Booking.query.filter_by(status='CANCELLATION_REQUESTED')\
        .order_by(Booking.created_at.desc()).all()
    processed = Booking.query.filter(Booking.status.in_(['CANCELLED', 'REFUNDED']))\
        .order_by(Booking.created_at.desc()).limit(20).all()
    auto_approve = SiteConfig.get('refund_auto_approve', 'false') == 'true'
    return render_template('admin_refunds.html', user=user,
                           pending=pending, processed=processed,
                           auto_approve=auto_approve)


@admin_ext_bp.route('/refunds/toggle-auto-approve', methods=['POST'])
@roles_required('admin')
def toggle_auto_approve():
    current = SiteConfig.get('refund_auto_approve', 'false')
    new_val = 'false' if current == 'true' else 'true'
    SiteConfig.set('refund_auto_approve', new_val)
    log_audit('REFUND_AUTO_APPROVE_TOGGLE', target_type='SETTING',
              target_id=None, target_label='refund_auto_approve',
              detail=dict(previous=current, new=new_val))
    state = 'enabled' if new_val == 'true' else 'disabled'
    flash(f'Auto-approve refunds has been {state}.', 'success')
    return redirect(url_for('admin_ext.refunds'))


@admin_ext_bp.route('/refunds/<int:booking_id>/approve', methods=['POST'])
@roles_required('admin')
def approve_refund(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = 'REFUNDED'
    notif = Notification(
        user_id=booking.user_id, type='CANCELLATION',
        title='Refund Processed!',
        message=f'Your refund of ₹{booking.total_amount:,.0f} for booking {booking.booking_code} has been processed.',
        link=url_for('public.my_bookings'),
    )
    db.session.add(notif)
    db.session.commit()
    log_audit('REFUND_APPROVE', target_type='BOOKING', target_id=booking_id,
              target_label=booking.booking_code,
              detail=dict(amount=booking.total_amount))
    flash(f'Refund approved for {booking.booking_code}.', 'success')
    return redirect(url_for('admin_ext.refunds'))


@admin_ext_bp.route('/refunds/<int:booking_id>/reject', methods=['POST'])
@roles_required('admin')
def reject_refund(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = 'CONFIRMED'
    notif = Notification(
        user_id=booking.user_id, type='CANCELLATION',
        title='Cancellation Request Rejected',
        message=f'Your cancellation request for {booking.booking_code} could not be processed. Please contact support.',
        link=url_for('public.my_bookings'),
    )
    db.session.add(notif)
    db.session.commit()
    log_audit('REFUND_REJECT', target_type='BOOKING', target_id=booking_id,
              target_label=booking.booking_code)
    flash(f'Refund request rejected for {booking.booking_code}.', 'warning')
    return redirect(url_for('admin_ext.refunds'))


# ---- Offers / Promo Management (Phase 4 link) --------------------------------

@admin_ext_bp.route('/blog')
@roles_required('admin')
def blog_list():
    user = get_current_user()
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin_blog.html', user=user, posts=posts)
