"""
Trains blueprint.
Search & book Indian Railways train routes with class-wise pricing.
"""
import logging
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, g
from app.models import Train, Booking, BookingItem, Notification
from app.services.auth import login_required, get_current_user
from app.services.chaos import (
    maybe_fail_search, maybe_fail_db, maybe_fail_checkout, maybe_fail_payment,
    ChaosInjectedError, CheckoutChaosError, PaymentChaosError, DatabaseChaosError,
    should_empty_search,
)
from app import db
from datetime import datetime, date
import uuid

logger = logging.getLogger('snaptravels.trains')

trains_bp = Blueprint('trains', __name__, url_prefix='/trains')

CLASSES = {
    'SL':  ('Sleeper',   'sleeper_fare',     'sleeper_seats'),
    '3AC': ('Third AC',  'third_ac_fare',    'third_ac_seats'),
    '2AC': ('Second AC', 'second_ac_fare',   'second_ac_seats'),
    '1AC': ('First AC',  'first_ac_fare',    'first_ac_seats'),
}


def _normalize(city):
    return city.lower().strip()


def search_trains(origin, destination, travel_date=None, travel_class='SL', passengers=1):
    maybe_fail_search('train')
    maybe_fail_db('train_search')
    origin_n = _normalize(origin)
    dest_n = _normalize(destination)

    query = Train.query.filter(
        Train.origin.ilike(f'%{origin_n}%'),
        Train.destination.ilike(f'%{dest_n}%'),
    )
    trains = query.all()

    # Filter by class availability and passengers
    results = []
    fare_field = CLASSES.get(travel_class, CLASSES['SL'])[1]
    seat_field = CLASSES.get(travel_class, CLASSES['SL'])[2]

    for t in trains:
        fare = getattr(t, fare_field, None)
        seats = getattr(t, seat_field, 0)
        if fare and seats >= passengers:
            results.append({
                'train': t,
                'fare': fare,
                'total_fare': round(fare * passengers, 2),
                'seats': seats,
                'class_name': CLASSES[travel_class][0],
                'class_code': travel_class,
            })

    if should_empty_search():
        logger.info("[CHAOS] func_search_empty active — returning empty train results")
        return []

    if not results:
        logger.debug("No trains found for %r → %r — returning empty", origin_n, dest_n)

    return results


@trains_bp.route('/', methods=['GET', 'POST'])
def search():
    search_performed = False
    search_error = None
    origin = request.form.get('origin', '').strip()
    destination = request.form.get('destination', '').strip()
    travel_date = request.form.get('travel_date', '')
    travel_class = request.form.get('travel_class', 'SL')
    passengers = int(request.form.get('passengers', 1))

    if request.method == 'POST' and origin and destination:
        search_performed = True
        try:
            results = search_trains(origin, destination, travel_date, travel_class, passengers)
        except ChaosInjectedError as e:
            search_error = str(e)
            flash(str(e), 'danger')
            results = []
        except Exception as e:
            logger.error("Train search failed: %s", e, exc_info=True)
            search_error = "Train search failed due to an internal error. Please try again."
            flash(search_error, 'danger')
            results = []
        session['train_search'] = {
            'origin': origin, 'destination': destination,
            'travel_date': travel_date, 'travel_class': travel_class,
            'passengers': passengers,
        }
    else:
        # Default: show popular trains on page load
        fare_field = CLASSES.get(travel_class, CLASSES['SL'])[1]
        seat_field = CLASSES.get(travel_class, CLASSES['SL'])[2]
        default_trains = Train.query.order_by(Train.id.asc()).limit(12).all()
        results = []
        for t in default_trains:
            fare = getattr(t, fare_field, None)
            if fare:
                results.append({
                    'train': t,
                    'fare': fare,
                    'total_fare': round(fare * passengers, 2),
                    'seats': getattr(t, seat_field, 0),
                    'class_name': CLASSES[travel_class][0],
                    'class_code': travel_class,
                })

    user = get_current_user()
    return render_template('trains.html', results=results, search_performed=search_performed,
                           search_error=search_error,
                           origin=origin, destination=destination, travel_date=travel_date,
                           travel_class=travel_class, passengers=passengers,
                           classes=CLASSES, user=user)


