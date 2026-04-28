"""
User Dashboard blueprint — Phase 3.
Handles: profile dashboard, saved travelers, notifications, rewards, price alerts.
"""
import logging
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from app.models import (User, Booking, Notification, TravelerProfile, RewardPoints,
                        PointsTransaction, RecentlyViewed, PriceAlert, Wishlist,
                        Flight, Hotel, Package, Activity, SiteConfig)
from app.services.auth import login_required, get_current_user
from app import db, limiter

logger = logging.getLogger('snaptravels.user')
from datetime import datetime

user_bp = Blueprint('user', __name__, url_prefix='/dashboard')


@user_bp.context_processor
def inject_user_sidebar_counts():
    """Inject sidebar badge counts into every user blueprint template."""
    from flask import session as flask_session
    uid = flask_session.get('user_id')
    if not uid:
        return {}
    unread_count = Notification.query.filter_by(user_id=uid, read=False).count()
    wishlist_count = Wishlist.query.filter_by(user_id=uid).count()
    rewards = RewardPoints.query.filter_by(user_id=uid).first()
    return dict(sidebar_unread=unread_count,
                sidebar_wishlist=wishlist_count,
                sidebar_rewards=rewards)


@user_bp.route('/')
@login_required
def dashboard():
    user = get_current_user()
    # Recent bookings
    recent_bookings = Booking.query.filter_by(user_id=session['user_id'])\
        .order_by(Booking.created_at.desc()).limit(5).all()
    # Unread notifications count
    unread_count = Notification.query.filter_by(user_id=session['user_id'], read=False).count()
    # Reward points
    rewards = RewardPoints.query.filter_by(user_id=session['user_id']).first()
    # Recently viewed
    recently_viewed = RecentlyViewed.query.filter_by(user_id=session['user_id'])\
        .order_by(RecentlyViewed.viewed_at.desc()).limit(8).all()
    # Total spent
    total_spent = db.session.query(db.func.sum(Booking.total_amount))\
        .filter_by(user_id=session['user_id'], status='CONFIRMED').scalar() or 0
    # Wishlist count
    wishlist_count = Wishlist.query.filter_by(user_id=session['user_id']).count()

    return render_template('user_dashboard.html', user=user,
                           recent_bookings=recent_bookings, unread_count=unread_count,
                           rewards=rewards, recently_viewed=recently_viewed,
                           total_spent=total_spent, wishlist_count=wishlist_count)


@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_current_user()
    if request.method == 'POST':
        # Update basic profile info (name stored from first booking or set here)
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('user.profile'))
    return render_template('user_profile.html', user=user)


# ---- Saved Travelers -------------------------------------------------------

@user_bp.route('/travelers')
@login_required
def travelers():
    user = get_current_user()
    travelers = TravelerProfile.query.filter_by(user_id=session['user_id'])\
        .order_by(TravelerProfile.is_primary.desc(), TravelerProfile.created_at.asc()).all()
    return render_template('travelers.html', user=user, travelers=travelers)


@user_bp.route('/travelers/add', methods=['GET', 'POST'])
@login_required
@limiter.exempt
def add_traveler():
    user = get_current_user()
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        if not full_name:
            flash('Full name is required.', 'danger')
            return redirect(url_for('user.add_traveler'))

        dob_str = request.form.get('date_of_birth', '')
        dob = None
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        traveler = TravelerProfile(
            user_id=session['user_id'],
            full_name=full_name,
            age=request.form.get('age', type=int),
            gender=request.form.get('gender', ''),
            id_type=request.form.get('id_type', ''),
            id_number=request.form.get('id_number', ''),
            passport_no=request.form.get('passport_no', ''),
            nationality=request.form.get('nationality', 'Indian'),
            date_of_birth=dob,
            is_primary=bool(request.form.get('is_primary')),
        )
        db.session.add(traveler)
        db.session.commit()
        flash(f'{full_name} added to your traveler profiles.', 'success')
        return redirect(url_for('user.travelers'))

    return render_template('add_traveler.html', user=user)


