
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import json
import random

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Email verification ────────────────────────────────────────────────────
    email_confirmed    = db.Column(db.Boolean, default=False, nullable=False)
    confirmation_token = db.Column(db.String(128), nullable=True, index=True)
    confirmation_sent_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    bookings = db.relationship('Booking', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'

    # ── 2FA Fields ─────────────────────────────────────────────────────────────
    totp_secret_enc   = db.Column(db.Text, nullable=True)      # Fernet-encrypted TOTP secret
    totp_enabled      = db.Column(db.Boolean, default=False, nullable=False)
    totp_verified_at  = db.Column(db.DateTime, nullable=True)  # When 2FA was last confirmed
    email_otp_enabled = db.Column(db.Boolean, default=False, nullable=False)  # Email OTP 2FA
    # ── End 2FA Fields ─────────────────────────────────────────────────────────

    @property
    def name(self):
        """Derive a display name from the email address (part before @)."""
        local = self.email.split('@')[0] if self.email else 'User'
        # Convert dot/underscore/hyphen-separated parts to Title Case
        return ' '.join(p.capitalize() for p in local.replace('.', ' ').replace('_', ' ').replace('-', ' ').split())

# ======================================================================
# Two-Factor Authentication
# ======================================================================
class BackupCode(db.Model):
    """One-time backup codes for 2FA recovery — stored as hashed values."""
    __tablename__ = 'backup_code'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    code_hash  = db.Column(db.String(255), nullable=False)  # pbkdf2 hash
    used       = db.Column(db.Boolean, default=False, nullable=False)
    used_at    = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TwoFactorLog(db.Model):
    """Audit trail for all 2FA events per user."""
    __tablename__ = 'two_factor_log'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    event      = db.Column(db.String(50), nullable=False)   # 2FA_ENABLED | 2FA_DISABLED | 2FA_LOGIN | 2FA_FAILED | 2FA_BACKUP_USED | 2FA_SETUP_STARTED
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(400), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Flight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    airline = db.Column(db.String(100), nullable=False)
    flight_no = db.Column(db.String(20), nullable=False)
    origin = db.Column(db.String(100), nullable=False, index=True)
    destination = db.Column(db.String(100), nullable=False, index=True)
    depart_time = db.Column(db.String(20), nullable=False)
    arrive_time = db.Column(db.String(20), nullable=False)
    depart_date = db.Column(db.Date, nullable=True)
    duration_mins = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    seats_left = db.Column(db.Integer, default=100)
    cabin_class = db.Column(db.String(20), default='Economy')
    
    # Relationships
    booking_items = db.relationship('BookingItem', backref='flight', lazy=True)

class Hotel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False, index=True)
    rating = db.Column(db.Float, nullable=False)
    price_per_night = db.Column(db.Float, nullable=False)
    amenities_json = db.Column(db.Text)
    image_path = db.Column(db.String(200))
    description = db.Column(db.Text)
    
    # Relationships
    booking_items = db.relationship('BookingItem', backref='hotel', lazy=True)
    
    @property
    def amenities(self):
        if self.amenities_json:
            try:
                return json.loads(self.amenities_json)
            except:
                return []
        return []
    
    @amenities.setter
    def amenities(self, amenities_list):
        self.amenities_json = json.dumps(amenities_list)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    booking_code = db.Column(db.String(20), unique=True, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR')
    status = db.Column(db.String(20), default='CONFIRMED')
    customer_name = db.Column(db.String(100), nullable=True)
    customer_email = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(20))
    payment_method = db.Column(db.String(20), default='card')  # card, upi, netbanking, wallet, cash
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    items = db.relationship('BookingItem', backref='booking', lazy=True, cascade='all, delete-orphan')

class BookingItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # FLIGHT or HOTEL
    ref_id = db.Column(db.Integer, nullable=False)  # flight_id or hotel_id
    title = db.Column(db.String(200), nullable=False)
    details_json = db.Column(db.Text)
    amount = db.Column(db.Float, nullable=False)
    
    # Foreign keys for specific types
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=True)
    
    @property
    def details(self):
        if self.details_json:
            try:
                return json.loads(self.details_json)
            except:
                return {}
        return {}
    
    @details.setter
    def details(self, details_dict):
        self.details_json = json.dumps(details_dict)


