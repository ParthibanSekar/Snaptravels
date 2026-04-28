
import pytest
import json
import sys
import os
from datetime import date, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models import User, Flight, Hotel, Booking, BookingItem
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    """Create application for testing"""
    test_app = create_app()
    test_app.config['TESTING'] = True
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    test_app.config['SERVER_NAME'] = 'localhost'

    with test_app.app_context():
        db.create_all()

        # Create test users
        admin = User(
            email='admin@test.com',
            password_hash=generate_password_hash('admin123'),
            role='admin'
        )
        user = User(
            email='user@test.com',
            password_hash=generate_password_hash('user123'),
            role='user'
        )

        # Create test flight with correct model field names
        flight = Flight(
            airline='Test Airlines',
            flight_no='TA123',
            origin='Delhi',
            destination='Mumbai',
            depart_time='10:00',
            arrive_time='12:30',
            depart_date=date.today() + timedelta(days=7),
            price=5000,
            duration_mins=150,
            seats_left=100,
            cabin_class='Economy'
        )

        # Create test hotel with correct model field names
        hotel = Hotel(
            name='Test Hotel',
            city='Mumbai',
            rating=4.5,
            price_per_night=3000,
            image_path='/assets/images/test.jpg',
            description='Test hotel description'
        )
        hotel.amenities = ['WiFi', 'Pool']

        db.session.add_all([admin, user, flight, hotel])
        db.session.commit()

    yield test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


# ============================================================
# Page Load Tests
# ============================================================

