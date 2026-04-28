
from flask import Blueprint, request, jsonify, session, current_app
from app.models import (
    User, Flight, Hotel, Booking, BookingItem,
    Bus, Train, Cab, Package, Activity, InsurancePlan,
    Review, Wishlist, Notification, TravelerProfile,
    RewardPoints, PointsTransaction, PriceAlert,
    PromoCode, RecentlyViewed
)
from app import db, limiter
from app.services.auth import AuthService
from app.services.search import SearchService
from app.services.booking import BookingService
from functools import wraps
import jwt
from datetime import datetime, timedelta
import os
import json

mobile_api = Blueprint('mobile_api', __name__, url_prefix='/mobile-api/v1')


# Chaos hook — applies to every mobile API endpoint automatically.
# We avoid the /config endpoint so Site24x7 REST API monitor can still
# poll a ground-truth check even during a scripted outage.
@mobile_api.before_request
def _inject_mobile_api_chaos():
    from flask import request as _req
    if _req.endpoint and _req.endpoint.endswith('.mobile_config'):
        return None
    try:
        from app.services.chaos import maybe_fail_api, ApiChaosError
        maybe_fail_api(endpoint=_req.endpoint)
    except ApiChaosError as e:
        return jsonify({'success': False, 'error': str(e)}), 503
    return None

def mobile_auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token missing'}), 401

        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

@mobile_api.route('/auth/register', methods=['POST'])
@limiter.exempt
def mobile_register():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    result = AuthService.signup(data['email'], data['password'])

    if result['success']:
        # Generate JWT token for mobile
        token = jwt.encode({
            'user_id': result['user'].id,
            'email': result['user'].email,
            'exp': datetime.utcnow() + timedelta(days=30)
        }, current_app.config['SECRET_KEY'])

        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': result['user'].id,
                'email': result['user'].email,
                'role': result['user'].role
            }
        })
    else:
        return jsonify({'error': result['error']}), 400

@mobile_api.route('/auth/login', methods=['POST'])
@limiter.exempt
def mobile_login():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    result = AuthService.login(data['email'], data['password'])

    if result['success']:
        # Generate JWT token for mobile
        token = jwt.encode({
            'user_id': result['user'].id,
            'email': result['user'].email,
            'exp': datetime.utcnow() + timedelta(days=30)
        }, current_app.config['SECRET_KEY'])

        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': result['user'].id,
                'email': result['user'].email,
                'role': result['user'].role
            }
        })
    else:
        return jsonify({'error': result['error']}), 401

@mobile_api.route('/auth/refresh', methods=['POST'])
@mobile_auth_required
def mobile_refresh_token(current_user):
    # Generate new JWT token
    token = jwt.encode({
        'user_id': current_user.id,
        'email': current_user.email,
        'exp': datetime.utcnow() + timedelta(days=30)
    }, current_app.config['SECRET_KEY'])

    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'role': current_user.role
        }
    })

@mobile_api.route('/flights/search', methods=['GET'])
def mobile_search_flights():
    flights = SearchService.search_flights(
        origin=request.args.get('origin'),
        destination=request.args.get('destination'),
        depart_date=request.args.get('date'),
        passengers=request.args.get('passengers', 1, type=int)
    )

    flights_data = []
    for flight in flights:
        flights_data.append({
            'id': flight.id,
            'airline': flight.airline,
            'flight_number': flight.flight_no,
            'origin': flight.origin,
            'destination': flight.destination,
            'departure_time': flight.depart_time,
            'arrival_time': flight.arrive_time,
            'depart_date': flight.depart_date.isoformat() if flight.depart_date else None,
            'price': float(flight.price),
            'duration_mins': flight.duration_mins,
            'available_seats': flight.seats_left,
            'cabin_class': flight.cabin_class
        })

    return jsonify({
        'success': True,
        'flights': flights_data,
        'total': len(flights_data)
    })

@mobile_api.route('/hotels/search', methods=['GET'])
def mobile_search_hotels():
    hotels = SearchService.search_hotels(
        city=request.args.get('city') or request.args.get('location'),
        checkin=request.args.get('checkin'),
        checkout=request.args.get('checkout'),
        guests=request.args.get('guests', 1, type=int)
    )

    hotels_data = []
    for hotel in hotels:
        hotels_data.append({
            'id': hotel.id,
            'name': hotel.name,
            'city': hotel.city,
            'rating': float(hotel.rating),
            'price_per_night': float(hotel.price_per_night),
            'amenities': hotel.amenities,
            'image_path': hotel.image_path,
            'description': hotel.description
        })

    return jsonify({
        'success': True,
        'hotels': hotels_data,
        'total': len(hotels_data)
    })