class FailureMode(db.Model):
    """
    Singleton-style chaos engineering control row.
    A row with id=1 always exists and holds every live toggle.
    The scheduler (app/services/chaos_scheduler.py) flips these on/off
    automatically so Site24x7 sees realistic outage windows; admins can
    also toggle them manually at /admin/chaos for live demos.
    """
    id = db.Column(db.Integer, primary_key=True)

    # Master kill-switch
    enabled = db.Column(db.Boolean, default=True, nullable=False)

    # Auth / login failures (0.0 - 1.0 probability)
    login_failure_rate = db.Column(db.Float, default=0.0, nullable=False)
    login_slowdown_ms = db.Column(db.Integer, default=0, nullable=False)

    # Database / SQL
    db_slowdown_ms = db.Column(db.Integer, default=0, nullable=False)
    db_down = db.Column(db.Boolean, default=False, nullable=False)

    # Search path
    search_timeout_rate = db.Column(db.Float, default=0.0, nullable=False)
    search_slowdown_ms = db.Column(db.Integer, default=0, nullable=False)

    # Booking / checkout
    checkout_exception_rate = db.Column(db.Float, default=0.0, nullable=False)
    checkout_slowdown_ms = db.Column(db.Integer, default=0, nullable=False)

    # Payment gateway
    payment_gateway_down = db.Column(db.Boolean, default=False, nullable=False)
    payment_failure_rate = db.Column(db.Float, default=0.0, nullable=False)

    # Mobile / REST API
    api_5xx_rate = db.Column(db.Float, default=0.0, nullable=False)
    api_slowdown_ms = db.Column(db.Integer, default=0, nullable=False)

    # Active outage window (set by scheduler)
    outage_label = db.Column(db.String(100), nullable=True)
    outage_started_at = db.Column(db.DateTime, nullable=True)
    outage_ends_at = db.Column(db.DateTime, nullable=True)

    # ── Section 1: Page Load Performance Chaos ──────────────────────────
    page_load_chaos = db.Column(db.Boolean, default=False, nullable=False)
    # Server-side sleep injected before every matching page response (ms)
    page_load_delay_ms = db.Column(db.Integer, default=0, nullable=False)
    # JSON list of blueprint slug targets, e.g. '["all"]' or '["flights","hotels"]'
    page_load_target_pages = db.Column(db.Text, default='["all"]', nullable=False)
    # Client-side JS injections
    page_load_inject_js_errors = db.Column(db.Boolean, default=False, nullable=False)
    page_load_inject_resource_failures = db.Column(db.Boolean, default=False, nullable=False)
    page_load_inject_memory_pressure = db.Column(db.Boolean, default=False, nullable=False)
    page_load_inject_render_blocking = db.Column(db.Boolean, default=False, nullable=False)
    page_load_large_payload = db.Column(db.Boolean, default=False, nullable=False)

    # ── Section 2: Functionality Failures Chaos ──────────────────────────
    func_chaos = db.Column(db.Boolean, default=False, nullable=False)
    func_search_empty = db.Column(db.Boolean, default=False, nullable=False)
    func_form_errors = db.Column(db.Boolean, default=False, nullable=False)
    func_broken_images = db.Column(db.Boolean, default=False, nullable=False)
    func_session_kill_rate = db.Column(db.Float, default=0.0, nullable=False)
    func_404_storm_rate = db.Column(db.Float, default=0.0, nullable=False)
    func_infinite_spin = db.Column(db.Boolean, default=False, nullable=False)
    func_broken_cta = db.Column(db.Boolean, default=False, nullable=False)

    # ── Section 3: Component-Level Chaos ────────────────────────────────
    # Page returns 200 but specific UI components break (JS/CSS failures)
    component_chaos = db.Column(db.Boolean, default=False, nullable=False)
    # 0-100: % chance per page load that component chaos fires
    component_chaos_rate = db.Column(db.Integer, default=50, nullable=False)
    # JSON list of target pages, same pattern as page_load_target_pages
    component_target_pages = db.Column(db.Text, default='["all"]', nullable=False)
    # Which components to break
    component_break_search  = db.Column(db.Boolean, default=False, nullable=False)
    component_break_results = db.Column(db.Boolean, default=False, nullable=False)
    component_break_booking = db.Column(db.Boolean, default=False, nullable=False)
    component_break_pricing = db.Column(db.Boolean, default=False, nullable=False)
    component_break_css     = db.Column(db.Boolean, default=False, nullable=False)
    component_break_nav     = db.Column(db.Boolean, default=False, nullable=False)

    # ── New Page Load injections (Section 1 additions) ───────────────────
    page_load_webfont_failure  = db.Column(db.Boolean, default=False, nullable=False)
    page_load_ttfb_spike       = db.Column(db.Boolean, default=False, nullable=False)
    page_load_cache_chaos      = db.Column(db.Boolean, default=False, nullable=False)

    # ── New Functionality Failures (Section 2 additions) ─────────────────
    func_wrong_search      = db.Column(db.Boolean, default=False, nullable=False)
    func_fake_soldout      = db.Column(db.Boolean, default=False, nullable=False)
    func_date_picker_broken = db.Column(db.Boolean, default=False, nullable=False)
    func_otp_invalid       = db.Column(db.Boolean, default=False, nullable=False)
    func_email_chaos       = db.Column(db.Boolean, default=False, nullable=False)
    func_maintenance_flood = db.Column(db.Boolean, default=False, nullable=False)

    # ── New Component Failures (Section 3 additions) ──────────────────────
    component_break_autocomplete = db.Column(db.Boolean, default=False, nullable=False)
    component_break_datepicker   = db.Column(db.Boolean, default=False, nullable=False)
    component_break_ratings      = db.Column(db.Boolean, default=False, nullable=False)
    component_break_loyalty      = db.Column(db.Boolean, default=False, nullable=False)

    # ── Section 4: A/B Test Chaos ─────────────────────────────────────────
    # Visually identical pages but with mutated identifiers — breaks analytics,
    # synthetic monitors, and A/B testing tools that rely on element selectors.
    ab_test_chaos          = db.Column(db.Boolean, default=False, nullable=False)
    ab_test_login          = db.Column(db.Boolean, default=False, nullable=False)
    ab_test_search         = db.Column(db.Boolean, default=False, nullable=False)
    ab_test_booking        = db.Column(db.Boolean, default=False, nullable=False)
    ab_test_profile        = db.Column(db.Boolean, default=False, nullable=False)

    # ── Engine settings ───────────────────────────────────────────────────
    # 0=Low 1=Medium 2=High 3=Critical — auto-chaos runners scale intensities
    chaos_intensity = db.Column(db.Integer, default=1, nullable=False)
    # Webhook URL to notify when auto-chaos starts/ends (Slack, Teams, PagerDuty)
    webhook_url     = db.Column(db.String(500), nullable=True)

    # ── Auto Chaos Mode (plug-and-play single-toggle) ────────────────────
    # When True, the scheduler automatically fires all 4 chaos categories
    # throughout the day with ≥2-hour gaps — no manual config needed.
    auto_chaos_mode         = db.Column(db.Boolean, default=False, nullable=False)
    # Tracks which auto-pilot event is currently live
    auto_chaos_current_type = db.Column(db.String(60),  nullable=True)
    # When the current auto-pilot segment ends (used by cleanup job)
    auto_chaos_ends_at      = db.Column(db.DateTime,    nullable=True)
    # JSON list of today's scheduled windows: [{"type":…,"start":…,"end":…}, …]
    auto_chaos_schedule_json = db.Column(db.Text,       nullable=True)
    # JSON list of excluded chaos types: ["ab_test","component_chaos"]
    auto_chaos_excluded_json = db.Column(db.Text,       nullable=True)

    # Audit
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(120), nullable=True)

    @classmethod
    def current(cls):
        """Always return the singleton row, creating it if missing."""
        row = cls.query.get(1)
        if row is None:
            row = cls(id=1)
            db.session.add(row)
            db.session.commit()
        return row

    def to_dict(self):
        return {
            'enabled': self.enabled,
            'login_failure_rate': self.login_failure_rate,
            'login_slowdown_ms': self.login_slowdown_ms,
            'db_slowdown_ms': self.db_slowdown_ms,
            'db_down': self.db_down,
            'search_timeout_rate': self.search_timeout_rate,
            'search_slowdown_ms': self.search_slowdown_ms,
            'checkout_exception_rate': self.checkout_exception_rate,
            'checkout_slowdown_ms': self.checkout_slowdown_ms,
            'payment_gateway_down': self.payment_gateway_down,
            'payment_failure_rate': self.payment_failure_rate,
            'api_5xx_rate': self.api_5xx_rate,
            'api_slowdown_ms': self.api_slowdown_ms,
            # Page Load Chaos
            'page_load_chaos': self.page_load_chaos,
            'page_load_delay_ms': self.page_load_delay_ms,
            'page_load_target_pages': self.page_load_target_pages,
            'page_load_inject_js_errors': self.page_load_inject_js_errors,
            'page_load_inject_resource_failures': self.page_load_inject_resource_failures,
            'page_load_inject_memory_pressure': self.page_load_inject_memory_pressure,
            'page_load_inject_render_blocking': self.page_load_inject_render_blocking,
            'page_load_large_payload': self.page_load_large_payload,
            # Functionality Chaos
            'func_chaos': self.func_chaos,
            'func_search_empty': self.func_search_empty,
            'func_form_errors': self.func_form_errors,
            'func_broken_images': self.func_broken_images,
            'func_session_kill_rate': self.func_session_kill_rate,
            'func_404_storm_rate': self.func_404_storm_rate,
            'func_infinite_spin': self.func_infinite_spin,
            'func_broken_cta': self.func_broken_cta,
            # Component Chaos
            'component_chaos': self.component_chaos,
            'component_chaos_rate': self.component_chaos_rate,
            'component_target_pages': self.component_target_pages,
            'component_break_search': self.component_break_search,
            'component_break_results': self.component_break_results,
            'component_break_booking': self.component_break_booking,
            'component_break_pricing': self.component_break_pricing,
            'component_break_css': self.component_break_css,
            'component_break_nav': self.component_break_nav,
            # New Page Load
            'page_load_webfont_failure': self.page_load_webfont_failure,
            'page_load_ttfb_spike': self.page_load_ttfb_spike,
            'page_load_cache_chaos': self.page_load_cache_chaos,
            # New Functionality
            'func_wrong_search': self.func_wrong_search,
            'func_fake_soldout': self.func_fake_soldout,
            'func_date_picker_broken': self.func_date_picker_broken,
            'func_otp_invalid': self.func_otp_invalid,
            'func_email_chaos': self.func_email_chaos,
            'func_maintenance_flood': self.func_maintenance_flood,
            # New Components
            'component_break_autocomplete': self.component_break_autocomplete,
            'component_break_datepicker': self.component_break_datepicker,
            'component_break_ratings': self.component_break_ratings,
            'component_break_loyalty': self.component_break_loyalty,
            # A/B Test Chaos
            'ab_test_chaos': self.ab_test_chaos,
            'ab_test_login': self.ab_test_login,
            'ab_test_search': self.ab_test_search,
            'ab_test_booking': self.ab_test_booking,
            'ab_test_profile': self.ab_test_profile,
            # Engine settings
            'chaos_intensity': self.chaos_intensity,
            'webhook_url': self.webhook_url,
            # Outage window
            'outage_label': self.outage_label,
            'outage_started_at': self.outage_started_at.isoformat() if self.outage_started_at else None,
            'outage_ends_at': self.outage_ends_at.isoformat() if self.outage_ends_at else None,
            # Auto Chaos Mode
            'auto_chaos_mode': self.auto_chaos_mode,
            'auto_chaos_current_type': self.auto_chaos_current_type,
            'auto_chaos_ends_at': self.auto_chaos_ends_at.isoformat() if self.auto_chaos_ends_at else None,
            'auto_chaos_schedule_json': self.auto_chaos_schedule_json,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
        }