def test_index_page(client):
    """Test home page loads correctly"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'SnapTravels' in response.data


def test_login_page_loads(client):
    """Test login page loads correctly"""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Sign In' in response.data or b'Login' in response.data


def test_signup_page_loads(client):
    """Test signup page loads correctly"""
    response = client.get('/signup')
    assert response.status_code == 200
    assert b'Create Account' in response.data or b'Sign Up' in response.data


def test_flights_page_loads(client):
    """Test flights page loads with default flights"""
    response = client.get('/flights')
    assert response.status_code == 200
    assert b'flight' in response.data.lower() or b'Flight' in response.data


def test_hotels_page_loads(client):
    """Test hotels page loads with default hotels"""
    response = client.get('/hotels')
    assert response.status_code == 200
    assert b'hotel' in response.data.lower() or b'Hotel' in response.data


# ============================================================
# Authentication Tests
# ============================================================

def test_user_signup(client, app):
    """Test user registration via form"""
    response = client.post('/signup', data={
        'email': 'newuser@test.com',
        'password': 'password123',
        'password2': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200

    # Verify user was created in database
    with app.app_context():
        new_user = User.query.filter_by(email='newuser@test.com').first()
        assert new_user is not None
        assert new_user.role == 'user'


def test_user_login(client):
    """Test user login via form"""
    response = client.post('/login', data={
        'email': 'user@test.com',
        'password': 'user123'
    }, follow_redirects=True)
    assert response.status_code == 200
    # After successful login, should redirect to home
    assert b'SnapTravels' in response.data


def test_admin_login(client):
    """Test admin login via form"""
    response = client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    }, follow_redirects=True)
    assert response.status_code == 200


def test_invalid_login(client):
    """Test login with invalid credentials"""
    response = client.post('/login', data={
        'email': 'user@test.com',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid email or password' in response.data


def test_logout(client):
    """Test user logout"""
    # Login first
    with client.session_transaction() as sess:
        sess['user_id'] = 2

    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200

    # Verify session is cleared
    with client.session_transaction() as sess:
        assert 'user_id' not in sess


# ============================================================
# Flight Search Tests
# ============================================================

def test_search_flights_by_origin(client):
    """Test flight search by origin"""
    response = client.post('/flights', data={
        'origin': 'Delhi',
        'destination': '',
        'passengers': 1,
        'cabin_class': 'any'
    }, follow_redirects=True)
    assert response.status_code == 200


def test_search_flights_by_destination(client):
    """Test flight search by destination"""
    response = client.post('/flights', data={
        'origin': '',
        'destination': 'Mumbai',
        'passengers': 1,
        'cabin_class': 'any'
    }, follow_redirects=True)
    assert response.status_code == 200


# ============================================================
# Hotel Search Tests
# ============================================================

def test_search_hotels_by_city(client):
    """Test hotel search by city"""
    response = client.post('/hotels', data={
        'city': 'Mumbai',
        'checkin': (date.today() + timedelta(days=1)).isoformat(),
        'checkout': (date.today() + timedelta(days=3)).isoformat(),
        'guests': 2,
        'rooms': 1
    }, follow_redirects=True)
    assert response.status_code == 200


# ============================================================
# Booking Tests (requires login)
# ============================================================

def test_booking_without_login(client):
    """Test booking page redirects without authentication"""
    response = client.get('/booking')
    # Should redirect to login
    assert response.status_code == 302
    assert '/login' in response.headers.get('Location', '')


def test_select_flight_without_login(client):
    """Test flight selection redirects to login"""
    response = client.get('/select-flight/1')
    assert response.status_code == 302
    assert '/login' in response.headers.get('Location', '')


def test_select_flight_with_login(client):
    """Test flight selection with login"""
    with client.session_transaction() as sess:
        sess['user_id'] = 2

    response = client.get('/select-flight/1')
    # Should redirect to booking page
    assert response.status_code == 302
    assert '/booking' in response.headers.get('Location', '')


def test_select_hotel_with_login(client):
    """Test hotel selection with login"""
    with client.session_transaction() as sess:
        sess['user_id'] = 2

    response = client.get('/select-hotel/1')
    assert response.status_code == 302
    assert '/booking' in response.headers.get('Location', '')


def test_booking_page_with_flight(client):
    """Test booking page loads with a selected flight"""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['selected_flight'] = 1

    response = client.get('/booking')
    assert response.status_code == 200
    assert b'Test Airlines' in response.data or b'booking' in response.data.lower()


def test_flight_booking_submit(client, app):
    """Test submitting a flight booking"""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['selected_flight'] = 1

    response = client.post('/booking', data={
        'customer_name': 'Test User',
        'customer_email': 'testuser@example.com',
        'customer_phone': '9876543210',
        'card_name': 'Test User',
        'card_number': '4111111111111111',
        'expiry_month': '12',
        'expiry_year': '2028',
        'cvv': '123'
    }, follow_redirects=True)
    assert response.status_code == 200

    # Verify booking was created
    with app.app_context():
        booking = Booking.query.filter_by(user_id=2).first()
        assert booking is not None
        assert booking.status == 'CONFIRMED'
        assert booking.customer_name == 'Test User'


def test_hotel_booking_submit(client, app):
    """Test submitting a hotel booking"""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['selected_hotel'] = 1
        sess['hotel_search'] = {
            'city': 'Mumbai',
            'checkin': (date.today() + timedelta(days=1)).isoformat(),
            'checkout': (date.today() + timedelta(days=3)).isoformat(),
            'guests': 2,
            'rooms': 1,
            'nights': 2
        }

    response = client.post('/booking', data={
        'customer_name': 'Hotel Guest',
        'customer_email': 'guest@example.com',
        'customer_phone': '9876543210',
        'card_name': 'Hotel Guest',
        'card_number': '4111111111111111',
        'expiry_month': '12',
        'expiry_year': '2028',
        'cvv': '123'
    }, follow_redirects=True)
    assert response.status_code == 200


def test_my_bookings_page(client):
    """Test my bookings page loads"""
    with client.session_transaction() as sess:
        sess['user_id'] = 2

    response = client.get('/my-bookings')
    assert response.status_code == 200


# ============================================================
# Admin Tests
# ============================================================

def test_admin_dashboard(client):
    """Test admin dashboard loads"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1  # admin ID

    response = client.get('/admin/')
    assert response.status_code == 200
    assert b'Dashboard' in response.data or b'Admin' in response.data


def test_admin_manage_flights(client):
    """Test admin flights management page"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1

    response = client.get('/admin/flights')
    assert response.status_code == 200


def test_admin_manage_bookings(client):
    """Test admin bookings management page"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1

    response = client.get('/admin/bookings')
    assert response.status_code == 200


