# SnapTravels — Project Skill Context

Use this file to onboard a new Claude session about the SnapTravels project. Read this before making any changes.

---

## Project Overview

SnapTravels is a full-stack travel booking platform built with Python Flask. It's used as a demo/testing app for monitoring tools (APM, RUM, Synthetic, Mobile APM). It includes a built-in chaos engineering console for injecting realistic failures across web and mobile.

**Live URL:** http://snaptravels.online (Nginx on port 80 → Flask on port 5000)
**GitHub:** https://github.com/ParthibanSekar/Snaptravels (public repo)
**Server:** Debian, deployed at /root/DemoApp/snaptravels-new/

---

## Tech Stack

- **Backend:** Python 3.10+, Flask 3.x, SQLAlchemy, APScheduler
- **Database:** SQLite (instance/snaptravels.db)
- **Frontend (web):** Bootstrap 5, Bootstrap Icons, vanilla JS, Web Components (Shadow DOM)
- **Mobile app:** React Native (Expo SDK 51), TypeScript — repo: `Snaptravels_Android/`
- **Monitoring:** Site24x7 APM (apminsight Python agent) + RUM (JS beacon) + Mobile APM
- **Server:** Nginx reverse proxy (port 80) → Flask (port 5000)

---

## Key Files — Flask Backend

| File | Purpose |
|------|---------|
| `main.py` | Dev entry point with APM init |
| `wsgi.py` | Gunicorn production entry point |
| `config.py` | Flask configuration |
| `requirements.txt` | Python dependencies |
| `.env` | Environment variables (not in git) |
| `snaptravels.sh` | App manager (start/stop/restart/logs) |
| `setup_nginx.sh` | Nginx setup script |
| `verify.sh` | Post-deployment health check (30+ tests) |
| `deploy_debian12.sh` | System package installer |
| `deploy_from_github.sh` | GitHub deploy script (auto-runs `migrate_mobile_chaos.py`) |
| `migrate_mobile_chaos.py` | Safe SQLite migration — adds 9 mobile chaos columns if absent |

---

## App Structure

```
app/
├── __init__.py           # App factory, middleware (IP access, chaos hooks)
├── models.py             # All SQLAlchemy models (FailureMode has 9 mobile chaos columns)
├── forms.py              # WTForms (BookingForm with conditional card validation)
├── blueprints/
│   ├── public.py         # Flights, hotels, booking, trip planner, quick book, travel dashboard
│   ├── trains.py         # Train search & booking
│   ├── buses.py          # Bus search & booking
│   ├── cabs.py           # Cab search & booking
│   ├── packages.py       # Holiday packages
│   ├── activities.py     # Activities booking
│   ├── insurance.py      # Travel insurance
│   ├── trips.py          # My Trips CRUD
│   ├── admin.py          # Admin dashboard + IP access control
│   ├── chaos_admin.py    # Chaos console, auto chaos, docs, excluded types
│   ├── mobile_api.py     # Mobile REST API (JWT auth, all 8 booking types, chaos hooks)
│   ├── auth.py           # Login/signup/2FA
│   └── user_dashboard.py # User profile, travelers, price alerts
├── services/
│   ├── chaos.py          # Chaos injection engine (6 sections incl. mobile)
│   ├── chaos_scheduler.py # APScheduler: auto chaos continuous loop, daily cleanup
│   ├── booking.py        # BookingService.create_booking()
│   ├── sanitize.py       # Server-side input sanitization (XSS, field validation)
│   ├── data_cleanup.py   # Daily DB cleanup (500/user, 1000/admin, 2000 events)
│   ├── ip_access.py      # IP whitelist/blacklist middleware
│   └── ...
├── templates/
│   ├── layouts/base.html
│   ├── admin_chaos.html  # Chaos console (6 sections, dark-theme, all readable)
│   └── ...
└── static/
```

---

## Booking Types & Routes

| Type | Search | Book | Booking Handler |
|------|--------|------|-----------------|
| Flights | /flights | /booking | public.py → BookingService |
| Hotels | /hotels | /booking | public.py → BookingService |
| Trains | /trains/ | /trains/booking | trains.py (direct DB) |
| Buses | /buses/ | /buses/booking | buses.py (direct DB) |
| Cabs | /cabs/ | /cabs/booking | cabs.py (direct DB) |
| Packages | /packages/ | /packages/<slug>/book | packages.py (direct DB) |
| Activities | /activities/ | /activities/<id>/book | activities.py (direct DB) |
| Insurance | /insurance/ | /insurance/buy/<id> | insurance.py (direct DB) |
| Quick Book | /quick-book | /quick-book/confirm | public.py (JSON API) |