class ChaosEvent(db.Model):
    """
    Audit log of every failure-injection event (scheduled or manual).
    Lets us prove to Site24x7 dashboards that an outage was chaos-induced
    and correlate it with the RCA timeline.
    """
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)  # 'OUTAGE_START', 'OUTAGE_END', 'MANUAL_TOGGLE', 'INJECTED_ERROR'
    label = db.Column(db.String(200), nullable=True)
    details_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @property
    def details(self):
        if self.details_json:
            try:
                return json.loads(self.details_json)
            except Exception:
                return {}
        return {}

    @details.setter
    def details(self, d):
        self.details_json = json.dumps(d)


# ======================================================================
# Holiday Packages
# ======================================================================
class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    destination = db.Column(db.String(100), nullable=False, index=True)
    country = db.Column(db.String(100), nullable=False, default='India')
    tag = db.Column(db.String(50), nullable=True)          # 'BESTSELLER', 'NEW', 'DEAL'
    description = db.Column(db.Text, nullable=True)
    duration_nights = db.Column(db.Integer, nullable=False, default=5)
    base_price = db.Column(db.Float, nullable=False)
    original_price = db.Column(db.Float, nullable=True)    # for showing crossed-out price
    image_path = db.Column(db.String(300), nullable=True)
    includes_flight = db.Column(db.Boolean, default=True)
    includes_hotel = db.Column(db.Boolean, default=True)
    includes_meals = db.Column(db.Boolean, default=False)
    includes_transfers = db.Column(db.Boolean, default=True)
    highlights_json = db.Column(db.Text, nullable=True)
    itinerary_json = db.Column(db.Text, nullable=True)
    max_persons = db.Column(db.Integer, default=8)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Fake "bookings today" counter — generates a stable random number from the id
    @property
    def bookings_today(self):
        return 5 + (self.id * 7) % 23

    @property
    def highlights(self):
        if self.highlights_json:
            try:
                return json.loads(self.highlights_json)
            except Exception:
                return []
        return []

    @highlights.setter
    def highlights(self, lst):
        self.highlights_json = json.dumps(lst)

    @property
    def itinerary(self):
        if self.itinerary_json:
            try:
                return json.loads(self.itinerary_json)
            except Exception:
                return []
        return []

    @itinerary.setter
    def itinerary(self, lst):
        self.itinerary_json = json.dumps(lst)

    @property
    def discount_pct(self):
        if self.original_price and self.original_price > self.base_price:
            return int(100 - (self.base_price / self.original_price * 100))
        return 0