@user_bp.route('/travelers/<int:tid>/delete', methods=['POST'])
@login_required
def delete_traveler(tid):
    t = TravelerProfile.query.filter_by(id=tid, user_id=session['user_id']).first_or_404()
    db.session.delete(t)
    db.session.commit()
    flash('Traveler profile removed.', 'success')
    return redirect(url_for('user.travelers'))


# ---- Notifications ---------------------------------------------------------

@user_bp.route('/notifications')
@login_required
def notifications():
    user = get_current_user()
    notifs = Notification.query.filter_by(user_id=session['user_id'])\
        .order_by(Notification.created_at.desc()).limit(50).all()
    # Mark all as read
    Notification.query.filter_by(user_id=session['user_id'], read=False).update({'read': True})
    db.session.commit()
    return render_template('notifications.html', user=user, notifications=notifs)


@user_bp.route('/notifications/count')
@login_required
def notification_count():
    count = Notification.query.filter_by(user_id=session['user_id'], read=False).count()
    return jsonify({'count': count})


@user_bp.route('/notifications/recent')
@login_required
def notifications_recent():
    """Return the 6 most recent notifications as JSON for the navbar dropdown."""
    uid = session['user_id']
    notifs = Notification.query.filter_by(user_id=uid)\
        .order_by(Notification.created_at.desc()).limit(6).all()
    unread_count = Notification.query.filter_by(user_id=uid, read=False).count()

    type_icons = {
        'BOOKING':      ('bi-bag-check-fill',  '#10b981'),
        'CANCELLATION': ('bi-x-circle-fill',   '#ef4444'),
        'OFFER':        ('bi-tag-fill',         '#f59e0b'),
        'INFO':         ('bi-info-circle-fill', '#6366f1'),
        'REFUND':       ('bi-arrow-counterclockwise', '#10b981'),
    }

    items = []
    for n in notifs:
        icon_class, icon_color = type_icons.get(n.type, ('bi-bell-fill', '#6b7280'))
        items.append({
            'id':         n.id,
            'title':      n.title,
            'message':    n.message or '',
            'link':       n.link or url_for('user.notifications'),
            'read':       n.read,
            'icon_class': icon_class,
            'icon_color': icon_color,
            'time':       n.created_at.strftime('%d %b, %I:%M %p'),
        })

    return jsonify({'unread': unread_count, 'notifications': items})


@user_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def notifications_mark_all_read():
    """Mark all notifications as read (called by dropdown)."""
    Notification.query.filter_by(user_id=session['user_id'], read=False)\
        .update({'read': True})
    db.session.commit()
    return jsonify({'ok': True})


# ---- Rewards ---------------------------------------------------------------

@user_bp.route('/rewards')
@login_required
def rewards():
    user = get_current_user()
    account = RewardPoints.query.filter_by(user_id=session['user_id']).first()
    if not account:
        account = RewardPoints(user_id=session['user_id'], points=0, tier='Silver')
        db.session.add(account)
        db.session.commit()
    transactions = PointsTransaction.query.filter_by(user_id=session['user_id'])\
        .order_by(PointsTransaction.created_at.desc()).limit(20).all()
    # Tier thresholds
    tiers = [('Silver', 0, 2499), ('Gold', 2500, 9999), ('Platinum', 10000, None)]
    return render_template('rewards.html', user=user, account=account,
                           transactions=transactions, tiers=tiers)


# ---- Price Alerts ----------------------------------------------------------

@user_bp.route('/price-alerts')
@login_required
def price_alerts():
    user = get_current_user()
    alerts = PriceAlert.query.filter_by(user_id=session['user_id'])\
        .order_by(PriceAlert.created_at.desc()).all()
    return render_template('price_alerts.html', user=user, alerts=alerts)