@mobile_api.route('/bookings', methods=['POST'])
@mobile_auth_required
def mobile_create_booking(current_user):
    data = request.get_json()

    if not data or not data.get('type'):
        return jsonify({'error': 'Booking type required'}), 400

    booking_type = data['type'].upper()

    # Determine item_id based on booking type
    if booking_type == 'FLIGHT':
        item_id = data.get('flight_id')
    elif booking_type == 'HOTEL':
        item_id = data.get('hotel_id')
    else:
        return jsonify({'error': 'Invalid booking type. Must be FLIGHT or HOTEL'}), 400

    if not item_id:
        return jsonify({'error': f'{booking_type.lower()}_id is required'}), 400

    customer_data = {
        'name': data.get('customer_name', current_user.email),
        'email': data.get('customer_email', current_user.email),
        'phone': data.get('customer_phone', ''),
        'nights': data.get('nights', 1),
        'checkin': data.get('checkin'),
        'checkout': data.get('checkout')
    }

    try:
        booking = BookingService.create_booking(
            user_id=current_user.id,
            booking_type=booking_type,
            item_id=item_id,
            customer_data=customer_data,
            amount=data.get('amount', 0)
        )

        if not booking:
            return jsonify({'error': 'Failed to create booking'}), 500

        return jsonify({
            'success': True,
            'booking': {
                'id': booking.id,
                'booking_code': booking.booking_code,
                'status': booking.status,
                'total_amount': float(booking.total_amount),
                'created_at': booking.created_at.isoformat(),
                'currency': booking.currency
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@mobile_api.route('/bookings', methods=['GET'])
@mobile_auth_required
def mobile_get_bookings(current_user):
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()

    bookings_data = []
    for booking in bookings:
        booking_data = {
            'id': booking.id,
            'booking_code': booking.booking_code,
            'status': booking.status,
            'total_amount': float(booking.total_amount),
            'currency': booking.currency,
            'created_at': booking.created_at.isoformat(),
            'customer_name': booking.customer_name,
            'customer_email': booking.customer_email
        }

        # Include booking items details
        items = []
        for item in booking.items:
            item_data = {
                'type': item.type,
                'title': item.title,
                'amount': float(item.amount),
                'details': item.details
            }

            if item.type == 'FLIGHT' and item.flight_id:
                flight = Flight.query.get(item.flight_id)
                if flight:
                    item_data['flight'] = {
                        'airline': flight.airline,
                        'flight_number': flight.flight_no,
                        'origin': flight.origin,
                        'destination': flight.destination,
                        'departure_time': flight.depart_time,
                        'arrival_time': flight.arrive_time
                    }

            if item.type == 'HOTEL' and item.hotel_id:
                hotel = Hotel.query.get(item.hotel_id)
                if hotel:
                    item_data['hotel'] = {
                        'name': hotel.name,
                        'city': hotel.city,
                        'rating': float(hotel.rating),
                        'image_path': hotel.image_path
                    }

            items.append(item_data)

        booking_data['items'] = items
        bookings_data.append(booking_data)

    return jsonify({
        'success': True,
        'bookings': bookings_data,
        'total': len(bookings_data)
    })

@mobile_api.route('/user/profile', methods=['GET'])
@mobile_auth_required
def mobile_get_profile(current_user):
    return jsonify({
        'success': True,
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'role': current_user.role,
            'created_at': current_user.created_at.isoformat()
        }
    })

@mobile_api.route('/config', methods=['GET'])
def mobile_config():
    return jsonify({
        'success': True,
        'config': {
            'app_version': '1.0.0',
            'api_version': 'v1',
            'supported_features': [
                'flight_booking', 'hotel_booking', 'bus_booking',
                'train_booking', 'cab_booking', 'package_booking',
                'activity_booking', 'insurance', 'user_authentication',
                'booking_history', 'push_notifications', 'wishlist',
                'reviews', 'price_alerts', 'promo_codes', 'rewards'
            ],
            'payment_methods': ['credit_card', 'debit_card', 'net_banking', 'upi'],
            'supported_currencies': ['INR'],
            'min_app_version': '1.0.0'
        }
    })


# ===========================================================================
#  AUTH EXTRAS — logout, change password
# ===========================================================================

@mobile_api.route('/auth/logout', methods=['POST'])
@mobile_auth_required
def mobile_logout(current_user):
    """Stateless JWT — just ack; client discards the token."""
    return jsonify({'success': True, 'message': 'Logged out successfully'})


@mobile_api.route('/auth/change-password', methods=['POST'])
@mobile_auth_required
def mobile_change_password(current_user):
    data = request.get_json() or {}
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({'error': 'current_password and new_password are required'}), 400

    if len(new_password) < 8:
        return jsonify({'error': 'New password must be at least 8 characters'}), 400

    # Verify current password
    check = AuthService.login(current_user.email, current_password)
    if not check.get('success'):
        return jsonify({'error': 'Current password is incorrect'}), 401

    # Set new password using the model's helper
    current_user.set_password(new_password)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Password changed successfully'})


# ===========================================================================
#  USER PROFILE — update, traveler profiles, rewards
# ===========================================================================

@mobile_api.route('/user/profile', methods=['PUT'])
@mobile_auth_required
def mobile_update_profile(current_user):
    data = request.get_json() or {}
    allowed = {'full_name', 'phone', 'gender', 'date_of_birth', 'nationality'}
    for field in allowed:
        if field in data:
            if hasattr(current_user, field):
                setattr(current_user, field, data[field])
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@mobile_api.route('/user/travelers', methods=['GET'])
@mobile_auth_required
def mobile_get_travelers(current_user):
    travelers = TravelerProfile.query.filter_by(user_id=current_user.id).order_by(
        TravelerProfile.is_primary.desc(), TravelerProfile.id).all()
    return jsonify({
        'success': True,
        'travelers': [{
            'id': t.id,
            'full_name': t.full_name,
            'gender': t.gender,
            'age': t.age,
            'date_of_birth': t.date_of_birth.isoformat() if t.date_of_birth else None,
            'nationality': t.nationality,
            'id_type': t.id_type,
            'id_number': t.id_number,
            'passport_no': t.passport_no,
            'is_primary': t.is_primary
        } for t in travelers]
    })


@mobile_api.route('/user/travelers', methods=['POST'])
@mobile_auth_required
def mobile_add_traveler(current_user):
    data = request.get_json() or {}
    if not data.get('full_name'):
        return jsonify({'error': 'full_name is required'}), 400

    dob = None
    if data.get('date_of_birth'):
        try:
            from datetime import date
            dob = date.fromisoformat(data['date_of_birth'])
        except ValueError:
            return jsonify({'error': 'Invalid date_of_birth format (YYYY-MM-DD)'}), 400

    # If new traveler is_primary, unset others
    if data.get('is_primary'):
        TravelerProfile.query.filter_by(user_id=current_user.id, is_primary=True).update({'is_primary': False})

    traveler = TravelerProfile(
        user_id=current_user.id,
        full_name=data['full_name'],
        gender=data.get('gender'),
        age=data.get('age'),
        date_of_birth=dob,
        nationality=data.get('nationality', 'Indian'),
        id_type=data.get('id_type'),
        id_number=data.get('id_number'),
        passport_no=data.get('passport_no'),
        is_primary=bool(data.get('is_primary', False))
    )
    db.session.add(traveler)
    db.session.commit()
    return jsonify({'success': True, 'id': traveler.id, 'message': 'Traveler profile added'}), 201


@mobile_api.route('/user/travelers/<int:traveler_id>', methods=['PUT'])
@mobile_auth_required
def mobile_update_traveler(current_user, traveler_id):
    traveler = TravelerProfile.query.filter_by(id=traveler_id, user_id=current_user.id).first()
    if not traveler:
        return jsonify({'error': 'Traveler not found'}), 404
    data = request.get_json() or {}
    fields = ['full_name', 'gender', 'age', 'nationality', 'id_type', 'id_number', 'passport_no', 'is_primary']
    for f in fields:
        if f in data:
            setattr(traveler, f, data[f])
    if 'date_of_birth' in data and data['date_of_birth']:
        try:
            from datetime import date
            traveler.date_of_birth = date.fromisoformat(data['date_of_birth'])
        except ValueError:
            return jsonify({'error': 'Invalid date_of_birth format'}), 400
    if data.get('is_primary'):
        TravelerProfile.query.filter_by(user_id=current_user.id, is_primary=True).filter(
            TravelerProfile.id != traveler_id).update({'is_primary': False})
    db.session.commit()
    return jsonify({'success': True, 'message': 'Traveler updated'})


@mobile_api.route('/user/travelers/<int:traveler_id>', methods=['DELETE'])
@mobile_auth_required
def mobile_delete_traveler(current_user, traveler_id):
    traveler = TravelerProfile.query.filter_by(id=traveler_id, user_id=current_user.id).first()
    if not traveler:
        return jsonify({'error': 'Traveler not found'}), 404
    db.session.delete(traveler)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Traveler profile deleted'})


@mobile_api.route('/user/rewards', methods=['GET'])
@mobile_auth_required
def mobile_get_rewards(current_user):
    rp = RewardPoints.query.filter_by(user_id=current_user.id).first()
    if not rp:
        rp = RewardPoints(user_id=current_user.id, points=0, lifetime_points=0, tier='Silver')
        db.session.add(rp)
        db.session.commit()

    transactions = PointsTransaction.query.filter_by(user_id=current_user.id).order_by(
        PointsTransaction.created_at.desc()).limit(20).all()

    return jsonify({
        'success': True,
        'rewards': {
            'points': rp.points,
            'lifetime_points': rp.lifetime_points,
            'tier': rp.tier,
            'next_tier': {'Silver': 'Gold', 'Gold': 'Platinum', 'Platinum': 'Platinum'}.get(rp.tier, 'Gold'),
            'points_to_next_tier': max(0, {'Silver': 1000, 'Gold': 5000, 'Platinum': 0}.get(rp.tier, 1000) - rp.lifetime_points)
        },
        'transactions': [{
            'id': t.id,
            'points': t.points,
            'type': t.transaction_type,
            'description': t.description,
            'created_at': t.created_at.isoformat()
        } for t in transactions]
    })


# ===========================================================================
#  BOOKINGS — single detail, cancel, resend confirmation
# ===========================================================================

@mobile_api.route('/bookings/<int:booking_id>', methods=['GET'])
@mobile_auth_required
def mobile_get_booking(current_user, booking_id):
    booking = Booking.query.filter_by(id=booking_id, user_id=current_user.id).first()
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404

    items = []
    for item in booking.items:
        item_data = {
            'type': item.type,
            'title': item.title,
            'amount': float(item.amount),
            'details': item.details
        }
        if item.type == 'FLIGHT' and item.flight_id:
            flight = Flight.query.get(item.flight_id)
            if flight:
                item_data['flight'] = {
                    'airline': flight.airline,
                    'flight_number': flight.flight_no,
                    'origin': flight.origin,
                    'destination': flight.destination,
                    'departure_time': flight.depart_time,
                    'arrival_time': flight.arrive_time,
                    'depart_date': flight.depart_date.isoformat() if flight.depart_date else None
                }
        if item.type == 'HOTEL' and item.hotel_id:
            hotel = Hotel.query.get(item.hotel_id)
            if hotel:
                item_data['hotel'] = {
                    'name': hotel.name,
                    'city': hotel.city,
                    'rating': float(hotel.rating),
                    'image_path': hotel.image_path
                }
        items.append(item_data)

    return jsonify({
        'success': True,
        'booking': {
            'id': booking.id,
            'booking_code': booking.booking_code,
            'status': booking.status,
            'total_amount': float(booking.total_amount),
            'currency': booking.currency,
            'created_at': booking.created_at.isoformat(),
            'customer_name': booking.customer_name,
            'customer_email': booking.customer_email,
            'customer_phone': booking.customer_phone,
            'items': items
        }
    })


@mobile_api.route('/bookings/<int:booking_id>/cancel', methods=['PUT'])
@mobile_auth_required
def mobile_cancel_booking(current_user, booking_id):
    booking = Booking.query.filter_by(id=booking_id, user_id=current_user.id).first()
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404
    if booking.status in ('CANCELLED', 'REFUNDED'):
        return jsonify({'error': f'Booking is already {booking.status.lower()}'}), 400
    booking.status = 'CANCELLED'
    db.session.commit()
    return jsonify({'success': True, 'message': 'Booking cancelled successfully', 'booking_code': booking.booking_code})


@mobile_api.route('/bookings/<int:booking_id>/resend', methods=['POST'])
@mobile_auth_required
def mobile_resend_confirmation(current_user, booking_id):
    """Re-send booking confirmation email (mock — just acks)."""
    booking = Booking.query.filter_by(id=booking_id, user_id=current_user.id).first()
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404
    return jsonify({'success': True, 'message': f'Confirmation sent to {booking.customer_email}'})


# ===========================================================================
#  BUS SEARCH
# ===========================================================================

@mobile_api.route('/buses/search', methods=['GET'])
def mobile_search_buses():
    origin = request.args.get('origin', '').strip()
    destination = request.args.get('destination', '').strip()
    travel_date = request.args.get('date', '').strip()
    bus_type = request.args.get('bus_type', '').strip()

    query = Bus.query
    if origin:
        query = query.filter(Bus.origin.ilike(f'%{origin}%'))
    if destination:
        query = query.filter(Bus.destination.ilike(f'%{destination}%'))
    if bus_type:
        query = query.filter(Bus.bus_type.ilike(f'%{bus_type}%'))

    buses = query.order_by(Bus.price).all()

    buses_data = [{
        'id': b.id,
        'bus_no': b.bus_no,
        'operator': b.operator,
        'origin': b.origin,
        'destination': b.destination,
        'depart_time': b.depart_time,
        'arrive_time': b.arrive_time,
        'duration_mins': b.duration_mins,
        'bus_type': b.bus_type,
        'price': float(b.price),
        'seats_left': b.seats_left,
        'amenities': b.amenities.split(',') if b.amenities else []
    } for b in buses]

    return jsonify({'success': True, 'buses': buses_data, 'total': len(buses_data), 'date': travel_date})


# ===========================================================================
#  TRAIN SEARCH
# ===========================================================================

@mobile_api.route('/trains/search', methods=['GET'])
def mobile_search_trains():
    origin = request.args.get('origin', '').strip()
    destination = request.args.get('destination', '').strip()
    travel_date = request.args.get('date', '').strip()
    train_class = request.args.get('class', '').strip().upper()  # SL/3A/2A/1A

    query = Train.query
    if origin:
        query = query.filter(Train.origin.ilike(f'%{origin}%'))
    if destination:
        query = query.filter(Train.destination.ilike(f'%{destination}%'))

    trains = query.order_by(Train.depart_time).all()

    class_map = {
        'SL': ('sleeper_fare', 'sleeper_seats'),
        '3A': ('third_ac_fare', 'third_ac_seats'),
        '2A': ('second_ac_fare', 'second_ac_seats'),
        '1A': ('first_ac_fare', 'first_ac_seats'),
    }

    trains_data = []
    for t in trains:
        classes = []
        for cls, (fare_attr, seats_attr) in [
            ('SL', ('sleeper_fare', 'sleeper_seats')),
            ('3A', ('third_ac_fare', 'third_ac_seats')),
            ('2A', ('second_ac_fare', 'second_ac_seats')),
            ('1A', ('first_ac_fare', 'first_ac_seats')),
        ]:
            fare = getattr(t, fare_attr)
            seats = getattr(t, seats_attr)
            if not train_class or train_class == cls:
                classes.append({'class': cls, 'fare': float(fare), 'seats_available': seats})

        trains_data.append({
            'id': t.id,
            'train_no': t.train_no,
            'train_name': t.train_name,
            'train_type': t.train_type,
            'run_days': t.run_days,
            'origin': t.origin,
            'destination': t.destination,
            'depart_time': t.depart_time,
            'arrive_time': t.arrive_time,
            'duration_mins': t.duration_mins,
            'distance_km': t.distance_km,
            'classes': classes
        })

    return jsonify({'success': True, 'trains': trains_data, 'total': len(trains_data), 'date': travel_date})


# ===========================================================================
#  CAB SEARCH
# ===========================================================================

@mobile_api.route('/cabs/search', methods=['GET'])
def mobile_search_cabs():
    pickup = request.args.get('pickup', '').strip()
    drop = request.args.get('drop', '').strip()
    distance_km = request.args.get('distance_km', 20, type=float)
    vehicle_type = request.args.get('vehicle_type', '').strip()

    query = Cab.query.filter_by(available=True)
    if vehicle_type:
        query = query.filter(Cab.vehicle_type.ilike(f'%{vehicle_type}%'))

    cabs = query.order_by(Cab.base_amount).all()

    cabs_data = [{
        'id': c.id,
        'vehicle_type': c.vehicle_type,
        'brand': c.brand,
        'base_fare': float(c.base_fare),
        'base_km': float(c.base_km),
        'base_amount': float(c.base_amount),
        'capacity': c.capacity,
        'ac': c.ac,
        'image_path': c.image_path,
        'estimated_fare': float(c.estimate_fare(distance_km))
    } for c in cabs]

    return jsonify({
        'success': True,
        'cabs': cabs_data,
        'total': len(cabs_data),
        'pickup': pickup,
        'drop': drop,
        'distance_km': distance_km
    })


# ===========================================================================
#  PACKAGES
# ===========================================================================

@mobile_api.route('/packages', methods=['GET'])
def mobile_list_packages():
    destination = request.args.get('destination', '').strip()
    tag = request.args.get('tag', '').strip().upper()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = Package.query.filter_by(active=True)
    if destination:
        query = query.filter(Package.destination.ilike(f'%{destination}%'))
    if tag:
        query = query.filter(Package.tag == tag)
    if min_price is not None:
        query = query.filter(Package.base_price >= min_price)
    if max_price is not None:
        query = query.filter(Package.base_price <= max_price)

    paginated = query.order_by(Package.base_price).paginate(page=page, per_page=per_page, error_out=False)

    packages_data = [{
        'id': p.id,
        'name': p.name,
        'slug': p.slug,
        'destination': p.destination,
        'country': p.country,
        'tag': p.tag,
        'description': p.description,
        'duration_nights': p.duration_nights,
        'base_price': float(p.base_price),
        'original_price': float(p.original_price) if p.original_price else None,
        'discount_pct': p.discount_pct,
        'image_path': p.image_path,
        'includes_flight': p.includes_flight,
        'includes_hotel': p.includes_hotel,
        'includes_meals': p.includes_meals,
        'includes_transfers': p.includes_transfers,
        'max_persons': p.max_persons,
        'bookings_today': p.bookings_today
    } for p in paginated.items]

    return jsonify({
        'success': True,
        'packages': packages_data,
        'total': paginated.total,
        'page': page,
        'pages': paginated.pages
    })


@mobile_api.route('/packages/<slug>', methods=['GET'])
def mobile_get_package(slug):
    pkg = Package.query.filter_by(slug=slug, active=True).first()
    if not pkg:
        # Fallback to ID lookup
        try:
            pkg = Package.query.get(int(slug))
        except (ValueError, TypeError):
            pkg = None
    if not pkg:
        return jsonify({'error': 'Package not found'}), 404

    return jsonify({
        'success': True,
        'package': {
            'id': pkg.id,
            'name': pkg.name,
            'slug': pkg.slug,
            'destination': pkg.destination,
            'country': pkg.country,
            'tag': pkg.tag,
            'description': pkg.description,
            'duration_nights': pkg.duration_nights,
            'base_price': float(pkg.base_price),
            'original_price': float(pkg.original_price) if pkg.original_price else None,
            'discount_pct': pkg.discount_pct,
            'image_path': pkg.image_path,
            'includes_flight': pkg.includes_flight,
            'includes_hotel': pkg.includes_hotel,
            'includes_meals': pkg.includes_meals,
            'includes_transfers': pkg.includes_transfers,
            'max_persons': pkg.max_persons,
            'bookings_today': pkg.bookings_today,
            'highlights': pkg.highlights,
            'itinerary': pkg.itinerary
        }
    })


# ===========================================================================
#  ACTIVITIES
# ===========================================================================

@mobile_api.route('/activities', methods=['GET'])
def mobile_list_activities():
    city = request.args.get('city', '').strip()
    category = request.args.get('category', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = Activity.query.filter_by(active=True)
    if city:
        query = query.filter(Activity.city.ilike(f'%{city}%'))
    if category:
        query = query.filter(Activity.category.ilike(f'%{category}%'))

    paginated = query.order_by(Activity.rating.desc()).paginate(page=page, per_page=per_page, error_out=False)

    activities_data = [{
        'id': a.id,
        'name': a.name,
        'city': a.city,
        'category': a.category,
        'description': a.description,
        'price_per_person': float(a.price_per_person),
        'original_price': float(a.original_price) if a.original_price else None,
        'discount_pct': a.discount_pct,
        'duration_hours': a.duration_hours,
        'duration_label': a.duration_label,
        'min_persons': a.min_persons,
        'max_persons': a.max_persons,
        'rating': float(a.rating),
        'review_count': a.review_count,
        'image_path': a.image_path,
        'includes': a.includes
    } for a in paginated.items]

    return jsonify({
        'success': True,
        'activities': activities_data,
        'total': paginated.total,
        'page': page,
        'pages': paginated.pages
    })


@mobile_api.route('/activities/<int:activity_id>', methods=['GET'])
def mobile_get_activity(activity_id):
    activity = Activity.query.filter_by(id=activity_id, active=True).first()
    if not activity:
        return jsonify({'error': 'Activity not found'}), 404

    return jsonify({
        'success': True,
        'activity': {
            'id': activity.id,
            'name': activity.name,
            'city': activity.city,
            'category': activity.category,
            'description': activity.description,
            'price_per_person': float(activity.price_per_person),
            'original_price': float(activity.original_price) if activity.original_price else None,
            'discount_pct': activity.discount_pct,
            'duration_hours': activity.duration_hours,
            'duration_label': activity.duration_label,
            'min_persons': activity.min_persons,
            'max_persons': activity.max_persons,
            'rating': float(activity.rating),
            'review_count': activity.review_count,
            'image_path': activity.image_path,
            'includes': activity.includes
        }
    })


# ===========================================================================
#  INSURANCE PLANS
# ===========================================================================

@mobile_api.route('/insurance/plans', methods=['GET'])
def mobile_list_insurance():
    plans = InsurancePlan.query.filter_by(active=True).order_by(InsurancePlan.price_per_person_per_day).all()
    plans_data = [{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'price_per_person_per_day': float(p.price_per_person_per_day),
        'medical_cover': float(p.medical_cover),
        'trip_cancellation': p.trip_cancellation,
        'baggage_loss': p.baggage_loss,
        'flight_delay': p.flight_delay,
        'adventure_sports': p.adventure_sports,
        'highlighted': p.highlighted,
        'tagline': p.tagline,
        'color': p.color,
        'coverage': p.coverage
    } for p in plans]
    return jsonify({'success': True, 'plans': plans_data})


# ===========================================================================
#  WISHLIST — CRUD
# ===========================================================================

@mobile_api.route('/wishlist', methods=['GET'])
@mobile_auth_required
def mobile_get_wishlist(current_user):
    items = Wishlist.query.filter_by(user_id=current_user.id).order_by(Wishlist.created_at.desc()).all()
    result = []
    for w in items:
        item = {'id': w.id, 'item_type': w.item_type, 'ref_id': w.ref_id, 'created_at': w.created_at.isoformat()}
        # Enrich with actual data
        if w.item_type == 'FLIGHT':
            obj = Flight.query.get(w.ref_id)
            if obj:
                item['detail'] = {'airline': obj.airline, 'flight_no': obj.flight_no,
                                  'origin': obj.origin, 'destination': obj.destination,
                                  'price': float(obj.price)}
        elif w.item_type == 'HOTEL':
            obj = Hotel.query.get(w.ref_id)
            if obj:
                item['detail'] = {'name': obj.name, 'city': obj.city,
                                  'rating': float(obj.rating), 'price_per_night': float(obj.price_per_night),
                                  'image_path': obj.image_path}
        elif w.item_type == 'PACKAGE':
            obj = Package.query.get(w.ref_id)
            if obj:
                item['detail'] = {'name': obj.name, 'destination': obj.destination,
                                  'base_price': float(obj.base_price), 'image_path': obj.image_path}
        result.append(item)
    return jsonify({'success': True, 'wishlist': result, 'total': len(result)})


@mobile_api.route('/wishlist', methods=['POST'])
@mobile_auth_required
def mobile_add_to_wishlist(current_user):
    data = request.get_json() or {}
    item_type = (data.get('item_type') or '').upper()
    ref_id = data.get('ref_id')

    if item_type not in ('FLIGHT', 'HOTEL', 'PACKAGE', 'ACTIVITY'):
        return jsonify({'error': 'item_type must be FLIGHT, HOTEL, PACKAGE, or ACTIVITY'}), 400
    if not ref_id:
        return jsonify({'error': 'ref_id is required'}), 400

    # Upsert — silently ignore duplicate
    existing = Wishlist.query.filter_by(user_id=current_user.id, item_type=item_type, ref_id=ref_id).first()
    if existing:
        return jsonify({'success': True, 'id': existing.id, 'message': 'Already in wishlist'})

    w = Wishlist(user_id=current_user.id, item_type=item_type, ref_id=ref_id)
    db.session.add(w)
    db.session.commit()
    return jsonify({'success': True, 'id': w.id, 'message': 'Added to wishlist'}), 201


@mobile_api.route('/wishlist/<int:wishlist_id>', methods=['DELETE'])
@mobile_auth_required
def mobile_remove_from_wishlist(current_user, wishlist_id):
    w = Wishlist.query.filter_by(id=wishlist_id, user_id=current_user.id).first()
    if not w:
        return jsonify({'error': 'Wishlist item not found'}), 404
    db.session.delete(w)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Removed from wishlist'})


# ===========================================================================
#  REVIEWS — submit & retrieve
# ===========================================================================

@mobile_api.route('/reviews', methods=['GET'])
def mobile_get_reviews():
    review_type = (request.args.get('type') or '').upper()
    ref_id = request.args.get('ref_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    if not review_type or not ref_id:
        return jsonify({'error': 'type and ref_id are required'}), 400
    if review_type not in ('HOTEL', 'FLIGHT', 'PACKAGE', 'ACTIVITY'):
        return jsonify({'error': 'type must be HOTEL, FLIGHT, PACKAGE, or ACTIVITY'}), 400

    query = Review.query.filter_by(review_type=review_type, ref_id=ref_id).order_by(Review.created_at.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    avg = db.session.query(db.func.avg(Review.rating)).filter_by(
        review_type=review_type, ref_id=ref_id).scalar() or 0

    reviews_data = [{
        'id': r.id,
        'rating': r.rating,
        'stars': r.stars,
        'title': r.title,
        'comment': r.comment,
        'verified_booking': r.verified_booking,
        'created_at': r.created_at.isoformat(),
        'user': r.user.email.split('@')[0] if r.user else 'Guest'
    } for r in paginated.items]

    return jsonify({
        'success': True,
        'reviews': reviews_data,
        'total': paginated.total,
        'page': page,
        'pages': paginated.pages,
        'average_rating': round(float(avg), 1)
    })


@mobile_api.route('/reviews', methods=['POST'])
@mobile_auth_required
def mobile_submit_review(current_user):
    data = request.get_json() or {}
    review_type = (data.get('review_type') or '').upper()
    ref_id = data.get('ref_id')
    rating = data.get('rating')

    if review_type not in ('HOTEL', 'FLIGHT', 'PACKAGE', 'ACTIVITY'):
        return jsonify({'error': 'review_type must be HOTEL, FLIGHT, PACKAGE, or ACTIVITY'}), 400
    if not ref_id:
        return jsonify({'error': 'ref_id is required'}), 400
    if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({'error': 'rating must be an integer between 1 and 5'}), 400

    # Check if user already reviewed this item
    existing = Review.query.filter_by(user_id=current_user.id, review_type=review_type, ref_id=ref_id).first()
    if existing:
        return jsonify({'error': 'You have already reviewed this item'}), 409

    # Check if verified booking
    verified = False
    if review_type == 'HOTEL':
        verified = BookingItem.query.join(Booking).filter(
            Booking.user_id == current_user.id,
            BookingItem.hotel_id == ref_id
        ).first() is not None
    elif review_type == 'FLIGHT':
        verified = BookingItem.query.join(Booking).filter(
            Booking.user_id == current_user.id,
            BookingItem.flight_id == ref_id
        ).first() is not None

    review = Review(
        user_id=current_user.id,
        review_type=review_type,
        ref_id=ref_id,
        rating=rating,
        title=data.get('title'),
        comment=data.get('comment'),
        verified_booking=verified
    )
    db.session.add(review)
    db.session.commit()
    return jsonify({'success': True, 'id': review.id, 'message': 'Review submitted'}), 201


# ===========================================================================
#  NOTIFICATIONS
# ===========================================================================

@mobile_api.route('/notifications', methods=['GET'])
@mobile_auth_required
def mobile_get_notifications(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'

    query = Notification.query.filter_by(user_id=current_user.id)
    if unread_only:
        query = query.filter_by(read=False)
    query = query.order_by(Notification.created_at.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    unread_count = Notification.query.filter_by(user_id=current_user.id, read=False).count()

    return jsonify({
        'success': True,
        'notifications': [{
            'id': n.id,
            'type': n.type,
            'title': n.title,
            'message': n.message,
            'link': n.link,
            'read': n.read,
            'created_at': n.created_at.isoformat()
        } for n in paginated.items],
        'total': paginated.total,
        'unread_count': unread_count,
        'page': page,
        'pages': paginated.pages
    })


@mobile_api.route('/notifications/<int:notification_id>/read', methods=['PUT'])
@mobile_auth_required
def mobile_mark_notification_read(current_user, notification_id):
    n = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not n:
        return jsonify({'error': 'Notification not found'}), 404
    n.read = True
    db.session.commit()
    return jsonify({'success': True, 'message': 'Marked as read'})


@mobile_api.route('/notifications/read-all', methods=['PUT'])
@mobile_auth_required
def mobile_mark_all_notifications_read(current_user):
    Notification.query.filter_by(user_id=current_user.id, read=False).update({'read': True})
    db.session.commit()
    return jsonify({'success': True, 'message': 'All notifications marked as read'})


# ===========================================================================
#  PROMO CODE VALIDATION
# ===========================================================================

@mobile_api.route('/promo/validate', methods=['POST'])
@mobile_auth_required
def mobile_validate_promo(current_user):
    data = request.get_json() or {}
    code = (data.get('code') or '').strip().upper()
    amount = data.get('amount', 0)

    if not code:
        return jsonify({'error': 'Promo code is required'}), 400

    promo = PromoCode.query.filter_by(code=code).first()
    if not promo:
        return jsonify({'error': 'Invalid promo code'}), 404

    valid, message = promo.is_valid(amount=amount)
    if not valid:
        return jsonify({'error': message}), 400

    discount = promo.compute_discount(amount)
    return jsonify({
        'success': True,
        'promo': {
            'code': promo.code,
            'description': promo.description,
            'discount_type': promo.discount_type,
            'discount_value': float(promo.discount_value),
            'discount_amount': float(discount),
            'final_amount': round(amount - discount, 2)
        }
    })


# ===========================================================================
#  PRICE ALERTS — CRUD
# ===========================================================================

@mobile_api.route('/price-alerts', methods=['GET'])
@mobile_auth_required
def mobile_get_price_alerts(current_user):
    alerts = PriceAlert.query.filter_by(user_id=current_user.id).order_by(PriceAlert.created_at.desc()).all()
    return jsonify({
        'success': True,
        'alerts': [{
            'id': a.id,
            'alert_type': a.alert_type,
            'origin': a.origin,
            'destination': a.destination,
            'city': a.city,
            'target_price': float(a.target_price),
            'triggered': a.triggered,
            'created_at': a.created_at.isoformat()
        } for a in alerts]
    })


@mobile_api.route('/price-alerts', methods=['POST'])
@mobile_auth_required
def mobile_create_price_alert(current_user):
    data = request.get_json() or {}
    alert_type = (data.get('alert_type') or '').upper()
    target_price = data.get('target_price')

    if alert_type not in ('FLIGHT', 'HOTEL'):
        return jsonify({'error': 'alert_type must be FLIGHT or HOTEL'}), 400
    if not target_price or float(target_price) <= 0:
        return jsonify({'error': 'target_price must be a positive number'}), 400

    alert = PriceAlert(
        user_id=current_user.id,
        alert_type=alert_type,
        origin=data.get('origin'),
        destination=data.get('destination'),
        city=data.get('city'),
        target_price=float(target_price)
    )
    db.session.add(alert)
    db.session.commit()
    return jsonify({'success': True, 'id': alert.id, 'message': 'Price alert created'}), 201


@mobile_api.route('/price-alerts/<int:alert_id>', methods=['DELETE'])
@mobile_auth_required
def mobile_delete_price_alert(current_user, alert_id):
    alert = PriceAlert.query.filter_by(id=alert_id, user_id=current_user.id).first()
    if not alert:
        return jsonify({'error': 'Price alert not found'}), 404
    db.session.delete(alert)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Price alert deleted'})


# ===========================================================================
#  POPULAR DESTINATIONS
# ===========================================================================

@mobile_api.route('/destinations/popular', methods=['GET'])
def mobile_popular_destinations():
    """Return popular destinations derived from packages + hotels."""
    limit = request.args.get('limit', 12, type=int)

    # Aggregate from packages
    pkg_dests = db.session.query(
        Package.destination,
        db.func.count(Package.id).label('pkg_count')
    ).filter_by(active=True).group_by(Package.destination).order_by(
        db.func.count(Package.id).desc()).limit(limit).all()

    destinations = []
    seen = set()
    for dest, count in pkg_dests:
        if dest not in seen:
            seen.add(dest)
            # Find a representative package image
            pkg = Package.query.filter_by(destination=dest, active=True).filter(
                Package.image_path.isnot(None)).first()
            destinations.append({
                'destination': dest,
                'package_count': count,
                'image_path': pkg.image_path if pkg else None,
                'starting_price': float(db.session.query(db.func.min(Package.base_price)).filter_by(
                    destination=dest, active=True).scalar() or 0)
            })

    # Top up with hotel cities if needed
    if len(destinations) < limit:
        hotel_cities = db.session.query(
            Hotel.city,
            db.func.count(Hotel.id).label('hotel_count')
        ).group_by(Hotel.city).order_by(db.func.count(Hotel.id).desc()).limit(limit).all()

        for city, count in hotel_cities:
            if city not in seen and len(destinations) < limit:
                seen.add(city)
                hotel = Hotel.query.filter_by(city=city).filter(
                    Hotel.image_path.isnot(None)).first()
                destinations.append({
                    'destination': city,
                    'hotel_count': count,
                    'image_path': hotel.image_path if hotel else None,
                    'starting_price': float(db.session.query(db.func.min(Hotel.price_per_night)).filter_by(
                        city=city).scalar() or 0)
                })

    return jsonify({'success': True, 'destinations': destinations, 'total': len(destinations)})


# ===========================================================================
#  AUTOCOMPLETE  (city / destination suggestions for mobile search boxes)
# ===========================================================================

@mobile_api.route('/autocomplete', methods=['GET'])
def mobile_autocomplete():
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify({'success': True, 'suggestions': []})

    pattern = f'%{q}%'
    from sqlalchemy import union

    origins = db.session.query(Flight.origin.label('city')).filter(Flight.origin.ilike(pattern))
    dests = db.session.query(Flight.destination.label('city')).filter(Flight.destination.ilike(pattern))
    hotel_cities = db.session.query(Hotel.city.label('city')).filter(Hotel.city.ilike(pattern))
    combined = union(origins, dests, hotel_cities).alias('cities')
    rows = db.session.execute(db.select(combined.c.city).order_by(combined.c.city)).fetchall()

    suggestions = sorted(set(r[0] for r in rows))[:10]
    return jsonify({'success': True, 'suggestions': suggestions})
