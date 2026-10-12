# SnapTravels — Project Skill Context

Read this file before making any changes to the project. It covers everything that is built, deployed, and supported.

---

## Project Overview

SnapTravels is a full-stack travel booking platform built with Python Flask. It is used as a demo/testing app for monitoring tools (APM, RUM, Synthetic, Mobile APM). It includes a built-in chaos engineering console for injecting realistic failures across web and mobile.

**Live URL:** https://snaptravels.online (Nginx port 80 → Flask port 5000)
**GitHub:** https://github.com/ParthibanSekar/Snaptravels (public repo)
**Server:** Debian, deployed at `/root/DemoApp/snaptravels-new/`

---

## Tech Stack

- **Backend:** Python 3.10+, Flask 3.x, SQLAlchemy, APScheduler, Flask-Limiter, Flask-Mail
- **Database:** SQLite (`instance/snaptravels.db`)
- **Frontend (web):** Bootstrap 5, Bootstrap Icons, vanilla JS, Web Components (Shadow DOM)
- **Mobile app:** React Native (Expo SDK 51), TypeScript — folder: `snaptravels-android/`
- **Monitoring:** Site24x7 APM (apminsight Python agent) + RUM (JS beacon) + Mobile APM
- **Server:** Nginx reverse proxy (port 80) → Flask (port 5000)

---

## Key Files — Flask Backend

| File | Purpose |
|------|---------|
| `main.py` | Dev entry point with APM init |
| `wsgi.py` | Gunicorn production entry point |
| `config.py` | Flask config (rate limits, mail, session, etc.) |
| `requirements.txt` | Python dependencies |
| `.env` | Environment variables (not in git) |
| `snaptravels.sh` | App manager: start/stop/restart/logs/reset-db |
| `setup_nginx.sh` | Nginx setup script |
| `verify.sh` | Post-deployment health check (30+ tests) |
| `deploy_debian12.sh` | System package installer |
| `deploy_from_github.sh` | GitHub deploy script (setup / update / restart / status) |
| `migrate_mobile_chaos.py` | Adds 9 mobile chaos columns to FailureMode |
| `migrate_corp_chaos.py` | Adds corporate chaos columns to FailureMode |
| `migrate_ad_popup_chaos.py` | Adds ad popup chaos columns to FailureMode |
| `migrate_shop.py` | Creates shop tables + seeds 20 products |
| `migrate_db.py` | General DB migration utility |
| `init_db.py` | DB initializer + seeder |

---

## App Structure

```
app/
├── __init__.py           # App factory, middleware (IP access, chaos hooks, rate limiter)
├── models.py             # All SQLAlchemy models
├── forms.py              # WTForms
├── blueprints/
│   ├── public.py         # Flights, hotels, booking, trip planner, quick book, travel dashboard
│   ├── trains.py         # Train search & booking
│   ├── buses.py          # Bus search & booking
│   ├── cabs.py           # Cab search & booking
│   ├── packages.py       # Holiday packages
│   ├── activities.py     # Activities booking
│   ├── insurance.py      # Travel insurance
│   ├── shop.py           # Travel shop (products, cart, checkout, orders)
│   ├── reviews.py        # Hotel reviews, wishlist, promo validation
│   ├── blog.py           # Blog listing, detail, admin CRUD
│   ├── trips.py          # My Trips CRUD
│   ├── auth.py           # Login / signup / 2FA (rate-limit exempt)
│   ├── two_factor.py     # TOTP 2FA, Email OTP, backup codes, activity log
│   ├── user_dashboard.py # User profile, travelers, price alerts
│   ├── admin.py          # Admin dashboard + IP access control
│   ├── admin_extended.py # Extended admin features
│   ├── chaos_admin.py    # Chaos console (7 sections), auto chaos, docs
│   ├── mobile_api.py     # Full mobile REST API (JWT, all booking types + shop)
│   ├── corporate.py      # Corporate portal (HTTP Basic Auth)
│   └── pwa.py            # PWA manifest + service worker
├── services/
│   ├── chaos.py          # Chaos injection engine (7 sections)
│   ├── chaos_scheduler.py# APScheduler: auto chaos loop + daily cleanup
│   ├── booking.py        # BookingService.create_booking()
│   ├── sanitize.py       # Server-side input sanitization
│   ├── data_cleanup.py   # Daily DB cleanup
│   ├── ip_access.py      # IP whitelist/blacklist middleware
│   └── seeder.py         # DB seeder (flights, hotels, transport, blog, etc.)
├── templates/            # Jinja2 HTML templates
└── static/               # CSS, JS, images
```