# ======================================================================
# Promo Codes
# ======================================================================
class PromoCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    description = db.Column(db.String(200), nullable=True)
    discount_type = db.Column(db.String(10), nullable=False, default='PERCENT')  # PERCENT | FLAT
    discount_value = db.Column(db.Float, nullable=False)   # % or INR
    min_amount = db.Column(db.Float, default=0.0)
    max_discount = db.Column(db.Float, nullable=True)      # cap on PERCENT discounts
    max_uses = db.Column(db.Integer, nullable=True)        # None = unlimited
    used_count = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_valid(self, amount=0):
        if not self.active:
            return False, 'Promo code is no longer active.'
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False, 'Promo code has expired.'
        if self.max_uses and self.used_count >= self.max_uses:
            return False, 'Promo code usage limit reached.'
        if amount < self.min_amount:
            return False, f'Minimum order amount is ₹{self.min_amount:,.0f}.'
        return True, 'Valid'

    def compute_discount(self, amount):
        if self.discount_type == 'PERCENT':
            disc = amount * (self.discount_value / 100)
            if self.max_discount:
                disc = min(disc, self.max_discount)
            return round(disc, 2)
        else:
            return min(self.discount_value, amount)


# ======================================================================
# Reviews
# ======================================================================
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    review_type = db.Column(db.String(20), nullable=False, index=True)  # HOTEL | FLIGHT | PACKAGE
    ref_id = db.Column(db.Integer, nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)          # 1-5
    title = db.Column(db.String(150), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    verified_booking = db.Column(db.Boolean, default=False) # True if user actually booked
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('reviews', lazy=True))

    @property
    def stars(self):
        return '★' * self.rating + '☆' * (5 - self.rating)


