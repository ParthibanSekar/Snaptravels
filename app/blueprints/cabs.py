"""
Cabs / Airport Transfers blueprint.
Search cabs by pickup city, drop city, date/time, passengers.
"""
import logging
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, g
from app.models import Cab, Booking, BookingItem
from app.services.auth import login_required, get_current_user
from app.services.chaos import (
    maybe_fail_search, maybe_fail_db, maybe_fail_checkout, maybe_fail_payment,
    ChaosInjectedError, CheckoutChaosError, PaymentChaosError, DatabaseChaosError,
    should_empty_search,
)
from app import db
from datetime import datetime
import uuid

logger = logging.getLogger('snaptravels.cabs')

cabs_bp = Blueprint('cabs', __name__, url_prefix='/cabs')

# Approximate distances (km) between popular Indian cities
CITY_DISTANCES = {
    ('chennai', 'bangalore'): 346, ('bangalore', 'chennai'): 346,
    ('chennai', 'hyderabad'): 627, ('hyderabad', 'chennai'): 627,
    ('mumbai', 'pune'): 149,       ('pune', 'mumbai'): 149,
    ('delhi', 'agra'): 233,        ('agra', 'delhi'): 233,
    ('delhi', 'jaipur'): 281,      ('jaipur', 'delhi'): 281,
    ('mumbai', 'goa'): 594,        ('goa', 'mumbai'): 594,
    ('bangalore', 'mysore'): 143,  ('mysore', 'bangalore'): 143,
    ('hyderabad', 'bangalore'): 570, ('bangalore', 'hyderabad'): 570,
    ('delhi', 'chandigarh'): 243,  ('chandigarh', 'delhi'): 243,
    ('kolkata', 'darjeeling'): 595, ('darjeeling', 'kolkata'): 595,
    ('mumbai', 'nashik'): 168,     ('nashik', 'mumbai'): 168,
    ('delhi', 'haridwar'): 225,    ('haridwar', 'delhi'): 225,
    ('chennai', 'pondicherry'): 150, ('pondicherry', 'chennai'): 150,
    ('chennai', 'madurai'): 461,   ('madurai', 'chennai'): 461,
    ('mumbai', 'shirdi'): 241,     ('shirdi', 'mumbai'): 241,
    ('bangalore', 'coorg'): 265,   ('coorg', 'bangalore'): 265,
    ('delhi', 'shimla'): 342,      ('shimla', 'delhi'): 342,
}

DEFAULT_DISTANCE_KM = 300


def get_distance(pickup, drop):
    """Return distance in km between two cities."""
    key = (pickup.lower().strip(), drop.lower().strip())
    return CITY_DISTANCES.get(key, DEFAULT_DISTANCE_KM)


@cabs_bp.route('/', methods=['GET', 'POST'])
def search():
    cabs = []
    search_performed = False
    search_error = None
    pickup = request.form.get('pickup', '').strip()
    drop = request.form.get('drop', '').strip()
    travel_date = request.form.get('travel_date', '')
    travel_time = request.form.get('travel_time', '10:00')
    passengers = int(request.form.get('passengers', 1))

    if request.method == 'POST' and pickup and drop:
        search_performed = True
        try:
            maybe_fail_search('cab')
            maybe_fail_db('cab_search')
        except ChaosInjectedError as e:
            search_error = str(e)
            flash(str(e), 'danger')
            user = get_current_user()
            return render_template('cabs.html', cabs=[], search_performed=True,
                                   search_error=search_error,
                                   pickup=pickup, drop=drop, travel_date=travel_date,
                                   travel_time=travel_time, passengers=passengers, user=user)
        distance_km = get_distance(pickup, drop)
        # func_search_empty chaos: return empty cab list to simulate no availability
        if should_empty_search():
            logger.info("[CHAOS] func_search_empty active — returning empty cab results")
            cabs = []
        else:
            all_cabs = Cab.query.filter_by(available=True).order_by(Cab.base_fare.asc()).all()
            cabs = [
                {
                    'cab': c,
                    'estimated_fare': c.estimate_fare(distance_km),
                    'distance_km': distance_km,
                }
                for c in all_cabs
                if c.capacity >= passengers
            ]
        session['cab_search'] = {
            'pickup': pickup, 'drop': drop,
            'travel_date': travel_date, 'travel_time': travel_time,
            'passengers': passengers, 'distance_km': distance_km,
        }

    user = get_current_user()
    return render_template('cabs.html', cabs=cabs, search_performed=search_performed,
                           search_error=search_error,
                           pickup=pickup, drop=drop, travel_date=travel_date,
                           travel_time=travel_time, passengers=passengers, user=user)