---

## Mobile API Endpoints

All under `/mobile-api/v1/`. All protected routes require `Authorization: Bearer <jwt>`.

### Auth
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| /auth/login | POST | No | Returns JWT token |
| /auth/register | POST | No | Create account |

### Search
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| /flights/search | GET | JWT | Search flights |
| /hotels/search | GET | JWT | Search hotels |
| /trains/search | GET | JWT | Search trains |
| /buses/search | GET | JWT | Search buses |
| /cabs/search | GET | JWT | Search cabs |
| /packages | GET | JWT | List packages |
| /activities | GET | JWT | List activities |
| /insurance | GET | JWT | List insurance plans |

### Bookings (all 8 types)
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| /bookings | POST | JWT | Create booking for any type |
| /bookings | GET | JWT | List user bookings (includes `type`, item IDs, items[]) |
| /bookings/<id> | GET | JWT | Get booking details |
| /bookings/<id>/cancel | POST | JWT | Cancel booking |
| /trains/book | POST | JWT | Direct train booking |
| /buses/book | POST | JWT | Direct bus booking |
| /cabs/book | POST | JWT | Direct cab booking |
| /packages/book | POST | JWT | Direct package booking |
| /activities/book | POST | JWT | Direct activity booking |
| /insurance/buy | POST | JWT | Direct insurance purchase |

### Other
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| /promo/validate | POST | JWT | Validate promo code |

### POST /bookings payload fields (by type)
```json
{
  "booking_type": "FLIGHT|HOTEL|TRAIN|BUS|CAB|PACKAGE|ACTIVITY|INSURANCE",
  "flight_id": ...,       // FLIGHT
  "hotel_id": ...,        // HOTEL
  "train_id": ...,        // TRAIN
  "bus_id": ...,          // BUS
  "cab_id": ...,          // CAB
  "package_id": ...,      // PACKAGE
  "activity_id": ...,     // ACTIVITY
  "insurance_id": ...,    // INSURANCE
  "passengers": [...],
  "payment": { "method": "card|upi|...", "card_number": "...", ... }
}
```

### GET /bookings response shape
```json
{
  "bookings": [
    {
      "id": 1,
      "type": "TRAIN",
      "train_id": 42,
      "status": "confirmed",
      "booking_code": "SN-123",
      "total_amount": 1200.0,
      "items": [{ "name": "...", "departure": "...", "arrival": "...", ... }],
      ...
    }
  ]
}
```

---

## Server-side Input Sanitization (`app/services/sanitize.py`)

All booking endpoints (web + mobile) call these before storing customer data:

```python
sanitize_str(value, max_len=200)         # strip HTML tags + html.escape
sanitize_int(value, default, min, max)
validate_name_server(name)               # letters/spaces/hyphens, 2-100 chars, no digits
validate_email_server(email)             # format regex, lowercase
validate_phone_server(phone)             # 10 digits, starts 6-9
sanitize_booking_customer(data, phone_required=True)  # returns (clean_dict, errors_dict)
```

---

## Chaos Engineering

### 6 Independent Sections
| Section | Name | Toggle Field |
|---------|------|-------------|
| §0 | Core Engine | `enabled` |
| §1 | Page Load | `page_load_chaos` |
| §2 | Functionality | `func_chaos` |
| §3 | Component | `component_chaos` |
| §4 | A/B Test | `ab_test_chaos` |
| §5 | Mobile App | `mobile_chaos` |

### Section 5 — Mobile App Chaos (8 scenarios)

These fields are on the `FailureMode` model. Migration: `migrate_mobile_chaos.py`.

