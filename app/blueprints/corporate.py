"""
Corporate Travel Portal blueprint.

All routes are protected by HTTP Basic Auth (WWW-Authenticate: Basic).
Credentials come from env vars:
    CORP_BASIC_USER  (default: corp_user)
    CORP_BASIC_PASS  (default: Corp@2024!)

Dashboard and Bookings pages show fixed sample data — no real user data is
exposed.  Search still queries the real Flight/Hotel DB tables (those are
catalogue data, not user data).

Useful for:
  - Site24x7 Synthetic Monitors that test Basic Auth flows
  - Multi-step transaction monitors (Login → Search → Bookings)
  - Demonstrating how APM handles Basic Auth protected pages
"""

import os
import base64
import logging
from functools import wraps
from datetime import datetime, date, timedelta
from types import SimpleNamespace

from flask import Blueprint, render_template, request, Response, g
from sqlalchemy import func

from app import db
from app.models import Flight, Hotel

logger = logging.getLogger('snaptravels.corporate')

corporate_bp = Blueprint('corporate', __name__, url_prefix='/corporate')

# ── Credentials ────────────────────────────────────────────────────────────────

def _get_credentials():
    return (
        os.environ.get('CORP_BASIC_USER', 'corp_user'),
        os.environ.get('CORP_BASIC_PASS', 'Corp@2024!'),
    )

def _check_auth(username: str, password: str) -> bool:
    valid_user, valid_pass = _get_credentials()
    return username == valid_user and password == valid_pass

def _unauthorized():
    return Response(
        'Authentication required. Please provide valid corporate credentials.',
        401,
        {
            'WWW-Authenticate': 'Basic realm="SnapTravels Corporate Portal"',
            'Content-Type': 'text/plain',
        }
    )

