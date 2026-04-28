# SnapTravels — Snap Docs Index

> **How to use:** In a new Claude session, read THIS file first (~150 tokens). Then read ONLY the specific file(s) for the task you're working on. Do NOT read the whole folder every session.

---

## What is SnapTravels?
Full-stack travel booking app — Python Flask 3.x + Jinja2 (server-rendered) + Bootstrap + vanilla JS. Built as an **observability demo for Site24x7**. Hosted at `https://snaptravels.online`.

**Test accounts:** `parthiban@snaptravels.online` / `Test@123` (user) · `admin@snaptravels.online` / `Admin@123` (admin)

**Run locally:** `source venv/bin/activate && python main.py` → http://localhost:5000

---

## File Map — Read ONLY what you need

| Task / Area | Read this file |
|---|---|
| Understanding the stack, project structure, env vars | `01_tech_stack.md` |
| Login, signup, 2FA, TOTP, session, role guards | `02_auth.md` |
| Flights search page, seat selection, flight cards | `03_flights.md` |
| Hotels search page, room selection, hotel cards | `04_hotels.md` |
| Buses search page (`buses.html`), bus cards, filters | `05_buses.md` |
| Trains search page (`trains.html`), train cards, filters | `06_trains.md` |
| Cabs search page (`cabs.html`), cab cards, filters | `07_cabs.md` |
| Holiday packages listing, detail, booking | `08_packages.md` |
| Booking flow, payment tabs, promo code, all booking templates | `09_booking_payment.md` |
| User dashboard, my bookings, profile, wishlist, trips | `10_dashboard.md` |
| Admin panel — flights, hotels, users, revenue, refunds | `11_admin.md` |
| Chaos engineering engine, failure profiles, chaos panel | `12_chaos.md` |
| Mobile REST API, health endpoints, PWA, Site24x7 observability | `13_api_observability.md` |
| What was done in previous sessions | `14_session_log.md` |

---

## Quick Design Rules (memorize these)

- **Search pages gold standard** = trains page: gradient hero → sidebar filters → search chips → sort bar → rich list cards → popular routes landing state
- **Colors:** Flights = blue (`#1d4ed8`), Hotels = teal (`#0f766e`), Buses = purple (`#7c3aed`), Trains = indigo (`#1d4ed8`), Cabs = teal (`#0f766e`)
- **Booking pages gold standard** = train_booking.html: purple/blue hero + 4-step indicator → journey card → Passenger form → GST panel (collapsible) → 4-tab Payment (Card/UPI/NetBanking/Wallets) → sticky summary with promo + breakdown
- **CSRF:** All forms need `{{ csrf_token() }}`. Mobile API and PWA are exempt.
- **Promo validation:** AJAX POST to `/promo/validate` with `{code, amount}` → returns `{valid, discount, final, message}`

---

## Session Log Summary
See `14_session_log.md` for full entries. Latest session: **Part 3 (2026-04-11)** — booking.html + bus_booking.html full rewrite.