def test_user_cannot_access_admin(client):
    """Test regular user cannot access admin endpoints"""
    with client.session_transaction() as sess:
        sess['user_id'] = 2  # regular user ID

    response = client.get('/admin/', follow_redirects=True)
    assert response.status_code == 200
    # Should be redirected away from admin - check for access denied or home page
    assert b'permission' in response.data.lower() or b'SnapTravels' in response.data


def test_admin_add_flight(client, app):
    """Test admin adding new flight via form"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1  # admin ID

    response = client.post('/admin/flights/new', data={
        'airline': 'New Airlines',
        'flight_no': 'NA456',
        'origin': 'Bangalore',
        'destination': 'Chennai',
        'depart_time': '15:00',
        'arrive_time': '16:30',
        'duration_mins': 90,
        'price': 4500,
        'seats_left': 150,
        'cabin_class': 'Economy'
    }, follow_redirects=True)
    assert response.status_code == 200

    # Verify flight was created
    with app.app_context():
        new_flight = Flight.query.filter_by(flight_no='NA456').first()
        assert new_flight is not None
        assert new_flight.airline == 'New Airlines'


def test_admin_edit_flight(client, app):
    """Test admin editing an existing flight"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1

    response = client.post('/admin/flights/1/edit', data={
        'airline': 'Updated Airlines',
        'flight_no': 'TA123',
        'origin': 'Delhi',
        'destination': 'Mumbai',
        'depart_time': '11:00',
        'arrive_time': '13:30',
        'duration_mins': 150,
        'price': 5500,
        'seats_left': 95,
        'cabin_class': 'Economy'
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        flight = Flight.query.get(1)
        assert flight.airline == 'Updated Airlines'
        assert flight.price == 5500


def test_admin_delete_flight_without_bookings(client, app):
    """Test admin deleting a flight without bookings"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1

    response = client.post('/admin/flights/1/delete', follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        flight = Flight.query.get(1)
        assert flight is None


# ============================================================
# Mobile API Tests
# ============================================================

def test_mobile_api_config(client):
    """Test mobile API config endpoint"""
    response = client.get('/mobile-api/v1/config')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'config' in data
    assert data['config']['api_version'] == 'v1'


def test_mobile_api_register(client, app):
    """Test mobile API registration"""
    response = client.post('/mobile-api/v1/auth/register',
        data=json.dumps({
            'email': 'mobile@test.com',
            'password': 'mobile123'
        }),
        content_type='application/json'
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'token' in data


def test_mobile_api_login(client):
    """Test mobile API login"""
    response = client.post('/mobile-api/v1/auth/login',
        data=json.dumps({
            'email': 'user@test.com',
            'password': 'user123'
        }),
        content_type='application/json'
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'token' in data
    assert data['user']['email'] == 'user@test.com'


def test_mobile_api_login_invalid(client):
    """Test mobile API login with invalid credentials"""
    response = client.post('/mobile-api/v1/auth/login',
        data=json.dumps({
            'email': 'user@test.com',
            'password': 'wrongpassword'
        }),
        content_type='application/json'
    )
    assert response.status_code == 401
    data = json.loads(response.data)
    assert 'error' in data


def test_mobile_api_search_flights(client):
    """Test mobile API flight search"""
    response = client.get('/mobile-api/v1/flights/search?origin=Delhi&destination=Mumbai')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'flights' in data


def test_mobile_api_search_hotels(client):
    """Test mobile API hotel search"""
    response = client.get('/mobile-api/v1/hotels/search?city=Mumbai')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'hotels' in data


def test_mobile_api_bookings_without_auth(client):
    """Test mobile API bookings without authentication"""
    response = client.get('/mobile-api/v1/bookings')
    assert response.status_code == 401


def test_mobile_api_profile_without_auth(client):
    """Test mobile API profile without authentication"""
    response = client.get('/mobile-api/v1/user/profile')
    assert response.status_code == 401


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
