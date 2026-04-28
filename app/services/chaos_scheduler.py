"""
Chaos scheduler — SnapTravels

Runs in-process via APScheduler BackgroundScheduler and fires chaos events
on a continuous automatic schedule.

──────────────────────────────────────────────────────────────────
AUTO CHAOS MODE  (toggle in /admin/chaos)
──────────────────────────────────────────────────────────────────
  When FailureMode.auto_chaos_mode is True the scheduler runs a
  CONTINUOUS LOOP of 5 chaos types, cycling 24/7:

    Slot 1 — Named Outage Profile        30 or 60 min
    Slot 2 — Page Load Performance Chaos 30 or 60 min
    Slot 3 — Functionality Failures      30 or 60 min
    Slot 4 — Component-Level Chaos       30 or 60 min
    Slot 5 — A/B Test Chaos             30 or 60 min

  Scheduling rules
  ─────────────────
  • All times are stored and compared in UTC; displayed in IST.
  • A minimum 3-hour (180 min) cooling-off gap is enforced between
    the end of one event and the start of the next.
  • The 5 types cycle continuously — after the last type finishes
    and its cooldown elapses, a new shuffled cycle begins.
  • The slot order is reshuffled fresh at 00:05 UTC every day.
  • On server restart: pending jobs are restored from the stored
    JSON schedule — the plan is NOT lost on restart.
  • Each event auto-expires (no manual action needed).
  • The schedule is stored as JSON in
    FailureMode.auto_chaos_schedule_json so the UI can render a
    timeline with past / running / upcoming status.

──────────────────────────────────────────────────────────────────
MANUAL MODE  (legacy — unchanged)
──────────────────────────────────────────────────────────────────
  • One "login_storm" + one "service_outage" at random times.
  • Reshuffled daily at 00:05 UTC.
"""

import json
import logging
import random
from datetime import datetime, timedelta

logger = logging.getLogger('snaptravels.chaos.scheduler')

_scheduler = None   # module-level singleton

# ──────────────────────────────────────────────────────────────────────────────
# Named outage profiles
# ──────────────────────────────────────────────────────────────────────────────
OUTAGE_PROFILES = [
    ('db_slowdown',             {'db_slowdown_ms': 2500, 'checkout_slowdown_ms': 1500}),
    ('payment_gateway_down',    {'payment_gateway_down': True}),
    ('checkout_exceptions',     {'checkout_exception_rate': 0.5, 'checkout_slowdown_ms': 600}),
    ('search_upstream_timeout', {'search_timeout_rate': 0.4, 'search_slowdown_ms': 1500}),
    ('api_5xx_storm',           {'api_5xx_rate': 0.35, 'api_slowdown_ms': 700}),
    ('db_unavailable',          {'db_down': True}),
    ('login_storm',             {'login_failure_rate': 0.6, 'login_slowdown_ms': 800}),
    ('email_service_down',      {'func_chaos': True, 'func_email_chaos': True}),
    ('cdn_failure',             {'page_load_chaos': True, 'page_load_webfont_failure': True,
                                  'page_load_inject_resource_failures': True, 'page_load_delay_ms': 0}),
    ('maintenance_flood',       {'func_chaos': True, 'func_maintenance_flood': True}),
    ('third_party_blackout',    {'page_load_chaos': True, 'page_load_inject_resource_failures': True,
                                  'component_chaos': True, 'component_break_booking': True}),
]

# Auto-mode slots: (type_key, human label, [duration choices in minutes])
AUTO_CHAOS_CATEGORIES = [
    ('named_outage',    'Named Outage Profile',        [30, 60]),
    ('page_load',       'Page Load Performance Chaos', [30, 60]),
    ('func_chaos',      'Functionality Failures',      [30, 60]),
    ('component_chaos', 'Component-Level Chaos',       [30, 60]),
    ('ab_test',         'A/B Test Chaos',              [30, 60]),
]

MIN_GAP_MINUTES = 180   # 3-hour mandatory cool-down between events


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.utcnow().replace(second=0, microsecond=0)


