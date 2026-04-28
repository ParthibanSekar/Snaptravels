"""
Trip Planner blueprint — Phase 4.
Users create trips and add flights, hotels, activities, etc. as itinerary items.
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from app.models import Trip, TripItem, Flight, Hotel, Package, Activity, Cab, Train, Bus
from app.services.auth import login_required, get_current_user
from app import db
from datetime import datetime

trips_bp = Blueprint('trips', __name__, url_prefix='/my-trips')

ITEM_TYPE_ICONS = {
    'FLIGHT': 'bi-airplane', 'HOTEL': 'bi-building', 'ACTIVITY': 'bi-stars',
    'CAB': 'bi-car-front', 'TRAIN': 'bi-train-front', 'BUS': 'bi-bus-front',
    'PACKAGE': 'bi-map', 'NOTE': 'bi-journal-text',
}


@trips_bp.route('/')
@login_required
def listing():
    user = get_current_user()
    trips = Trip.query.filter_by(user_id=session['user_id'])\
        .order_by(Trip.created_at.desc()).all()
    return render_template('trips.html', user=user, trips=trips)


@trips_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_trip():
    user = get_current_user()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Trip name is required.', 'danger')
            return redirect(url_for('trips.new_trip'))

        start_str = request.form.get('start_date', '')
        end_str = request.form.get('end_date', '')
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else None
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else None

        trip = Trip(
            user_id=session['user_id'],
            name=name,
            destination=request.form.get('destination', ''),
            start_date=start_date,
            end_date=end_date,
            notes=request.form.get('notes', ''),
        )
        db.session.add(trip)
        db.session.commit()
        flash(f'Trip "{name}" created!', 'success')
        return redirect(url_for('trips.detail', trip_id=trip.id))

    return render_template('trip_new.html', user=user)


@trips_bp.route('/<int:trip_id>')
@login_required
def detail(trip_id):
    trip = Trip.query.filter_by(id=trip_id, user_id=session['user_id']).first_or_404()
    user = get_current_user()
    # Group items by day
    days = {}
    for item in trip.items:
        days.setdefault(item.day_number, []).append(item)
    return render_template('trip_detail.html', user=user, trip=trip,
                           days=days, icons=ITEM_TYPE_ICONS)


@trips_bp.route('/<int:trip_id>/add-item', methods=['POST'])
@login_required
def add_item(trip_id):
    trip = Trip.query.filter_by(id=trip_id, user_id=session['user_id']).first_or_404()
    title = request.form.get('title', '').strip()
    item_type = request.form.get('item_type', 'NOTE')
    day_number = int(request.form.get('day_number', 1))
    notes = request.form.get('notes', '')

    if not title:
        flash('Item title is required.', 'danger')
        return redirect(url_for('trips.detail', trip_id=trip_id))

    item = TripItem(
        trip_id=trip.id,
        item_type=item_type,
        day_number=day_number,
        title=title,
        notes=notes,
    )
    db.session.add(item)
    db.session.commit()
    flash('Item added to your trip!', 'success')
    return redirect(url_for('trips.detail', trip_id=trip_id))


@trips_bp.route('/<int:trip_id>/items/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(trip_id, item_id):
    trip = Trip.query.filter_by(id=trip_id, user_id=session['user_id']).first_or_404()
    item = TripItem.query.filter_by(id=item_id, trip_id=trip.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash('Item removed.', 'success')
    return redirect(url_for('trips.detail', trip_id=trip_id))


@trips_bp.route('/<int:trip_id>/delete', methods=['POST'])
@login_required
def delete_trip(trip_id):
    trip = Trip.query.filter_by(id=trip_id, user_id=session['user_id']).first_or_404()
    db.session.delete(trip)
    db.session.commit()
    flash(f'Trip "{trip.name}" deleted.', 'success')
    return redirect(url_for('trips.listing'))