---

## Database Models

| Model | Purpose |
|-------|---------|
| `User` | Accounts, roles, 2FA flags, email confirmation |
| `BackupCode` | 2FA backup codes (pbkdf2 hashed) |
| `TwoFactorLog` | Audit log for 2FA events |
| `Flight` | Flight listings |
| `Hotel` | Hotel listings |
| `Booking` | All booking types (flight, hotel, train, bus, cab, package, activity, insurance) |
| `BookingItem` | Line items per booking |
| `FailureMode` | Chaos engine state (singleton row) |
| `Product` | Shop products |
| `CartItem` | Session/user cart |
| `ShopOrder` | Shop orders |
| `ShopOrderItem` | Shop order line items |

---

## Booking Types & Web Routes

| Type | Search Route | Book Route |
|------|-------------|------------|
| Flights | `/flights` | `/booking` |
| Hotels | `/hotels` | `/booking` |
| Trains | `/trains/` | `/trains/booking` |
| Buses | `/buses/` | `/buses/booking` |
| Cabs | `/cabs/` | `/cabs/booking` |
| Packages | `/packages/` | `/packages/<slug>/book` |
| Activities | `/activities/` | `/activities/<id>/book` |
| Insurance | `/insurance/` | `/insurance/buy/<id>` |
| Quick Book | `/quick-book` | `/quick-book/confirm` |

---

## Payment Methods

All booking forms support: **Card, UPI, Net Banking, Wallets**
- Hidden field `payment_method` in all forms; `switchPay()` JS updates it
- Card validation is conditional (skipped for non-card payments)
- Stored in `Booking.payment_method`

---

## Mobile REST API

**Base URL:** `https://snaptravels.online/mobile-api/v1`
All protected routes require: `Authorization: Bearer <jwt>`

### Auth
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/auth/register` | POST | No | Create account |
| `/auth/login` | POST | No | Returns JWT token |
| `/auth/refresh` | POST | No | Refresh JWT token |
| `/auth/logout` | POST | JWT | Logout |
| `/auth/change-password` | POST | JWT | Change password |

### User Profile
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/user/profile` | GET | JWT | Get profile |
| `/user/profile` | PUT | JWT | Update profile |
| `/user/travelers` | GET | JWT | List saved travelers |
| `/user/travelers` | POST | JWT | Add traveler |
| `/user/travelers/<id>` | PUT | JWT | Update traveler |
| `/user/travelers/<id>` | DELETE | JWT | Delete traveler |
| `/user/rewards` | GET | JWT | Loyalty rewards & points |

### Search
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/flights/search` | GET | JWT | Search flights |
| `/hotels/search` | GET | JWT | Search hotels |
| `/trains/search` | GET | JWT | Search trains |
| `/buses/search` | GET | JWT | Search buses |
| `/cabs/search` | GET | JWT | Search cabs |
| `/packages` | GET | JWT | List packages |
| `/packages/<slug>` | GET | JWT | Package detail |
| `/activities` | GET | JWT | List activities |
| `/activities/<id>` | GET | JWT | Activity detail |
| `/insurance/plans` | GET | JWT | List insurance plans |
| `/insurance` | GET | JWT | Insurance list (alt) |
| `/destinations/popular` | GET | JWT | Popular destinations |
| `/autocomplete` | GET | JWT | Search autocomplete |
| `/config` | GET | JWT | App config/settings |

### Bookings
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/bookings` | POST | JWT | Create booking (any type) |
| `/bookings` | GET | JWT | List user bookings |
| `/bookings/<id>` | GET | JWT | Booking detail |
| `/bookings/<id>/cancel` | POST/PUT | JWT | Cancel booking |
| `/bookings/<id>/resend` | POST | JWT | Resend confirmation |
| `/trains/book` | POST | JWT | Direct train booking |
| `/buses/book` | POST | JWT | Direct bus booking |
| `/cabs/book` | POST | JWT | Direct cab booking |
| `/packages/book` | POST | JWT | Direct package booking |
| `/activities/book` | POST | JWT | Direct activity booking |
| `/insurance/buy` | POST | JWT | Buy insurance |

