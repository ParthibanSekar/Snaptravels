
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
from app.services.sanitize import sanitize_str, sanitize_booking_customer

mobile_api = Blueprint('mobile_api', __name__, url_prefix='/mobile-api/v1')


# ── Global chaos hook — runs before every mobile API request ─────────────
# Exempts /config so Site24x7 REST API monitors can poll a ground-truth
# check even during a scripted outage.
@mobile_api.before_request
def _inject_mobile_api_chaos():
    from flask import request as _req
    if _req.endpoint and _req.endpoint.endswith('.mobile_config'):
        return None
    try:
        from app.services.chaos import (
            maybe_fail_api, ApiChaosError,
            maybe_mobile_timeout, MobileTimeoutChaosError,
            maybe_mobile_rate_limit, MobileRateLimitChaosError,
        )
        # Global API chaos (existing) — random 5xx + slowdown
        maybe_fail_api(endpoint=_req.endpoint)
        # Mobile-specific: timeout simulation (must run before rate-limit)
        maybe_mobile_timeout()
        # Mobile-specific: rate-limit simulation
        maybe_mobile_rate_limit()
    except MobileTimeoutChaosError as e:
        return jsonify({'success': False, 'error': str(e), 'chaos': 'timeout'}), 504
    except MobileRateLimitChaosError as e:
        return jsonify({
            'success': False, 'error': str(e),
            'chaos': 'rate_limit',
            'retry_after': 60
        }), 429
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
@limiter.limit("10 per minute; 30 per hour")
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
@limiter.limit("10 per minute; 50 per hour")
def mobile_login():
    # Mobile chaos: auth failure injection
    try:
        from app.services.chaos import maybe_fail_mobile_auth, MobileAuthChaosError
        maybe_fail_mobile_auth()
    except MobileAuthChaosError as e:
        return jsonify({'error': str(e), 'chaos': 'auth_failure'}), 401

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
    # Mobile chaos: search slowdown + empty results injection
    try:
        from app.services.chaos import maybe_slow_mobile_search
        _force_empty = maybe_slow_mobile_search(kind='flight')
    except Exception:
        _force_empty = False
    if _force_empty:
        return jsonify({'success': True, 'flights': [], 'total': 0})
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

    ALL_BOOKING_TYPES = {'FLIGHT', 'HOTEL', 'TRAIN', 'BUS', 'CAB', 'PACKAGE', 'ACTIVITY', 'INSURANCE'}
    if booking_type not in ALL_BOOKING_TYPES:
        return jsonify({'error': f'Invalid booking type. Must be one of: {", ".join(sorted(ALL_BOOKING_TYPES))}'}), 400

    # ── FLIGHT & HOTEL — use existing BookingService (chaos hooks, seat decrement) ──
    if booking_type in ('FLIGHT', 'HOTEL'):
        if booking_type == 'FLIGHT':
            item_id = data.get('flight_id')
        else:
            item_id = data.get('hotel_id')

        try:
            item_id = int(item_id) if item_id else None
        except (ValueError, TypeError):
            item_id = None

        if not item_id:
            return jsonify({'error': f'{booking_type.lower()}_id is required'}), 400

        if booking_type == 'FLIGHT':
            item = Flight.query.get(item_id)
            if not item:
                return jsonify({'error': 'Flight not found'}), 404
            amount = item.price
        else:
            item = Hotel.query.get(item_id)
            if not item:
                return jsonify({'error': 'Hotel not found'}), 404
            nights = int(data.get('nights', 1)) or 1
            amount = item.price_per_night * nights

        # Server-side sanitization — runs regardless of what the client sent
        clean, s_errors = sanitize_booking_customer(data)
        if s_errors:
            return jsonify({'error': 'Validation failed', 'fields': s_errors}), 422

        customer_data = {
            'name': clean['customer_name'],
            'email': clean['customer_email'],
            'phone': clean['customer_phone'],
            'nights': data.get('nights', 1),
            'checkin': sanitize_str(data.get('checkin', ''), 20),
            'checkout': sanitize_str(data.get('checkout', ''), 20),
        }

        try:
            booking = BookingService.create_booking(
                user_id=current_user.id,
                booking_type=booking_type,
                item_id=item_id,
                customer_data=customer_data,
                amount=amount
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
                    'currency': booking.currency,
                }
            }), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    # ── TRAIN, BUS, CAB, PACKAGE, ACTIVITY, INSURANCE — direct creation ──
    return _create_non_flight_booking(current_user, booking_type, data)