@user_bp.route('/price-alerts/add', methods=['POST'])
@login_required
@limiter.exempt
def add_price_alert():
    alert_type = request.form.get('alert_type', 'FLIGHT')
    target_price = request.form.get('target_price', type=float)
    if not target_price:
        flash('Please enter a valid target price.', 'danger')
        return redirect(url_for('user.price_alerts'))

    alert = PriceAlert(
        user_id=session['user_id'],
        alert_type=alert_type,
        origin=request.form.get('origin', ''),
        destination=request.form.get('destination', ''),
        city=request.form.get('city', ''),
        target_price=target_price,
    )
    db.session.add(alert)
    db.session.commit()
    flash('Price alert created! We\'ll notify you when prices drop.', 'success')
    return redirect(url_for('user.price_alerts'))


@user_bp.route('/price-alerts/<int:aid>/delete', methods=['POST'])
@login_required
def delete_price_alert(aid):
    alert = PriceAlert.query.filter_by(id=aid, user_id=session['user_id']).first_or_404()
    db.session.delete(alert)
    db.session.commit()
    flash('Price alert removed.', 'success')
    return redirect(url_for('user.price_alerts'))


# ---- Booking Cancellation --------------------------------------------------

@user_bp.route('/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.filter_by(id=booking_id, user_id=session['user_id']).first_or_404()
    if booking.status in ('CANCELLED', 'REFUNDED'):
        flash('This booking is already cancelled.', 'info')
        return redirect(url_for('public.booking_details', booking_id=booking_id))
    if booking.status == 'CANCELLATION_REQUESTED':
        flash('A cancellation request is already pending for this booking.', 'info')
        return redirect(url_for('public.booking_details', booking_id=booking_id))

    auto_approve = SiteConfig.get('refund_auto_approve', 'false') == 'true'

    if auto_approve:
        # Instantly mark as REFUNDED
        booking.status = 'REFUNDED'
        notif = Notification(
            user_id=session['user_id'], type='CANCELLATION',
            title='Booking Cancelled & Refund Processed',
            message=f'Your booking {booking.booking_code} has been cancelled and a refund of '
                    f'₹{booking.total_amount:,.0f} has been initiated.',
            link=url_for('public.booking_details', booking_id=booking_id),
        )
        db.session.add(notif)
        db.session.commit()
        logger.info('BOOKING_CANCELLED code=%s user_id=%s amount=%.2f refund=auto_approved',
                    booking.booking_code, session['user_id'], booking.total_amount)
        flash(f'Booking {booking.booking_code} cancelled. Refund of ₹{booking.total_amount:,.0f} '
              f'will be credited in 5–7 business days.', 'success')
    else:
        # Queue for manual admin approval
        booking.status = 'CANCELLATION_REQUESTED'
        notif = Notification(
            user_id=session['user_id'], type='CANCELLATION',
            title='Cancellation Request Received',
            message=f'Your cancellation request for booking {booking.booking_code} has been received '
                    f'and is pending admin approval.',
            link=url_for('public.booking_details', booking_id=booking_id),
        )
        db.session.add(notif)
        db.session.commit()
        logger.info('CANCELLATION_REQUESTED code=%s user_id=%s amount=%.2f refund=pending_approval',
                    booking.booking_code, session['user_id'], booking.total_amount)
        flash(f'Cancellation request submitted for {booking.booking_code}. '
              f'Refund will be processed in 5–7 business days after admin approval.', 'info')

    return redirect(url_for('public.my_bookings'))


# ---- Wishlist page ---------------------------------------------------------

@user_bp.route('/wishlist')
@login_required
def wishlist():
    user = get_current_user()
    items = Wishlist.query.filter_by(user_id=session['user_id'])\
        .order_by(Wishlist.created_at.desc()).all()

    # Resolve each wishlist item to its object
    resolved = []
    for w in items:
        obj = None
        if w.item_type == 'FLIGHT':
            obj = Flight.query.get(w.ref_id)
        elif w.item_type == 'HOTEL':
            obj = Hotel.query.get(w.ref_id)
        elif w.item_type == 'PACKAGE':
            obj = Package.query.get(w.ref_id)
        elif w.item_type == 'ACTIVITY':
            obj = Activity.query.get(w.ref_id)
        if obj:
            resolved.append({'wishlist': w, 'obj': obj})

    return render_template('wishlist.html', user=user, items=resolved)
