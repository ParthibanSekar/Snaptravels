# SnapTravels — Session Log

> All work sessions are logged here. In a new Claude session, read this file to quickly see what was done last and what's pending.

---

## Session — 2026-04-11 (Part 1)
**Account:** parthaupt@gmail.com
**Task:** Initial project deep-read + create handoff guide

**What was done:**
- Fully read and analyzed all key project files: `app/__init__.py`, `app/models.py`, `config.py`, all blueprints, README, CHAOS_README
- Created `claude_app_guide.md` as single-file persistent handoff document

**Files created:**
- `claude_app_guide.md` (now replaced by `snap_docs/` folder)

---

## Session — 2026-04-11 (Part 2)
**Account:** parthaupt@gmail.com
**Task:** Upgrade buses.html and cabs.html to trains gold standard design

**Design pattern applied:** trains page (sidebar + sort bar + rich list cards + landing state)

**buses.html changes:**
- Deep purple gradient hero (matching existing purple theme)
- Sidebar: Sort By / Bus Type buttons (Volvo/Sleeper/Seater/Non-AC/Luxury) / Departure Time slots / Seats toggle
- Cards: operator + bus_no + type badge (color-coded) + route visualization + seat bar + amenity pills + footer row
- Landing: 6 popular route cards + 4 trust badges
- JS: `sortBuses`, `filterBusType`, `applyBusFilters`, `updateBusCount`, `resetBusFilters`

**cabs.html changes:**
- Teal gradient hero (preserved existing theme, polished)
- Sidebar: Sort By (price/capacity/per-km) / Vehicle Type (Hatchback/Sedan/SUV/Premium/Tempo) / AC only / Capacity 4+/6+
- Switched from 3-col grid to full-width LIST cards (consistent with trains/buses)
- Cards: teal vehicle icon block + name + brand + stat row + feature pills + footer trust row
- Search chips now show: pickup, drop, date, time, passengers, distance km
- JS: `sortCabs`, `filterCabType`, `applyCabFilters`, `updateCabCount`, `resetCabFilters`

**Files modified:** `app/templates/buses.html`, `app/templates/cabs.html`

---

## Session — 2026-04-11 (Part 3)
**Account:** parthaupt@gmail.com
**Task:** Make all booking flows production-ready

**booking.html (flights + hotels shared template) — full rewrite:**
- Conditional Jinja2 theming: `{% set is_flight = flight is not none %}` → blue (flights) or teal (hotels)
- 4-step indicator in hero + journey card (flight route viz OR hotel details)
- Section ①: Passenger Details (name/email/phone + DOB + ID type for flights, special requests for hotels)
- Section ②: GST Invoice collapsible panel
- Section ③: 4-tab payment (Card + UPI 6-app grid + Net Banking 8-bank tiles + Wallets 4-tile)
- Terms checkbox (required) + loading submit button
- Sticky summary: price breakdown + live promo AJAX + What's Included + trust badges

**bus_booking.html — full rewrite:**
- Purple gradient hero matching buses.html
- Same 4-section structure as booking.html
- Bus type badge CSS classes: `btype-volvo`, `btype-sleeper`, `btype-seater`, `btype-nonac`, `btype-luxury`
- Price breakdown: base fare × passengers + ₹30/seat convenience fee + 5% GST
- Summary shows: operator / bus_no / bus_type / date / depart / arrive / duration / passengers / selected seats

**Files modified:** `app/templates/booking.html`, `app/templates/bus_booking.html`

---

## Session — 2026-04-11 (Part 4)
**Account:** parthaupt@gmail.com
**Task:** Restructure `claude_app_guide.md` into modular `snap_docs/` folder

**Motivation:** Single 400-line file costs ~3,000 tokens to read every session. With split files, each session reads only the 1-2 relevant files (~300-500 tokens each) — 80-90% token savings.

**Files created (snap_docs/ folder):**
- `00_INDEX.md` — Master index: file map, quick design rules, test accounts (~150 tokens to read)
- `01_tech_stack.md` — Full tech stack, project structure, all models, env vars, how to run
- `02_auth.md` — Auth mechanism, 2FA, session guards, role decorators
- `03_flights.md` — Flights routes, model, search page design, seat selection
- `04_hotels.md` — Hotels routes, model, search page design, room selection
- `05_buses.md` — Buses routes, model, buses.html design, bus_booking.html design
- `06_trains.md` — Trains routes, model, trains.html (gold standard), train_booking.html
- `07_cabs.md` — Cabs routes, model, cabs.html design, cab_booking.html design
- `08_packages.md` — Packages + activities routes, models, design notes
- `09_booking_payment.md` — All booking flow patterns, payment tabs implementation, promo code, price breakdown
- `10_dashboard.md` — User dashboard, my bookings, profile, security, wishlist, trips
- `11_admin.md` — All admin routes, PromoCode model, booking data model
- `12_chaos.md` — Chaos engine architecture, FailureMode model, all profiles, scheduler, admin panel
- `13_api_observability.md` — Mobile REST API, PWA, health endpoints, Site24x7 RUM, email
- `14_session_log.md` — This file