@cabs_bp.route('/select/<int:cab_id>')
def select(cab_id):
    if 'user_id' not in session:
        flash('Please log in to book a cab.', 'warning')
        return redirect(url_for('auth.login'))
    cab = Cab.query.get_or_404(cab_id)
    session['selected_cab'] = cab_id
    return redirect(url_for('cabs.booking'))


@cabs_bp.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():
    cab_search = session.get('cab_search', {})
    cab_id = session.get('selected_cab')
    if not cab_id:
        flash('Please select a cab first.', 'warning')
        return redirect(url_for('cabs.search'))

    cab = Cab.query.get_or_404(cab_id)
    distance_km = cab_search.get('distance_km', DEFAULT_DISTANCE_KM)
    estimated_fare = cab.estimate_fare(distance_km)

    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        customer_email = request.form.get('customer_email', '').strip()
        customer_phone = request.form.get('customer_phone', '').strip()
        travel_date = request.form.get('travel_date', '').strip() or cab_search.get('travel_date')
        special_instructions = request.form.get('special_instructions', '').strip()
        payment_method = request.form.get('payment_method', 'card').strip() or 'card'

        if not customer_name or not customer_email:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('cabs.booking'))

        try:
            maybe_fail_db('cab_booking')
            maybe_fail_checkout(booking_type='CAB', amount=estimated_fare)
            maybe_fail_payment(amount=estimated_fare)
        except (CheckoutChaosError, PaymentChaosError, DatabaseChaosError) as ce:
            logger.exception(f"Chaos-induced cab booking failure: {ce}")
            from app.blueprints.public import _chaos_fail_ctx
            session['payment_fail'] = _chaos_fail_ctx(ce, url_for('cabs.booking'))
            return redirect(url_for('public.payment_failed'))

        booking_code = f"ST-CAB-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
        bk = Booking(
            user_id=session['user_id'],
            booking_code=booking_code,
            total_amount=estimated_fare,
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
            type='CAB',
            ref_id=cab.id,
            title=f"{cab.vehicle_type} — {cab_search.get('pickup', '')} → {cab_search.get('drop', '')}",
            amount=estimated_fare,
        )
        item.details = {
            'vehicle_type': cab.vehicle_type,
            'brand': cab.brand,
            'pickup': cab_search.get('pickup'),
            'drop': cab_search.get('drop'),
            'travel_date': cab_search.get('travel_date'),
            'travel_time': cab_search.get('travel_time'),
            'passengers': cab_search.get('passengers'),
            'distance_km': distance_km,
            'special_instructions': special_instructions,
        }
        db.session.add(item)
        db.session.commit()

        # Notify
        from app.models import Notification
        notif = Notification(
            user_id=session['user_id'], type='BOOKING',
            title='Cab Booking Confirmed!',
            message=f"Your cab from {cab_search.get('pickup')} to {cab_search.get('drop')} is booked. Code: {booking_code}",
            link=url_for('public.booking_confirmation', booking_id=bk.id),
        )
        db.session.add(notif)
        db.session.commit()

        for k in ['selected_cab', 'cab_search']:
            session.pop(k, None)

        return redirect(url_for('public.booking_confirmation', booking_id=bk.id))

    user = get_current_user()
    return render_template('cab_booking.html', cab=cab, cab_search=cab_search,
                           estimated_fare=estimated_fare, distance_km=distance_km, user=user)
