from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, g
from app import db
from app.models import Flight, Hotel, Booking, BookingItem, Package, PromoCode
from app.forms import RoundTripSearchForm, HotelSearchForm, BookingForm
from app.services.search import SearchService
from app.services.booking import BookingService
from app.services.auth import login_required, get_current_user
from app.services.chaos import (
    ChaosInjectedError, CheckoutChaosError, PaymentChaosError,
    DatabaseChaosError, maybe_fail_checkout, maybe_fail_payment, maybe_fail_db,
)
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('snaptravels.public')

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def home():
    user = get_current_user()
    popular_destinations = SearchService.get_popular_destinations()
    featured_packages = Package.query.filter_by(active=True).order_by(Package.id.asc()).limit(3).all()
    promo_banner = PromoCode.query.filter_by(active=True).first()
    return render_template('home.html', user=user, destinations=popular_destinations,
                           featured_packages=featured_packages, promo_banner=promo_banner)

@public_bp.route('/flights', methods=['GET', 'POST'])
def flights():
    form = RoundTripSearchForm()
    flights = []
    search_performed = False
    search_error = None

    # Pre-fill destination from GET param (destination tiles on home page)
    if request.method == 'GET' and request.args.get('destination'):
        form.destination.data = request.args.get('destination')

    if form.validate_on_submit():
        search_performed = True
        # Search flights with debug info
        origin = form.origin.data.strip() if form.origin.data else None
        destination = form.destination.data.strip() if form.destination.data else None
        depart_date = form.depart_date.data
        cabin_class = form.cabin_class.data
        passengers = form.passengers.data if form.passengers.data else 1

        logger.debug("flights form: origin=%r destination=%r date=%s class=%s passengers=%s",
                     origin, destination, depart_date, cabin_class, passengers)

        try:
            flights = SearchService.search_flights(
                origin=origin,
                destination=destination,
                depart_date=depart_date,
                cabin_class=cabin_class,
                passengers=passengers
            )
        except ChaosInjectedError as e:
            search_error = str(e)
            flash(str(e), 'danger')
            flights = []
        except Exception as e:
            logger.error("Flight search failed: %s", e, exc_info=True)
            search_error = "Flight search failed due to an internal error. Please try again."
            flash(search_error, 'danger')
            flights = []

        logger.debug("flights search returned %d results", len(flights))

        # Store search params in session for booking
        session['flight_search'] = {
            'origin': form.origin.data,
            'destination': form.destination.data,
            'depart_date': form.depart_date.data.isoformat() if form.depart_date.data else None,
            'passengers': form.passengers.data,
            'cabin_class': form.cabin_class.data
        }
    else:
        # Show default flights when no search is performed
        flights = SearchService.get_default_flights()

    user = get_current_user()
    return render_template('flights.html', form=form, flights=flights,
                         search_performed=search_performed, search_error=search_error, user=user)

@public_bp.route('/hotels', methods=['GET', 'POST'])
def hotels():
    form = HotelSearchForm()
    hotels = []
    search_performed = False
    search_error = None

    if form.validate_on_submit():
        search_performed = True
        try:
            hotels = SearchService.search_hotels(
                city=form.city.data,
                checkin=form.checkin.data,
                checkout=form.checkout.data,
                guests=form.guests.data,
                rooms=form.rooms.data
            )
        except ChaosInjectedError as e:
            search_error = str(e)
            flash(str(e), 'danger')
            hotels = []
        except Exception as e:
            logger.error("Hotel search failed: %s", e, exc_info=True)
            search_error = "Hotel search failed due to an internal error. Please try again."
            flash(search_error, 'danger')
            hotels = []

        # Calculate nights
        if form.checkin.data and form.checkout.data:
            nights = (form.checkout.data - form.checkin.data).days
        else:
            nights = 1

        # Store search params in session for booking
        session['hotel_search'] = {
            'city': form.city.data,
            'checkin': form.checkin.data.isoformat() if form.checkin.data else None,
            'checkout': form.checkout.data.isoformat() if form.checkout.data else None,
            'guests': form.guests.data,
            'rooms': form.rooms.data,
            'nights': nights
        }
    else:
        # Show default hotels when no search is performed
        hotels = SearchService.get_default_hotels()

    user = get_current_user()
    return render_template('hotels.html', form=form, hotels=hotels,
                         search_performed=search_performed, search_error=search_error, user=user)

