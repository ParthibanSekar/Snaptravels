# SnapTravels — Tech Stack & Project Structure

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask 3.x |
| ORM | Flask-SQLAlchemy |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Auth | Flask sessions + Werkzeug password hashing |
| Forms | Flask-WTF (CSRF on all forms; mobile_api + pwa are exempt) |
| Rate Limiting | Flask-Limiter (Redis or in-memory) |
| Email | Flask-Mail (SMTP) |
| 2FA | TOTP (pyotp, Fernet-encrypted) + Email OTP |
| Chaos Engine | APScheduler + custom FailureMode DB model |
| Observability | Site24x7 RUM beacon, JSON structured logs, trace ID middleware |
| Deployment | Replit Autoscale OR Ubuntu + Nginx + systemd (see DEPLOYMENT_GUIDE.md) |

---

## Project Directory

```
snaptravels-final-production-build-2/
├── main.py                      # Entry point — runs Flask dev server
├── config.py                    # Config class (all settings from env)
├── app/
│   ├── __init__.py              # create_app() factory, registers all blueprints
│   ├── models.py                # All SQLAlchemy models
│   ├── forms.py                 # All Flask-WTF form classes
│   ├── commands.py              # Flask CLI commands (flask seed-db)
│   ├── blueprints/              # One file per feature area
│   │   ├── auth.py              # /login /signup /logout
│   │   ├── public.py            # / /flights /hotels /booking /payment
│   │   ├── admin.py             # /admin/* CRUD for flights/hotels/bookings
│   │   ├── admin_extended.py    # /admin/* users/refunds/revenue/packages/promos
│   │   ├── chaos_admin.py       # /admin/chaos (chaos control panel)
│   │   ├── user_dashboard.py    # /dashboard /profile /security /wishlist
│   │   ├── trips.py             # /trips (trip planner)
│   │   ├── packages.py          # /packages
│   │   ├── activities.py        # /activities
│   │   ├── buses.py             # /buses + /bus-book/<id>
│   │   ├── trains.py            # /trains + /train-book/<id>
│   │   ├── cabs.py              # /cabs + /cab-book/<id>
│   │   ├── insurance.py         # /insurance
│   │   ├── reviews.py           # /reviews /wishlist/toggle /promo/validate
│   │   ├── blog.py              # /blog
│   │   ├── mobile_api.py        # /mobile-api/v1/* (REST, JWT, CSRF-exempt)
│   │   ├── pwa.py               # PWA manifest + service worker
│   │   └── two_factor.py        # /2fa/* (TOTP setup, OTP, backup codes)
│   ├── services/
│   │   ├── auth.py              # login_required / roles_required decorators
│   │   ├── booking.py           # BookingService (create, seat deduction)
│   │   ├── search.py            # SearchService (flights, hotels, popular)
│   │   ├── chaos.py             # maybe_fail_login / maybe_fail_db / etc.
│   │   ├── chaos_scheduler.py   # APScheduler: auto daily outage windows
│   │   ├── audit.py             # Audit log helpers
│   │   ├── email.py             # Flask-Mail email sending
│   │   ├── observability.py     # Trace ID middleware, JSON logging
│   │   ├── seeder.py            # Seeds DB (flights, hotels, packages, etc.)
│   │   └── two_factor.py        # TOTP/OTP generation & verification
│   └── templates/
│       ├── layouts/
│       │   ├── base.html        # Master layout (navbar, footer, RUM beacon)
│       │   └── auth_base.html   # Minimal layout for login/signup
│       └── [all page templates]
├── assets/                      # Hotel/package images
├── snap_docs/                   # ← Claude session guide (this folder)
├── CHAOS_README.md
├── DEPLOYMENT_GUIDE.md
└── Dockerfile
```

---

## All Database Models (app/models.py)

| Model | Key Fields | Notes |
|---|---|---|
| `User` | id, email, password_hash, role, name, phone, totp_secret, email_otp_enabled | role = 'user' or 'admin' |
| `BackupCode` | user_id, code_hash, used | 8 codes per user |
| `TwoFactorLog` | user_id, event_type, ip, timestamp | Audit trail |
| `Flight` | origin, destination, depart_time, arrive_time, price, seats_left, cabin_class, airline, flight_no, duration_mins | |
| `Hotel` | name, city, rating, price_per_night, amenities, image_url, rooms_left | |
| `Booking` | user_id, booking_code, total, status, created_at | status: confirmed/cancelled |
| `BookingItem` | booking_id, item_type, item_id, quantity, unit_price | item_type: FLIGHT/HOTEL/BUS/TRAIN/CAB |
| `FailureMode` | (singleton) login_storm, db_slowdown, db_unavailable, payment_gateway_down, checkout_exceptions, search_upstream_timeout, api_5xx_storm | All boolean + rate fields |
| `ChaosEvent` | event_type, triggered_by, note, timestamp | Chaos audit log |
| `Package` | name, destination, duration_days, price, inclusions, itinerary, image_url | |
| `PromoCode` | code, discount_type, discount_value, max_uses, times_used, expiry_date | PERCENT or FLAT |
| `Review` | user_id, item_type, item_id, rating, comment, created_at | |
| `Wishlist` | user_id, item_type, item_id | |
| `Activity` | name, city, category, price, duration_hrs, image_url | |
| `Bus` | bus_no, operator, origin, destination, depart_time, arrive_time, duration_mins, bus_type, price, seats_left, amenities | |
| `Train` | train_no, train_name, train_type, origin, destination, depart_time, arrive_time, duration_mins, distance_km, sl_fare, ac3_fare, ac2_fare, ac1_fare | |
| `Cab` | vehicle_name, brand, vehicle_type, capacity, per_km_fare, base_fare, ac, image_url | |
| `InsurancePlan` | name, plan_type, coverage_amount, premium, features | |

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | `snaptravels-dev-key-2024` | Flask session encryption |
| `DATABASE_URL` | `sqlite:///snaptravels.db` | DB connection string |
| `MAIL_SERVER` | `smtp.gmail.com` | SMTP server |
| `MAIL_USERNAME` | none | Email disabled if not set |
| `MAIL_PASSWORD` | none | SMTP password |
| `REDIS_URL` | `memory://` | Rate limiter backend |
| `CHAOS_SCHEDULER_ENABLED` | `0` | `1` = auto daily outages |
| `SITE24X7_RUM_APP_KEY` | none | Injects RUM beacon |
| `APP_ENV` | `development` | Shown in health/metrics |
| `SNAPTRAVELS_JSON_LOGS` | unset | `1` = structured JSON logs |

---

## How to Run

```bash
source venv/bin/activate
python main.py            # → http://localhost:5000

# Seed demo data
flask seed-db
```

**Test accounts:**
- User: `parthiban@snaptravels.online` / `Test@123`
- Admin: `admin@snaptravels.online` / `Admin@123`