**`claude_app_guide.md` updated** to redirect to `snap_docs/` folder.

---

---

## Session — 2026-04-12 (Part 5)
**Account:** parthaupt@gmail.com
**Task:** Page transition loader + Chaos v2 (Page Load Performance + Functionality Failures)

### Page Transition Loader (base.html)
- Full-screen white overlay (`#snapLoader`) shown on every page navigation
- SnapTravels branded: coral icon + brand name + animated plane flying across + progress bar
- JS: shows on `<a>` link clicks (skips `#anchor`, `mailto:`, `tel:`, `target=_blank`, external URLs) and form submits
- Progress bar animates 0→80% while waiting, completes to 100% on `window.load` then fades out
- Minimum visible time: 500ms (prevents flash on cached pages)
- Safety net: auto-hides after 62 seconds maximum
- Handles browser back/forward via `pageshow` event (bfcache)

### Chaos — New FailureMode DB Columns (16 new fields)
**Page Load Chaos (Section 1):**
- `page_load_chaos` — master toggle
- `page_load_delay_ms` — server-side sleep 0–60,000ms
- `page_load_target_pages` — JSON list of pages to target
- `page_load_inject_js_errors` — console errors injection
- `page_load_inject_resource_failures` — broken JS/CSS/fetch calls
- `page_load_inject_memory_pressure` — 96MB heap allocation
- `page_load_inject_render_blocking` — synchronous JS busy-wait
- `page_load_large_payload` — 8,000 hidden DOM nodes

**Functionality Failures (Section 2):**
- `func_chaos` — master toggle
- `func_search_empty` — force all search pages to return 0 results
- `func_form_errors` — 60% of form submits show 503 error
- `func_broken_images` — 55% of images get broken src URLs
- `func_session_kill_rate` — randomly clear user sessions
- `func_404_storm_rate` — random % of requests return 404
- `func_infinite_spin` — Book buttons spin forever after click
- `func_broken_cta` — 45% of buttons become unclickable

### SQLite Auto-Migration
- `__init__.py` now runs `ALTER TABLE failure_mode ADD COLUMN` for all 16 new columns on startup
- Safe: wrapped in try/except, only runs for missing columns, existing DBs are migrated automatically

### chaos.py New Helpers
- `maybe_delay_page(path)` — server-side sleep with target page filtering
- `get_page_chaos_js()` — generates all JS injection snippets for browser
- `should_empty_search()` — returns True if search should be empty (checked in search blueprints)
- `maybe_404_storm()` — random 404 abort (called in `before_request`)
- `maybe_kill_session()` — random session clear (called in `before_request`)

### __init__.py Changes
- `@app.context_processor inject_chaos_js` — provides `chaos_page_js` to ALL templates
- `@app.before_request apply_page_chaos` — calls page delay + 404 storm + session kill

### base.html Changes
- Added full page transition loader overlay + CSS + JS before navbar
- Added `{{ chaos_page_js | safe }}` injection block at end of body

### admin_chaos.html — Full Rebuild (dark theme, 3 sections)
- **Section 0 (Core):** existing knobs — login/DB/search/checkout/payment/API sliders
- **Section 1 (Page Load):** server delay slider (0–60s) + target page chips + 5 injection checkboxes
- **Section 2 (Functionality):** 404 storm rate + session kill rate + 5 toggle checkboxes
- **Right column:** Named outage profiles + Live state snapshot (all 22 chaos fields) + Event log
- Master section toggles enable/disable entire sections with opacity effect

### Files Modified
- `app/models.py` — 16 new FailureMode columns + updated to_dict()
- `app/services/chaos.py` — 5 new helpers + updated end_outage()
- `app/blueprints/chaos_admin.py` — new field registrations + target_pages JSON handling
- `app/__init__.py` — context processor + before_request + SQLite migration
- `app/templates/layouts/base.html` — page transition loader + chaos JS injection
- `app/templates/admin_chaos.html` — full 3-section dark panel rebuild

---

## Pending / Suggested Next Tasks

- [ ] Check `package_booking.html` — may still be basic Bootstrap, needs same booking flow upgrade
- [ ] Polish `booking_confirmation.html` — make it more celebratory/branded (confetti animation, clear CTA, email confirmation note)
- [ ] Check `activities.html` / `activity_booking.html` — may need search page + booking upgrade
- [ ] Insurance page (`insurance.html`) — compare quality to trains/buses, upgrade if needed
- [ ] Blog page (`blog.html`) — content and layout quality check
- [ ] Advanced flight filters (airline filter, max stops)
- [ ] Trip planner UX improvements (`trips.html`)