@public_bp.route('/select-flight/<int:flight_id>')
def select_flight(flight_id):
    """Legacy redirect → now goes to seat selection first."""
    if 'user_id' not in session:
        flash('Please log in to continue with booking.', 'warning')
        return redirect(url_for('auth.login', next=url_for('public.flight_seat_select', flight_id=flight_id)))
    return redirect(url_for('public.flight_seat_select', flight_id=flight_id))


@public_bp.route('/flights/<int:flight_id>/seats', methods=['GET', 'POST'])
def flight_seat_select(flight_id):
    if 'user_id' not in session:
        flash('Please log in to continue with booking.', 'warning')
        return redirect(url_for('auth.login', next=url_for('public.flight_seat_select', flight_id=flight_id)))

    flight = Flight.query.get_or_404(flight_id)
    flight_search = session.get('flight_search', {})
    passengers = int(flight_search.get('passengers', 1))

    if request.method == 'POST':
        selected_seats = request.form.get('selected_seats', '').strip()
        if not selected_seats:
            flash('Please select your seat(s) before continuing.', 'warning')
            return redirect(url_for('public.flight_seat_select', flight_id=flight_id))

        # Store selection and proceed to booking — clear any prior hotel selection
        session['selected_flight'] = flight_id
        session['selected_seats'] = selected_seats
        session.pop('selected_hotel', None)
        session.pop('selected_room_type', None)
        session.pop('selected_room_price', None)
        session.pop('selected_room_name', None)
        session.pop('hotel_search', None)
        return redirect(url_for('public.booking'))

    return render_template('flight_seat_select.html', flight=flight, passengers=passengers,
                           user=get_current_user())

@public_bp.route('/select-hotel/<int:hotel_id>')
def select_hotel(hotel_id):
    """Legacy → redirect to room selection."""
    if 'user_id' not in session:
        flash('Please log in to continue with booking.', 'warning')
        return redirect(url_for('auth.login', next=url_for('public.hotel_room_select', hotel_id=hotel_id)))
    return redirect(url_for('public.hotel_room_select', hotel_id=hotel_id))


@public_bp.route('/hotels/<int:hotel_id>/rooms', methods=['GET', 'POST'])
def hotel_room_select(hotel_id):
    if 'user_id' not in session:
        flash('Please log in to continue with booking.', 'warning')
        return redirect(url_for('auth.login', next=url_for('public.hotel_room_select', hotel_id=hotel_id)))

    hotel = Hotel.query.get_or_404(hotel_id)
    hotel_search = session.get('hotel_search', {})

    checkin = hotel_search.get('checkin', '')
    checkout = hotel_search.get('checkout', '')
    guests = hotel_search.get('guests', 1)
    rooms = hotel_search.get('rooms', 1)
    nights = hotel_search.get('nights', 1)

    if request.method == 'POST':
        room_type = request.form.get('room_type', '').strip()
        room_name = request.form.get('room_name', 'Standard Room')
        if not room_type:
            flash('Please select a room type before continuing.', 'warning')
            return redirect(url_for('public.hotel_room_select', hotel_id=hotel_id))

        # Server-side room price validation — recalculate from hotel base price
        valid_room_prices = {
            'standard': hotel.price_per_night,
            'dorm':     round(hotel.price_per_night * 0.35),
            'deluxe':   round(hotel.price_per_night * 1.6),
            'premium':  round(hotel.price_per_night * 2.8),
        }
        if room_type not in valid_room_prices:
            flash('Invalid room type selected.', 'danger')
            return redirect(url_for('public.hotel_room_select', hotel_id=hotel_id))
        room_price = valid_room_prices[room_type]
        # Clear any prior flight selection so booking page shows hotel, not flight
        session.pop('selected_flight', None)
        session.pop('selected_seats', None)
        session.pop('flight_search', None)
        session['selected_hotel'] = hotel_id
        session['selected_room_type'] = room_type
        session['selected_room_price'] = float(room_price)
        session['selected_room_name'] = room_name
        # Override hotel search price with selected room price
        hotel_search['nights'] = nights
        session['hotel_search'] = hotel_search
        return redirect(url_for('public.booking'))

    return render_template('hotel_room_select.html', hotel=hotel,
                           checkin=checkin, checkout=checkout,
                           guests=guests, rooms=rooms, nights=nights,
                           user=get_current_user())

