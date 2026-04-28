# SnapTravels — Chaos Engineering Engine

## Purpose

The chaos engine makes SnapTravels a **live observability demo for Site24x7**. It injects realistic failures into real code paths so monitoring tools (Synthetic, APM, RUM, Mobile APM) detect, alert, and correlate outages.

---

## Architecture

```
FailureMode (DB singleton row)
    ↓ read by
app/services/chaos.py — maybe_fail_*() helpers
    ↓ called from
Real code paths (login, search, checkout, API, DB queries, etc.)
    ↑ also triggered by
APScheduler (chaos_scheduler.py) — auto daily outage windows
    ↑ and from
Admin Panel (/admin/chaos) — manual toggle
```

---

## FailureMode Model (app/models.py)

Singleton — always exactly one row (id=1).

```python
class FailureMode(db.Model):
    # On/Off toggles
    login_storm             # Boolean — 60% login failures + 800ms slowdown
    db_slowdown             # Boolean — 2.5s DB queries + 1.5s checkout
    db_unavailable          # Boolean — DB completely down (503 on /health/deep)
    payment_gateway_down    # Boolean — All payments fail at checkout
    checkout_exceptions     # Boolean — 50% random checkout crashes
    search_upstream_timeout # Boolean — 40% search timeouts
    api_5xx_storm           # Boolean — 35% mobile API calls return 503

    # Rate fields (allow partial failure, not just on/off)
    login_failure_rate      # Float 0.0-1.0 (default 0.6 for login_storm)
    api_failure_rate        # Float (default 0.35 for api_5xx_storm)
    search_timeout_rate     # Float (default 0.4)

    # Timing fields
    db_latency_ms           # Integer — added to DB queries during db_slowdown
    checkout_latency_ms     # Integer — added to checkout during db_slowdown

    # Metadata
    last_updated            # DateTime
    updated_by              # String (admin email or 'scheduler')
```

---

## Chaos Helpers (app/services/chaos.py)

```python
maybe_fail_login(user)         # Raises AuthError or sleeps — called in auth.py /login
maybe_fail_db()                # Raises DBError or sleeps — called before DB queries
maybe_fail_payment()           # Raises PaymentError — called in booking confirm route
maybe_fail_checkout()          # 50% chance raises exception — called in checkout flow
maybe_fail_search()            # Sleeps/raises timeout — called in SearchService
maybe_fail_api()               # Returns 503 JSON — called in mobile_api.py routes
```

Each helper reads `FailureMode.query.get(1)` and uses `random.random()` against the failure rate.

---

## Failure Profiles (Named Scenarios)

The admin can fire these named profiles (each sets multiple FailureMode fields at once):

| Profile Name | What it does |
|---|---|
| `login_storm` | login_storm=True, login_failure_rate=0.6, db_latency_ms=800 |
| `db_degraded` | db_slowdown=True, db_latency_ms=2500, checkout_latency_ms=1500 |
| `full_outage` | db_unavailable=True, payment_gateway_down=True — most severe |
| `payment_failure` | payment_gateway_down=True only |
| `api_storm` | api_5xx_storm=True, api_failure_rate=0.35 |
| `search_timeout` | search_upstream_timeout=True, search_timeout_rate=0.4 |
| `checkout_chaos` | checkout_exceptions=True — random 50% checkout crashes |

---

## Auto Scheduler (chaos_scheduler.py)

- Uses APScheduler (BackgroundScheduler)
- Requires `CHAOS_SCHEDULER_ENABLED=1` env var
- Default schedule: fires 2 outage windows per day
  - Window 1: 10:00 AM local → runs `login_storm` for 15 minutes
  - Window 2: 2:00 PM local → runs `api_storm` for 10 minutes
- After each window: resets all FailureMode fields to False
- All events logged to `ChaosEvent` table

---

## ChaosEvent Model (chaos audit log)

```python
class ChaosEvent(db.Model):
    id, event_type       # 'ENABLED' / 'DISABLED' / 'PROFILE_FIRED' / 'AUTO_RESET'
    failure_mode         # Which mode (e.g. 'login_storm')
    triggered_by         # 'admin:email@...' or 'scheduler'
    note                 # Optional description
    timestamp            # DateTime
```

---

## Admin Chaos Panel (/admin/chaos) — chaos_admin.py

**Template:** `admin/chaos.html`

**Sections:**
1. **Current State** — Live toggle switches for each failure mode (updates via AJAX POST)
2. **Named Profiles** — Fire buttons for each profile (sets multiple modes at once)
3. **Scheduler Status** — Shows if auto scheduler is enabled, next fire times
4. **ChaosEvent Log** — Last 50 chaos events (type / mode / who / when)

**AJAX endpoints:**
- `POST /admin/chaos/toggle` — `{mode: 'login_storm', enabled: true/false}`
- `POST /admin/chaos/profile` — `{profile: 'full_outage'}`
- `GET /admin/chaos/state.json` — Public JSON of current chaos state (for Site24x7 REST API monitor)

---

## Observability Integration

- `/health` — Always returns 200 (shallow)
- `/health/deep` — Hits DB, returns 503 if `db_unavailable=True`
- `/metrics` — Plain text: user count, booking count, chaos state summary
- `/admin/chaos/state.json` — Full chaos state as JSON (Site24x7 can poll this)
- All chaos events log to structured JSON (if `SNAPTRAVELS_JSON_LOGS=1`)
- Trace IDs injected into every request (`X-Trace-Id` header) via observability.py middleware