### Shop (Mobile)
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/shop/products` | GET | JWT | List products (filter by category) |
| `/shop/products/<id>` | GET | JWT | Product detail |
| `/shop/cart` | GET | JWT | Get cart |
| `/shop/cart` | POST | JWT | Add item to cart |
| `/shop/cart/<item_id>` | PUT | JWT | Update cart item |
| `/shop/cart/<item_id>` | DELETE | JWT | Remove cart item |
| `/shop/checkout` | POST | JWT | Place order |
| `/shop/orders` | GET | JWT | List user orders |

### Wishlist & Reviews
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/wishlist` | GET | JWT | Get wishlist |
| `/wishlist` | POST | JWT | Add to wishlist |
| `/wishlist/<id>` | DELETE | JWT | Remove from wishlist |
| `/reviews` | GET | JWT | List reviews |
| `/reviews` | POST | JWT | Submit review |

### Notifications & Alerts
| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/notifications` | GET | JWT | List notifications |
| `/notifications/<id>/read` | PUT | JWT | Mark notification read |
| `/notifications/read-all` | PUT | JWT | Mark all read |
| `/price-alerts` | GET | JWT | List price alerts |
| `/price-alerts` | POST | JWT | Create price alert |
| `/price-alerts/<id>` | DELETE | JWT | Delete price alert |
| `/promo/validate` | POST | JWT | Validate promo code |

### POST /bookings payload (by type)
```json
{
  "booking_type": "FLIGHT|HOTEL|TRAIN|BUS|CAB|PACKAGE|ACTIVITY|INSURANCE",
  "flight_id": 1,
  "hotel_id": 1,
  "train_id": 1,
  "bus_id": 1,
  "cab_id": 1,
  "package_id": 1,
  "activity_id": 1,
  "insurance_id": 1,
  "passengers": [{"name": "...", "email": "...", "phone": "..."}],
  "payment": {"method": "card|upi|netbanking|wallet", "card_number": "...", "expiry": "...", "cvv": "..."}
}
```

### GET /bookings response shape
```json
{
  "bookings": [{
    "id": 1,
    "type": "FLIGHT",
    "flight_id": 42,
    "status": "CONFIRMED",
    "booking_code": "SN-123",
    "total_amount": 4500.0,
    "items": [{"name": "...", "departure": "...", "arrival": "..."}]
  }]
}
```

### Axios Error Handling (client.ts)
| HTTP Code | Meaning | Handling |
|-----------|---------|---------|
| 401 | Auth failed | Show auth error |
| 402 | Payment declined | Show payment error |
| 422 + `data.fields` | Validation error | Show first field error |
| 429 | Rate limited | Show rate limit + retry-after |
| 503 | Service unavailable | Show unavailable message |
| 504 | Gateway timeout | Show timeout message |
| ECONNABORTED | Request too slow | Show slow connection |
| No response | No internet | Show offline message |

---

## Shop (Web)

Routes under `/shop/`:
- `/shop/` — product listing with category filter
- `/shop/product/<id>` — product detail
- `/shop/cart` — cart view
- `/shop/cart/add` — add to cart (POST)
- `/shop/cart/update` — update quantity (POST)
- `/shop/cart/remove` — remove item (POST)
- `/shop/checkout` — checkout (GET/POST)
- `/shop/checkout/guest` — guest checkout (POST)
- `/shop/confirmation/<code>` — order confirmation
- `/shop/orders` — my orders
- `/shop/order/<code>/cancel` — cancel order (POST)
- `/shop/order/<code>/return` — return order (POST)

**20 products seeded** across 4 categories: Clothing, Bags, Accessories, Footwear.
Run `python3 migrate_shop.py` on the server to create tables and seed products.

---

## Authentication & Security

### Login / Signup (`auth.py`)
- Login route: `@limiter.exempt` (no rate limit)
- Signup, password reset: rate limited
- Email confirmation token flow

### Two-Factor Authentication (`two_factor.py`)
| Feature | Detail |
|---------|--------|
| TOTP | Google Authenticator compatible, Fernet-encrypted secret |
| Email OTP | OTP sent to registered email |
| Backup codes | 8 codes, pbkdf2 hashed, single-use |
| Audit log | `TwoFactorLog` — events: `2FA_ENABLED`, `2FA_DISABLED`, `2FA_LOGIN`, `2FA_FAILED`, `2FA_BACKUP_USED`, `2FA_SETUP_STARTED` |

Routes:
- `/security` — 2FA settings page
- `/security/2fa/start` — begin TOTP setup
- `/security/2fa/setup` — show QR code
- `/security/2fa/verify-setup` — verify TOTP code
- `/security/2fa/backup-codes` — view backup codes
- `/security/2fa/regenerate` — regenerate backup codes
- `/security/2fa/disable` — disable 2FA
- `/security/2fa/activity` — activity log
- `/auth/2fa` — OTP entry on login
- `/security/email-otp/enable` — enable email OTP

---

## Server-Side Input Sanitization (`app/services/sanitize.py`)

```python
sanitize_str(value, max_len=200)         # strip HTML + html.escape
sanitize_int(value, default, min, max)
validate_name_server(name)               # letters/spaces/hyphens, 2-100 chars, no digits
validate_email_server(email)             # format regex, lowercase
validate_phone_server(phone)             # 10 digits, starts 6-9
sanitize_booking_customer(data, phone_required=True)  # returns (clean_dict, errors_dict)
```

---

## Mobile App (`snaptravels-android/`)

React Native (Expo SDK 51), TypeScript.
API base: `https://snaptravels.online/mobile-api/v1`