@public_bp.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():
    form = BookingForm()

    # Get selected items
    selected_flight = None
    selected_hotel = None

    if 'selected_flight' in session:
        selected_flight = Flight.query.get(session['selected_flight'])

    if 'selected_hotel' in session:
        selected_hotel = Hotel.query.get(session['selected_hotel'])

    if not selected_flight and not selected_hotel:
        flash('No items selected for booking.', 'warning')
        return redirect(url_for('public.home'))

    # Calculate total amount
    total_amount = 0
    nights = 1

    if selected_flight:
        total_amount += selected_flight.price

    if selected_hotel:
        hotel_search = session.get('hotel_search', {})
        nights = hotel_search.get('nights', 1)
        rooms = hotel_search.get('rooms', 1)
        # Use selected room price if available, otherwise fall back to hotel default
        room_price = session.get('selected_room_price', selected_hotel.price_per_night)
        total_amount += float(room_price) * nights * int(rooms)

    if form.validate_on_submit():
        # Determine booking type and retry URL for error page
        booking_type = 'FLIGHT' if selected_flight else 'HOTEL'
        retry_url = url_for('public.booking')

        # ── Chaos injection point (before BookingService to show explicit errors) ──
        try:
            maybe_fail_db('booking_create')
            maybe_fail_checkout(booking_type=booking_type, amount=total_amount)
            maybe_fail_payment(amount=total_amount)
        except (DatabaseChaosError, CheckoutChaosError, PaymentChaosError) as ce:
            logger.exception(f"Chaos-induced {booking_type} booking failure: {ce}")
            ctx = _chaos_fail_ctx(ce, retry_url)
            session['payment_fail'] = ctx
            return redirect(url_for('public.payment_failed'))

        # Create booking
        customer_data = {
            'name': form.customer_name.data,
            'email': form.customer_email.data,
            'phone': form.customer_phone.data
        }

        # Add hotel-specific data if hotel is selected
        if selected_hotel:
            hotel_search = session.get('hotel_search', {})
            customer_data.update({
                'checkin': hotel_search.get('checkin'),
                'checkout': hotel_search.get('checkout'),
                'nights': nights,
                'rooms': hotel_search.get('rooms', 1),
                'room_type': session.get('selected_room_type', 'standard'),
                'room_name': session.get('selected_room_name', 'Standard Room'),
                'room_price': session.get('selected_room_price', selected_hotel.price_per_night),
            })

        # Add flight-specific data (seats) if flight is selected
        if selected_flight:
            customer_data['selected_seats'] = session.get('selected_seats', '')

        # Read selected payment method
        payment_method = request.form.get('payment_method', 'card').strip() or 'card'

        # Create booking for the selected item
        booking = None
        if selected_flight:
            booking = BookingService.create_booking(
                user_id=session['user_id'],
                booking_type='FLIGHT',
                item_id=selected_flight.id,
                customer_data=customer_data,
                amount=total_amount,
                payment_method=payment_method,
            )
        elif selected_hotel:
            booking = BookingService.create_booking(
                user_id=session['user_id'],
                booking_type='HOTEL',
                item_id=selected_hotel.id,
                customer_data=customer_data,
                amount=total_amount,
                payment_method=payment_method,
            )

        if not booking:
            flash('Booking failed due to an unexpected error. Please try again.', 'danger')
            return redirect(url_for('public.booking'))

        # Clear session data
        for key in ['selected_flight', 'selected_hotel', 'flight_search', 'hotel_search',
                    'selected_seats', 'selected_room_type', 'selected_room_price', 'selected_room_name']:
            session.pop(key, None)

        return redirect(url_for('public.booking_confirmation', booking_id=booking.id))

    user = get_current_user()
    selected_seats = session.get('selected_seats', '')
    selected_room_name = session.get('selected_room_name', '')
    return render_template('booking.html', form=form, flight=selected_flight,
                         hotel=selected_hotel, total_amount=total_amount,
                         nights=nights, user=user, selected_seats=selected_seats,
                         selected_room_name=selected_room_name)

