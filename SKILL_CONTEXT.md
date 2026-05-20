# SnapTravels — Project Skill Context

Use this file to onboard a new Claude session about the SnapTravels project. Read this before making any changes.

---

## Project Overview

SnapTravels is a full-stack travel booking platform built with Python Flask. It's used as a demo/testing app for monitoring tools (APM, RUM, Synthetic). It includes a built-in chaos engineering console for injecting realistic failures.

**Live URL:** http://snaptravels.online (Nginx on port 80 → Flask on port 5000)
**GitHub:** https://github.com/ParthibanSekar/Snaptravels (public repo)
**Server:** Debian, deployed at /root/DemoApp/snaptravels-new/

---

## Tech Stack

- **Backend:** Python 3.10+, Flask 3.x, SQLAlchemy, APScheduler
- **Database:** SQLite (instance/snaptravels.db)
- **Frontend:** Bootstrap 5, Bootstrap Icons, vanilla JS, Web Components (Shadow DOM)
- **Monitoring:** Site24x7 APM (apminsight Python agent) + RUM (JS beacon)
- **Server:** Nginx reverse proxy (port 80) → Flask (port 5000)

---

## Key Files

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
| `deploy_from_github.sh` | GitHub deploy script |

---

## App Structure

```
app/
├── __init__.py           # App factory, middleware (IP access, chaos hooks)
├── models.py             # All SQLAlchemy models
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
│   ├── mobile_api.py     # Mobile REST API (JWT auth, all endpoints)
│   ├── auth.py           # Login/signup/2FA
│   └── user_dashboard.py # User profile, travelers, price alerts
├── services/
│   ├── chaos.py          # Chaos injection engine (5 sections + page slug map)
│   ├── chaos_scheduler.py # APScheduler: auto chaos continuous loop, daily cleanup
│   ├── booking.py        # BookingService.create_booking()
│   ├── data_cleanup.py   # Daily DB cleanup (500/user, 1000/admin, 2000 events)
│   ├── ip_access.py      # IP whitelist/blacklist middleware
│   └── ...
├── templates/
│   ├── layouts/base.html # Base template with navbar, footer, RUM beacon
│   ├── home.html         # Homepage with India hero images
│   ├── trip_planner.html # 5-step trip planner (all iframes)
│   ├── quick_book.html   # Shadow DOM Web Components booking flow
│   ├── travel_dashboard.html # SVG charts + iframes dashboard
│   ├── admin_chaos.html  # Chaos console
│   ├── admin_chaos_auto.html # Auto chaos timeline
│   ├── admin_chaos_docs.html # Chaos documentation
│   ├── admin_ip_access.html  # IP access control
│   ├── frames/           # iframe content (trip steps, dashboard frames)
│   ├── popups/           # Popup windows (compare frameset, seat map, price alert)
│   └── ...
└── static/
    ├── images/hero/      # Hero background images
    ├── images/destinations/ # Destination photos
    └── ...
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

## Chaos Engineering

### 5 Independent Sections
0. Core Engine — login/DB/search/payment/API failures
1. Page Load — server delay, JS errors, resource failures, memory pressure
2. Functionality — broken images/forms/CTAs, 404 storm, session kill
3. Component — random UI component breakage (40-80% rate)
4. A/B Test — DOM identifier mutation

### Auto Chaos
- Continuous loop of all 5 types (or subset via exclude checkboxes)
- 30-60 min per event, 3-hour cooling gap
- Schedule stored in `FailureMode.auto_chaos_schedule_json`
- Excluded types in `FailureMode.auto_chaos_excluded_json`
- Daily reshuffle at 00:05 UTC (05:35 IST)
- Schedule always generated even if APScheduler unavailable

### Page Targets (chaos can target specific pages)
```python
PAGE_SLUG_MAP keys: flights, hotels, buses, trains, cabs, packages, activities,
                    insurance, booking, dashboard, trip-planner, quick-book,
                    travel-dashboard, home
```

---

## Mobile API Endpoints

All under `/mobile-api/v1/`:

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| /auth/login | POST | No | Returns JWT token |
| /auth/register | POST | No | Create account |
| /flights/search | GET | JWT | Search flights |
| /hotels/search | GET | JWT | Search hotels |
| /bookings | POST | JWT | Create booking (validates price from DB) |
| /bookings | GET | JWT | List user bookings |
| /bookings/<id> | GET | JWT | Get booking details |
| /bookings/<id>/cancel | POST | JWT | Cancel booking |
| /promo/validate | POST | JWT | Validate promo code |

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
```

### Update:
```bash
bash snaptravels.sh stop
git pull origin main
PORT=5000 bash snaptravels.sh start
```

---

## Default Accounts
- Admin: admin@snaptravels.online / Admin@123
- User: parthiban@snaptravels.online / Test@123

---

## Pending Items (for next session)
1. **React Native mobile app** — Android APK + iOS IPA using existing mobile API
2. **User Travel Dashboard** — personalized expense tracking, travel history, SVG charts per user
3. **Shadow DOM enhancements** — more nested components, slot-based content
4. **REST API Transaction Monitor** — 5-step monitor in Site24x7 (Login→Search→Book→Verify→Cancel)