### Key Files
| File | Purpose |
|------|---------|
| `src/api/client.ts` | Axios instance with JWT interceptor + error handling |
| `src/api/bookings.ts` | BookingType enum, CreateBookingPayload, cancelBooking |
| `src/utils/validators.ts` | Client-side validators + formatters |
| `src/context/AuthContext.tsx` | JWT storage, login/register/guest/logout |

### Booking Screens
- `FlightBookingScreen.tsx` — passenger + payment validation
- `HotelBookingScreen.tsx` — passenger + payment validation
- `GenericBookingScreen.tsx` — Train/Bus/Cab/Package/Activity/Insurance

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
validatePassenger(form)  // returns Record<string, string> errors
validatePayment(form)    // returns Record<string, string> errors
formatCardNumber(v)      // inserts spaces every 4 digits
formatExpiry(v, prev)    // auto-inserts /
formatPhone(v)           // digits only, max 10
```

### BookingType Enum
```typescript
type BookingType = 'FLIGHT' | 'HOTEL' | 'TRAIN' | 'BUS' | 'CAB' | 'PACKAGE' | 'ACTIVITY' | 'INSURANCE'
```

---

## Chaos Engineering

### 7 Independent Sections

| Section | Name | Toggle Field |
|---------|------|-------------|
| §0 | Core Engine | `enabled` |
| §1 | Page Load | `page_load_chaos` |
| §2 | Functionality | `func_chaos` |
| §3 | Component | `component_chaos` |
| §4 | A/B Test | `ab_test_chaos` |
| §5 | Mobile App | `mobile_chaos` |
| §6 | Corporate Portal | `corp_chaos` |
| §7 | Ad Popup | `ad_popup_chaos` |

### Section 5 — Mobile Chaos (9 fields on FailureMode)

| Field | Type | Effect |
|-------|------|--------|
| `mobile_chaos` | bool | Master toggle |
| `mobile_auth_failure_rate` | float 0-1 | `/auth/login` → 401 |
| `mobile_search_slow_ms` | int | All search endpoints → sleep N ms |
| `mobile_search_empty_rate` | float 0-1 | Search returns empty list |
| `mobile_booking_decline_rate` | float 0-1 | `POST /bookings` → 402 |
| `mobile_cancel_failure_rate` | float 0-1 | Cancel → 503 |
| `mobile_timeout_rate` | float 0-1 | Any endpoint → 504 |
| `mobile_rate_limit_rate` | float 0-1 | Any endpoint → 429 |
| `mobile_malform_rate` | float 0-1 | Booking response strips `booking_code` + `total_amount` |

Migration: `python3 migrate_mobile_chaos.py`

### Section 6 — Corporate Portal Chaos

| Field | Type | Effect |
|-------|------|--------|
| `corp_chaos` | bool | Master toggle |
| `corp_auth_failure_rate` | float | Basic auth → 401 |
| `corp_slowdown_ms` | int | All corp pages → sleep |
| `corp_search_fail_rate` | float | Search → 500 |

Migration: `python3 migrate_corp_chaos.py`

### Section 7 — Ad Popup Chaos

| Field | Type | Effect |
|-------|------|--------|
| `ad_popup_chaos` | bool | Master toggle |
| `ad_popup_rate` | float (default 0.3) | Probability popup appears |
| `ad_popup_delay_ms` | int (default 1500) | Delay before popup shows |
| `ad_popup_close_delay_ms` | int (default 0) | Delay before close button appears |
| `ad_popup_target_pages` | JSON text | Pages to show popup on (default `["all"]`) |

Migration: `python3 migrate_ad_popup_chaos.py`

### Chaos Functions (`app/services/chaos.py`)
```python
maybe_fail_login(email)           # LoginChaosError
maybe_fail_db(op)                 # DatabaseChaosError
maybe_fail_search(kind)           # SearchChaosError
maybe_fail_checkout(booking_type) # CheckoutChaosError
maybe_fail_payment(amount)        # PaymentChaosError
maybe_fail_api(endpoint)          # APIChaosError
maybe_fail_mobile_auth()          # MobileAuthChaosError → 401
maybe_slow_mobile_search()        # sleep or empty=True
maybe_fail_mobile_booking()       # MobileBookingChaosError → 402
maybe_fail_mobile_cancel()        # MobileCancelChaosError → 503
maybe_mobile_timeout()            # MobileTimeoutChaosError → 504
maybe_mobile_rate_limit()         # MobileRateLimitChaosError → 429
should_mobile_malform()           # bool
maybe_fail_corp_auth()            # CorpAuthChaosError
```

### Auto Chaos
- Continuous loop of all sections (or subset via exclude checkboxes)
- 30–60 min per event, 3-hour cooling gap
- Schedule stored in `FailureMode.auto_chaos_schedule_json`
- Excluded types in `FailureMode.auto_chaos_excluded_json`
- Daily reshuffle at 00:05 UTC

### Chaos Page Targets
```
flights, hotels, buses, trains, cabs, packages, activities,
insurance, booking, dashboard, trip-planner, quick-book,
travel-dashboard, home
```

---

## Special Web Features

### Trip Planner (`/trip-planner`)
- 5-step flow, each step in its own iframe
- Step 1: SVG India map destination picker
- Step 2: Flight list popup (iframe + action frame)
- Step 3: SVG seat map (new window)
- Step 4: Price alert popup form
- Step 5: Review & save trip to DB
- Cross-window communication via `postMessage`

### Quick Book (`/quick-book`) — Shadow DOM
- 5-step Web Component flow using `attachShadow({mode:'open'})`
- Components: `<snap-flight-card>`, `<snap-selection-summary>`, `<snap-passenger-form>`, `<snap-payment-widget>`, `<snap-booking-confirmation>`
- Payment widget has nested Shadow DOM: `<snap-card-input>` and `<snap-upi-input>` inside
- Creates real bookings via `POST /quick-book/confirm`

### Travel Dashboard (`/travel-dashboard`)
- SVG charts, India route map, live booking feed
- Each section in its own iframe

### Blog (`/blog`)
- Public listing + detail pages
- Admin CRUD at `/blog/admin`

### Reviews & Wishlist
- Hotel reviews: `POST /reviews/hotel/<id>`
- Wishlist toggle: `POST /wishlist/toggle`
- Promo validation: `POST /promo/validate`

### IP Access Control (`/admin/ip-access`)
- Whitelist/blacklist modes stored in `SiteConfig`
- Admin pages always exempt

---

## Corporate Travel Portal (`/corporate/`)

Protected by **HTTP Basic Authentication** — zero dependency on Flask sessions or JWT.

### Credentials (from `.env`)
```
CORP_BASIC_USER=corp_user      (default)
CORP_BASIC_PASS=Corp@2024!     (default)
```

### Routes
| Route | Purpose |
|-------|---------|
| `GET /corporate/` | Dashboard — stats + quick search + recent bookings |
| `GET /corporate/search` | Search form |
| `POST /corporate/search` | Search results |
| `GET /corporate/bookings` | Paginated booking history with status filter |

---

## Rate Limits (config.py)

- **Global default:** `10000 per day; 1000 per hour; 200 per minute`
- **Login route:** `@limiter.exempt` (no limit)
- **Storage:** in-memory (upgrade to Redis for multi-worker)
- **Key:** IP address (`get_remote_address`)

---

## Data Cleanup (Daily at midnight UTC)

| Resource | Limit |
|----------|-------|
| Bookings per user | 500 |
| Bookings for admin | 1000 |
| Chaos events total | 2000 |
| Notifications per user | 200 |

Config: `app/services/data_cleanup.py`

---

## Deployment

### .env Required Keys
```
SECRET_KEY=<random 32-byte hex>
S247_LICENSE_KEY=<site24x7 apm key>
SITE24X7_RUM_APP_KEY=<site24x7 rum key>
PORT=5000
APP_NAME=SnapTravels