@public_bp.route('/booking-confirmation/<int:booking_id>')
@login_required
def booking_confirmation(booking_id):
    booking = Booking.query.filter_by(id=booking_id, user_id=session['user_id']).first_or_404()
    user = get_current_user()
    return render_template('booking_confirmation.html', booking=booking, user=user)


# ── Frames / Frameset pages ────────────────────────────────────────────────
@public_bp.route('/travel-dashboard')
def travel_dashboard():
    """Multi-frame travel dashboard with SVG charts, iframes, and live data."""
    user = get_current_user()
    return render_template('travel_dashboard.html', user=user)

@public_bp.route('/travel-dashboard/stats-frame')
def stats_frame():
    """Stats frame content for the travel dashboard."""
    from app.models import Flight, Hotel, Booking
    stats = {
        'flights': Flight.query.count(),
        'hotels': Hotel.query.count(),
        'bookings': Booking.query.count(),
    }
    return render_template('frames/stats_frame.html', stats=stats)

@public_bp.route('/travel-dashboard/chart-frame')
def chart_frame():
    """SVG chart frame content."""
    from app.models import Booking
    from sqlalchemy import func
    # Get bookings by type
    data = {}
    for row in db.session.query(
        func.coalesce(BookingItem.type, 'OTHER'),
        func.count()
    ).group_by(BookingItem.type).all():
        data[row[0]] = row[1]
    return render_template('frames/chart_frame.html', data=data)

@public_bp.route('/travel-dashboard/map-frame')
def map_frame():
    """SVG map frame content."""
    return render_template('frames/map_frame.html')

@public_bp.route('/travel-dashboard/feed-frame')
def feed_frame():
    """Live feed frame content."""
    from app.models import Booking
    recent = Booking.query.order_by(Booking.created_at.desc()).limit(10).all()
    return render_template('frames/feed_frame.html', bookings=recent)


# ── Trip Planner (popup/new-window/SVG interaction flows) ─────────────────
@public_bp.route('/trip-planner')
def trip_planner():
    """Multi-step trip planner with popups, SVG interactions, and cross-window actions."""
    user = get_current_user()
    destinations = db.session.query(Flight.destination).distinct().limit(8).all()
    destinations = [d[0] for d in destinations]
    return render_template('trip_planner.html', user=user, destinations=destinations)

@public_bp.route('/trip-planner/step1-frame')
def trip_step1_frame():
    """Step 1 frame: SVG map destination picker."""
    destinations = db.session.query(Flight.destination).distinct().limit(8).all()
    destinations = [d[0] for d in destinations]
    return render_template('frames/trip_step1.html', destinations=destinations)

@public_bp.route('/trip-planner/step5-frame')
def trip_step5_frame():
    """Step 5 frame: Review & Save."""
    user = get_current_user()
    return render_template('frames/trip_step5.html', user=user)

