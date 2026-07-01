"""
Chaos admin blueprint.

Gives the site owner a live control panel at /admin/chaos to:
  - See the current FailureMode state
  - Toggle any individual failure knob
  - Fire a named outage manually (for live Site24x7 RCA demos)
  - End the current outage immediately
  - View the last N ChaosEvent audit rows
"""

import ipaddress
import urllib.parse

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import FailureMode, ChaosEvent
from app.services.auth import roles_required, get_current_user
from app.services import chaos as chaos_engine
from app.services.audit import log_audit

chaos_admin_bp = Blueprint('chaos_admin', __name__, url_prefix='/admin/chaos')


def _validate_webhook_url(url: str) -> str | None:
    """
    Validate a webhook URL to prevent Server-Side Request Forgery (SSRF).
    - Only http:// and https:// schemes are allowed.
    - Loopback, link-local, and RFC-1918 private IPs are blocked.
    Returns the URL if valid, None otherwise (and flashes a warning).
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            flash('Webhook URL must use http:// or https://.', 'warning')
            return None
        hostname = parsed.hostname or ''
        if not hostname:
            flash('Webhook URL must have a valid hostname.', 'warning')
            return None
        # Block numeric IPs that resolve to internal/private ranges
        try:
            addr = ipaddress.ip_address(hostname)
            if (addr.is_loopback or addr.is_private or
                    addr.is_link_local or addr.is_multicast or addr.is_reserved):
                flash('Webhook URL cannot point to an internal or private IP address.', 'warning')
                return None
        except ValueError:
            # hostname is a domain name — allow it (DNS resolution is out of scope here)
            pass
        return url
    except Exception:
        flash('Invalid webhook URL.', 'warning')
        return None


FLOAT_FIELDS = {
    'login_failure_rate', 'search_timeout_rate',
    'checkout_exception_rate', 'payment_failure_rate', 'api_5xx_rate',
    # Section 2
    'func_session_kill_rate', 'func_404_storm_rate',
    # Section 5 — Mobile App Chaos
    'mobile_auth_failure_rate', 'mobile_search_empty_rate',
    'mobile_booking_decline_rate', 'mobile_cancel_failure_rate',
    'mobile_timeout_rate', 'mobile_rate_limit_rate', 'mobile_malform_rate',
    # Section 6 — Corporate Portal Chaos
    'corp_auth_failure_rate', 'corp_maintenance_rate',
    # Section 7 — Ad Popup Chaos
    'ad_popup_rate',
}
INT_FIELDS = {
    'login_slowdown_ms', 'db_slowdown_ms', 'search_slowdown_ms',
    'checkout_slowdown_ms', 'api_slowdown_ms',
    # Section 1
    'page_load_delay_ms',
    # Section 3
    'component_chaos_rate',
    # Chaos intensity
    'chaos_intensity',
    # Section 5 — Mobile App Chaos
    'mobile_search_slow_ms',
    # Section 6 — Corporate Portal Chaos
    'corp_slow_ms',
    # Section 7 — Ad Popup Chaos
    'ad_popup_delay_ms', 'ad_popup_close_delay_ms',
}
BOOL_FIELDS = {
    'enabled', 'db_down', 'payment_gateway_down',
    # Section 1 — Page Load
    'page_load_chaos', 'page_load_inject_js_errors',
    'page_load_inject_resource_failures', 'page_load_inject_memory_pressure',
    'page_load_inject_render_blocking', 'page_load_large_payload',
    # New Page Load
    'page_load_webfont_failure', 'page_load_ttfb_spike', 'page_load_cache_chaos',
    # Section 2 — Functionality
    'func_chaos', 'func_search_empty', 'func_form_errors',
    'func_broken_images', 'func_infinite_spin', 'func_broken_cta',
    # New Functionality
    'func_wrong_search', 'func_fake_soldout', 'func_date_picker_broken',
    'func_otp_invalid', 'func_email_chaos', 'func_maintenance_flood',
    # Section 3 — Component Chaos
    'component_chaos', 'component_break_search', 'component_break_results',
    'component_break_booking', 'component_break_pricing',
    'component_break_css', 'component_break_nav',
    # New Components
    'component_break_autocomplete', 'component_break_datepicker',
    'component_break_ratings', 'component_break_loyalty',
    # A/B Test
    'ab_test_chaos', 'ab_test_login', 'ab_test_search', 'ab_test_booking', 'ab_test_profile',
    # Section 5 — Mobile App Chaos
    'mobile_chaos',
    # Section 6 — Corporate Portal Chaos
    'corp_chaos',
    # Section 7 — Ad Popup Chaos
    'ad_popup_chaos',
}

PAGE_TARGETS = ['all', 'flights', 'hotels', 'buses', 'trains',
                'cabs', 'packages', 'activities', 'insurance', 'booking',
                'trip-planner', 'quick-book', 'travel-dashboard', 'dashboard', 'home']


@chaos_admin_bp.route('/', methods=['GET'])
@roles_required('admin')
def dashboard():
    import json
    from datetime import datetime
    from sqlalchemy.exc import OperationalError
    try:
        state = FailureMode.current()
    except OperationalError as e:
        # DB schema is out of date — pending migrations
        col = str(e).split('column:')[-1].strip() if 'column:' in str(e) else str(e)[:80]
        flash(
            f'⚠️ Database schema is out of date (missing column: {col}). '
            f'Run: python3 migrate_ad_popup_chaos.py — then restart the app.',
            'warning'
        )
        from flask import redirect
        return redirect(url_for('admin.dashboard'))
    recent_events = (ChaosEvent.query
                     .order_by(ChaosEvent.created_at.desc())
                     .limit(100).all())
    user = get_current_user()

    # Parse target pages JSON for template
    try:
        target_pages = json.loads(state.page_load_target_pages or '["all"]')
    except Exception:
        target_pages = ['all']
    try:
        raw_comp = getattr(state, 'component_target_pages', None)
        component_pages = json.loads(raw_comp) if raw_comp else ['all']
        if not component_pages:
            component_pages = ['all']
    except Exception:
        component_pages = ['all']

    # Ad popup target pages — Section 7 (column may not exist until migration runs)
    try:
        raw_ad = getattr(state, 'ad_popup_target_pages', None)
        ad_popup_pages = json.loads(raw_ad) if raw_ad else ['all']
        if not ad_popup_pages:
            ad_popup_pages = ['all']
        # Patch state so template can safely read it
        if not hasattr(state, 'ad_popup_target_pages') or state.ad_popup_target_pages is None:
            state.ad_popup_target_pages = '["all"]'
    except Exception:
        ad_popup_pages = ['all']
        state.ad_popup_target_pages = '["all"]'

    # Ensure all Section 7 fields have safe defaults if columns missing
    for attr, default in [('ad_popup_chaos', False), ('ad_popup_rate', 0.3),
                           ('ad_popup_delay_ms', 1500), ('ad_popup_close_delay_ms', 0)]:
        try:
            if getattr(state, attr, None) is None:
                setattr(state, attr, default)
        except Exception:
            pass

    # ── Build enriched schedule windows for the timeline UI ─────────────────
    # Each window gets a 'status': 'past' | 'running' | 'upcoming'
    schedule_windows = []
    if state.auto_chaos_schedule_json:
        try:
            now = datetime.utcnow()
            raw_windows = json.loads(state.auto_chaos_schedule_json)
            for w in raw_windows:
                start = datetime.fromisoformat(w['start'])
                end   = datetime.fromisoformat(w['end'])
                if end <= now:
                    status = 'past'
                elif start <= now:
                    status = 'running'
                else:
                    status = 'upcoming'
                schedule_windows.append({
                    'type':     w['type'],
                    'label':    w['label'],
                    'duration': w['duration'],
                    'start':    start,
                    'end':      end,
                    'status':   status,
                })
        except Exception:
            schedule_windows = []

    # ── History: last 20 AUTO_CHAOS_START/END pairs ──────────────────────────
    history_events = (ChaosEvent.query
                      .filter(ChaosEvent.event_type.in_(
                          ['AUTO_CHAOS_START', 'AUTO_CHAOS_END',
                           'OUTAGE_START', 'OUTAGE_END']))
                      .order_by(ChaosEvent.created_at.desc())
                      .limit(40).all())

    # UTC midnight for 24h countdown reference
    now_utc = datetime.utcnow()
    next_midnight_utc = now_utc.replace(
        hour=0, minute=5, second=0, microsecond=0
    )
    if next_midnight_utc <= now_utc:
        from datetime import timedelta
        next_midnight_utc += timedelta(days=1)

    from app.services.chaos import AD_POPUP_TRANSACTION_BUNDLES
    return render_template('admin_chaos.html',
                           state=state,
                           events=recent_events,
                           history_events=history_events,
                           schedule_windows=schedule_windows,
                           target_pages=target_pages,
                           component_pages=component_pages,
                           page_targets=PAGE_TARGETS,
                           ad_popup_bundles=AD_POPUP_TRANSACTION_BUNDLES,
                           next_reshuffle_utc=next_midnight_utc.isoformat(),
                           profiles=['db_slowdown', 'payment_gateway_down', 'checkout_exceptions',
                                     'search_upstream_timeout', 'api_5xx_storm', 'db_unavailable',
                                     'login_storm', 'email_service_down', 'cdn_failure',
                                     'maintenance_flood', 'third_party_blackout'],
                           user=user)


@chaos_admin_bp.route('/update', methods=['POST'])
@roles_required('admin')
def update():
    import json
    state = FailureMode.current()
    form = request.form

    for f in FLOAT_FIELDS:
        if f in form:
            try:
                val = float(form.get(f, 0) or 0)
                val = max(0.0, min(1.0, val))
                setattr(state, f, val)
            except ValueError:
                pass

    for f in INT_FIELDS:
        if f in form:
            try:
                # page_load_delay_ms can go up to 60000ms
                maxval = 60000 if 'page_load' in f else 30000
                setattr(state, f, max(0, min(maxval, int(form.get(f, 0) or 0))))
            except ValueError:
                pass

    for f in BOOL_FIELDS:
        setattr(state, f, form.get(f) in ('on', 'true', '1', 'yes'))

    # Webhook URL — validate to prevent SSRF
    if 'webhook_url' in form:
        raw_url = form.get('webhook_url', '').strip()
        if not raw_url:
            state.webhook_url = None
        else:
            state.webhook_url = _validate_webhook_url(raw_url)

    # Intensity (0-3)
    if 'chaos_intensity' in form:
        try:
            state.chaos_intensity = max(0, min(3, int(form.get('chaos_intensity', 1))))
        except ValueError:
            pass

    # Handle page target checkboxes (multi-select) — Section 1
    selected_targets = form.getlist('page_load_target_pages')
    if not selected_targets:
        selected_targets = ['all']
    state.page_load_target_pages = json.dumps(selected_targets)

    # Handle component target pages — Section 3
    component_targets = form.getlist('component_target_pages')
    if not component_targets:
        component_targets = ['all']
    state.component_target_pages = json.dumps(component_targets)

    # Handle ad popup target pages — Section 7 (safe — column may not exist yet)
    try:
        ad_popup_targets = form.getlist('ad_popup_target_pages')
        if not ad_popup_targets:
            ad_popup_targets = ['all']
        state.ad_popup_target_pages = json.dumps(ad_popup_targets)
    except Exception:
        pass

    user = get_current_user()
    state.updated_by = user.email if user else 'admin'
    db.session.commit()

    from app.models import ChaosEvent
    ev = ChaosEvent(event_type='MANUAL_TOGGLE', label='admin_update')
    ev.details = state.to_dict()
    db.session.add(ev)
    db.session.commit()

    log_audit('CHAOS_UPDATE', target_type='CHAOS', target_label='FailureMode',
              detail=state.to_dict())
    flash('Chaos settings updated.', 'success')
    return redirect(url_for('chaos_admin.dashboard'))


@chaos_admin_bp.route('/trigger-outage', methods=['POST'])
@roles_required('admin')
def trigger_outage():
    label = request.form.get('profile', 'manual_outage')
    try:
        duration = int(request.form.get('duration_minutes', 15))
    except ValueError:
        duration = 15

    overrides_map = {
        'login_storm': {'login_failure_rate': 0.6, 'login_slowdown_ms': 800},
        'db_slowdown': {'db_slowdown_ms': 2500, 'checkout_slowdown_ms': 1500},
        'payment_gateway_down': {'payment_gateway_down': True},
        'checkout_exceptions': {'checkout_exception_rate': 0.5,
                                'checkout_slowdown_ms': 600},
        'search_upstream_timeout': {'search_timeout_rate': 0.4,
                                    'search_slowdown_ms': 1500},
        'api_5xx_storm': {'api_5xx_rate': 0.35, 'api_slowdown_ms': 700},
        'db_unavailable': {'db_down': True},
        'email_service_down':   {'func_chaos': True, 'func_email_chaos': True},
        'cdn_failure':          {'page_load_chaos': True, 'page_load_webfont_failure': True,
                                  'page_load_inject_resource_failures': True},
        'maintenance_flood':    {'func_chaos': True, 'func_maintenance_flood': True},
        'third_party_blackout': {'page_load_chaos': True, 'page_load_inject_resource_failures': True,
                                  'component_chaos': True, 'component_break_booking': True},
    }
    overrides = overrides_map.get(label, {})
    chaos_engine.start_outage(label, duration_minutes=duration, **overrides)
    log_audit('CHAOS_OUTAGE_START', target_type='CHAOS', target_label=label,
              detail=dict(duration_minutes=duration, overrides=overrides))
    flash(f'Outage "{label}" started for {duration} min.', 'warning')
    return redirect(url_for('chaos_admin.dashboard'))


@chaos_admin_bp.route('/end-outage', methods=['POST'])
@roles_required('admin')
def end_outage_now():
    chaos_engine.end_outage(reason='manual')
    # Also clear auto-chaos tracking fields so the cleanup job doesn't
    # re-fire after a manual "End All Chaos" while auto-mode is running.
    state = FailureMode.current()
    state.auto_chaos_current_type = None
    state.auto_chaos_ends_at = None
    state.auto_chaos_schedule_json = None
    state.auto_chaos_mode = False
    # Reset all Section 1 / 2 / 3 knobs that auto-mode may have set
    state.page_load_chaos = False
    state.page_load_delay_ms = 0
    state.page_load_inject_js_errors = False
    state.page_load_inject_resource_failures = False
    state.page_load_inject_memory_pressure = False
    state.page_load_inject_render_blocking = False
    state.page_load_large_payload = False
    state.func_chaos = False
    state.func_search_empty = False
    state.func_form_errors = False
    state.func_broken_images = False
    state.func_session_kill_rate = 0.0
    state.func_404_storm_rate = 0.0
    state.func_infinite_spin = False
    state.func_broken_cta = False
    state.component_chaos = False
    state.component_break_search = False
    state.component_break_results = False
    state.component_break_booking = False
    state.component_break_pricing = False
    state.component_break_css = False
    state.component_break_nav = False
    # New page load
    state.page_load_webfont_failure = False
    state.page_load_ttfb_spike = False
    state.page_load_cache_chaos = False
    # New functionality
    state.func_wrong_search = False
    state.func_fake_soldout = False
    state.func_date_picker_broken = False
    state.func_otp_invalid = False
    state.func_email_chaos = False
    state.func_maintenance_flood = False
    # New components
    state.component_break_autocomplete = False
    state.component_break_datepicker = False
    state.component_break_ratings = False
    state.component_break_loyalty = False
    # A/B test
    state.ab_test_chaos = False
    state.ab_test_login = False
    state.ab_test_search = False
    state.ab_test_booking = False
    state.ab_test_profile = False
    db.session.commit()
    log_audit('CHAOS_OUTAGE_END', target_type='CHAOS', target_label='manual')
    flash('Outage cleared. All chaos settings reset.', 'success')
    return redirect(url_for('chaos_admin.dashboard'))


@chaos_admin_bp.route('/toggle-auto-mode', methods=['POST'])
@roles_required('admin')
def toggle_auto_mode():
    """
    Toggle Auto Chaos Mode on or off.
    ON  → immediately schedules today's 4-event sequence.
    OFF → cancels all pending auto-chaos jobs and resets state.
    """
    from flask import current_app
    from app.services.chaos_scheduler import reschedule_auto_chaos, cancel_auto_chaos

    state    = FailureMode.current()
    new_mode = not state.auto_chaos_mode
    state.auto_chaos_mode = new_mode
    user = get_current_user()
    state.updated_by = user.email if user else 'admin'
    db.session.commit()

    log_audit('AUTO_CHAOS_TOGGLE', target_type='CHAOS', target_label='auto_chaos_mode',
              detail={'auto_chaos_mode': new_mode})

    app = current_app._get_current_object()
    if new_mode:
        reschedule_auto_chaos(app)
        flash("Auto Chaos Mode ENABLED — continuous chaos schedule generated. View details in Auto Chaos tab.", 'warning')
    else:
        cancel_auto_chaos(app)
        flash('Auto Chaos Mode DISABLED — all pending events cancelled and systems restored.', 'success')

    return redirect(url_for('chaos_admin.dashboard'))


@chaos_admin_bp.route('/update-excluded-types', methods=['POST'])
@roles_required('admin')
def update_excluded_types():
    """Update which chaos types are excluded from auto chaos loop."""
    import json as _json
    from flask import current_app
    from app.services.chaos_scheduler import reschedule_auto_chaos

    state = FailureMode.current()
    # Read which types are checked (included) — unchecked ones are excluded
    all_types = ['named_outage', 'page_load', 'func_chaos', 'component_chaos', 'ab_test']
    included = request.form.getlist('included_types')
    excluded = [t for t in all_types if t not in included]

    state.auto_chaos_excluded_json = _json.dumps(excluded) if excluded else None
    user = get_current_user()
    state.updated_by = user.email if user else 'admin'
    db.session.commit()

    log_audit('AUTO_CHAOS_EXCLUDED_UPDATE', target_type='CHAOS',
              target_label='excluded_types', detail={'excluded': excluded, 'included': included})

    # Rebuild schedule with new exclusions if auto mode is on
    if state.auto_chaos_mode:
        app = current_app._get_current_object()
        reschedule_auto_chaos(app)
        flash(f'Schedule rebuilt — {len(included)} chaos type(s) active, {len(excluded)} excluded.', 'success')
    else:
        flash(f'Exclusions saved — will apply when Auto Chaos is enabled.', 'success')

    return redirect(url_for('chaos_admin.auto_chaos_dashboard'))


@chaos_admin_bp.route('/auto', methods=['GET'])
@roles_required('admin')
def auto_chaos_dashboard():
    """Dedicated Auto Chaos tab — full timeline, planned events, history, and settings."""
    import json
    from datetime import datetime, timedelta
    state = FailureMode.current()
    user = get_current_user()

    # ── Build enriched schedule windows for the timeline UI ─────────────────
    schedule_windows = []
    if state.auto_chaos_schedule_json:
        try:
            now = datetime.utcnow()
            raw_windows = json.loads(state.auto_chaos_schedule_json)
            for w in raw_windows:
                start = datetime.fromisoformat(w['start'])
                end   = datetime.fromisoformat(w['end'])
                if end <= now:
                    status = 'past'
                elif start <= now:
                    status = 'running'
                else:
                    status = 'upcoming'
                schedule_windows.append({
                    'type':     w['type'],
                    'label':    w['label'],
                    'duration': w['duration'],
                    'start':    start,
                    'end':      end,
                    'status':   status,
                })
        except Exception:
            schedule_windows = []

    # ── Compute stats ───────────────────────────────────────────────────────
    total_events = len(schedule_windows)
    completed_events = sum(1 for w in schedule_windows if w['status'] == 'past')
    upcoming_events  = sum(1 for w in schedule_windows if w['status'] == 'upcoming')
    running_event    = next((w for w in schedule_windows if w['status'] == 'running'), None)

    # ── Next upcoming event ─────────────────────────────────────────────────
    next_event = next((w for w in schedule_windows if w['status'] == 'upcoming'), None)

    # ── History: chaos events ───────────────────────────────────────────────
    history_events = (ChaosEvent.query
                      .filter(ChaosEvent.event_type.in_(
                          ['AUTO_CHAOS_START', 'AUTO_CHAOS_END',
                           'OUTAGE_START', 'OUTAGE_END']))
                      .order_by(ChaosEvent.created_at.desc())
                      .limit(50).all())

    # ── Next reshuffle countdown ────────────────────────────────────────────
    now_utc = datetime.utcnow()
    next_reshuffle_utc = now_utc.replace(hour=0, minute=5, second=0, microsecond=0)
    if next_reshuffle_utc <= now_utc:
        next_reshuffle_utc += timedelta(days=1)

    # ── Cycle info ──────────────────────────────────────────────────────────
    active_count = 5
    excluded_types = []
    if state.auto_chaos_excluded_json:
        try:
            excluded_types = json.loads(state.auto_chaos_excluded_json)
            active_count = 5 - len(excluded_types)
        except Exception:
            excluded_types = []
    total_cycles = (total_events + max(active_count, 1) - 1) // max(active_count, 1)

    return render_template('admin_chaos_auto.html',
                           state=state,
                           schedule_windows=schedule_windows,
                           history_events=history_events,
                           total_events=total_events,
                           completed_events=completed_events,
                           upcoming_events=upcoming_events,
                           running_event=running_event,
                           next_event=next_event,
                           total_cycles=total_cycles,
                           excluded_types=excluded_types,
                           next_reshuffle_utc=next_reshuffle_utc.isoformat(),
                           user=user)


@chaos_admin_bp.route('/state.json', methods=['GET'])
def state_json():
    """
    Unauthenticated read-only JSON endpoint for Site24x7 REST API
    monitor — lets you alert on chaos-induced outages vs real ones.
    Sensitive fields (webhook_url, updated_by) are stripped from the response.
    """
    data = FailureMode.current().to_dict()
    # Strip fields that could expose internal infrastructure or admin emails
    data.pop('webhook_url', None)
    data.pop('updated_by', None)
    return jsonify(data)


@chaos_admin_bp.route('/docs', methods=['GET'])
@roles_required('admin')
def docs():
    """Full chaos engineering documentation page."""
    user = get_current_user()
    return render_template('admin_chaos_docs.html', user=user)


@chaos_admin_bp.route('/debug', methods=['GET'])
@roles_required('admin')
def chaos_debug():
    """Diagnostic endpoint — shows exactly why chaos might not fire."""
    import json, traceback
    from sqlalchemy import inspect as sa_inspect
    from app import db as _db
    lines = ['=== CHAOS DIAGNOSTIC ===', '']

    # 1. Check DB columns exist
    try:
        insp = sa_inspect(_db.engine)
        cols = {c['name'] for c in insp.get_columns('failure_mode')}
        needed = ['page_load_chaos', 'page_load_delay_ms', 'page_load_target_pages',
                  'page_load_inject_js_errors', 'page_load_inject_resource_failures',
                  'page_load_inject_memory_pressure', 'page_load_inject_render_blocking',
                  'page_load_large_payload']
        missing = [c for c in needed if c not in cols]
        if missing:
            lines.append(f'[FAIL] DB columns MISSING: {missing}')
            lines.append('  → The ALTER TABLE migration did not run. Restart the server.')
        else:
            lines.append('[OK] All 8 page_load columns exist in DB.')
    except Exception as e:
        lines.append(f'[FAIL] Cannot inspect DB: {e}')

    lines.append('')

    # 2. Read raw values from DB
    try:
        state = FailureMode.current()
        lines.append(f'[DB] enabled             = {state.enabled}')
        lines.append(f'[DB] page_load_chaos     = {getattr(state, "page_load_chaos", "MISSING")}')
        lines.append(f'[DB] page_load_delay_ms  = {getattr(state, "page_load_delay_ms", "MISSING")}')
        lines.append(f'[DB] page_load_target_pages = {getattr(state, "page_load_target_pages", "MISSING")}')
        lines.append('')

        # 3. Check _get_state() chain
        if not state.enabled:
            lines.append('[INFO] state.enabled = False → Core Chaos (login/DB/search/payment/API) is disabled.')
            lines.append('  → Section 1 & 2 work independently — they do NOT need Core Chaos ON.')
        else:
            lines.append('[OK] state.enabled = True (core chaos master switch ON)')

        if not getattr(state, 'page_load_chaos', False):
            lines.append('[FAIL] page_load_chaos = False → Section 1 is OFF, no delay will fire.')
            lines.append('  → Turn ON the Section 1 toggle and save.')
        else:
            lines.append('[OK] page_load_chaos = True (Section 1 ON)')

        delay = getattr(state, 'page_load_delay_ms', 0) or 0
        if delay == 0:
            lines.append('[FAIL] page_load_delay_ms = 0 → No delay configured.')
        else:
            lines.append(f'[OK] page_load_delay_ms = {delay} ({delay/1000:.1f}s)')

        # 4. Check target pages
        try:
            targets = json.loads(getattr(state, 'page_load_target_pages', '["all"]') or '["all"]')
        except Exception:
            targets = ['all']
        lines.append(f'[DB] Parsed target pages: {targets}')

        from app.services.chaos import PAGE_SLUG_MAP
        test_path = '/flights'
        if targets and 'all' not in targets:
            matched = False
            for slug in targets:
                prefixes = PAGE_SLUG_MAP.get(slug, [f'/{slug}'])
                if any(test_path.startswith(p) for p in prefixes):
                    matched = True
                    break
            if matched:
                lines.append(f'[OK] Path "/flights" matches target "{slug}"')
            else:
                lines.append(f'[FAIL] Path "/flights" does NOT match any target in {targets}')
        else:
            lines.append('[OK] Target = "all" — every page gets delayed')

    except Exception as e:
        lines.append(f'[FAIL] Error reading state: {e}')
        lines.append(traceback.format_exc())

    lines.append('')

    # 5. Check if before_request hook is registered
    from flask import current_app
    hook_names = [f.__name__ for f in current_app.before_request_funcs.get(None, [])]
    if 'apply_page_chaos' in hook_names:
        lines.append('[OK] before_request hook "apply_page_chaos" is registered')
    else:
        lines.append('[FAIL] before_request hook "apply_page_chaos" NOT registered!')
        lines.append(f'  → Registered hooks: {hook_names}')

    lines.append('')
    lines.append('=== END DIAGNOSTIC ===')
    return '<pre>' + '\n'.join(lines) + '</pre>', 200, {'Content-Type': 'text/html'}