@trains_bp.route('/select/<int:train_id>/<travel_class>')
def select(train_id, travel_class):
    if 'user_id' not in session:
        flash('Please log in to book a train ticket.', 'warning')
        return redirect(url_for('auth.login'))
    Train.query.get_or_404(train_id)
    session['selected_train'] = train_id
    session['selected_train_class'] = travel_class
    return redirect(url_for('trains.booking'))


@trains_bp.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():
    train_search = session.get('train_search', {})
    train_id = session.get('selected_train')
    travel_class = session.get('selected_train_class', 'SL')

    if not train_id:
        flash('Please select a train first.', 'warning')
        return redirect(url_for('trains.search'))

    train = Train.query.get_or_404(train_id)
    passengers = int(train_search.get('passengers', 1))
    fare_field = CLASSES.get(travel_class, CLASSES['SL'])[1]
    class_name = CLASSES.get(travel_class, CLASSES['SL'])[0]
    per_ticket = getattr(train, fare_field) or 0
    base_fare = round(per_ticket * passengers, 2)
    reservation_charge = passengers * 40
    gst = round(base_fare * 0.05, 2)
    total = round(base_fare + reservation_charge + gst, 2)

    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        customer_email = request.form.get('customer_email', '').strip()
        customer_phone = request.form.get('customer_phone', '').strip()
        travel_date = request.form.get('travel_date', '').strip() or train_search.get('travel_date')

        payment_method = request.form.get('payment_method', 'card').strip() or 'card'

        if not customer_name or not customer_email:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('trains.booking'))

        try:
            maybe_fail_db('train_booking')
            maybe_fail_checkout(booking_type='TRAIN', amount=total)
            maybe_fail_payment(amount=total)
        except (CheckoutChaosError, PaymentChaosError, DatabaseChaosError) as ce:
            logger.exception(f"Chaos-induced train booking failure: {ce}")
            from app.blueprints.public import _chaos_fail_ctx
            session['payment_fail'] = _chaos_fail_ctx(ce, url_for('trains.booking'))
            return redirect(url_for('public.payment_failed'))

        booking_code = f"ST-TRN-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
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
            type='TRAIN',
            ref_id=train.id,
            title=f"{train.train_name} ({train.train_no}) — {class_name}",
            amount=total,
        )
        item.details = {
            'train_no': train.train_no,
            'train_name': train.train_name,
            'origin': train.origin,
            'destination': train.destination,
            'depart_time': train.depart_time,
            'arrive_time': train.arrive_time,
            'travel_class': travel_class,
            'class_name': class_name,
            'passengers': passengers,
            'travel_date': travel_date,
            'fare_per_ticket': per_ticket,
        }
        db.session.add(item)

        notif = Notification(
            user_id=session['user_id'], type='BOOKING',
            title='Train Ticket Confirmed!',
            message=f"{train.train_name} from {train.origin} to {train.destination} — {class_name}. Code: {booking_code}",
            link=url_for('public.booking_confirmation', booking_id=bk.id),
        )
        db.session.add(notif)
        db.session.commit()

        for k in ['selected_train', 'selected_train_class', 'train_search']:
            session.pop(k, None)

        return redirect(url_for('public.booking_confirmation', booking_id=bk.id))

    user = get_current_user()
    return render_template('train_booking.html', train=train, train_search=train_search,
                           travel_class=travel_class, class_name=class_name,
                           passengers=passengers, per_ticket=per_ticket, total=total,
                           base_fare=base_fare, reservation_charge=reservation_charge,
                           gst=gst, user=user)