def _job_id(chaos_type: str, start: datetime, idx: int) -> str:
    """Unique job ID that includes the calendar date so it never collides across days."""
    return f"auto_chaos_{chaos_type}_{start.strftime('%Y%m%d_%H%M')}_{idx}"


# ──────────────────────────────────────────────────────────────────────────────
# Intensity scaling ─────────────────────────────────────────────────────────────
# 0=Low, 1=Medium, 2=High, 3=Critical
_INTENSITY_RATE_SCALE  = {0: 0.2, 1: 0.5, 2: 0.8, 3: 1.0}
_INTENSITY_DELAY_SCALE = {0: 0.3, 1: 0.6, 2: 0.9, 3: 1.0}

def _get_intensity(app) -> int:
    with app.app_context():
        from app.models import FailureMode
        return getattr(FailureMode.current(), 'chaos_intensity', 1) or 1

def _scale_rate(value: float, intensity: int) -> float:
    return round(value * _INTENSITY_RATE_SCALE.get(intensity, 0.5), 2)

def _scale_delay(value: int, intensity: int) -> int:
    return max(0, int(value * _INTENSITY_DELAY_SCALE.get(intensity, 0.6)))


# ── Webhook notification ───────────────────────────────────────────────────────
def _fire_webhook(app, event_type: str, chaos_type: str, duration: int = 0, **extra):
    """POST chaos event to the configured webhook URL (non-blocking, best-effort)."""
    try:
        with app.app_context():
            from app.models import FailureMode
            url = getattr(FailureMode.current(), 'webhook_url', None)
        if not url:
            return
        import urllib.request, urllib.error, json as _json, threading
        from datetime import datetime as _dt
        payload = {
            'event': event_type,
            'chaos_type': chaos_type,
            'duration_minutes': duration,
            'timestamp': _dt.utcnow().isoformat() + 'Z',
            **extra
        }
        body = _json.dumps(payload).encode()
        req  = urllib.request.Request(url, data=body,
               headers={'Content-Type': 'application/json', 'User-Agent': 'SnapTravels-Chaos/1.0'})
        def _send():
            try:
                urllib.request.urlopen(req, timeout=5)
                logger.info(f"[chaos] webhook fired: {event_type} → {url}")
            except Exception as e:
                logger.warning(f"[chaos] webhook failed: {e}")
        threading.Thread(target=_send, daemon=True).start()
    except Exception as e:
        logger.warning(f"[chaos] webhook setup error: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Manual-mode runners  (unchanged)
# ──────────────────────────────────────────────────────────────────────────────

def _run_login_storm(app):
    """Inject a 15-30 minute login failure storm (manual mode)."""
    from app.services.chaos import start_outage
    duration = random.randint(15, 30)
    with app.app_context():
        logger.warning(f"[chaos] manual login_storm for {duration}min")
        start_outage(
            'login_storm',
            duration_minutes=duration,
            login_failure_rate=round(random.uniform(0.4, 0.8), 2),
            login_slowdown_ms=random.randint(400, 1200),
        )


def _run_service_outage(app):
    """Pick a random named profile and apply it for ~30 min (manual mode)."""
    from app.services.chaos import start_outage
    label, overrides = random.choice(OUTAGE_PROFILES)
    duration = random.randint(25, 35)
    with app.app_context():
        logger.warning(f"[chaos] manual {label} for {duration}min")
        start_outage(label, duration_minutes=duration, **overrides)


# ──────────────────────────────────────────────────────────────────────────────
# Auto-mode runners
# ──────────────────────────────────────────────────────────────────────────────

def _auto_start_named_outage(app, duration):
    """Auto-mode: fire a random named outage profile."""
    from app.services.chaos import start_outage
    from app.models import FailureMode, ChaosEvent
    from app import db
    label, overrides = random.choice(OUTAGE_PROFILES)
    with app.app_context():
        logger.warning(f"[auto-chaos] NAMED OUTAGE → {label} for {duration}min")
        start_outage(label, duration_minutes=duration, **overrides)
        state = FailureMode.current()
        state.auto_chaos_current_type = f'named_outage:{label}'
        state.auto_chaos_ends_at      = _utcnow() + timedelta(minutes=duration)
        ev = ChaosEvent(event_type='AUTO_CHAOS_START', label=f'named_outage:{label}')
        ev.details = {'duration_minutes': duration, 'profile': label, 'overrides': overrides}
        db.session.add(ev)
        db.session.commit()
        _fire_webhook(app, 'AUTO_CHAOS_START', 'named_outage', duration, profile=label)


def _auto_start_page_load(app, duration):
    """Auto-mode: enable Page Load Performance Chaos."""
    from app.models import FailureMode, ChaosEvent
    from app import db
    with app.app_context():
        state = FailureMode.current()
        logger.warning(f"[auto-chaos] PAGE LOAD CHAOS for {duration}min")
        state.page_load_chaos                    = True
        state.page_load_delay_ms                 = random.choice([1500, 2000, 2500, 3000])
        state.page_load_target_pages             = '["all"]'
        state.page_load_inject_js_errors         = random.choice([True, False])
        state.page_load_inject_resource_failures = random.choice([True, False])
        state.page_load_inject_render_blocking   = True
        state.page_load_large_payload            = random.choice([True, False])
        state.page_load_inject_memory_pressure   = False
        # New page load fields
        state.page_load_webfont_failure          = random.choice([True, False])
        state.page_load_ttfb_spike               = random.choice([True, False])
        state.page_load_cache_chaos              = random.choice([True, False])
        state.auto_chaos_current_type            = 'page_load'
        state.auto_chaos_ends_at                 = _utcnow() + timedelta(minutes=duration)
        ev = ChaosEvent(event_type='AUTO_CHAOS_START', label='page_load')
        ev.details = {
            'duration_minutes': duration,
            'page_load_delay_ms': state.page_load_delay_ms,
            'js_errors': state.page_load_inject_js_errors,
            'resource_failures': state.page_load_inject_resource_failures,
            'render_blocking': state.page_load_inject_render_blocking,
            'large_payload': state.page_load_large_payload,
        }
        db.session.add(ev)
        db.session.commit()
        _fire_webhook(app, 'AUTO_CHAOS_START', 'page_load', duration)


def _auto_start_func_chaos(app, duration):
    """Auto-mode: enable Functionality Failures Chaos."""
    from app.models import FailureMode, ChaosEvent
    from app import db
    with app.app_context():
        state = FailureMode.current()
        logger.warning(f"[auto-chaos] FUNCTIONALITY FAILURES for {duration}min")
        state.func_chaos                = True
        state.func_search_empty         = random.choice([True, False])
        state.func_form_errors          = random.choice([True, False])
        state.func_broken_images        = random.choice([True, False])
        state.func_infinite_spin        = random.choice([True, False])
        state.func_broken_cta           = random.choice([True, False])
        state.func_session_kill_rate    = round(random.uniform(0.1, 0.3), 2)
        state.func_404_storm_rate       = round(random.uniform(0.05, 0.2), 2)
        # New func_* fields (added in chaos expansion)
        state.func_wrong_search         = random.choice([True, False])
        state.func_fake_soldout         = random.choice([True, False])
        state.func_date_picker_broken   = random.choice([True, False])
        state.func_otp_invalid          = random.choice([True, False])
        state.func_email_chaos          = random.choice([True, False])
        state.func_maintenance_flood    = random.choice([True, False])
        state.auto_chaos_current_type   = 'func_chaos'
        state.auto_chaos_ends_at        = _utcnow() + timedelta(minutes=duration)
        ev = ChaosEvent(event_type='AUTO_CHAOS_START', label='func_chaos')
        ev.details = {
            'duration_minutes': duration,
            'search_empty': state.func_search_empty,
            'form_errors': state.func_form_errors,
            'broken_images': state.func_broken_images,
            'infinite_spin': state.func_infinite_spin,
            'broken_cta': state.func_broken_cta,
            'session_kill_rate': state.func_session_kill_rate,
            '404_storm_rate': state.func_404_storm_rate,
            'wrong_search': state.func_wrong_search,
            'fake_soldout': state.func_fake_soldout,
            'date_picker_broken': state.func_date_picker_broken,
            'otp_invalid': state.func_otp_invalid,
            'email_chaos': state.func_email_chaos,
            'maintenance_flood': state.func_maintenance_flood,
        }
        db.session.add(ev)
        db.session.commit()
        _fire_webhook(app, 'AUTO_CHAOS_START', 'func_chaos', duration)


def _auto_start_component_chaos(app, duration):
    """Auto-mode: enable Component-Level Chaos."""
    from app.models import FailureMode, ChaosEvent
    from app import db
    with app.app_context():
        state = FailureMode.current()
        logger.warning(f"[auto-chaos] COMPONENT-LEVEL CHAOS for {duration}min")
        state.component_chaos              = True
        state.component_chaos_rate         = random.randint(40, 80)
        state.component_target_pages       = '["all"]'
        state.component_break_search       = random.choice([True, False])
        state.component_break_results      = random.choice([True, False])
        state.component_break_booking      = random.choice([True, False])
        state.component_break_pricing      = random.choice([True, False])
        state.component_break_css          = random.choice([True, False])
        state.component_break_nav          = random.choice([True, False])
        # New component_* fields (added in chaos expansion)
        state.component_break_autocomplete = random.choice([True, False])
        state.component_break_datepicker   = random.choice([True, False])
        state.component_break_ratings      = random.choice([True, False])
        state.component_break_loyalty      = random.choice([True, False])
        state.auto_chaos_current_type      = 'component_chaos'
        state.auto_chaos_ends_at           = _utcnow() + timedelta(minutes=duration)
        ev = ChaosEvent(event_type='AUTO_CHAOS_START', label='component_chaos')
        ev.details = {
            'duration_minutes': duration,
            'chaos_rate': state.component_chaos_rate,
            'break_search': state.component_break_search,
            'break_results': state.component_break_results,
            'break_booking': state.component_break_booking,
            'break_pricing': state.component_break_pricing,
            'break_css': state.component_break_css,
            'break_nav': state.component_break_nav,
            'break_autocomplete': state.component_break_autocomplete,
            'break_datepicker': state.component_break_datepicker,
            'break_ratings': state.component_break_ratings,
            'break_loyalty': state.component_break_loyalty,
        }
        db.session.add(ev)
        db.session.commit()
        _fire_webhook(app, 'AUTO_CHAOS_START', 'component_chaos', duration)


def _auto_start_ab_test(app, duration):
    """Auto-mode: enable A/B Test Chaos — mutates page identifiers without visual change."""
    from app.models import FailureMode, ChaosEvent
    from app import db
    with app.app_context():
        state = FailureMode.current()
        logger.warning(f"[auto-chaos] A/B TEST CHAOS for {duration}min")
        state.ab_test_chaos   = True
        state.ab_test_login   = random.choice([True, False])
        state.ab_test_search  = True   # always on — most impactful for monitoring
        state.ab_test_booking = random.choice([True, False])
        state.ab_test_profile = random.choice([True, False])
        state.auto_chaos_current_type = 'ab_test'
        state.auto_chaos_ends_at      = _utcnow() + timedelta(minutes=duration)
        ev = ChaosEvent(event_type='AUTO_CHAOS_START', label='ab_test')
        ev.details = {
            'duration_minutes': duration,
            'login': state.ab_test_login,
            'search': state.ab_test_search,
            'booking': state.ab_test_booking,
            'profile': state.ab_test_profile,
        }
        db.session.add(ev)
        db.session.commit()
        _fire_webhook(app, 'AUTO_CHAOS_START', 'ab_test', duration)


_AUTO_RUNNERS = {
    'named_outage':    _auto_start_named_outage,
    'page_load':       _auto_start_page_load,
    'func_chaos':      _auto_start_func_chaos,
    'component_chaos': _auto_start_component_chaos,
    'ab_test':         _auto_start_ab_test,
}


# ──────────────────────────────────────────────────────────────────────────────
# Auto-mode cleanup: end a running chaos segment
# ──────────────────────────────────────────────────────────────────────────────

def _auto_end_section_chaos(app, chaos_type: str):
    """
    Reset the chaos knobs for the given type and clear auto tracking fields.
    For named_outage types this delegates to end_outage().
    """
    from app.models import FailureMode, ChaosEvent
    from app import db
    from app.services.chaos import end_outage

    with app.app_context():
        state = FailureMode.current()
        logger.warning(f"[auto-chaos] END {chaos_type}")

        if chaos_type == 'page_load':
            state.page_load_chaos                    = False
            state.page_load_delay_ms                 = 0
            state.page_load_inject_js_errors         = False
            state.page_load_inject_resource_failures = False
            state.page_load_inject_render_blocking   = False
            state.page_load_large_payload            = False
            state.page_load_inject_memory_pressure   = False
            # New page load fields
            state.page_load_webfont_failure          = False
            state.page_load_ttfb_spike               = False
            state.page_load_cache_chaos              = False

        elif chaos_type == 'func_chaos':
            state.func_chaos              = False
            state.func_search_empty       = False
            state.func_form_errors        = False
            state.func_broken_images      = False
            state.func_infinite_spin      = False
            state.func_broken_cta         = False
            state.func_session_kill_rate  = 0.0
            state.func_404_storm_rate     = 0.0
            # New functionality fields
            state.func_wrong_search       = False
            state.func_fake_soldout       = False
            state.func_date_picker_broken = False
            state.func_otp_invalid        = False
            state.func_email_chaos        = False
            state.func_maintenance_flood  = False

        elif chaos_type == 'component_chaos':
            state.component_chaos         = False
            state.component_chaos_rate    = 50
            state.component_break_search  = False
            state.component_break_results = False
            state.component_break_booking = False
            state.component_break_pricing = False
            state.component_break_css     = False
            state.component_break_nav     = False
            # New component fields
            state.component_break_autocomplete = False
            state.component_break_datepicker   = False
            state.component_break_ratings      = False
            state.component_break_loyalty      = False

        elif chaos_type == 'ab_test':
            state.ab_test_chaos   = False
            state.ab_test_login   = False
            state.ab_test_search  = False
            state.ab_test_booking = False
            state.ab_test_profile = False

        elif 'named_outage' in chaos_type:
            end_outage(reason='auto_chaos_window_expired')

        state.auto_chaos_current_type = None
        state.auto_chaos_ends_at      = None

        ev = ChaosEvent(event_type='AUTO_CHAOS_END', label=chaos_type)
        ev.details = {'reason': 'window_expired'}
        db.session.add(ev)
        db.session.commit()
        _fire_webhook(app, 'AUTO_CHAOS_END', chaos_type)


# ──────────────────────────────────────────────────────────────────────────────
# Cleanup job — runs every minute, handles both modes
# ──────────────────────────────────────────────────────────────────────────────

def _cleanup_expired(app):
    """End any outage or auto-chaos segment whose window has expired."""
    from app.services.chaos import end_outage
    from app.models import FailureMode

    with app.app_context():
        state = FailureMode.current()
        now   = _utcnow()

        if state.auto_chaos_mode:
            # ── Auto mode: only check auto_chaos_ends_at ─────────────────────
            if (state.auto_chaos_ends_at
                    and state.auto_chaos_ends_at <= now
                    and state.auto_chaos_current_type):
                _auto_end_section_chaos(app, state.auto_chaos_current_type)
        else:
            # ── Manual mode: check named outage window ────────────────────────
            if state.outage_ends_at and state.outage_ends_at <= now:
                end_outage(reason='window_expired')


# ──────────────────────────────────────────────────────────────────────────────
# Job registration helper
# ──────────────────────────────────────────────────────────────────────────────

def _register_job(w: dict, app, idx: int):
    """
    Register a single auto-chaos window as an APScheduler 'date' job.
    Silently skips windows whose start time is already in the past.
    """
    global _scheduler
    if _scheduler is None:
        return

    start = w['start_dt']
    now   = _utcnow()
    if start <= now:
        logger.debug(f"[auto-chaos] skip past window {w['type']} @{start:%H:%M} UTC")
        return

    runner = _AUTO_RUNNERS.get(w['type'])
    if runner is None:
        logger.warning(f"[auto-chaos] unknown chaos type '{w['type']}' — skipping")
        return

    job_id = _job_id(w['type'], start, idx)
    try:
        _scheduler.add_job(
            runner, 'date',
            run_date=start,
            args=[app, w['duration']],
            id=job_id,
            replace_existing=True,
        )
        logger.info(
            f"[auto-chaos] registered {w['label']} "
            f"@{start:%H:%M} UTC for {w['duration']}min (job={job_id})"
        )
    except Exception as e:
        logger.exception(f"[auto-chaos] failed to register job {job_id}: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Daily schedule builder — auto-chaos mode
# ──────────────────────────────────────────────────────────────────────────────

def _build_auto_chaos_windows(excluded_types=None) -> list:
    """
    Build a CONTINUOUS 24-hour auto-chaos schedule in UTC.

    Rules:
    • The chaos categories (minus any excluded) cycle in a loop.
    • Each cycle shuffles the types randomly.
    • First event starts ~10 minutes from now.
    • Each event lasts 30 or 60 min (randomly chosen).
    • A 3-hour (MIN_GAP_MINUTES) cooling-off gap between events.
    • The loop continues until the schedule extends past midnight UTC.
    • All datetimes are UTC.

    Args:
        excluded_types: set of type_keys to skip (e.g. {'ab_test', 'component_chaos'})

    Returns a list of window dicts with:
        type, label, duration (int minutes), start_dt, end_dt (datetime UTC)
    """
    excluded = set(excluded_types or [])
    now          = _utcnow()
    utc_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day   = utc_midnight + timedelta(hours=24)

    # Start at least 10 minutes from now
    cursor = now + timedelta(minutes=10)

    # Filter out excluded types
    active_categories = [c for c in AUTO_CHAOS_CATEGORIES if c[0] not in excluded]
    if not active_categories:
        logger.warning("[auto-chaos] All chaos types are excluded — no schedule generated")
        return []

    windows = []
    cycle_count = 0
    max_cycles  = 10

    while cursor < end_of_day and cycle_count < max_cycles:
        # Shuffle categories for each cycle
        sequence = list(active_categories)
        random.shuffle(sequence)

        for type_key, label, duration_choices in sequence:
            if cursor >= end_of_day:
                break

            duration = random.choice(duration_choices)
            start    = cursor
            end      = start + timedelta(minutes=duration)

            # Don't schedule events that would end way past midnight
            if start >= end_of_day:
                break

            windows.append({
                'type':     type_key,
                'label':    label,
                'duration': duration,
                'start_dt': start,
                'end_dt':   end,
            })

            # 3-hour gap + random 0–30 min jitter
            gap    = random.randint(MIN_GAP_MINUTES, MIN_GAP_MINUTES + 30)
            cursor = end + timedelta(minutes=gap)

        cycle_count += 1

    return windows


def _windows_to_json(windows: list) -> str:
    """Serialise window list (with datetime objects) to JSON string."""
    return json.dumps([
        {
            'type':     w['type'],
            'label':    w['label'],
            'duration': w['duration'],
            'start':    w['start_dt'].isoformat(),
            'end':      w['end_dt'].isoformat(),
        }
        for w in windows
    ])


def _windows_from_json(json_str: str) -> list:
    """Deserialise JSON string back to window list with datetime objects."""
    rows = json.loads(json_str)
    result = []
    for r in rows:
        result.append({
            'type':     r['type'],
            'label':    r['label'],
            'duration': r['duration'],
            'start_dt': datetime.fromisoformat(r['start']),
            'end_dt':   datetime.fromisoformat(r['end']),
        })
    return result


def _schedule_auto_chaos_day(app):
    """
    Build a fresh continuous-loop schedule, persist it, and register all jobs.
    Called by the 00:05 UTC daily cron and when auto-mode is first enabled.
    The schedule fills the 24h window with repeating cycles of all 5 chaos types.

    NOTE: The schedule JSON is ALWAYS generated and stored (for the UI timeline)
    even if APScheduler is not available. Job registration is best-effort.
    """
    global _scheduler

    with app.app_context():
        from app.models import FailureMode
        state = FailureMode.current()
        if not state.auto_chaos_mode:
            return
        # Read excluded types
        excluded = set()
        if state.auto_chaos_excluded_json:
            try:
                excluded = set(json.loads(state.auto_chaos_excluded_json))
            except Exception:
                excluded = set()

    windows = _build_auto_chaos_windows(excluded_types=excluded)

    # Always persist the schedule so the UI can display the timeline
    with app.app_context():
        from app.models import FailureMode
        from app import db
        state = FailureMode.current()
        state.auto_chaos_schedule_json = _windows_to_json(windows)
        db.session.commit()

    # Register APScheduler jobs (best-effort — skipped if scheduler not available)
    if _scheduler is not None:
        for idx, w in enumerate(windows):
            _register_job(w, app, idx)

    logger.info(
        "[auto-chaos] Today's schedule (%d events): " % len(windows)
        + " → ".join(
            f"{w['label']}@{w['start_dt']:%H:%M}UTC({w['duration']}min)"
            for w in windows
        )
    )


def _restore_auto_chaos_jobs(app):
    """
    On server restart: re-register pending APScheduler jobs from the
    already-stored auto_chaos_schedule_json without rebuilding the schedule.
    Returns True if any future jobs were found and registered.
    """
    global _scheduler
    if _scheduler is None:
        return False

    with app.app_context():
        from app.models import FailureMode
        state = FailureMode.current()
        if not state.auto_chaos_mode:
            return False
        if not state.auto_chaos_schedule_json:
            return False

        try:
            windows = _windows_from_json(state.auto_chaos_schedule_json)
        except Exception as e:
            logger.warning(f"[auto-chaos] couldn't parse stored schedule: {e}")
            return False

        now   = _utcnow()

        # Only use windows that haven't started yet
        future_windows = [
            w for w in windows
            if w['start_dt'] > now
        ]
        if not future_windows:
            logger.info("[auto-chaos] stored schedule has no future events — will rebuild")
            return False

        for idx, w in enumerate(windows):
            _register_job(w, app, idx)   # skips past windows silently

        logger.info(
            f"[auto-chaos] restored {len(future_windows)} pending job(s) from stored schedule"
        )
        return True


# ──────────────────────────────────────────────────────────────────────────────
# Daily schedule builder — manual mode
# ──────────────────────────────────────────────────────────────────────────────

def _schedule_daily_windows(app):
    """Pick fresh times for today's login_storm + service_outage (manual mode)."""
    global _scheduler
    if _scheduler is None:
        return

    with app.app_context():
        from app.models import FailureMode
        if FailureMode.current().auto_chaos_mode:
            logger.info("[chaos] auto_chaos_mode ON — skipping manual daily windows")
            return

    now       = _utcnow()
    today_end = now.replace(hour=23, minute=30, second=0)
    min_start = now + timedelta(hours=1)
    if min_start >= today_end:
        return

    avail = max(1, int((today_end - min_start).total_seconds() // 60) - 60)
    login_start   = min_start + timedelta(minutes=random.randint(0, avail))
    service_start = min_start + timedelta(minutes=random.randint(0, avail))

    if abs((service_start - login_start).total_seconds()) < 60 * 45:
        service_start = login_start + timedelta(minutes=90)
        if service_start >= today_end:
            service_start = login_start - timedelta(minutes=90)

    try:
        _scheduler.add_job(
            _run_login_storm, 'date', run_date=login_start,
            args=[app], id=f'login_storm_{login_start.isoformat()}',
            replace_existing=True,
        )
        _scheduler.add_job(
            _run_service_outage, 'date', run_date=service_start,
            args=[app], id=f'service_outage_{service_start.isoformat()}',
            replace_existing=True,
        )
        logger.info(
            f"[chaos] manual schedule: login_storm@{login_start:%H:%M}UTC "
            f"service_outage@{service_start:%H:%M}UTC"
        )
    except Exception as e:
        logger.exception(f"[chaos] failed to schedule manual daily windows: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Daily reshuffle cron — 00:05 UTC
# ──────────────────────────────────────────────────────────────────────────────

def _daily_reshuffle(app):
    """Called at 00:05 UTC. Rebuilds today's schedule for whichever mode is active."""
    with app.app_context():
        from app.models import FailureMode
        auto = FailureMode.current().auto_chaos_mode

    if auto:
        logger.info("[auto-chaos] daily reshuffle — building new 24h schedule")
        _schedule_auto_chaos_day(app)
    else:
        _schedule_daily_windows(app)


# ──────────────────────────────────────────────────────────────────────────────
# Public APIs
# ──────────────────────────────────────────────────────────────────────────────

def reschedule_auto_chaos(app):
    """
    Called when auto_chaos_mode is toggled ON.
    Schedules today's sequence immediately without waiting for the cron.
    Always generates the schedule JSON even if APScheduler is unavailable.
    """
    logger.info("[auto-chaos] reschedule_auto_chaos called — building fresh schedule")
    _schedule_auto_chaos_day(app)


def cancel_auto_chaos(app):
    """
    Called when auto_chaos_mode is toggled OFF.
    Stops any running chaos event and removes all pending auto-chaos jobs.
    """
    global _scheduler

    # End any currently running auto-chaos event
    with app.app_context():
        from app.models import FailureMode
        from app import db
        state = FailureMode.current()
        ctype = state.auto_chaos_current_type

    if ctype:
        _auto_end_section_chaos(app, ctype)

    # Clear schedule tracking fields
    with app.app_context():
        from app.models import FailureMode
        from app import db
        state = FailureMode.current()
        state.auto_chaos_schedule_json = None
        state.auto_chaos_current_type  = None
        state.auto_chaos_ends_at       = None
        db.session.commit()

    # Remove all pending auto-chaos APScheduler jobs
    if _scheduler:
        for job in list(_scheduler.get_jobs()):
            if job.id.startswith('auto_chaos_'):
                try:
                    job.remove()
                except Exception:
                    pass

    logger.info("[auto-chaos] cancelled — all pending jobs removed, state cleared")


# ──────────────────────────────────────────────────────────────────────────────
# Scheduler initialisation
# ──────────────────────────────────────────────────────────────────────────────

def init_scheduler(app):
    """Wire APScheduler into the Flask app. Idempotent — safe to call multiple times."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        app.logger.warning(
            "APScheduler not installed — chaos scheduler disabled. "
            "Run: pip install APScheduler"
        )
        return None

    _scheduler = BackgroundScheduler(daemon=True, timezone='UTC')

    # ── Permanent jobs ────────────────────────────────────────────────────────
    _scheduler.add_job(
        _cleanup_expired, 'interval', minutes=1,
        args=[app], id='chaos_cleanup', replace_existing=True,
    )
    _scheduler.add_job(
        _daily_reshuffle, 'cron',
        hour=0, minute=5, args=[app],
        id='chaos_daily_reshuffle', replace_existing=True,
    )

    # ── Data sampling: daily cleanup at midnight UTC (05:30 IST) ─────────
    try:
        from app.services.data_cleanup import run_cleanup
        _scheduler.add_job(
            run_cleanup, 'cron',
            hour=0, minute=0, args=[app],
            id='daily_data_cleanup', replace_existing=True,
        )
        app.logger.info("[cleanup] Daily data cleanup job registered (midnight UTC)")
    except Exception as e:
        app.logger.warning(f"[cleanup] Failed to register cleanup job: {e}")

    _scheduler.start()

    # ── On startup: restore or build today's schedule ─────────────────────────
    with app.app_context():
        try:
            from app.models import FailureMode
            state = FailureMode.current()
            if state.auto_chaos_mode:
                app.logger.info("[chaos] auto_chaos_mode ON — restoring/building schedule")
                restored = _restore_auto_chaos_jobs(app)
                if not restored:
                    _schedule_auto_chaos_day(app)
            else:
                _schedule_daily_windows(app)
        except Exception as e:
            app.logger.warning(f"[chaos] startup scheduling error: {e}")

    app.logger.info("[chaos] scheduler started (UTC, cleanup every 1min, daily reshuffle @00:05)")
    return _scheduler