@public_bp.route('/trip-planner/compare-popup')
def compare_popup():
    """Opens in a popup — frameset with flight list frame + action frame."""
    origin = request.args.get('origin', 'Delhi')
    destination = request.args.get('destination', 'Mumbai')
    return render_template('popups/compare_frameset.html', origin=origin, destination=destination)

@public_bp.route('/trip-planner/compare-popup/flights-frame')
def compare_flights_frame():
    """Top frame: flight list with selectable cards."""
    origin = request.args.get('origin', 'Delhi')
    destination = request.args.get('destination', 'Mumbai')
    flights = Flight.query.filter_by(origin=origin, destination=destination).limit(6).all()
    if not flights:
        flights = Flight.query.limit(6).all()
    return render_template('popups/compare_flights_frame.html', flights=flights, origin=origin, destination=destination)

@public_bp.route('/trip-planner/compare-popup/action-frame')
def compare_action_frame():
    """Bottom frame: confirm button + selected flight display."""
    return render_template('popups/compare_action_frame.html')

@public_bp.route('/trip-planner/seat-preview-popup')
def seat_preview_popup():
    """Opens in a popup — interactive SVG seat map preview."""
    flight_id = request.args.get('flight_id', 1, type=int)
    flight = Flight.query.get(flight_id)
    if not flight:
        flight = Flight.query.first()
    return render_template('popups/seat_preview_popup.html', flight=flight)

@public_bp.route('/trip-planner/price-alert-popup')
def price_alert_popup():
    """Opens in a popup — set price alert with form submission back to parent."""
    destination = request.args.get('destination', 'Goa')
    return render_template('popups/price_alert_popup.html', destination=destination)

@public_bp.route('/trip-planner/save-redirect')
@login_required
def save_trip_redirect():
    """GET-based save for iframe step5 (can't POST with CSRF from iframe)."""
    from app.models import Trip, TripItem, Notification
    destination = request.args.get('destination', '').strip()
    origin = request.args.get('origin', '').strip()
    flight_choice = request.args.get('flight_choice', '').strip()
    seat_choice = request.args.get('seat_choice', '').strip()
    price_alert = request.args.get('price_alert', '').strip()

    if not destination:
        flash('Please select a destination first.', 'warning')
        return redirect(url_for('public.trip_planner'))

    trip_name = f"{origin} → {destination}" if origin else f"Trip to {destination}"
    trip = Trip(user_id=session['user_id'], name=trip_name, destination=destination, notes="Planned via Trip Planner")
    db.session.add(trip)
    db.session.flush()
    if origin and destination:
        db.session.add(TripItem(trip_id=trip.id, item_type='FLIGHT', day_number=1,
                                title=f"Flight: {origin} → {destination}", notes=flight_choice or 'Not selected'))
    if seat_choice:
        db.session.add(TripItem(trip_id=trip.id, item_type='NOTE', day_number=1, title=f"Preferred Seat: {seat_choice}"))
    if price_alert:
        db.session.add(TripItem(trip_id=trip.id, item_type='NOTE', day_number=1, title=f"Price Alert: {price_alert}"))
    notif = Notification(user_id=session['user_id'], type='INFO', title='Trip Planned!',
                         message=f"Your trip to {destination} has been saved.",
                         link=url_for('trips.detail', trip_id=trip.id))
    db.session.add(notif)
    db.session.commit()
    flash(f'Trip to {destination} saved!', 'success')
    return redirect(url_for('trips.detail', trip_id=trip.id))