@mobile_api.route('/bookings', methods=['GET'])
@mobile_auth_required
def mobile_get_bookings(current_user):
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()

    bookings_data = []
    for booking in bookings:
        # Derive top-level type + item ID from the first BookingItem
        first_item = booking.items[0] if booking.items else None
        booking_type = first_item.type if first_item else None
        item_ref_id  = first_item.ref_id if first_item else None

        # Build a type-specific ID field so the mobile app can navigate directly
        type_id_field = {}
        if booking_type == 'FLIGHT':
            type_id_field = {'flight_id': item_ref_id}
        elif booking_type == 'HOTEL':
            type_id_field = {'hotel_id': item_ref_id}
        elif booking_type == 'TRAIN':
            type_id_field = {'train_id': item_ref_id}
        elif booking_type == 'BUS':
            type_id_field = {'bus_id': item_ref_id}
        elif booking_type == 'CAB':
            type_id_field = {'cab_id': item_ref_id}
        elif booking_type == 'PACKAGE':
            type_id_field = {'package_id': item_ref_id}
        elif booking_type == 'ACTIVITY':
            type_id_field = {'activity_id': item_ref_id}
        elif booking_type == 'INSURANCE':
            type_id_field = {'insurance_id': item_ref_id}

        booking_data = {
            'id': booking.id,
            'booking_code': booking.booking_code,
            'type': booking_type,          # ← top-level type field
            'status': booking.status,
            'total_amount': float(booking.total_amount),
            'currency': booking.currency,
            'created_at': booking.created_at.isoformat(),
            'customer_name': booking.customer_name,
            'customer_email': booking.customer_email,
            **type_id_field,               # ← e.g. flight_id / train_id / etc.
        }

        # Include booking items details (enriched for all types)
        items = []
        for item in booking.items:
            item_data = {
                'type': item.type,
                'title': item.title,
                'amount': float(item.amount),
                'details': item.details,
                'ref_id': item.ref_id,
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
                    }

            elif item.type == 'HOTEL' and item.hotel_id:
                hotel = Hotel.query.get(item.hotel_id)
                if hotel:
                    item_data['hotel'] = {
                        'name': hotel.name,
                        'city': hotel.city,
                        'rating': float(hotel.rating),
                        'image_path': hotel.image_path,
                    }

            elif item.type == 'TRAIN':
                train = Train.query.get(item.ref_id)
                if train:
                    item_data['train'] = {
                        'train_no': train.train_no,
                        'train_name': train.train_name,
                        'origin': train.origin,
                        'destination': train.destination,
                        'depart_time': train.depart_time,
                        'arrive_time': train.arrive_time,
                    }

            elif item.type == 'BUS':
                bus = Bus.query.get(item.ref_id)
                if bus:
                    item_data['bus'] = {
                        'operator': bus.operator,
                        'bus_type': bus.bus_type,
                        'origin': bus.origin,
                        'destination': bus.destination,
                        'depart_time': bus.depart_time,
                        'arrive_time': bus.arrive_time,
                    }

            elif item.type == 'CAB':
                cab = Cab.query.get(item.ref_id)
                if cab:
                    item_data['cab'] = {
                        'vehicle_type': cab.vehicle_type,
                        'brand': cab.brand,
                        'ac': cab.ac,
                        'capacity': cab.capacity,
                    }

            elif item.type == 'PACKAGE':
                pkg = Package.query.get(item.ref_id)
                if pkg:
                    item_data['package'] = {
                        'name': pkg.name,
                        'destination': pkg.destination,
                        'duration_nights': pkg.duration_nights,
                        'image_path': pkg.image_path,
                    }

            elif item.type == 'ACTIVITY':
                activity = Activity.query.get(item.ref_id)
                if activity:
                    item_data['activity'] = {
                        'name': activity.name,
                        'city': activity.city,
                        'category': activity.category,
                        'duration_label': activity.duration_label,
                        'image_path': activity.image_path,
                    }

            elif item.type == 'INSURANCE':
                plan = InsurancePlan.query.get(item.ref_id)
                if plan:
                    item_data['insurance'] = {
                        'name': plan.name,
                        'medical_cover': plan.medical_cover,
                        'trip_cancellation': plan.trip_cancellation,
                        'baggage_loss': plan.baggage_loss,
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
        if item.type == 'TRAIN' and item.train_id:
            from app.models import Train
            train = Train.query.get(item.train_id)
            if train:
                item_data['train'] = {
                    'train_name': train.train_name,
                    'train_number': train.train_number,
                    'origin': train.origin,
                    'destination': train.destination,
                    'depart_time': train.depart_time,
                    'arrive_time': train.arrive_time,
                    'depart_date': train.depart_date.isoformat() if train.depart_date else None,
                    'class_type': train.class_type,
                }
        if item.type == 'BUS' and item.bus_id:
            from app.models import Bus
            bus = Bus.query.get(item.bus_id)
            if bus:
                item_data['bus'] = {
                    'operator': bus.operator,
                    'bus_type': bus.bus_type,
                    'origin': bus.origin,
                    'destination': bus.destination,
                    'depart_time': bus.depart_time,
                    'arrive_time': bus.arrive_time,
                    'depart_date': bus.depart_date.isoformat() if bus.depart_date else None,
                }
        if item.type == 'CAB' and item.cab_id:
            from app.models import Cab
            cab = Cab.query.get(item.cab_id)
            if cab:
                item_data['cab'] = {
                    'cab_type': cab.cab_type,
                    'pickup': cab.pickup_location,
                    'dropoff': cab.dropoff_location,
                    'distance_km': float(cab.distance_km) if cab.distance_km else None,
                }
        if item.type == 'PACKAGE' and item.package_id:
            from app.models import Package
            pkg = Package.query.get(item.package_id)
            if pkg:
                item_data['package'] = {
                    'name': pkg.name,
                    'destination': pkg.destination,
                    'duration_days': pkg.duration_days,
                    'image_path': pkg.image_path,
                }
        if item.type == 'ACTIVITY' and item.activity_id:
            from app.models import Activity
            act = Activity.query.get(item.activity_id)
            if act:
                item_data['activity'] = {
                    'name': act.name,
                    'location': act.location,
                    'duration_hours': act.duration_hours,
                    'image_path': act.image_path,
                }
        if item.type == 'INSURANCE' and item.insurance_id:
            from app.models import InsurancePlan
            plan = InsurancePlan.query.get(item.insurance_id)
            if plan:
                item_data['insurance'] = {
                    'plan_name': plan.plan_name,
                    'coverage_type': plan.coverage_type,
                    'coverage_amount': float(plan.coverage_amount),
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


@mobile_api.route('/bookings/<int:booking_id>/cancel', methods=['POST', 'PUT'])
@mobile_auth_required
def mobile_cancel_booking(current_user, booking_id):
    # Mobile chaos: cancel failure injection
    try:
        from app.services.chaos import maybe_fail_mobile_cancel, MobileCancelChaosError
        maybe_fail_mobile_cancel()
    except MobileCancelChaosError as e:
        return jsonify({'error': str(e), 'chaos': 'cancel_failure'}), 503

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
    # Mobile chaos: search slowdown + empty results injection
    try:
        from app.services.chaos import maybe_slow_mobile_search
        _force_empty = maybe_slow_mobile_search(kind='bus')
    except Exception:
        _force_empty = False
    if _force_empty:
        return jsonify({'success': True, 'buses': [], 'total': 0, 'date': ''})
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
    # Mobile chaos: search slowdown + empty results injection
    try:
        from app.services.chaos import maybe_slow_mobile_search
        _force_empty = maybe_slow_mobile_search(kind='train')
    except Exception:
        _force_empty = False
    if _force_empty:
        return jsonify({'success': True, 'trains': [], 'total': 0, 'date': ''})
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
    # Mobile chaos: search slowdown + empty results injection
    try:
        from app.services.chaos import maybe_slow_mobile_search
        _force_empty = maybe_slow_mobile_search(kind='cab')
    except Exception:
        _force_empty = False
    if _force_empty:
        return jsonify({'success': True, 'cabs': [], 'total': 0})
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

    if not code:
        return jsonify({'error': 'Promo code is required'}), 400

    # Validate amount from DB item, not from user input
    from app.models import Flight, Hotel
    amount = 0
    item_type = (data.get('type') or '').upper()
    item_id = data.get('flight_id') or data.get('hotel_id')
    if item_type == 'FLIGHT' and item_id:
        flight = Flight.query.get(item_id)
        amount = flight.price if flight else 0
    elif item_type == 'HOTEL' and item_id:
        hotel = Hotel.query.get(item_id)
        nights = int(data.get('nights', 1)) or 1
        amount = (hotel.price_per_night * nights) if hotel else 0
    else:
        # Fallback: accept client amount but cap it
        amount = min(float(data.get('amount', 0)), 500000)

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


# ===========================================================================
#  SHARED HELPER — non-flight/hotel booking creation (chaos-aware)
# ===========================================================================

def _create_non_flight_booking(current_user, booking_type, data):
    """
    Internal helper used by both the generic POST /bookings endpoint
    and the dedicated /trains/book, /buses/book … /insurance/buy endpoints.
    Returns a Flask Response object.
    """
    import logging
    from app.services.booking import generate_booking_code
    from app.services.chaos import (
        maybe_fail_db, maybe_fail_checkout, maybe_fail_payment,
        CheckoutChaosError, PaymentChaosError, DatabaseChaosError,
    )
    logger = logging.getLogger('snaptravels.booking')

    # ── resolve item + amount from DB ──────────────────────────────────────
    try:
        if booking_type == 'TRAIN':
            item_id = int(data.get('train_id') or 0)
            train = Train.query.get(item_id)
            if not train:
                return jsonify({'error': 'Train not found'}), 404
            travel_class = (data.get('travel_class') or data.get('class', 'SL')).upper()
            class_fare_map = {
                'SL': train.sleeper_fare,
                '3A': train.third_ac_fare,
                '2A': train.second_ac_fare,
                '1A': train.first_ac_fare,
            }
            fare = class_fare_map.get(travel_class, train.sleeper_fare)
            passengers = int(data.get('passengers', 1) or 1)
            amount = float(fare) * passengers
            item = train
            item_title = f"{train.train_name} ({train.train_no})"
            item_details = {
                'train_no': train.train_no,
                'train_name': train.train_name,
                'origin': train.origin,
                'destination': train.destination,
                'depart_time': train.depart_time,
                'arrive_time': train.arrive_time,
                'travel_class': travel_class,
                'passengers': passengers,
            }

        elif booking_type == 'BUS':
            item_id = int(data.get('bus_id') or 0)
            bus = Bus.query.get(item_id)
            if not bus:
                return jsonify({'error': 'Bus not found'}), 404
            passengers = int(data.get('passengers', 1) or 1)
            amount = float(bus.price) * passengers
            item = bus
            item_title = f"{bus.operator} — {bus.bus_no}"
            item_details = {
                'bus_no': bus.bus_no,
                'operator': bus.operator,
                'origin': bus.origin,
                'destination': bus.destination,
                'depart_time': bus.depart_time,
                'arrive_time': bus.arrive_time,
                'bus_type': bus.bus_type,
                'passengers': passengers,
            }

        elif booking_type == 'CAB':
            item_id = int(data.get('cab_id') or 0)
            cab = Cab.query.get(item_id)
            if not cab:
                return jsonify({'error': 'Cab not found'}), 404
            distance_km = float(data.get('distance_km', 20) or 20)
            amount = float(cab.estimate_fare(distance_km))
            item = cab
            item_title = f"{cab.brand} ({cab.vehicle_type})"
            item_details = {
                'vehicle_type': cab.vehicle_type,
                'brand': cab.brand,
                'pickup': data.get('pickup') or data.get('origin', ''),
                'drop': data.get('drop') or data.get('destination', ''),
                'distance_km': distance_km,
                'estimated_fare': amount,
                'ac': cab.ac,
            }

        elif booking_type == 'PACKAGE':
            item_id = int(data.get('package_id') or 0)
            pkg = Package.query.get(item_id)
            if not pkg:
                return jsonify({'error': 'Package not found'}), 404
            persons = int(data.get('persons', 1) or 1)
            amount = float(pkg.base_price) * persons
            item = pkg
            item_title = f"{pkg.name} — {pkg.destination}"
            item_details = {
                'destination': pkg.destination,
                'duration_nights': pkg.duration_nights,
                'persons': persons,
                'includes_flight': pkg.includes_flight,
                'includes_hotel': pkg.includes_hotel,
                'includes_meals': pkg.includes_meals,
            }

        elif booking_type == 'ACTIVITY':
            item_id = int(data.get('activity_id') or 0)
            activity = Activity.query.get(item_id)
            if not activity:
                return jsonify({'error': 'Activity not found'}), 404
            persons = int(data.get('persons', 1) or 1)
            amount = float(activity.price_per_person) * persons
            item = activity
            item_title = f"{activity.name} — {activity.city}"
            item_details = {
                'city': activity.city,
                'category': activity.category,
                'duration_label': activity.duration_label,
                'persons': persons,
            }

        elif booking_type == 'INSURANCE':
            item_id = int(data.get('insurance_id') or 0)
            plan = InsurancePlan.query.get(item_id)
            if not plan:
                return jsonify({'error': 'Insurance plan not found'}), 404
            persons = int(data.get('persons', 1) or 1)
            days = int(data.get('days', 1) or 1)
            amount = float(plan.price_per_person_per_day) * persons * days
            item = plan
            item_title = f"{plan.name} Insurance"
            item_details = {
                'plan_name': plan.name,
                'persons': persons,
                'days': days,
                'medical_cover': plan.medical_cover,
                'trip_cancellation': plan.trip_cancellation,
                'baggage_loss': plan.baggage_loss,
            }
        else:
            return jsonify({'error': f'Unhandled booking type: {booking_type}'}), 400

    except (ValueError, TypeError):
        return jsonify({'error': f'{booking_type.lower()}_id must be a valid integer'}), 400

    # ── server-side sanitization (runs even if client bypassed the app) ────
    clean, s_errors = sanitize_booking_customer(data)
    if s_errors:
        return jsonify({'error': 'Validation failed', 'fields': s_errors}), 422

    # ── chaos hooks ────────────────────────────────────────────────────────
    try:
        from app.services.chaos import maybe_fail_mobile_booking, MobileBookingChaosError
        maybe_fail_mobile_booking()          # mobile-specific: payment gateway decline
        maybe_fail_db('create_booking')
        maybe_fail_checkout(booking_type=booking_type, amount=amount)
        maybe_fail_payment(amount=amount)
    except MobileBookingChaosError as ce:
        logger.exception("Mobile booking decline: %s", ce)
        return jsonify({'error': str(ce), 'chaos': 'booking_decline'}), 402
    except (CheckoutChaosError, PaymentChaosError, DatabaseChaosError) as ce:
        logger.exception("Chaos-induced %s booking failure: %s", booking_type, ce)
        return jsonify({'error': 'Booking failed, please try again'}), 503

    # ── persist ────────────────────────────────────────────────────────────
    try:
        booking = Booking(
            user_id=current_user.id,
            booking_code=generate_booking_code(),
            total_amount=amount,
            customer_name=clean['customer_name'],
            customer_email=clean['customer_email'],
            customer_phone=clean['customer_phone'],
            payment_method=sanitize_str(data.get('payment_method', 'card'), 20),
        )
        db.session.add(booking)
        db.session.flush()

        booking_item = BookingItem(
            booking_id=booking.id,
            type=booking_type,
            ref_id=item_id,
            title=item_title,
            amount=amount,
        )
        booking_item.details = item_details
        db.session.add(booking_item)
        db.session.commit()

        logger.info('BOOKING_CREATED code=%s user_id=%d type=%s amount=%.2f item_id=%d',
                    booking.booking_code, current_user.id, booking_type, amount, item_id)

        # ── malformed response chaos ──────────────────────────────────────
        from app.services.chaos import should_mobile_malform
        booking_payload = {
            'id': booking.id,
            'booking_code': booking.booking_code,
            'status': booking.status,
            'total_amount': float(booking.total_amount),
            'currency': booking.currency,
            'created_at': booking.created_at.isoformat(),
        }
        if should_mobile_malform():
            # Strip key fields so mobile app must handle incomplete data
            booking_payload.pop('booking_code', None)
            booking_payload.pop('total_amount', None)

        return jsonify({'success': True, 'booking': booking_payload}), 201

    except Exception as e:
        db.session.rollback()
        logger.error("BOOKING_FAILED user_id=%d type=%s error=%s", current_user.id, booking_type, e)
        return jsonify({'error': str(e)}), 500


# ===========================================================================
#  TRAINS — dedicated book endpoint
# ===========================================================================

@mobile_api.route('/trains/book', methods=['POST'])
@mobile_auth_required
def mobile_book_train(current_user):
    data = request.get_json() or {}
    data['type'] = 'TRAIN'
    return _create_non_flight_booking(current_user, 'TRAIN', data)


# ===========================================================================
#  BUSES — dedicated book endpoint
# ===========================================================================

@mobile_api.route('/buses/book', methods=['POST'])
@mobile_auth_required
def mobile_book_bus(current_user):
    data = request.get_json() or {}
    data['type'] = 'BUS'
    return _create_non_flight_booking(current_user, 'BUS', data)


# ===========================================================================
#  CABS — dedicated book endpoint
# ===========================================================================

@mobile_api.route('/cabs/book', methods=['POST'])
@mobile_auth_required
def mobile_book_cab(current_user):
    data = request.get_json() or {}
    data['type'] = 'CAB'
    return _create_non_flight_booking(current_user, 'CAB', data)


# ===========================================================================
#  PACKAGES — dedicated book endpoint
# ===========================================================================

@mobile_api.route('/packages/book', methods=['POST'])
@mobile_auth_required
def mobile_book_package(current_user):
    data = request.get_json() or {}
    data['type'] = 'PACKAGE'
    return _create_non_flight_booking(current_user, 'PACKAGE', data)


# ===========================================================================
#  ACTIVITIES — dedicated book endpoint
# ===========================================================================

@mobile_api.route('/activities/book', methods=['POST'])
@mobile_auth_required
def mobile_book_activity(current_user):
    data = request.get_json() or {}
    data['type'] = 'ACTIVITY'
    return _create_non_flight_booking(current_user, 'ACTIVITY', data)


# ===========================================================================
#  INSURANCE — list alias + dedicated buy endpoint
# ===========================================================================

@mobile_api.route('/insurance', methods=['GET'])
def mobile_list_insurance_alias():
    """Alias for /insurance/plans — matches the spec's GET /insurance."""
    return mobile_list_insurance()


@mobile_api.route('/insurance/buy', methods=['POST'])
@mobile_auth_required
def mobile_buy_insurance(current_user):
    data = request.get_json() or {}
    data['type'] = 'INSURANCE'
    return _create_non_flight_booking(current_user, 'INSURANCE', data)


# ===========================================================================
#  SHOP — Products, Cart, Orders
# ===========================================================================

@mobile_api.route('/shop/products', methods=['GET'])
@mobile_auth_required
def mobile_shop_products(current_user):
    """List products. Optional ?category=clothing|bags|accessories|footwear"""
    from app.models import Product
    category = request.args.get('category')
    sort     = request.args.get('sort', 'popular')
    q = Product.query.filter_by(in_stock=True)
    if category:
        q = q.filter_by(category=category)
    if sort == 'price_asc':
        q = q.order_by(Product.price.asc())
    elif sort == 'price_desc':
        q = q.order_by(Product.price.desc())
    elif sort == 'newest':
        q = q.order_by(Product.created_at.desc())
    else:
        q = q.order_by(Product.review_count.desc())
    return jsonify(products=[p.to_dict() for p in q.all()])


@mobile_api.route('/shop/products/<int:product_id>', methods=['GET'])
@mobile_auth_required
def mobile_shop_product_detail(current_user, product_id):
    from app.models import Product
    p = Product.query.get_or_404(product_id)
    return jsonify(product=p.to_dict())


@mobile_api.route('/shop/cart', methods=['GET'])
@mobile_auth_required
def mobile_shop_cart_get(current_user):
    from app.models import CartItem, Product
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    result = []
    total = 0.0
    for ci in items:
        p = Product.query.get(ci.product_id)
        if p:
            subtotal = p.price * ci.quantity
            total += subtotal
            result.append({
                'cart_item_id': ci.id,
                'product': p.to_dict(),
                'size': ci.size,
                'quantity': ci.quantity,
                'subtotal': round(subtotal, 2),
            })
    shipping = 0 if total >= 999 else 99
    return jsonify(items=result, subtotal=round(total, 2),
                   shipping=shipping, grand_total=round(total + shipping, 2))


@mobile_api.route('/shop/cart', methods=['POST'])
@mobile_auth_required
def mobile_shop_cart_add(current_user):
    from app.models import CartItem, Product
    data       = request.get_json() or {}
    product_id = data.get('product_id')
    size       = data.get('size')
    quantity   = max(1, int(data.get('quantity', 1)))

    p = Product.query.get(product_id)
    if not p:
        return jsonify(error='Product not found'), 404
    if p.category in ('clothing', 'footwear') and not size:
        return jsonify(error='Size is required for this product'), 422

    existing = CartItem.query.filter_by(
        user_id=current_user.id, product_id=product_id, size=size).first()
    if existing:
        existing.quantity = min(existing.quantity + quantity, 10)
    else:
        db.session.add(CartItem(user_id=current_user.id,
                                product_id=product_id, size=size, quantity=quantity))
    db.session.commit()
    return jsonify(message='Added to cart'), 201


@mobile_api.route('/shop/cart/<int:item_id>', methods=['PUT'])
@mobile_auth_required
def mobile_shop_cart_update(current_user, item_id):
    from app.models import CartItem
    ci = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    data = request.get_json() or {}
    qty  = int(data.get('quantity', ci.quantity))
    if qty < 1:
        db.session.delete(ci)
    else:
        ci.quantity = min(qty, 10)
    db.session.commit()
    return jsonify(message='Cart updated')


@mobile_api.route('/shop/cart/<int:item_id>', methods=['DELETE'])
@mobile_auth_required
def mobile_shop_cart_remove(current_user, item_id):
    from app.models import CartItem
    ci = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(ci)
    db.session.commit()
    return jsonify(message='Removed from cart')


@mobile_api.route('/shop/checkout', methods=['POST'])
@mobile_auth_required
def mobile_shop_checkout(current_user):
    from app.models import CartItem, Product, ShopOrder, ShopOrderItem
    import uuid
    data = request.get_json() or {}

    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        return jsonify(error='Cart is empty'), 400

    name    = data.get('name', '').strip()
    email   = data.get('email', '').strip() or current_user.email
    phone   = data.get('phone', '').strip()
    address = data.get('address', '').strip()
    payment = data.get('payment_method', 'card')

    if not name or not address:
        return jsonify(error='name and address are required',
                       fields={'name': 'Required', 'address': 'Required'}), 422

    total = 0.0
    order = ShopOrder(
        order_code       = 'SH-' + uuid.uuid4().hex[:8].upper(),
        user_id          = current_user.id,
        customer_name    = name,
        customer_email   = email,
        customer_phone   = phone or None,
        shipping_address = address,
        total_amount     = 0,
        payment_method   = payment,
        status           = 'CONFIRMED',
    )
    db.session.add(order)
    db.session.flush()

    for ci in items:
        p = Product.query.get(ci.product_id)
        if p:
            subtotal = p.price * ci.quantity
            total += subtotal
            db.session.add(ShopOrderItem(
                order_id=order.id, product_id=p.id,
                product_name=p.name, size=ci.size,
                quantity=ci.quantity, unit_price=p.price,
            ))
        db.session.delete(ci)

    shipping = 0 if total >= 999 else 99
    order.total_amount = round(total + shipping, 2)
    db.session.commit()
    return jsonify(message='Order placed', order=order.to_dict()), 201


@mobile_api.route('/shop/orders', methods=['GET'])
@mobile_auth_required
def mobile_shop_orders(current_user):
    from app.models import ShopOrder
    orders = (ShopOrder.query.filter_by(user_id=current_user.id)
              .order_by(ShopOrder.created_at.desc()).all())
    return jsonify(orders=[o.to_dict() for o in orders])


@mobile_api.route('/shop/orders/<int:order_id>', methods=['GET'])
@mobile_auth_required
def mobile_shop_order_detail(current_user, order_id):
    from app.models import ShopOrder
    order = ShopOrder.query.filter_by(id=order_id, user_id=current_user.id).first()
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    return jsonify({'success': True, 'order': order.to_dict()})


# ===========================================================================
#  FLIGHT & HOTEL DETAIL
# ===========================================================================

@mobile_api.route('/flights/<int:flight_id>', methods=['GET'])
def mobile_get_flight(flight_id):
    flight = Flight.query.get(flight_id)
    if not flight:
        return jsonify({'error': 'Flight not found'}), 404
    return jsonify({
        'success': True,
        'flight': {
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
            'cabin_class': flight.cabin_class,
        }
    })


@mobile_api.route('/hotels/<int:hotel_id>', methods=['GET'])
def mobile_get_hotel(hotel_id):
    hotel = Hotel.query.get(hotel_id)
    if not hotel:
        return jsonify({'error': 'Hotel not found'}), 404
    return jsonify({
        'success': True,
        'hotel': {
            'id': hotel.id,
            'name': hotel.name,
            'city': hotel.city,
            'rating': float(hotel.rating),
            'price_per_night': float(hotel.price_per_night),
            'amenities': hotel.amenities,
            'image_path': hotel.image_path,
            'description': hotel.description,
        }
    })


# ===========================================================================
#  AUTH — forgot / reset password (token-based, unauthenticated)
# ===========================================================================

_reset_tokens: dict = {}  # token → {user_id, expires}


@mobile_api.route('/auth/forgot-password', methods=['POST'])
@limiter.limit("5 per hour")
def mobile_forgot_password():
    import secrets
    from datetime import timezone
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    if not email:
        return jsonify({'error': 'email is required'}), 400

    user = User.query.filter_by(email=email).first()
    # Always return success to avoid user enumeration
    if user:
        token = secrets.token_urlsafe(32)
        _reset_tokens[token] = {
            'user_id': user.id,
            'expires': datetime.now(timezone.utc) + timedelta(hours=1),
        }
        # In production this would send an email; for demo we return the token
        # so the mobile app can drive the reset flow end-to-end.
        current_app.logger.info('PASSWORD_RESET_TOKEN user_id=%d token=%s', user.id, token)
        return jsonify({
            'success': True,
            'message': 'If that email is registered you will receive a reset link.',
            'reset_token': token,  # demo only — remove in production
        })

    return jsonify({
        'success': True,
        'message': 'If that email is registered you will receive a reset link.',
    })


@mobile_api.route('/auth/reset-password', methods=['POST'])
@limiter.limit("10 per hour")
def mobile_reset_password():
    from datetime import timezone
    data = request.get_json() or {}
    token = (data.get('token') or '').strip()
    new_password = data.get('new_password') or ''

    if not token or not new_password:
        return jsonify({'error': 'token and new_password are required'}), 400
    if len(new_password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    entry = _reset_tokens.get(token)
    if not entry:
        return jsonify({'error': 'Invalid or expired reset token'}), 400

    if datetime.now(timezone.utc) > entry['expires']:
        _reset_tokens.pop(token, None)
        return jsonify({'error': 'Reset token has expired'}), 400

    user = User.query.get(entry['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.set_password(new_password)
    db.session.commit()
    _reset_tokens.pop(token, None)
    return jsonify({'success': True, 'message': 'Password reset successfully'})


# ===========================================================================
#  PUSH NOTIFICATION DEVICE REGISTRATION
# ===========================================================================

@mobile_api.route('/device/register-push', methods=['POST'])
@mobile_auth_required
def mobile_register_push(current_user):
    data = request.get_json() or {}
    push_token = (data.get('push_token') or '').strip()
    platform = (data.get('platform') or '').strip().lower()

    if not push_token:
        return jsonify({'error': 'push_token is required'}), 400
    if platform not in ('ios', 'android', 'expo'):
        return jsonify({'error': 'platform must be ios, android, or expo'}), 400

    # Store on the user model if the column exists, else log for APM visibility
    if hasattr(current_user, 'push_token'):
        current_user.push_token = push_token
        db.session.commit()

    current_app.logger.info(
        'PUSH_REGISTER user_id=%d platform=%s token_prefix=%s',
        current_user.id, platform, push_token[:12]
    )
    return jsonify({
        'success': True,
        'message': 'Push token registered',
        'user_id': current_user.id,
        'platform': platform,
    })


@mobile_api.route('/device/unregister-push', methods=['DELETE'])
@mobile_auth_required
def mobile_unregister_push(current_user):
    if hasattr(current_user, 'push_token'):
        current_user.push_token = None
        db.session.commit()
    current_app.logger.info('PUSH_UNREGISTER user_id=%d', current_user.id)
    return jsonify({'success': True, 'message': 'Push token removed'})