def requires_basic_auth(f):
    """Decorator that enforces HTTP Basic Auth on any route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Basic '):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
                username, password = decoded.split(':', 1)
                if _check_auth(username, password):
                    g.corp_user = username
                    return f(*args, **kwargs)
            except Exception:
                pass
        return _unauthorized()
    return decorated


# ── Sample Data ────────────────────────────────────────────────────────────────
# Fixed set of corporate travel records. No real user data is used.

_TODAY = date.today()

def _d(days_ago):
    """Return a datetime N days before today."""
    return datetime.combine(_TODAY - timedelta(days=days_ago), datetime.min.time()).replace(
        hour=[9,10,11,14,15,16,17][days_ago % 7],
        minute=[0,15,30,45][days_ago % 4],
    )

SAMPLE_BOOKINGS = [
    # (booking_code, customer_name, customer_email, customer_phone, total_amount, payment_method, status, days_ago, booking_type)
    ('CORP-1001', 'Arjun Mehta',      'arjun.mehta@example.com',    '9876543210', 12450.0,  'card',       'CONFIRMED',  2,  'Flight · DEL → BOM'),
    ('CORP-1002', 'Priya Sharma',     'priya.sharma@example.com',   '9845612300', 8200.0,   'upi',        'CONFIRMED',  3,  'Hotel · Taj Lands End, Mumbai'),
    ('CORP-1003', 'Karthik Rajan',    'karthik.rajan@example.com',  '9994561230', 5600.0,   'card',       'CONFIRMED',  5,  'Train · SBC → MAS (2AC)'),
    ('CORP-1004', 'Sneha Iyer',       'sneha.iyer@example.com',     '9988776655', 31200.0,  'netbanking', 'CONFIRMED',  7,  'Flight · BLR → DEL'),
    ('CORP-1005', 'Rohit Verma',      'rohit.verma@example.com',    '9123456789', 4800.0,   'upi',        'CANCELLED',  8,  'Bus · Pune → Goa (AC Sleeper)'),
    ('CORP-1006', 'Deepika Nair',     'deepika.nair@example.com',   '9765432100', 18750.0,  'card',       'CONFIRMED',  10, 'Flight · MAA → HYD + Hotel'),
    ('CORP-1007', 'Arjun Mehta',      'arjun.mehta@example.com',    '9876543210', 7300.0,   'card',       'CONFIRMED',  12, 'Hotel · Marriott, Bengaluru'),
    ('CORP-1008', 'Vikram Bose',      'vikram.bose@example.com',    '9632587410', 22100.0,  'card',       'CONFIRMED',  14, 'Flight · CCU → BOM'),
    ('CORP-1009', 'Priya Sharma',     'priya.sharma@example.com',   '9845612300', 3500.0,   'upi',        'CANCELLED',  15, 'Cab · Airport Transfer, Pune'),
    ('CORP-1010', 'Meena Pillai',     'meena.pillai@example.com',   '9871234560', 9800.0,   'card',       'CONFIRMED',  17, 'Train · NDLS → BCT (1AC)'),
    ('CORP-1011', 'Karthik Rajan',    'karthik.rajan@example.com',  '9994561230', 41500.0,  'netbanking', 'CONFIRMED',  19, 'Flight · BLR → SIN (International)'),
    ('CORP-1012', 'Sneha Iyer',       'sneha.iyer@example.com',     '9988776655', 6200.0,   'upi',        'CONFIRMED',  21, 'Hotel · ITC Grand, Chennai'),
    ('CORP-1013', 'Rohit Verma',      'rohit.verma@example.com',    '9123456789', 14300.0,  'card',       'CONFIRMED',  23, 'Flight · BOM → AMD'),
    ('CORP-1014', 'Vikram Bose',      'vikram.bose@example.com',    '9632587410', 5100.0,   'card',       'CANCELLED',  25, 'Hotel · Hyatt, Hyderabad'),
    ('CORP-1015', 'Arjun Mehta',      'arjun.mehta@example.com',    '9876543210', 28900.0,  'card',       'CONFIRMED',  28, 'Flight · DEL → BLR + Hotel'),
    ('CORP-1016', 'Deepika Nair',     'deepika.nair@example.com',   '9765432100', 3900.0,   'upi',        'CONFIRMED',  30, 'Train · MAS → BZA (SL)'),
    ('CORP-1017', 'Meena Pillai',     'meena.pillai@example.com',   '9871234560', 16600.0,  'netbanking', 'CONFIRMED',  33, 'Flight · HYD → DEL'),
    ('CORP-1018', 'Priya Sharma',     'priya.sharma@example.com',   '9845612300', 7700.0,   'card',       'CONFIRMED',  36, 'Hotel · Westin, Mumbai'),
    ('CORP-1019', 'Karthik Rajan',    'karthik.rajan@example.com',  '9994561230', 4400.0,   'upi',        'CANCELLED',  39, 'Bus · Chennai → Bengaluru (Volvo)'),
    ('CORP-1020', 'Rohit Verma',      'rohit.verma@example.com',    '9123456789', 19800.0,  'card',       'CONFIRMED',  42, 'Flight · BOM → CCU'),
    ('CORP-1021', 'Sneha Iyer',       'sneha.iyer@example.com',     '9988776655', 11200.0,  'card',       'CONFIRMED',  45, 'Flight · MAA → DEL'),
    ('CORP-1022', 'Vikram Bose',      'vikram.bose@example.com',    '9632587410', 8900.0,   'netbanking', 'CONFIRMED',  48, 'Hotel · Leela Palace, Delhi'),
    ('CORP-1023', 'Arjun Mehta',      'arjun.mehta@example.com',    '9876543210', 6800.0,   'upi',        'CONFIRMED',  52, 'Train · BOM → PUNE (2AC)'),
    ('CORP-1024', 'Deepika Nair',     'deepika.nair@example.com',   '9765432100', 34500.0,  'card',       'CONFIRMED',  57, 'Flight · BLR → BOM + Hotel 3N'),
    ('CORP-1025', 'Meena Pillai',     'meena.pillai@example.com',   '9871234560', 5500.0,   'card',       'CANCELLED',  62, 'Activity · City Tour, Jaipur'),
]

def _make_booking(row):
    code, name, email, phone, amount, pay, status, days, btype = row
    b = SimpleNamespace()
    b.booking_code   = code
    b.customer_name  = name
    b.customer_email = email
    b.customer_phone = phone
    b.total_amount   = amount
    b.payment_method = pay
    b.status         = status
    b.created_at     = _d(days)
    b.booking_type   = btype
    return b

# Pre-build the full list once at import time
ALL_SAMPLE = [_make_booking(r) for r in SAMPLE_BOOKINGS]


def _sample_stats():
    confirmed  = sum(1 for b in ALL_SAMPLE if b.status == 'CONFIRMED')
    cancelled  = sum(1 for b in ALL_SAMPLE if b.status == 'CANCELLED')
    total_spend = sum(b.total_amount for b in ALL_SAMPLE)
    travellers = len({b.customer_email for b in ALL_SAMPLE})
    month_start = _TODAY.replace(day=1)
    this_month = sum(1 for b in ALL_SAMPLE if b.created_at.date() >= month_start)
    return {
        'total_bookings': len(ALL_SAMPLE),
        'total_spend':    round(total_spend, 2),
        'confirmed':      confirmed,
        'cancelled':      cancelled,
        'travellers':     travellers,
        'this_month':     this_month,
    }


class _FakePagination:
    """Minimal pagination object that mimics Flask-SQLAlchemy's Pagination."""
    def __init__(self, items_all, page, per_page):
        self.total    = len(items_all)
        self.page     = page
        self.per_page = per_page
        self.pages    = max(1, (self.total + per_page - 1) // per_page)
        start = (page - 1) * per_page
        self.items    = items_all[start:start + per_page]
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_num = page - 1
        self.next_num = page + 1

    def iter_pages(self, left_edge=1, right_edge=1, left_current=2, right_current=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge
                    or (self.page - left_current <= num <= self.page + right_current)
                    or num > self.pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num


def _paginated_sample(page=1, per_page=20, status_filter='ALL'):
    filtered = ALL_SAMPLE if status_filter == 'ALL' else [
        b for b in ALL_SAMPLE if b.status == status_filter
    ]
    return _FakePagination(filtered, page, per_page)


# ── Routes ─────────────────────────────────────────────────────────────────────

@corporate_bp.route('/')
@requires_basic_auth
def index():
    """Corporate travel dashboard — sample stats + recent bookings + quick search."""
    return render_template(
        'corporate/index.html',
        stats=_sample_stats(),
        recent=ALL_SAMPLE[:8],
        now=datetime.utcnow(),
        corp_user=g.get('corp_user', 'corp_user'),
    )


@corporate_bp.route('/search', methods=['GET', 'POST'])
@requires_basic_auth
def search():
    """Flight and hotel search — queries real catalogue (not user data)."""
    flights  = []
    hotels   = []
    query    = {}
    searched = False

    if request.method == 'POST':
        search_type = request.form.get('search_type', 'flight')
        query = {
            'search_type': search_type,
            'origin':      request.form.get('origin', '').strip(),
            'destination': request.form.get('destination', '').strip(),
            'travel_date': request.form.get('travel_date', ''),
            'city':        request.form.get('city', '').strip(),
            'checkin':     request.form.get('checkin', ''),
            'checkout':    request.form.get('checkout', ''),
            'passengers':  int(request.form.get('passengers', 1)),
        }
        searched = True
        try:
            if search_type == 'flight' and query['origin'] and query['destination']:
                flights = Flight.query.filter(
                    func.lower(Flight.origin).contains(query['origin'].lower()),
                    func.lower(Flight.destination).contains(query['destination'].lower()),
                ).limit(20).all()
            elif search_type == 'hotel' and query['city']:
                hotels = Hotel.query.filter(
                    func.lower(Hotel.city).contains(query['city'].lower()),
                ).limit(20).all()
        except Exception as e:
            logger.error(f'[CORP] search error: {e}')

    return render_template(
        'corporate/search.html',
        flights=flights,
        hotels=hotels,
        query=query,
        searched=searched,
        today=date.today().isoformat(),
        corp_user=g.get('corp_user', 'corp_user'),
    )


@corporate_bp.route('/bookings')
@requires_basic_auth
def bookings():
    """Full paginated sample booking history."""
    page          = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'ALL')
    pagination    = _paginated_sample(page=page, per_page=10, status_filter=status_filter)

    return render_template(
        'corporate/bookings.html',
        pagination=pagination,
        status_filter=status_filter,
        stats=_sample_stats(),
        corp_user=g.get('corp_user', 'corp_user'),
    )