@public_bp.route('/trip-planner/save', methods=['POST'])
@login_required
def save_trip():
    """Save the planned trip to the user's account."""
    from app.models import Trip, TripItem, Notification
    destination = request.form.get('destination', '').strip()
    flight_choice = request.form.get('flight_choice', '').strip()
    seat_choice = request.form.get('seat_choice', '').strip()
    price_alert = request.form.get('price_alert', '').strip()
    origin = request.form.get('origin', '').strip()

    if not destination:
        flash('Please select a destination first.', 'warning')
        return redirect(url_for('public.trip_planner'))

    trip_name = f"Trip to {destination}"
    if origin:
        trip_name = f"{origin} → {destination}"

    trip = Trip(
        user_id=session['user_id'],
        name=trip_name,
        destination=destination,
        notes=f"Planned via Trip Planner",
    )
    db.session.add(trip)
    db.session.flush()

    # Add items from each step
    if origin and destination:
        db.session.add(TripItem(trip_id=trip.id, item_type='FLIGHT', day_number=1,
                                title=f"Flight: {origin} → {destination}",
                                notes=flight_choice or 'Not selected'))
    if seat_choice:
        db.session.add(TripItem(trip_id=trip.id, item_type='NOTE', day_number=1,
                                title=f"Preferred Seat: {seat_choice}"))
    if price_alert:
        db.session.add(TripItem(trip_id=trip.id, item_type='NOTE', day_number=1,
                                title=f"Price Alert: {price_alert}"))

    # Notification
    notif = Notification(
        user_id=session['user_id'], type='INFO',
        title='Trip Planned!',
        message=f"Your trip to {destination} has been saved.",
        link=url_for('trips.detail', trip_id=trip.id),
    )
    db.session.add(notif)
    db.session.commit()

    flash(f'Trip to {destination} saved! View it in My Trips.', 'success')
    return redirect(url_for('trips.detail', trip_id=trip.id))


# ── Chaos-safe helper ───────────────────────────────────────────────────────
def _chaos_fail_ctx(exc: Exception, retry_url: str) -> dict:
    """Build a serialisable context dict for the payment_failed page."""
    trace_id = getattr(g, 'trace_id', None)
    if isinstance(exc, PaymentChaosError):
        stage = 'payment'
        etype = 'PaymentGatewayError'
        detail = ('The payment gateway is currently unreachable. '
                  'No charge has been made to your account.')
        chain_label = 'Payment Gateway'
        resolution = 'Usually resolved within 10–30 minutes.'
    elif isinstance(exc, CheckoutChaosError):
        stage = 'checkout'
        etype = 'CheckoutServiceError'
        detail = ('The checkout service crashed mid-transaction. '
                  'Your booking was not created and no charge was made.')
        chain_label = 'Checkout Service'
        resolution = 'Usually resolved within 5–15 minutes.'
    else:  # DatabaseChaosError
        stage = 'db'
        etype = 'DatabaseError'
        detail = ('The booking database is temporarily unavailable. '
                  'Your booking could not be saved and no charge was made.')
        chain_label = 'Booking Database'
        resolution = 'Our team has been automatically alerted. ETA: 15–30 minutes.'
    return dict(
        title='Payment Failed',
        subtitle='We were unable to process your payment — no charge was made.',
        error_type=etype,
        error_detail=detail,
        error_stage=stage,
        chain_fail_label=chain_label,
        resolution=resolution,
        trace_id=trace_id,
        retry_url=retry_url,
        failed_at=datetime.utcnow().strftime('%b %d, %Y — %I:%M %p UTC'),
    )


@public_bp.route('/payment-failed')
@login_required
def payment_failed():
    ctx = session.pop('payment_fail', None)
    if not ctx:
        # Direct navigation without a failure context — redirect home
        flash('No payment error to display.', 'info')
        return redirect(url_for('public.home'))
    user = get_current_user()
    return render_template('payment_failed.html', user=user, **ctx)


@public_bp.route('/my-bookings')
@login_required
def my_bookings():
    bookings = BookingService.get_user_bookings(session['user_id'])
    user = get_current_user()
    return render_template('my_bookings.html', bookings=bookings, user=user)

