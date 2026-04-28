# SnapTravels — Mobile API, PWA & Observability

## Mobile REST API (blueprint: mobile_api.py)

**Base URL:** `/mobile-api/v1/`
**Auth:** JWT tokens (Authorization: Bearer <token>)
**CSRF:** Exempt (no CSRF tokens needed)
**Chaos:** `maybe_fail_api()` called on each route — returns 503 during `api_5xx_storm`

| Route | Method | Description |
|---|---|---|
| `/mobile-api/v1/auth/login` | POST | `{email, password}` → `{token, user}` |
| `/mobile-api/v1/auth/register` | POST | `{name, email, password}` → `{token, user}` |
| `/mobile-api/v1/flights/search` | GET | `?origin=&destination=&date=&passengers=` → flight list |
| `/mobile-api/v1/flights/<id>` | GET | Single flight detail |
| `/mobile-api/v1/hotels/search` | GET | `?city=&check_in=&check_out=&guests=` → hotel list |
| `/mobile-api/v1/hotels/<id>` | GET | Single hotel detail |
| `/mobile-api/v1/bookings` | GET | User's booking history (auth required) |
| `/mobile-api/v1/bookings` | POST | Create booking (auth required) |
| `/mobile-api/v1/bookings/<id>` | GET | Single booking detail |
| `/mobile-api/v1/packages` | GET | List packages |
| `/mobile-api/v1/user/profile` | GET/PUT | Get/update profile (auth required) |
| `/mobile-api/v1/wishlist` | GET/POST/DELETE | Wishlist management (auth required) |

**Response format:**
```json
{ "success": true, "data": {...}, "message": "..." }
// Error:
{ "success": false, "error": "Error description", "code": 404 }
```

---

## PWA (blueprint: pwa.py)

**CSRF:** Exempt

| Route | Description |
|---|---|
| `/manifest.json` | PWA manifest (name, icons, theme_color, display: standalone) |
| `/sw.js` | Service worker JS (caches static assets, offline fallback) |
| `/offline` | Offline fallback page |

**Theme color:** `#1d4ed8` (blue — matches flights theme)
**Short name:** SnapTravels
**Icons:** 192×192 and 512×512 PNG

---

## Health & Metrics Endpoints

| Route | Returns | Notes |
|---|---|---|
| `/health` | `{"status":"ok"}` 200 | Shallow — always 200 |
| `/health/deep` | `{"status":"ok"}` or 503 | Hits DB — 503 if `db_unavailable=True` (chaos) |
| `/metrics` | Plain text | user_count, booking_count, chaos_state summary |
| `/admin/chaos/state.json` | JSON | Full chaos state, public (no auth needed) |

**Deep health check response:**
```json
{ "status": "ok", "db": "connected", "chaos_active": false, "env": "production" }
// During db_unavailable chaos:
{ "status": "degraded", "db": "unavailable", "chaos_active": true }  → HTTP 503
```

---

## Observability Middleware (app/services/observability.py)

**Trace ID injection:**
- Every incoming request gets a `X-Trace-Id` header generated (UUID4)
- Trace ID added to all response headers
- Trace ID included in all JSON log entries

**JSON Structured Logging** (when `SNAPTRAVELS_JSON_LOGS=1`):
```json
{
  "timestamp": "2026-04-11T10:30:00Z",
  "level": "INFO",
  "trace_id": "abc-123-...",
  "method": "POST",
  "path": "/login",
  "status_code": 200,
  "duration_ms": 145,
  "user_id": 42,
  "chaos_active": false
}
```

---

## Site24x7 RUM Integration

**Injection:** `base.html` injects the Site24x7 RUM beacon script if `SITE24X7_RUM_APP_KEY` env var is set:
```html
{% if config.SITE24X7_RUM_APP_KEY %}
<script>
  (function(w,d,...) { /* Site24x7 RUM beacon */ })(window, document, '{{ config.SITE24X7_RUM_APP_KEY }}');
</script>
{% endif %}
```

**What it tracks:** Page load times, AJAX call durations, JS errors, user sessions, geo distribution

**Site24x7 Monitor Types used with SnapTravels:**
- **Web Transaction (Synthetic)** — Scripts for: login flow, flight search + booking, hotel search + booking
- **REST API Monitor** — Polls `/health/deep` and `/admin/chaos/state.json`
- **APM** — Traces Flask request lifecycle (if Site24x7 APM agent installed)
- **RUM** — Browser-side monitoring via injected beacon
- **Mobile APM** — Tracks mobile API calls if a native app uses `/mobile-api/v1/`

---

## Email Notifications (app/services/email.py)

Uses Flask-Mail. Disabled if `MAIL_USERNAME` not set (dev mode).

**Emails sent:**
- Booking confirmation — to customer email after successful booking
- Email OTP — 6-digit code for 2FA login
- Password reset — reset link (if /forgot-password implemented)
- Refund notification — when admin processes refund

**SMTP config:** Gmail SMTP by default (`MAIL_SERVER=smtp.gmail.com`, port 587, TLS)