# Optional email
MAIL_SERVER=smtp.zoho.in
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your@email.com
MAIL_PASSWORD=your-password
MAIL_DEFAULT_SENDER=SnapTravels <your@email.com>

# Corporate portal
CORP_BASIC_USER=corp_user
CORP_BASIC_PASS=Corp@2024!
```

### Fresh Server Setup
```bash
git clone https://github.com/ParthibanSekar/Snaptravels.git /root/DemoApp/snaptravels-new
cd /root/DemoApp/snaptravels-new
bash deploy_debian12.sh
vi .env   # fill in required keys
PORT=5000 bash snaptravels.sh start
bash setup_nginx.sh --domain snaptravels.online
bash verify.sh 5000
```

### Update from GitHub
```bash
cd /root/DemoApp/snaptravels-new
bash deploy_from_github.sh update
# Auto-runs all migrations and restarts the app
```

### Manual Migrations (run in order if needed)
```bash
python3 migrate_mobile_chaos.py
python3 migrate_corp_chaos.py
python3 migrate_ad_popup_chaos.py
python3 migrate_shop.py
```

### App Management
```bash
bash snaptravels.sh start     # install deps + init DB + start
bash snaptravels.sh stop      # stop
bash snaptravels.sh restart   # stop + start
bash snaptravels.sh status    # check running status
bash snaptravels.sh logs      # tail logs
bash snaptravels.sh reset-db  # delete DB + re-seed
```

---

## Default Accounts

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@snaptravels.online | Admin@123 |
| User | parthiban@snaptravels.online | Test@123 |

---

## Pending / Next Steps

1. **Build Android APK** — `eas build --platform android` or `expo build:android`
2. **iOS app** — extend React Native app for iOS (Expo supports both platforms)
3. **Site24x7 Mobile APM** — add `s247-mobile-sdk` to the Expo app
4. **REST API Transaction Monitor (Site24x7)** — 5-step: Login → Search → Book → Verify → Cancel
5. **Live Chaos State panel** — add §5 mobile + §6 corp + §7 ad popup fields to the right-column snapshot in `admin_chaos.html`
6. **Webhook chaos** — simulate payment gateway + SMS provider webhook failures (new §8)
7. **Push notifications** — Expo push notifications for booking confirmations
8. **Revenue analytics charts** — visual graphs on admin dashboard
9. **PDF booking ticket** — downloadable ticket after booking confirmation
10. **Loyalty/points system** — earn points per booking, redeem for discounts
