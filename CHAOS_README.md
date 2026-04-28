# SnapTravels — Chaos Engineering & Site24x7 Observability Guide

SnapTravels ships with a built-in chaos / failure-injection engine that makes it a living demo for Full Stack Observability and Digital Experience Monitoring. This guide explains what the engine does, how to control it, and how to correlate every injected failure across Site24x7 Synthetic, APM, RUM, Mobile APM, and REST API monitors.

## 1. What the engine does

The engine has three layers:

1. **FailureMode singleton** (`app/models.py`) — a single DB row holding every live failure knob: login failure rate, DB slowdown, payment gateway state, checkout exception rate, API 5xx rate, and more.
2. **Chaos hooks** (`app/services/chaos.py`) — the real code paths (login, search, booking, payment, mobile API) call `maybe_fail_*()` helpers that read the singleton and deterministically decide whether to sleep, raise, or return an error. Every injected failure is logged to `ChaosEvent` and to the structured JSON log stream with the active `trace_id`.
3. **Scheduler** (`app/services/chaos_scheduler.py`) — an APScheduler `BackgroundScheduler` that, once per day, picks two random windows during business hours: one 15–30 min login storm and one ~30 min service outage chosen from a rotating profile list (DB slowdown, payment gateway down, checkout exceptions, search upstream timeouts, API 5xx storm, DB unavailable). A cleanup job runs every minute and closes any window whose end time has passed.

## 2. Admin UI — `/admin/chaos`

Log in as an admin and visit `/admin/chaos` for the live control panel. You can:

- Flip the master switch on/off
- Tune any individual knob (failure rates, latency, gateway state)
- Fire a named outage on demand for a specified duration — perfect for live RCA demos
- End the current outage immediately
- Review the last 50 `ChaosEvent` audit rows

The panel also exposes a JSON state endpoint at `GET /admin/chaos/state.json` which is unauthenticated and CSRF-exempt so you can point a Site24x7 REST API monitor at it and alert when a chaos window is active.

## 3. Turning on the scheduler

The background scheduler is opt-in. Set:

```
export CHAOS_SCHEDULER_ENABLED=1
```

before launching the app. Leave it unset when you don't want automatic outages (e.g. for pre-recorded demos).

## 4. Site24x7 integration points

| Site24x7 product | SnapTravels integration |
| --- | --- |
| **Synthetic web transaction browser monitor** | Record a journey against `/`, `/flights`, `/hotels`, `/login`, `/booking`. Each response carries `X-Site24x7-Trace-Id` so you can pivot from a failing step to the APM trace. Point a second synthetic at `/health/deep` — it flips to 503 during a `db_down` window. |
| **APM (Python agent)** | Install the Site24x7 Python APM agent alongside the app. The `ChaosInjectedError` subclasses (`LoginChaosError`, `PaymentChaosError`, …) appear as distinct error groups in the APM dashboard so you can prove that the chaos module is the root cause. |
| **RUM** | Set `SITE24X7_RUM_APP_KEY` in the environment — the beacon is injected automatically by `app/templates/layouts/base.html` on every page view. |
| **Mobile APM (iOS / Android)** | Point your mobile apps at `/mobile-api/v1/*`. During an `api_5xx_storm` outage the `before_request` hook returns 503s with a `trace_id` so the mobile APM → backend APM correlation demo works end-to-end. |
| **REST API monitor** | Monitor `/health`, `/health/deep`, `/metrics`, `/mobile-api/v1/config`, and `/admin/chaos/state.json`. The last one tells you whether the system is "down for real" or "down because of a scheduled chaos window". |
| **Log management** | Set `SNAPTRAVELS_JSON_LOGS=1` to emit structured JSON logs with `trace_id`, `level`, and message fields. The log collector auto-correlates to APM traces via `trace_id`. |

## 5. Reproducible RCA story

When a scheduled outage fires, here is what Site24x7 sees in order:

1. **Synthetic** — the scripted browser journey fails at the login step with `LoginChaosError` (or checkout, etc.), capturing the failing step + response trace id.
2. **RUM** — real users on `snaptravels.online` show a spike in failed transactions and rage clicks on the same page.
3. **APM** — the Python agent reports a spike in a specific exception class. Drill into the trace and you see the `maybe_fail_login` stack frame.
4. **Logs** — the JSON log stream contains `CHAOS_EVENT type=INJECTED_ERROR label=login_failure` entries sharing the same `trace_id`.
5. **Mobile APM** — iOS / Android sessions show matching 503s from `/mobile-api/v1/auth/login` with the same trace id in the response header.
6. **Chaos state API** — `/admin/chaos/state.json` confirms `outage_label=login_storm` with start + end timestamps, closing the RCA loop.

## 6. Failure profiles shipped out of the box

| Profile | Knobs set | Typical demo |
| --- | --- | --- |
| `login_storm` | `login_failure_rate=0.6`, `login_slowdown_ms=800` | Auth outage → RUM rage clicks → APM auth errors |
| `db_slowdown` | `db_slowdown_ms=2500`, `checkout_slowdown_ms=1500` | Slow page loads, timeouts, cart abandonment |
| `db_unavailable` | `db_down=True` | `/health/deep` flips to 503, synthetic fails, APM shows DB errors |
| `payment_gateway_down` | `payment_gateway_down=True` | Booking reaches payment then fails, checkout funnel drop |
| `checkout_exceptions` | `checkout_exception_rate=0.5`, `checkout_slowdown_ms=600` | Random booking crashes, APM exception spike |
| `search_upstream_timeout` | `search_timeout_rate=0.4`, `search_slowdown_ms=1500` | Search page hangs, RUM long tasks, APM timeouts |
| `api_5xx_storm` | `api_5xx_rate=0.35`, `api_slowdown_ms=700` | Mobile APM 5xx spike, REST monitor alerts |

## 7. Manual testing

After running `pip install -r requirements.txt` and starting the app:

```
# Fire a login storm for 5 minutes manually
curl -X POST -H "Cookie: session=<admin-session>" \
     -d 'profile=login_storm&duration_minutes=5' \
     http://localhost:5000/admin/chaos/trigger-outage

# Confirm it is active
curl http://localhost:5000/admin/chaos/state.json

# Clear it
curl -X POST -H "Cookie: session=<admin-session>" \
     http://localhost:5000/admin/chaos/end-outage
```

## 8. Production hardening checklist

- [ ] Set `SECRET_KEY` env var (remove the dev fallback before prod)
- [ ] Set `DATABASE_URL` to a Postgres instance so `db_down` outages are realistic
- [ ] Set `SNAPTRAVELS_JSON_LOGS=1` so APM log ingestion is structured
- [ ] Set `SITE24X7_RUM_APP_KEY` to enable the RUM beacon
- [ ] Install the Site24x7 Python APM agent (`site24x7monitoring`) per their docs
- [ ] Set `CHAOS_SCHEDULER_ENABLED=1` once you are ready for automatic daily outages
- [ ] Point Site24x7 REST API monitor at `/admin/chaos/state.json` so alerts distinguish scheduled chaos from real incidents

That is everything needed to run SnapTravels as a production-grade observability demo with built-in, believable, correlated failures.