@public_bp.route('/booking-details/<int:booking_id>')
@login_required
def booking_details(booking_id):
    booking = Booking.query.filter_by(id=booking_id, user_id=session['user_id']).first_or_404()
    user = get_current_user()
    return render_template('booking_details.html', booking=booking, user=user)


@public_bp.route('/offers')
def offers():
    """Promotional offers and deals page."""
    from app.models import PromoCode
    promos = PromoCode.query.filter_by(active=True).all()
    user = get_current_user()
    return render_template('offers.html', promos=promos, user=user)


@public_bp.route('/seat-selection')
@login_required
def seat_selection():
    """Visual seat map for a selected flight."""
    flight_id = session.get('selected_flight_id')
    passengers = int(session.get('passengers', 1))
    if not flight_id:
        flash('Please select a flight first.', 'warning')
        return redirect(url_for('public.flights'))
    flight = Flight.query.get_or_404(flight_id)
    # Build seat grid: 30 rows × 6 seats (A-F)
    import random
    rng = random.Random(flight.id * 7)
    total_seats = 30 * 6
    occupied_count = total_seats - max(flight.seats_left, 0)
    all_seats = [f"{row}{col}" for row in range(1, 31) for col in 'ABCDEF']
    occupied = set(rng.sample(all_seats, min(occupied_count, len(all_seats))))
    rows = []
    for row in range(1, 31):
        row_seats = []
        for col in 'ABCDEF':
            seat_id = f"{row}{col}"
            row_seats.append({'id': seat_id, 'occupied': seat_id in occupied})
        rows.append(row_seats)
    user = get_current_user()
    return render_template('seat_selection.html', flight=flight, rows=rows,
                           passengers=passengers, user=user)


@public_bp.route('/api/price-calendar')
def price_calendar():
    """Return 30-day price data for a flight (AJAX)."""
    import random
    flight_id = request.args.get('flight_id', type=int)
    if not flight_id:
        return jsonify([])
    flight = Flight.query.get(flight_id)
    if not flight:
        return jsonify([])
    rng = random.Random(flight.id)
    base = flight.price
    from datetime import date
    today = date.today()
    result = []
    for i in range(30):
        d = today + timedelta(days=i)
        variation = rng.uniform(0.85, 1.30)
        price = round(base * variation / 100) * 100
        result.append({'date': d.strftime('%d %b'), 'price': int(price)})
    return jsonify(result)


@public_bp.route('/api/autocomplete')
def autocomplete():
    """City autocomplete — covers flights, hotels, buses, trains, and cabs."""
    from app import db
    from app.models import Hotel, Bus, Train
    from sqlalchemy import union, select, text
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    pattern = f'{q}%'
    # Flight cities
    flight_origins = db.session.query(Flight.origin.label('city')).filter(Flight.origin.ilike(pattern))
    flight_dests   = db.session.query(Flight.destination.label('city')).filter(Flight.destination.ilike(pattern))
    # Hotel cities
    hotel_cities   = db.session.query(Hotel.city.label('city')).filter(Hotel.city.ilike(pattern))
    # Bus cities
    bus_origins    = db.session.query(Bus.origin.label('city')).filter(Bus.origin.ilike(pattern))
    bus_dests      = db.session.query(Bus.destination.label('city')).filter(Bus.destination.ilike(pattern))
    # Train cities
    train_origins  = db.session.query(Train.origin.label('city')).filter(Train.origin.ilike(pattern))
    train_dests    = db.session.query(Train.destination.label('city')).filter(Train.destination.ilike(pattern))

    combined = union(
        flight_origins, flight_dests,
        hotel_cities,
        bus_origins, bus_dests,
        train_origins, train_dests,
    ).alias('cities')
    rows = db.session.execute(select(text('city')).select_from(combined).limit(10)).fetchall()
    cities = sorted(set(r[0] for r in rows))
    return jsonify(cities)