# ======================================================================
# Wishlist
# ======================================================================
class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_type = db.Column(db.String(20), nullable=False)    # FLIGHT | HOTEL | PACKAGE
    ref_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'item_type', 'ref_id', name='uq_wishlist'),
    )


# ======================================================================
# Activities
# ======================================================================
class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False, default='Sightseeing')
    description = db.Column(db.Text, nullable=True)
    price_per_person = db.Column(db.Float, nullable=False, default=999.0)
    original_price = db.Column(db.Float, nullable=True)   # struck-through price
    includes_json = db.Column(db.Text, nullable=True)      # e.g. ["Guide","Equipment","Lunch"]
    duration_hours = db.Column(db.Float, default=3.0)
    min_persons = db.Column(db.Integer, default=1)
    max_persons = db.Column(db.Integer, default=20)
    rating = db.Column(db.Float, default=4.0)
    review_count = db.Column(db.Integer, default=0)
    image_path = db.Column(db.String(300), nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def discount_pct(self):
        if self.original_price and self.original_price > self.price_per_person:
            return int(round((self.original_price - self.price_per_person) / self.original_price * 100))
        return 0

    @property
    def duration_label(self):
        h = self.duration_hours or 0
        if h < 1:
            return f"{int(h * 60)} mins"
        elif h == int(h):
            return f"{int(h)} hrs"
        else:
            hrs = int(h)
            mins = int((h - hrs) * 60)
            return f"{hrs}h {mins}m"

    @property
    def includes(self):
        if self.includes_json:
            try:
                return json.loads(self.includes_json)
            except Exception:
                return []
        return []

    @includes.setter
    def includes(self, lst):
        self.includes_json = json.dumps(lst)


# ======================================================================
# Transport — Bus
# ======================================================================
class Bus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bus_no = db.Column(db.String(20), unique=True, nullable=False)
    operator = db.Column(db.String(100), nullable=False)
    origin = db.Column(db.String(100), nullable=False, index=True)
    destination = db.Column(db.String(100), nullable=False, index=True)
    depart_time = db.Column(db.String(10), nullable=False)
    arrive_time = db.Column(db.String(10), nullable=False)
    duration_mins = db.Column(db.Integer, default=300)
    bus_type = db.Column(db.String(50), default='AC Sleeper')  # AC Sleeper/Volvo/Non-AC
    price = db.Column(db.Float, nullable=False)
    seats_left = db.Column(db.Integer, default=40)
    amenities = db.Column(db.Text, nullable=True)             # comma-separated


# ======================================================================
# Transport — Train
# ======================================================================
class Train(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    train_no = db.Column(db.String(20), unique=True, nullable=False)
    train_name = db.Column(db.String(200), nullable=False)
    train_type = db.Column(db.String(50), default='Express')   # Superfast/Express/Passenger
    run_days = db.Column(db.String(50), default='Daily')       # Daily/Mon-Sat/Mon Wed Fri
    origin = db.Column(db.String(100), nullable=False, index=True)
    destination = db.Column(db.String(100), nullable=False, index=True)
    depart_time = db.Column(db.String(10), nullable=False)
    arrive_time = db.Column(db.String(10), nullable=False)
    duration_mins = db.Column(db.Integer, default=480)
    distance_km = db.Column(db.Integer, default=500)
    # Class-wise fares and availability
    sleeper_fare = db.Column(db.Float, default=350.0)
    sleeper_seats = db.Column(db.Integer, default=200)
    third_ac_fare = db.Column(db.Float, default=900.0)
    third_ac_seats = db.Column(db.Integer, default=64)
    second_ac_fare = db.Column(db.Float, default=1300.0)
    second_ac_seats = db.Column(db.Integer, default=46)
    first_ac_fare = db.Column(db.Float, default=2400.0)
    first_ac_seats = db.Column(db.Integer, default=18)


# ======================================================================
# Transport — Cab
# ======================================================================
class Cab(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_type = db.Column(db.String(50), nullable=False)  # Sedan/SUV/Hatchback
    brand = db.Column(db.String(100), nullable=False, default='Swift Dzire')
    base_fare = db.Column(db.Float, nullable=False, default=10.0)   # ₹ per km
    base_km = db.Column(db.Float, default=10.0)                     # included km
    base_amount = db.Column(db.Float, default=100.0)                # minimum charge
    capacity = db.Column(db.Integer, default=4)
    ac = db.Column(db.Boolean, default=True)
    available = db.Column(db.Boolean, default=True)
    image_path = db.Column(db.String(300), nullable=True)

    def estimate_fare(self, distance_km):
        """Calculate estimated fare for a given distance."""
        extra_km = max(0, distance_km - self.base_km)
        return round(self.base_amount + extra_km * self.base_fare, 2)


# ======================================================================
# Insurance
# ======================================================================
class InsurancePlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)           # Basic/Standard/Premium
    description = db.Column(db.Text, nullable=True)
    price_per_person_per_day = db.Column(db.Float, nullable=False, default=50.0)
    medical_cover = db.Column(db.Float, default=500000.0)      # ₹
    trip_cancellation = db.Column(db.Boolean, default=False)
    baggage_loss = db.Column(db.Boolean, default=False)
    flight_delay = db.Column(db.Boolean, default=False)
    adventure_sports = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)

    # ── Display helpers used by insurance.html ──────────────────
    @property
    def highlighted(self):
        """Mark Standard plan as 'Most Popular'."""
        return self.name.lower() == 'standard'

    @property
    def color(self):
        mapping = {'basic': 'primary', 'standard': 'success', 'premium': 'purple'}
        return mapping.get(self.name.lower(), 'primary')

    @property
    def tagline(self):
        mapping = {
            'basic': 'Essential coverage for short trips',
            'standard': 'Best value for most travellers',
            'premium': 'Complete protection for peace of mind',
        }
        return mapping.get(self.name.lower(), '')

    @property
    def coverage(self):
        """Return a list of coverage dicts compatible with insurance.html."""
        items = []
        if self.medical_cover:
            items.append({'label': 'Medical Cover', 'limit': f'₹{self.medical_cover:,.0f}'})
        if self.trip_cancellation:
            items.append({'label': 'Trip Cancellation Cover'})
        if self.baggage_loss:
            items.append({'label': 'Baggage Loss / Delay'})
        if self.flight_delay:
            items.append({'label': 'Flight Delay Compensation'})
        if self.adventure_sports:
            items.append({'label': 'Adventure Sports Cover'})
        return items


# ======================================================================
# Blog / Travel Guides
# ======================================================================
class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    slug = db.Column(db.String(300), unique=True, nullable=False)
    destination = db.Column(db.String(100), nullable=True, index=True)
    category = db.Column(db.String(100), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=True)
    author_name = db.Column(db.String(100), default='SnapTravels Team')
    cover_image = db.Column(db.String(300), nullable=True)
    tags_json = db.Column(db.Text, nullable=True)
    views = db.Column(db.Integer, default=0)
    published = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def tags(self):
        if self.tags_json:
            try:
                return json.loads(self.tags_json)
            except Exception:
                return []
        return []

    @tags.setter
    def tags(self, lst):
        self.tags_json = json.dumps(lst)

    # ── Template / blueprint aliases ────────────────────────────
    @property
    def featured_image(self):
        """Alias for cover_image used in blog_listing.html and blog blueprint."""
        return self.cover_image

    @featured_image.setter
    def featured_image(self, value):
        self.cover_image = value

    @property
    def excerpt(self):
        """Alias for summary used in blog_listing.html and blog blueprint."""
        return self.summary

    @excerpt.setter
    def excerpt(self, value):
        self.summary = value

    @property
    def author(self):
        """Alias for author_name used in blog blueprint."""
        return self.author_name

    @author.setter
    def author(self, value):
        self.author_name = value


# ======================================================================
# Trips (user-created trip plans)
# ======================================================================
class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    destination = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('TripItem', backref='trip', lazy=True,
                            cascade='all, delete-orphan',
                            order_by='TripItem.day_number, TripItem.id')


class TripItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    item_type = db.Column(db.String(50), nullable=False)  # NOTE/FLIGHT/HOTEL/ACTIVITY
    day_number = db.Column(db.Integer, default=1)
    title = db.Column(db.String(300), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ======================================================================
# Notifications
# ======================================================================
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    type = db.Column(db.String(30), default='INFO')   # BOOKING/CANCELLATION/OFFER/INFO
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(300), nullable=True)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ── Site Configuration ────────────────────────────────────────────────────────

class SiteConfig(db.Model):
    """Simple key-value store for site-wide admin settings."""
    __tablename__ = 'site_config'
    id         = db.Column(db.Integer, primary_key=True)
    key        = db.Column(db.String(80), unique=True, nullable=False, index=True)
    value      = db.Column(db.String(255), nullable=False, default='')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get(cls, key: str, default: str = '') -> str:
        """Return the config value for key, or default if not found."""
        row = cls.query.filter_by(key=key).first()
        return row.value if row else default

    @classmethod
    def set(cls, key: str, value: str) -> None:
        """Upsert a config value."""
        row = cls.query.filter_by(key=key).first()
        if row:
            row.value = value
            row.updated_at = datetime.utcnow()
        else:
            db.session.add(cls(key=key, value=value))
        db.session.commit()


# ======================================================================
# Saved Travelers
# ======================================================================
class TravelerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    full_name = db.Column(db.String(200), nullable=False)
    gender = db.Column(db.String(20), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    nationality = db.Column(db.String(100), default='Indian')
    id_type = db.Column(db.String(50), nullable=True)    # Aadhaar/PAN/Passport
    id_number = db.Column(db.String(100), nullable=True)
    passport_no = db.Column(db.String(50), nullable=True)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ======================================================================
# Rewards & Loyalty
# ======================================================================
class RewardPoints(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    points = db.Column(db.Integer, default=0)
    lifetime_points = db.Column(db.Integer, default=0)
    tier = db.Column(db.String(20), default='Silver')  # Silver/Gold/Platinum


class PointsTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    points = db.Column(db.Integer, nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)  # EARN/REDEEM
    description = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ======================================================================
# Price Alerts
# ======================================================================
class PriceAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    alert_type = db.Column(db.String(10), nullable=False)   # FLIGHT/HOTEL
    origin = db.Column(db.String(100), nullable=True)
    destination = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    target_price = db.Column(db.Float, nullable=False)
    triggered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ======================================================================
# Recently Viewed
# ======================================================================
class RecentlyViewed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    item_type = db.Column(db.String(20), nullable=False)   # HOTEL/FLIGHT/PACKAGE/ACTIVITY
    ref_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=True)
    image_path = db.Column(db.String(300), nullable=True)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)


# ======================================================================
# Hotel extras (for admin image gallery and room types)
# ======================================================================
class HotelImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False, index=True)
    image_url = db.Column(db.String(500), nullable=False)
    sort_order = db.Column(db.Integer, default=0)


