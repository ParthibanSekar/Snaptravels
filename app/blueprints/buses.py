"""
Bus booking blueprint.
Search intercity buses by origin, destination, date.
"""
import logging
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, g
from app.models import Bus, Booking, BookingItem, Notification
from app.services.auth import login_required, get_current_user
from app.services.chaos import (
    maybe_fail_search, maybe_fail_db, maybe_fail_checkout, maybe_fail_payment,
    ChaosInjectedError, CheckoutChaosError, PaymentChaosError, DatabaseChaosError,
    should_empty_search,
)
from app import db
from datetime import datetime
import uuid
from app.services.sanitize import sanitize_str, sanitize_booking_customer

logger = logging.getLogger('snaptravels.buses')

buses_bp = Blueprint('buses', __name__, url_prefix='/buses')


def search_buses(origin, destination, travel_date=None, bus_type=None, passengers=1):
    maybe_fail_search('bus')
    maybe_fail_db('bus_search')
    query = Bus.query.filter(
        Bus.origin.ilike(f'%{origin.lower()}%'),
        Bus.destination.ilike(f'%{destination.lower()}%'),
        Bus.seats_left >= passengers,
    )
    if bus_type and bus_type != 'ALL':
        query = query.filter(Bus.bus_type.ilike(f'%{bus_type}%'))

    buses = query.order_by(Bus.price.asc()).all()

    if should_empty_search():
        logger.info("[CHAOS] func_search_empty active — returning empty bus results")
        return []

    if not buses:
        logger.debug("No buses found for %r → %r — returning empty", origin, destination)

    return buses


@buses_bp.route('/', methods=['GET', 'POST'])
def search():
    search_performed = False
    search_error = None
    origin = request.form.get('origin', '').strip()
    destination = request.form.get('destination', '').strip()
    travel_date = request.form.get('travel_date', '')
    bus_type = request.form.get('bus_type', 'ALL')
    passengers = int(request.form.get('passengers', 1))

    if request.method == 'POST' and origin and destination:
        search_performed = True
        try:
            buses = search_buses(origin, destination, travel_date, bus_type, passengers)
        except ChaosInjectedError as e:
            search_error = str(e)
            flash(str(e), 'danger')
            buses = []
        except Exception as e:
            logger.error("Bus search failed: %s", e, exc_info=True)
            search_error = "Bus search failed due to an internal error. Please try again."
            flash(search_error, 'danger')
            buses = []
        session['bus_search'] = {
            'origin': origin, 'destination': destination,
            'travel_date': travel_date, 'bus_type': bus_type,
            'passengers': passengers,
        }
    else:
        # Default: show popular buses on page load
        buses = Bus.query.order_by(Bus.price.asc()).limit(12).all()

    user = get_current_user()
    return render_template('buses.html', buses=buses, search_performed=search_performed,
                           search_error=search_error,
                           origin=origin, destination=destination,
                           travel_date=travel_date, bus_type=bus_type,
                           passengers=passengers, user=user)


@buses_bp.route('/select/<int:bus_id>')
def select(bus_id):
    """Legacy entry point → redirect to seat selection."""
    if 'user_id' not in session:
        flash('Please log in to book a bus ticket.', 'warning')
        return redirect(url_for('auth.login'))
    Bus.query.get_or_404(bus_id)
    session['selected_bus'] = bus_id
    return redirect(url_for('buses.seat_select', bus_id=bus_id))


@buses_bp.route('/<int:bus_id>/seats', methods=['GET', 'POST'])
@login_required
def seat_select(bus_id):
    bus = Bus.query.get_or_404(bus_id)
    bus_search = session.get('bus_search', {})
    passengers = int(bus_search.get('passengers', 1))

    if request.method == 'POST':
        selected_seats = request.form.get('selected_seats', '').strip()
        if not selected_seats:
            flash('Please select your seat(s) before continuing.', 'warning')
            return redirect(url_for('buses.seat_select', bus_id=bus_id))
        session['selected_bus'] = bus_id
        session['selected_bus_seats'] = selected_seats
        return redirect(url_for('buses.booking'))

    user = get_current_user()
    return render_template('bus_seat_select.html', bus=bus,
                           passengers=passengers, user=user)


@buses_bp.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():
    bus_search = session.get('bus_search', {})
    bus_id = session.get('selected_bus')

    if not bus_id:
        flash('Please select a bus first.', 'warning')
        return redirect(url_for('buses.search'))

    bus = Bus.query.get_or_404(bus_id)
    passengers = int(bus_search.get('passengers', 1))
    base_fare = round(bus.price * passengers, 2)
    conv_fee = passengers * 30
    gst = round(base_fare * 0.05, 2)
    total = round(base_fare + conv_fee + gst, 2)
    selected_seats = session.get('selected_bus_seats', '')

    if request.method == 'POST':
        _raw = {
            'customer_name':  request.form.get('customer_name', ''),
            'customer_email': request.form.get('customer_email', ''),
            'customer_phone': request.form.get('customer_phone', ''),
        }
        _clean, _errs = sanitize_booking_customer(_raw, phone_required=False)
        if _errs:
            flash('Invalid input: ' + '; '.join(_errs.values()), 'danger')
            return redirect(request.referrer or url_for('buses.buses_home'))
        customer_name  = _clean['customer_name']
        customer_email = _clean['customer_email']
        customer_phone = _clean.get('customer_phone', '')
        travel_date = request.form.get('travel_date', '').strip() or bus_search.get('travel_date')

        payment_method = request.form.get('payment_method', 'card').strip() or 'card'

        if not customer_name or not customer_email:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('buses.booking'))

        try:
            maybe_fail_db('bus_booking')
            maybe_fail_checkout(booking_type='BUS', amount=total)
            maybe_fail_payment(amount=total)
        except (CheckoutChaosError, PaymentChaosError, DatabaseChaosError) as ce:
            logger.exception(f"Chaos-induced bus booking failure: {ce}")
            from app.blueprints.public import _chaos_fail_ctx
            session['payment_fail'] = _chaos_fail_ctx(ce, url_for('buses.booking'))
            return redirect(url_for('public.payment_failed'))

        booking_code = f"ST-BUS-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
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
            type='BUS',
            ref_id=bus.id,
            title=f"{bus.operator} — {bus.origin} → {bus.destination} ({bus.bus_type})",
            amount=total,
        )
        item.details = {
            'operator': bus.operator,
            'bus_no': bus.bus_no,
            'origin': bus.origin,
            'destination': bus.destination,
            'depart_time': bus.depart_time,
            'arrive_time': bus.arrive_time,
            'bus_type': bus.bus_type,
            'passengers': passengers,
            'travel_date': travel_date,
            'price_per_seat': bus.price,
            'selected_seats': selected_seats,
        }
        db.session.add(item)

        notif = Notification(
            user_id=session['user_id'], type='BOOKING',
            title='Bus Ticket Confirmed!',
            message=f"{bus.operator} from {bus.origin} to {bus.destination}. Code: {booking_code}",
            link=url_for('public.booking_confirmation', booking_id=bk.id),
        )
        db.session.add(notif)
        db.session.commit()

        # Decrement seats
        bus.seats_left = max(0, bus.seats_left - passengers)
        db.session.commit()

        for k in ['selected_bus', 'bus_search', 'selected_bus_seats']:
            session.pop(k, None)

        return redirect(url_for('public.booking_confirmation', booking_id=bk.id))

    user = get_current_user()
    return render_template('bus_booking.html', bus=bus, bus_search=bus_search,
                           passengers=passengers, total=total, user=user,
                           selected_seats=selected_seats)