| Field | Type | Effect |
|-------|------|--------|
| `mobile_chaos` | bool | Master toggle for section 5 |
| `mobile_auth_failure_rate` | float 0-1 | POST /auth/login → HTTP 401 |
| `mobile_search_slow_ms` | int 0-10000 | All /*/search → sleep N ms |
| `mobile_search_empty_rate` | float 0-1 | Search returns empty list |
| `mobile_booking_decline_rate` | float 0-1 | POST /bookings → HTTP 402 |
| `mobile_cancel_failure_rate` | float 0-1 | Cancel → HTTP 503 |
| `mobile_timeout_rate` | float 0-1 | Any endpoint → HTTP 504 |
| `mobile_rate_limit_rate` | float 0-1 | Any endpoint → HTTP 429 |
| `mobile_malform_rate` | float 0-1 | Booking response strips `booking_code` + `total_amount` |

### Chaos Functions (`app/services/chaos.py`)
```python
maybe_fail_mobile_auth()          # raises MobileAuthChaosError → 401
maybe_slow_mobile_search()        # sleeps, or returns empty=True
maybe_fail_mobile_booking()       # raises MobileBookingChaosError → 402
maybe_fail_mobile_cancel()        # raises MobileCancelChaosError → 503
maybe_mobile_timeout()            # raises MobileTimeoutChaosError → 504
maybe_mobile_rate_limit()         # raises MobileRateLimitChaosError → 429
should_mobile_malform()           # returns bool
```

### Auto Chaos
- Continuous loop of all 6 types (or subset via exclude checkboxes)
- 30-60 min per event, 3-hour cooling gap
- Schedule stored in `FailureMode.auto_chaos_schedule_json`
- Excluded types in `FailureMode.auto_chaos_excluded_json`
- Daily reshuffle at 00:05 UTC (05:35 IST)

### Page Targets (chaos can target specific pages)
```python
PAGE_SLUG_MAP keys: flights, hotels, buses, trains, cabs, packages, activities,
                    insurance, booking, dashboard, trip-planner, quick-book,
                    travel-dashboard, home
```

---

## Android Mobile App (`Snaptravels_Android/`)

React Native (Expo SDK 51), TypeScript. Connects to Flask mobile API at `https://snaptravels.online/mobile-api/v1`.

### Key Files
| File | Purpose |
|------|---------|
| `src/api/client.ts` | Axios instance with JWT interceptor + error handling (401/402/422/429/503/504) |
| `src/api/bookings.ts` | BookingType enum (8 types), CreateBookingPayload, cancelBooking |
| `src/utils/validators.ts` | Client-side field validators + formatters |
| `src/context/AuthContext.tsx` | JWT storage, login/register/guest/logout |

### Validators (`src/utils/validators.ts`)
```typescript
validateName(v)          // no digits, 2-100 chars
validateEmail(v)
validatePhone(v)         // 10 digits, starts 6-9
validateCardNumber(v)    // 16 digits
validateCardExpiry(v)    // MM/YY not expired
validateCVV(v)           // 3-4 digits
validateCardName(v)
validateUPI(v)
validatePassenger(form)  // returns Record<string,string> errors
validatePayment(form)    // returns Record<string,string> errors
formatCardNumber(v)      // inserts spaces every 4 digits
formatExpiry(v, prev)    // auto-inserts /
formatPhone(v)           // digits only, max 10
```

### Booking Screens with Validation
- `FlightBookingScreen.tsx` — passenger + payment validation
- `HotelBookingScreen.tsx` — passenger + payment validation
- `GenericBookingScreen.tsx` — shared screen for Train/Bus/Cab/Package/Activity/Insurance
- `RegisterScreen.tsx` — name (no digits), email, phone (10 digits), password (8+ chars)
- `LoginScreen.tsx` — email format, password (8+ chars)

### BookingType enum
```typescript
type BookingType = 'FLIGHT' | 'HOTEL' | 'TRAIN' | 'BUS' | 'CAB' | 'PACKAGE' | 'ACTIVITY' | 'INSURANCE'
```

### Axios Error Handling (client.ts)
- 401 → auth failed message
- 402 → payment declined message
- 422 + `data.fields` → first field-level error message
- 429 → rate limit + retry-after
- 503 → service unavailable
- 504 → gateway timeout
- ECONNABORTED → request too slow
- No response → no internet

---

## Special Features

### Trip Planner (/trip-planner)
- 5 steps, each in its own iframe
- Step 1: SVG India map destination picker
- Step 2: Opens popup frameset (flight list frame + action frame)
- Step 3: Opens new window with SVG seat map
- Step 4: Opens popup form (price alert)
- Step 5: Review & save trip to DB
- Cross-window communication via postMessage

### Quick Book (/quick-book) — Shadow DOM
- 5-step flow using Web Components with `attachShadow({mode:'open'})`
- Components: `<snap-flight-card>`, `<snap-selection-summary>`, `<snap-passenger-form>`, `<snap-payment-widget>`, `<snap-booking-confirmation>`
- Payment widget has NESTED shadow DOM: `<snap-card-input>` and `<snap-upi-input>` inside
- Creates real bookings via POST /quick-book/confirm

### Travel Dashboard (/travel-dashboard)
- SVG charts, India route map, live booking feed
- Each section in its own iframe

### IP Access Control (/admin/ip-access)
- Whitelist/blacklist modes, stored in SiteConfig
- Admin pages always exempt

---

## Payment Methods
All booking forms support: Card, UPI, Net Banking, Wallets
- Hidden field `payment_method` in all forms
- `switchPay()` JS updates the hidden field
- Card validation conditional (skipped for non-card payments)
- Stored in `Booking.payment_method` column

---

## Data Cleanup (Daily at midnight UTC)
- Bookings: 500/user, 1000 for admin accounts
- Chaos events: 2000 total
- Notifications: 200/user
- Config in `app/services/data_cleanup.py`

---

## Rate Limits
- Global: 100,000/day, 10,000/hour
- All per-route limits: `@limiter.exempt`

---

## Deployment

### Fresh server:
```bash
git clone https://github.com/ParthibanSekar/Snaptravels.git /root/DemoApp/snaptravels
cd /root/DemoApp/snaptravels
bash deploy_debian12.sh
vi .env  # Set SECRET_KEY, S247_LICENSE_KEY, SITE24X7_RUM_APP_KEY, PORT=5000
PORT=5000 bash snaptravels.sh start
bash setup_nginx.sh --domain yourdomain.com
bash verify.sh 5000
# Note: migrate_mobile_chaos.py is auto-run by deploy_from_github.sh on updates
```

### Update (from GitHub):
```bash
bash deploy_from_github.sh
# This auto-runs: python3 migrate_mobile_chaos.py (safe, skips existing columns)
```

### Manual migration (if needed):
```bash
python3 migrate_mobile_chaos.py
```

---

## Default Accounts
- Admin: admin@snaptravels.online / Admin@123
- User: parthiban@snaptravels.online / Test@123

---

## Corporate Travel Portal (`/corporate/`)

Standalone section protected by **HTTP Basic Authentication** (`WWW-Authenticate: Basic realm="SnapTravels Corporate Portal"`). Zero dependency on Flask sessions or JWT.

### Credentials (from `.env`)
```
CORP_BASIC_USER=corp_user      (default)
CORP_BASIC_PASS=Corp@2024!     (default)
```

### Pages
| Route | Purpose |
|-------|---------|
| `GET /corporate/` | Dashboard — stats cards + quick search + 8 recent bookings |
| `GET /corporate/search` | Flight & hotel search form |
| `POST /corporate/search` | Search results (flights or hotels) |
| `GET /corporate/bookings` | Paginated full booking history with status filter |

### Blueprint file
`app/blueprints/corporate.py` — contains `requires_basic_auth` decorator, uses `db.session` queries directly, CSRF-exempt in `app/__init__.py`.

### For Site24x7 Synthetic Monitors
Set the monitor's **HTTP Authentication** to Basic, username/password from `.env`. Build a multi-step monitor:
1. `GET /corporate/` — assert `Travel Dashboard` in body
2. `POST /corporate/search` with `search_type=flight&origin=delhi&destination=mumbai` — assert `Flight Results`
3. `GET /corporate/bookings` — assert `Booking Records`

---

## Pending Items (for next session)
1. **Build Android APK** — run `eas build --platform android` or `expo build:android`
2. **Push Android app to GitHub** — `Snaptravels_Android/` not yet pushed to a separate repo
3. **Site24x7 Mobile APM integration** — add `s247-mobile-sdk` to the Expo app
4. **REST API Transaction Monitor (Site24x7)** — 5-step monitor: Login → Search → Book → Verify → Cancel
5. **Live Chaos State panel** — add §5 mobile fields to the right-column Live Chaos State snapshot in admin_chaos.html
6. **User Travel Dashboard** — personalized expense tracking, travel history, SVG charts per user
7. **Shadow DOM enhancements** — more nested components, slot-based content