class RoomType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)         # Deluxe/Suite/Standard
    price = db.Column(db.Float, nullable=False)
    capacity = db.Column(db.Integer, default=2)
    available = db.Column(db.Boolean, default=True)


# ======================================================================
# Admin Audit Log
# ======================================================================
class AdminAuditLog(db.Model):
    """
    Immutable record of every admin action — who did what, when, and on
    which object. Written by the @audit_admin_action decorator in
    app/services/audit.py.  Never update or delete rows here.
    """
    __tablename__ = 'admin_audit_log'
    id          = db.Column(db.Integer, primary_key=True)
    admin_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    admin_email = db.Column(db.String(120), nullable=True)   # denormed for readability
    action      = db.Column(db.String(80),  nullable=False, index=True)  # e.g. FLIGHT_CREATE
    target_type = db.Column(db.String(50),  nullable=True)   # FLIGHT / HOTEL / USER / etc.
    target_id   = db.Column(db.Integer,     nullable=True)
    target_label= db.Column(db.String(200), nullable=True)   # human-readable name
    detail_json = db.Column(db.Text,        nullable=True)   # JSON snapshot of changed data
    ip_address  = db.Column(db.String(50),  nullable=True)
    user_agent  = db.Column(db.String(400), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @property
    def detail(self):
        import json
        try:
            return json.loads(self.detail_json) if self.detail_json else {}
        except Exception:
            return {}

    @detail.setter
    def detail(self, value):
        import json
        self.detail_json = json.dumps(value, default=str) if value else None
