from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Flight, Hotel, Booking, User
from app.forms import FlightFormAdmin
from app.services.auth import roles_required, get_current_user
from app.services.audit import audit_action, log_audit
from app import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@roles_required('admin')
def dashboard():
    # Get statistics
    total_flights = Flight.query.count()
    total_hotels = Hotel.query.count()
    total_bookings = Booking.query.count()
    total_users = User.query.filter_by(role='user').count()

    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()

    user = get_current_user()
    return render_template('admin_dashboard.html', 
                         total_flights=total_flights,
                         total_hotels=total_hotels,
                         total_bookings=total_bookings,
                         total_users=total_users,
                         recent_bookings=recent_bookings,
                         user=user)

@admin_bp.route('/flights')
@roles_required('admin')
def manage_flights():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    flights = Flight.query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    user = get_current_user()
    return render_template('admin_manage_flights.html', flights=flights, user=user)

@admin_bp.route('/flights/new', methods=['GET', 'POST'])
@roles_required('admin')
def new_flight():
    form = FlightFormAdmin()

    if form.validate_on_submit():
        flight = Flight(
            airline=form.airline.data,
            flight_no=form.flight_no.data,
            origin=form.origin.data,
            destination=form.destination.data,
            depart_time=form.depart_time.data,
            arrive_time=form.arrive_time.data,
            duration_mins=form.duration_mins.data,
            price=form.price.data,
            seats_left=form.seats_left.data,
            cabin_class=form.cabin_class.data
        )
        db.session.add(flight)
        db.session.commit()
        log_audit('FLIGHT_CREATE', target_type='FLIGHT', target_id=flight.id,
                  target_label=f'{flight.airline} {flight.flight_no} ({flight.origin}→{flight.destination})',
                  detail=dict(price=flight.price, cabin_class=flight.cabin_class))
        flash('Flight added successfully!', 'success')
        return redirect(url_for('admin.manage_flights'))

    user = get_current_user()
    return render_template('admin_flight_form.html', form=form, title='Add New Flight', user=user)

@admin_bp.route('/flights/<int:flight_id>/edit', methods=['GET', 'POST'])
@roles_required('admin')
def edit_flight(flight_id):
    flight = Flight.query.get_or_404(flight_id)
    form = FlightFormAdmin(obj=flight)

    if form.validate_on_submit():
        before = dict(price=flight.price, seats_left=flight.seats_left)
        flight.airline = form.airline.data
        flight.flight_no = form.flight_no.data
        flight.origin = form.origin.data
        flight.destination = form.destination.data
        flight.depart_time = form.depart_time.data
        flight.arrive_time = form.arrive_time.data
        flight.duration_mins = form.duration_mins.data
        flight.price = form.price.data
        flight.seats_left = form.seats_left.data
        flight.cabin_class = form.cabin_class.data
        db.session.commit()
        log_audit('FLIGHT_EDIT', target_type='FLIGHT', target_id=flight_id,
                  target_label=f'{flight.airline} {flight.flight_no}',
                  detail=dict(before=before, after=dict(price=flight.price, seats_left=flight.seats_left)))
        flash('Flight updated successfully!', 'success')
        return redirect(url_for('admin.manage_flights'))

    user = get_current_user()
    return render_template('admin_flight_form.html', form=form, title='Edit Flight',
                           flight=flight, user=user)

@admin_bp.route('/flights/<int:flight_id>/delete', methods=['POST'])
@roles_required('admin')
def delete_flight(flight_id):
    flight = Flight.query.get_or_404(flight_id)
    if flight.booking_items:
        flash('Cannot delete flight with existing bookings.', 'error')
    else:
        label = f'{flight.airline} {flight.flight_no} ({flight.origin}→{flight.destination})'
        db.session.delete(flight)
        db.session.commit()
        log_audit('FLIGHT_DELETE', target_type='FLIGHT', target_id=flight_id, target_label=label)
        flash('Flight deleted successfully!', 'success')
    return redirect(url_for('admin.manage_flights'))

@admin_bp.route('/bookings')
@roles_required('admin')
def manage_bookings():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    bookings = Booking.query.order_by(Booking.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    user = get_current_user()
    return render_template('admin_manage_bookings.html', bookings=bookings, user=user)

@admin_bp.route('/bookings/<int:booking_id>')
@roles_required('admin')
def view_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    user = get_current_user()
    return render_template('admin_booking_details.html', booking=booking, user=user)