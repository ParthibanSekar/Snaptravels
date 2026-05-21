"""
Chaos / Failure-Injection engine for SnapTravels.

This module is the single source of truth for "is X broken right now?".
Every risky code path (login, search, booking, payment, mobile API)
calls one of the `maybe_*` helpers below, which read the live
FailureMode singleton row and deterministically decide whether to:

  - sleep (latency injection)
  - raise an exception
  - return a synthetic error

The goal is to make Site24x7 Synthetic, APM, RUM, and Mobile APM all
light up together during a scheduled outage window, so the RCA demo
correlates naturally across the stack.

All injected failures are logged as ChaosEvent rows and also emitted
to app.logger so the APM log pipeline picks them up with the active
request trace id (see app/services/observability.py).
"""

import random
import time
import logging
from datetime import datetime
from flask import g, has_app_context, current_app

logger = logging.getLogger('snaptravels.chaos')


# ----------------------------------------------------------------------
# Exception types — APM agents will group these as distinct error classes
# ----------------------------------------------------------------------
class ChaosInjectedError(Exception):
    """Base class for all chaos-injected failures."""
    pass


class LoginChaosError(ChaosInjectedError):
    pass


class DatabaseChaosError(ChaosInjectedError):
    pass


class SearchChaosError(ChaosInjectedError):
    pass


class CheckoutChaosError(ChaosInjectedError):
    pass


class PaymentChaosError(ChaosInjectedError):
    pass


class ApiChaosError(ChaosInjectedError):
    pass

# ── Section 5: Mobile-specific chaos errors ───────────────────────────────
class MobileAuthChaosError(ChaosInjectedError):
    pass

class MobileBookingChaosError(ChaosInjectedError):
    pass

class MobileCancelChaosError(ChaosInjectedError):
    pass

class MobileTimeoutChaosError(ChaosInjectedError):
    pass

class MobileRateLimitChaosError(ChaosInjectedError):
    pass


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------
def _get_state():
    """
    Load the FailureMode singleton. Returns None if the CORE chaos engine
    is globally disabled (`enabled=False`), the app context is missing,
    or the table does not yet exist (e.g. during migrations).
    Used by Section 0 (core) chaos functions: login, DB, search, payment, API.
    """
    if not has_app_context():
        return None
    try:
        from app.models import FailureMode
        state = FailureMode.current()
        if not state.enabled:
            return None
        # If an outage window has expired, treat it as inactive
        if state.outage_ends_at and state.outage_ends_at < datetime.utcnow():
            return state  # still return — scheduler will clear it
        return state
    except Exception as e:
        # Never let chaos break the app
        logger.debug(f"Chaos state unavailable: {e}")
        return None


def _get_state_raw():
    """
    Load the FailureMode singleton WITHOUT checking the core `enabled` flag.
    Used by Section 1 (page load) and Section 2 (functionality) chaos,
    which have their own independent master toggles (page_load_chaos, func_chaos).
    """
    if not has_app_context():
        return None
    try:
        from app.models import FailureMode
        return FailureMode.current()
    except Exception as e:
        logger.debug(f"Chaos state unavailable: {e}")
        return None


def _log_event(event_type: str, label: str, **details):
    """Persist a ChaosEvent row and emit a structured log line."""
    try:
        from app.models import ChaosEvent
        from app import db
        ev = ChaosEvent(event_type=event_type, label=label)
        ev.details = details
        db.session.add(ev)
        db.session.commit()
    except Exception as e:
        logger.debug(f"Failed to persist chaos event: {e}")

    trace_id = getattr(g, 'trace_id', None) if has_app_context() else None
    logger.warning(
        "CHAOS_EVENT type=%s label=%s trace_id=%s details=%s",
        event_type, label, trace_id, details
    )


def _roll(rate: float) -> bool:
    """Return True with probability `rate` (0.0 - 1.0)."""
    if rate <= 0:
        return False
    if rate >= 1:
        return True
    return random.random() < rate


def _sleep(ms: int):
    if ms and ms > 0:
        time.sleep(ms / 1000.0)


# ----------------------------------------------------------------------
# Public hooks — call these from the real code paths
# ----------------------------------------------------------------------
def maybe_fail_login(email: str = None):
    """Call at the top of AuthService.login()."""
    state = _get_state()
    if not state:
        return
    _sleep(state.login_slowdown_ms)
    if _roll(state.login_failure_rate):
        _log_event('INJECTED_ERROR', 'login_failure', email=email,
                   outage_label=state.outage_label)
        raise LoginChaosError("Authentication service is temporarily unavailable")


def maybe_fail_db(op: str = 'query'):
    """Call at the top of DB-heavy service methods."""
    state = _get_state()
    if not state:
        return
    _sleep(state.db_slowdown_ms)
    if state.db_down:
        _log_event('INJECTED_ERROR', 'db_down', op=op,
                   outage_label=state.outage_label)
        raise DatabaseChaosError(f"Database connection refused (op={op})")


def maybe_fail_search(kind: str = 'flight'):
    """Call at the top of SearchService.search_flights/search_hotels."""
    state = _get_state()
    if not state:
        return
    _sleep(state.search_slowdown_ms)
    if _roll(state.search_timeout_rate):
        _log_event('INJECTED_ERROR', f'{kind}_search_timeout',
                   outage_label=state.outage_label)
        raise SearchChaosError(f"{kind.capitalize()} search upstream timeout")


def maybe_fail_checkout(booking_type: str = None, amount: float = None):
    """Call at the top of BookingService.create_booking()."""
    state = _get_state()
    if not state:
        return
    _sleep(state.checkout_slowdown_ms)
    if _roll(state.checkout_exception_rate):
        _log_event('INJECTED_ERROR', 'checkout_exception',
                   booking_type=booking_type, amount=amount,
                   outage_label=state.outage_label)
        raise CheckoutChaosError("Checkout service crashed mid-transaction")


def maybe_fail_payment(amount: float = None):
    """Call just before 'charging' the card in create_booking."""
    state = _get_state()
    if not state:
        return
    if state.payment_gateway_down:
        _log_event('INJECTED_ERROR', 'payment_gateway_down', amount=amount,
                   outage_label=state.outage_label)
        raise PaymentChaosError("Payment gateway is unreachable")
    if _roll(state.payment_failure_rate):
        _log_event('INJECTED_ERROR', 'payment_declined', amount=amount,
                   outage_label=state.outage_label)
        raise PaymentChaosError("Card declined by issuing bank")


def maybe_fail_api(endpoint: str = None):
    """Call inside mobile API before_request / at top of each handler."""
    state = _get_state()
    if not state:
        return
    _sleep(state.api_slowdown_ms)
    if _roll(state.api_5xx_rate):
        _log_event('INJECTED_ERROR', 'api_5xx', endpoint=endpoint,
                   outage_label=state.outage_label)
        raise ApiChaosError("Upstream service returned 500")


# ── Section 5: Mobile App Chaos ───────────────────────────────────────────

def _mobile_chaos_enabled():
    """Return the FailureMode row if mobile chaos is active, else None."""
    state = _get_state()
    if not state:
        return None
    return state if getattr(state, 'mobile_chaos', False) else None


def maybe_fail_mobile_auth():
    """
    Random JWT / authentication failures.
    Call at the top of /auth/login and /auth/refresh handlers.
    Raises MobileAuthChaosError (→ caller returns 401).
    """
    state = _mobile_chaos_enabled()
    if not state:
        return
    rate = getattr(state, 'mobile_auth_failure_rate', 0.0) or 0.0
    if _roll(rate):
        _log_event('INJECTED_ERROR', 'mobile_auth_failure',
                   outage_label=state.outage_label)
        raise MobileAuthChaosError("Authentication service temporarily unavailable")


def maybe_slow_mobile_search(kind: str = 'generic') -> bool:
    """
    Artificial search slowdown + optional empty-results injection.
    Call at the top of every /search endpoint.
    Returns True if the caller should return an empty result set.
    """
    state = _mobile_chaos_enabled()
    if not state:
        return False
    delay = getattr(state, 'mobile_search_slow_ms', 0) or 0
    _sleep(delay)
    empty_rate = getattr(state, 'mobile_search_empty_rate', 0.0) or 0.0
    if _roll(empty_rate):
        _log_event('INJECTED_ERROR', f'mobile_search_empty:{kind}',
                   outage_label=state.outage_label)
        return True   # caller should return empty list
    return False


def maybe_fail_mobile_booking():
    """
    Random booking decline (simulates payment gateway rejection).
    Call inside booking creation handlers before DB write.
    Raises MobileBookingChaosError (→ caller returns 402/503).
    """
    state = _mobile_chaos_enabled()
    if not state:
        return
    rate = getattr(state, 'mobile_booking_decline_rate', 0.0) or 0.0
    if _roll(rate):
        _log_event('INJECTED_ERROR', 'mobile_booking_decline',
                   outage_label=state.outage_label)
        raise MobileBookingChaosError("Booking declined by payment gateway. Please try again.")


def maybe_fail_mobile_cancel():
    """
    Random cancel-endpoint failure.
    Call at the top of the /bookings/<id>/cancel handler.
    Raises MobileCancelChaosError (→ caller returns 503).
    """
    state = _mobile_chaos_enabled()
    if not state:
        return
    rate = getattr(state, 'mobile_cancel_failure_rate', 0.0) or 0.0
    if _roll(rate):
        _log_event('INJECTED_ERROR', 'mobile_cancel_failure',
                   outage_label=state.outage_label)
        raise MobileCancelChaosError("Cancellation service temporarily unavailable")


def maybe_mobile_timeout():
    """
    Deliberate response delay > client timeout (16 s).
    Call inside the before_request hook for the mobile API.
    Raises MobileTimeoutChaosError so APM captures it as a slow transaction.
    """
    state = _mobile_chaos_enabled()
    if not state:
        return
    rate = getattr(state, 'mobile_timeout_rate', 0.0) or 0.0
    if _roll(rate):
        _log_event('INJECTED_ERROR', 'mobile_timeout',
                   outage_label=state.outage_label)
        _sleep(16000)   # 16 s — exceeds the 15 s Axios client timeout
        raise MobileTimeoutChaosError("Request timed out")


def maybe_mobile_rate_limit():
    """
    Simulate HTTP 429 Too Many Requests.
    Call inside the before_request hook for the mobile API.
    Raises MobileRateLimitChaosError (→ caller returns 429).
    """
    state = _mobile_chaos_enabled()
    if not state:
        return
    rate = getattr(state, 'mobile_rate_limit_rate', 0.0) or 0.0
    if _roll(rate):
        _log_event('INJECTED_ERROR', 'mobile_rate_limit',
                   outage_label=state.outage_label)
        raise MobileRateLimitChaosError("Too many requests — rate limit exceeded")


def should_mobile_malform() -> bool:
    """
    Returns True if the response should drop key fields (malformed JSON).
    Call after building the response dict; if True, strip non-essential keys
    so the mobile app receives incomplete data and has to handle it gracefully.
    """
    state = _mobile_chaos_enabled()
    if not state:
        return False
    rate = getattr(state, 'mobile_malform_rate', 0.0) or 0.0
    if _roll(rate):
        _log_event('INJECTED_ERROR', 'mobile_malform',
                   outage_label=state.outage_label)
        return True
    return False


# ── Section 1: Page Load Performance Chaos ────────────────────────────────

PAGE_SLUG_MAP = {
    'flights': ['/flights', '/book/flight', '/flight/'],
    'hotels':  ['/hotels',  '/book/hotel',  '/hotel/'],
    'buses':   ['/buses',   '/bus-book'],
    'trains':  ['/trains',  '/train-book'],
    'cabs':    ['/cabs',    '/cab-book'],
    'packages':['/packages'],
    'activities':['/activities'],
    'booking': ['/book', '/booking'],
    'dashboard':['/dashboard', '/my-bookings', '/profile', '/security'],
    'trip-planner': ['/trip-planner'],
    'quick-book': ['/quick-book'],
    'travel-dashboard': ['/travel-dashboard'],
    'insurance': ['/insurance'],
    'home':    ['/'],
}


def maybe_delay_page(path: str = None):
    """
    Server-side sleep injected before every matching page response.
    Call this from a before_request hook.
    Skip for static files, health checks, API calls, and admin routes.
    Uses _get_state_raw() — independent of the Core Chaos master switch.
    """
    state = _get_state_raw()
    if not state or not getattr(state, 'page_load_chaos', False):
        return
    delay = getattr(state, 'page_load_delay_ms', 0) or 0
    if not delay:
        return
    # Skip non-page requests
    if path and any(path.startswith(p) for p in (
        '/static/', '/assets/', '/health', '/metrics', '/mobile-api/',
        '/admin/chaos/state', '/favicon'
    )):
        return
    # Check target pages filter
    import json
    try:
        targets = json.loads(getattr(state, 'page_load_target_pages', '["all"]') or '["all"]')
    except Exception:
        targets = ['all']
    if targets and 'all' not in targets:
        matched = False
        for slug in targets:
            prefixes = PAGE_SLUG_MAP.get(slug, [f'/{slug}'])
            if any(path.startswith(p) for p in prefixes):
                matched = True
                break
        if not matched:
            return
    _log_event('PAGE_LOAD_DELAY', 'page_load_chaos', path=path, delay_ms=delay)
    _sleep(delay)


def get_page_chaos_js() -> str:
    """
    Returns a JavaScript string to inject into every page <body>.
    Produces realistic console errors, resource failures, memory pressure,
    render-blocking, and functionality failures for Site24x7 RUM demos.
    Uses _get_state_raw() — independent of the Core Chaos master switch.
    """
    state = _get_state_raw()
    if not state:
        return ''

    parts = []

    # ── Page Load JS injections ──────────────────────────────────────────
    if getattr(state, 'page_load_chaos', False):

        if getattr(state, 'page_load_inject_js_errors', False):
            parts.append(r"""
/* [SnapTravels Chaos] JS Error Injection */
(function(){
  console.error('[SnapTravels] TypeError: Cannot read properties of undefined (reading "flightData") at FlightSearchWidget.js:247');
  console.error('[SnapTravels] ReferenceError: snapAnalyticsSDK is not defined at analytics.min.js:1:342');
  console.warn('[SnapTravels] net::ERR_FAILED 503 (Service Unavailable) /api/v2/search/autocomplete');
  console.error('[SnapTravels] Uncaught (in promise) Error: Request failed with status 503 at SearchService.js:89:14');
  setTimeout(function(){
    try { snapAnalyticsSDK.track('pageview', {page: location.pathname}); }
    catch(e){ console.error('[SnapTravels] Analytics SDK init failed:', e.message); }
  }, 600);
  setTimeout(function(){
    var err = new TypeError("Cannot set properties of null (setting 'innerHTML') at FlightCard.render:67");
    console.error('[SnapTravels]', err);
    window.dispatchEvent(new ErrorEvent('error', {error: err, message: err.message, filename: 'FlightCard.js', lineno: 67}));
  }, 1200);
  setTimeout(function(){
    console.error('[SnapTravels] ChunkLoadError: Loading chunk vendors~main failed. (missing: /static/js/chunk-vendors.98f3a2.js)');
    console.warn('[SnapTravels] Retrying chunk load... attempt 1/3');
  }, 2100);
})();
""")

        if getattr(state, 'page_load_inject_resource_failures', False):
            parts.append(r"""
/* [SnapTravels Chaos] Resource Failure Injection */
(function(){
  // Broken JS — 404s in Network tab
  ['search-personalization-v3.min.js','flight-widget-sdk.js','booking-analytics.min.js'].forEach(function(f){
    var s = document.createElement('script');
    s.src = '/static/js/' + f + '?t=' + Date.now();
    s.onerror = function(){ console.error('[SnapTravels] Failed to load script: ' + f + '. Feature degraded.'); };
    document.head.appendChild(s);
  });
  // Broken CSS — 404s in Network tab
  var l = document.createElement('link');
  l.rel='stylesheet'; l.href='/static/css/flight-widgets-premium.css?v=2.1.' + Date.now();
  l.onerror = function(){ console.warn('[SnapTravels] CSS missing: flight-widgets-premium.css. Layout may be degraded.'); };
  document.head.appendChild(l);
  // Failed XHR calls visible in Network tab
  fetch('/api/v2/recommendations/personalized?src=topnav', {
    signal: typeof AbortSignal.timeout === 'function' ? AbortSignal.timeout(250) : undefined
  }).then(function(r){ if(!r.ok) throw new Error('HTTP ' + r.status); })
    .catch(function(e){ console.error('[SnapTravels] RecommendationService: fetch failed:', e.message); });
  fetch('/analytics/v1/session/init', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({sid: Math.random().toString(36).slice(2), ts: Date.now()}),
    signal: typeof AbortSignal.timeout === 'function' ? AbortSignal.timeout(200) : undefined
  }).catch(function(e){ console.error('[SnapTravels] SessionTracking: init failed:', e.message); });
  fetch('/api/v2/user/preferences', {
    signal: typeof AbortSignal.timeout === 'function' ? AbortSignal.timeout(300) : undefined
  }).then(function(r){ if(!r.ok) throw new Error('HTTP ' + r.status); })
    .catch(function(e){ console.error('[SnapTravels] UserPreferences: load failed:', e.message); });
})();
""")

        if getattr(state, 'page_load_inject_memory_pressure', False):
            parts.append(r"""
/* [SnapTravels Chaos] Memory Pressure Injection */
(function(){
  try {
    console.warn('[SnapTravels] Initializing in-browser search index cache (cold start)...');
    var _searchCache = new Array(1500000).fill(null).map(function(_,i){
      return { id:'FL'+i, origin:'DEL', dest:'BOM', price: 3000+Math.random()*15000,
               ts: Date.now(), hash: Math.random().toString(36) };
    });
    console.warn('[SnapTravels] Search index ready: ' + _searchCache.length + ' entries (~96MB heap)');
    // Keep a ref so GC doesn't collect it
    window.__snapSearchCache = _searchCache;
  } catch(e) {
    console.error('[SnapTravels] Search cache init failed — possible memory exhaustion:', e.message);
  }
})();
""")

        if getattr(state, 'page_load_inject_render_blocking', False):
            block_ms = min(getattr(state, 'page_load_delay_ms', 2000) or 2000, 4000)
            parts.append("""
/* [SnapTravels Chaos] Render-Blocking Script Injection */
(function(){
  var _start = performance.now();
  var _end = _start + """ + str(block_ms) + """;
  while(performance.now() < _end){ /* intentional render-block */ }
  console.warn('[SnapTravels] Bootstrap SDK: init took ' + Math.round(performance.now()-_start) + 'ms (render-blocking synchronous execution)');
})();
""")

        if getattr(state, 'page_load_large_payload', False):
            parts.append(r"""
/* [SnapTravels Chaos] Large DOM Payload Injection */
(function(){
  var frag = document.createDocumentFragment();
  for(var i=0;i<8000;i++){
    var el = document.createElement('span');
    el.setAttribute('data-flight-id','SNAP_FL_'+i);
    el.setAttribute('data-price', String(3000 + Math.floor(Math.random()*15000)));
    el.setAttribute('data-route','DEL-BOM');
    el.setAttribute('data-cache-key', 'fc_' + i + '_' + Date.now());
    el.style.display='none';
    el.textContent='CacheEntry_'+i+'_'+('x'.repeat(80));
    frag.appendChild(el);
  }
  document.body.appendChild(frag);
  console.warn('[SnapTravels] DOM enrichment complete: 8000 prefetch nodes appended. Reflow cost: high.');
})();
""")

        # ── WebFont Failure
        if getattr(state, 'page_load_webfont_failure', False):
            parts.append(r"""
/* ── WebFont Failure ───────────────────────────────────────────────── */
(function(){
  document.querySelectorAll('link[rel="stylesheet"]').forEach(function(l){
    if (l.href && (l.href.includes('fonts.googleapis') || l.href.includes('fonts.gstatic') || l.href.includes('cdnjs'))) {
      l.href = l.href + '?chaos_bust=' + Date.now();
    }
  });
  var style = document.createElement('style');
  style.textContent = '@import url("https://fonts.googleapis.com/css2?family=BrokenFont404:wght@400&display=swap"); body, * { font-family: "Times New Roman", serif !important; letter-spacing: -0.02em; }';
  document.head.appendChild(style);
  console.warn('[chaos] WebFont failure injected — fallback fonts active');
})();
""")

        # ── Cache-Control Chaos
        if getattr(state, 'page_load_cache_chaos', False):
            parts.append(r"""
/* ── Cache-Control Chaos (meta tag approach) ───────────────────────── */
(function(){
  ['cache-control','pragma','expires'].forEach(function(n){
    var m = document.querySelector('meta[http-equiv="'+n+'"]');
    if (!m) { m = document.createElement('meta'); m.setAttribute('http-equiv', n); document.head.appendChild(m); }
    m.setAttribute('content', n === 'cache-control' ? 'no-store, no-cache, must-revalidate' : (n === 'expires' ? '0' : 'no-cache'));
  });
  console.warn('[chaos] Cache-Control chaos — no-store injected via meta');
})();
""")

        # ── TTFB Spike
        if getattr(state, 'page_load_ttfb_spike', False):
            parts.append(r"""
/* ── TTFB Spike simulation (client-perceived) ──────────────────────── */
(function(){
  var overlay = document.createElement('div');
  overlay.id = 'chaos-ttfb-overlay';
  overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:#fff;z-index:999999;';
  document.body.appendChild(overlay);
  var delay = 3000 + Math.random() * 5000;
  setTimeout(function(){ var o = document.getElementById('chaos-ttfb-overlay'); if(o) o.remove(); }, delay);
  console.warn('[chaos] TTFB spike simulated — ' + Math.round(delay) + 'ms white-screen overlay');
})();
""")

    # ── Functionality Chaos JS injections ────────────────────────────────
    # Only inject on content pages — never on login, signup, admin, or home
    if getattr(state, 'func_chaos', False):

        if getattr(state, 'func_broken_images', False):
            parts.append(r"""
/* [SnapTravels Chaos] Broken Images */
(function(){
  var p = location.pathname;
  if(p === '/' || p.startsWith('/login') || p.startsWith('/signup') || p.startsWith('/logout') || p.startsWith('/admin') || p.startsWith('/auth')) return;
  document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('img').forEach(function(img){
    if(Math.random() < 0.55){
      var orig = img.src;
      img.src = '/static/images/cache_miss_' + Date.now() + '_' + Math.random().toString(36).slice(2) + '.jpg';
      img.onerror = function(){
        this.style.filter='grayscale(1) opacity(0.25)';
        this.style.border='2px dashed #dc2626';
        console.error('[SnapTravels] ImageLoader: ERR_FILE_NOT_FOUND ' + orig.split('/').pop());
      };
    }
  });
  });
})();
""")

        if getattr(state, 'func_infinite_spin', False):
            parts.append(r"""
/* [SnapTravels Chaos] Infinite Spinner on CTAs */
(function(){
  var p = location.pathname;
  if(p === '/' || p.startsWith('/login') || p.startsWith('/signup') || p.startsWith('/logout') || p.startsWith('/admin') || p.startsWith('/auth')) return;
  document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('a.btn, button[type=submit], .btn-confirm, [class*="book"]').forEach(function(btn){
      btn.addEventListener('click', function(e){
        if(btn.tagName==='A') e.preventDefault();
        var orig = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Processing…';
        btn.disabled = true;
        console.error('[SnapTravels] BookingService: Request timed out after 30000ms (attempt 1/3)');
        setTimeout(function(){ console.error('[SnapTravels] BookingService: Retry 2/3 failed — ECONNRESET'); }, 4000);
        setTimeout(function(){ console.error('[SnapTravels] BookingService: All retries exhausted. Booking incomplete.'); }, 8000);
      }, {once:true});
    });
  });
})();
""")

        if getattr(state, 'func_broken_cta', False):
            parts.append(r"""
/* [SnapTravels Chaos] Broken / Disabled CTAs */
(function(){
  var p = location.pathname;
  if(p === '/' || p.startsWith('/login') || p.startsWith('/signup') || p.startsWith('/logout') || p.startsWith('/admin') || p.startsWith('/auth')) return;
  document.addEventListener('DOMContentLoaded', function(){
    var btns = Array.from(document.querySelectorAll('a.btn, button.btn, .btn-primary, .btn-confirm'));
    btns.forEach(function(el){
      if(Math.random() < 0.45){
        el.style.pointerEvents='none';
        el.style.opacity='0.45';
        el.style.cursor='not-allowed';
        el.title='Service temporarily unavailable (503)';
      }
    });
    console.error('[SnapTravels] InteractionService: Failed to bind ' + Math.floor(btns.length*0.45) + ' of ' + btns.length + ' interactive elements. UX degraded.');
  });
})();
""")

        if getattr(state, 'func_form_errors', False):
            parts.append(r"""
/* [SnapTravels Chaos] Form Validation Error Injection */
(function(){
  var p = location.pathname;
  if(p === '/' || p.startsWith('/login') || p.startsWith('/signup') || p.startsWith('/logout') || p.startsWith('/admin') || p.startsWith('/auth')) return;
  document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('form').forEach(function(form){
      form.addEventListener('submit', function(e){
        if(Math.random() < 0.6){
          e.preventDefault();
          var alert = document.createElement('div');
          alert.className = 'alert alert-danger mt-3';
          alert.setAttribute('role','alert');
          alert.innerHTML = '<strong>Server Error:</strong> An unexpected error occurred while processing your request. Please try again. (Error Code: 503-SNAP-' + Math.floor(Math.random()*9000+1000) + ')';
          form.prepend(alert);
          console.error('[SnapTravels] FormService: POST ' + form.action + ' failed with 503 — downstream payment gateway unreachable');
          setTimeout(function(){ alert.remove(); }, 6000);
        }
      });
    });
  });
})();
""")

    # ── New Section 2 JS injections ──────────────────────────────────────
    if getattr(state, 'func_chaos', False):

        if getattr(state, 'func_fake_soldout', False):
            parts.append(r"""
/* [SnapTravels Chaos] Fake Sold-Out */
(function(){
  var p = location.pathname;
  if(p === '/' || p.startsWith('/login') || p.startsWith('/signup') || p.startsWith('/admin') || p.startsWith('/auth')) return;
  document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('.btn-book, .btn-select, a[href*="booking"], a[href*="seat"], button[type=submit]').forEach(function(btn){
      btn.disabled = true;
      btn.style.opacity = '0.5';
      btn.title = 'Sold Out';
      btn.textContent = 'Sold Out';
    });
    var banner = document.createElement('div');
    banner.style.cssText = 'background:#fef2f2;border:1.5px solid #fca5a5;border-radius:8px;padding:14px 20px;margin:16px 0;text-align:center;font-weight:600;color:#b91c1c;font-size:.92rem;';
    banner.innerHTML = '🚫 This item is fully booked. No availability for the selected dates.';
    var main = document.querySelector('main, .container, #main-content, body');
    if(main) main.prepend(banner);
    console.warn('[SnapTravels] InventoryService: All slots marked as SOLD_OUT — inventory sync failure');
  });
})();
""")

        if getattr(state, 'func_wrong_search', False):
            parts.append(r"""
/* [SnapTravels Chaos] Wrong Search Results — mismatched destination data */
(function(){
  var p = location.pathname;
  if(p === '/' || p.startsWith('/login') || p.startsWith('/signup') || p.startsWith('/admin') || p.startsWith('/auth')) return;
  document.addEventListener('DOMContentLoaded', function(){
    var wrongCities = ['Mumbai','Goa','Jaipur','Chennai','Kolkata','Hyderabad','Pune','Ahmedabad'];
    document.querySelectorAll('.city-name, .destination-label, .route-label, [class*="destination"], [class*="origin"]').forEach(function(el){
      var orig = el.textContent.trim();
      if(orig && orig.length > 2){
        el.textContent = wrongCities[Math.floor(Math.random()*wrongCities.length)];
        el.style.color = '#dc2626';
        el.title = 'Search data mismatch — cached stale result';
      }
    });
    console.error('[SnapTravels] SearchService: Stale cache served — destination mismatch detected. ResultSet may not match query params.');
  });
})();
""")

        if getattr(state, 'func_date_picker_broken', False):
            parts.append(r"""
/* [SnapTravels Chaos] Date Picker Broken */
(function(){
  var p = location.pathname;
  if(p === '/' || p.startsWith('/login') || p.startsWith('/signup') || p.startsWith('/admin') || p.startsWith('/auth')) return;
  document.addEventListener('DOMContentLoaded', function(){
    var yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
    document.querySelectorAll('input[type="date"], input[name*="date"], input[name*="checkin"], input[name*="checkout"], input[name*="depart"], input[name*="return"], input[name*="travel"]').forEach(function(inp){
      inp.setAttribute('max', yesterday);
      inp.value = '';
      inp.style.borderColor = '#ef4444';
      inp.style.color = '#ef4444';
      inp.setAttribute('placeholder', 'Invalid date');
      inp.addEventListener('input', function(){ inp.value = ''; });
    });
    console.error('[SnapTravels] DatePickerService: Calendar widget initialization failed — future dates unavailable');
  });
})();
""")

        if getattr(state, 'func_maintenance_flood', False):
            parts.append(r"""
/* [SnapTravels Chaos] Maintenance Flood — 25% of pages show overlay */
(function(){
  var p = location.pathname;
  if(p === '/' || p.startsWith('/login') || p.startsWith('/signup') || p.startsWith('/admin') || p.startsWith('/auth')) return;
  if(Math.random() > 0.25) return; // 25% probability
  document.addEventListener('DOMContentLoaded', function(){
    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:88888;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;';
    overlay.innerHTML = '<div style="background:#fff;border-radius:16px;padding:40px 48px;text-align:center;max-width:460px;box-shadow:0 20px 60px rgba(0,0,0,.3)">'
      + '<div style="font-size:3rem;margin-bottom:16px">🔧</div>'
      + '<h3 style="font-size:1.3rem;font-weight:700;color:#111;margin-bottom:12px">Scheduled Maintenance</h3>'
      + '<p style="color:#6b7280;font-size:.92rem;line-height:1.6;margin-bottom:20px">We are performing scheduled system maintenance. This section will be back shortly.<br><strong>Estimated completion: ' + new Date(Date.now()+3600000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) + '</strong></p>'
      + '<button onclick="this.closest(\'div\').parentNode.parentNode.remove()" style="background:#2563eb;color:#fff;border:none;border-radius:8px;padding:10px 28px;font-weight:600;cursor:pointer;font-size:.9rem">Dismiss</button>'
      + '</div>';
    document.body.appendChild(overlay);
    console.warn('[SnapTravels] MaintenanceService: Scheduled maintenance window active for this section');
  });
})();
""")

    return '\n'.join(parts)


# ── Section 3: Component-Level Chaos ─────────────────────────────────────

def get_component_chaos_js() -> str:
    """
    Returns JavaScript that simulates component-level failures on a 200 page.
    Unlike Section 1/2 chaos (which breaks the whole page or functionality),
    this targets specific UI components — search widget, results, booking CTAs,
    pricing display, CSS/layout, navigation — mimicking real JS/CSS chunk
    load failures seen in production SPAs.

    Injected into every template via the inject_chaos_js context processor.
    Skips admin, auth, and static routes.
    """
    from flask import request as flask_request
    state = _get_state_raw()
    if not state or not getattr(state, 'component_chaos', False):
        return ''

    # Skip admin / auth routes — never break the chaos control panel itself
    try:
        path = flask_request.path
        safe_prefixes = ('/admin/', '/login', '/signup', '/logout', '/auth/',
                         '/static/', '/assets/', '/health', '/api/')
        if any(path.startswith(p) for p in safe_prefixes) or path == '/':
            return ''
    except Exception:
        return ''

    rate = int(getattr(state, 'component_chaos_rate', 50)) / 100.0
    break_search  = getattr(state, 'component_break_search',  False)
    break_results = getattr(state, 'component_break_results', False)
    break_booking = getattr(state, 'component_break_booking', False)
    break_pricing = getattr(state, 'component_break_pricing', False)
    break_css     = getattr(state, 'component_break_css',     False)
    break_nav     = getattr(state, 'component_break_nav',     False)

    # Check page target filter (same pattern as page_load_target_pages)
    try:
        import json as _json
        target_pages = _json.loads(getattr(state, 'component_target_pages', '["all"]') or '["all"]')
    except Exception:
        target_pages = ['all']

    # Reuse the global PAGE_SLUG_MAP so component chaos targets the same
    # pages as page-load chaos (including booking/detail sub-paths).
    if 'all' not in target_pages:
        matched = False
        for slug in target_pages:
            prefixes = PAGE_SLUG_MAP.get(slug, [f'/{slug}'])
            if any(path.startswith(p) for p in prefixes):
                matched = True
                break
        if not matched:
            return ''

    # Build JS flags from Python booleans
    def js_bool(v): return 'true' if v else 'false'

    _log_event('INJECTED_ERROR', 'component_chaos',
               path=path, rate=rate,
               search=break_search, results=break_results,
               booking=break_booking, pricing=break_pricing,
               css=break_css, nav=break_nav)

    js_code = f"""
<script>
/* SnapTravels Component Chaos — Section 3 */
(function() {{
  var RATE = {rate};
  if (Math.random() > RATE) return; // probabilistic trigger

  var BREAK_SEARCH  = {js_bool(break_search)};
  var BREAK_RESULTS = {js_bool(break_results)};
  var BREAK_BOOKING = {js_bool(break_booking)};
  var BREAK_PRICING = {js_bool(break_pricing)};
  var BREAK_CSS     = {js_bool(break_css)};
  var BREAK_NAV     = {js_bool(break_nav)};

  // Component error box HTML helper
  function errorBox(icon, title, detail) {{
    var d = document.createElement('div');
    d.style.cssText = 'border:1.5px dashed #f87171;background:#fff1f2;border-radius:10px;padding:20px 24px;text-align:center;margin:12px 0;';
    d.innerHTML = '<div style="font-size:2rem;margin-bottom:8px">' + icon + '</div>'
      + '<div style="font-weight:700;color:#b91c1c;font-size:.95rem;margin-bottom:4px">' + title + '</div>'
      + '<div style="color:#6b7280;font-size:.8rem">' + detail + '</div>';
    return d;
  }}

  document.addEventListener('DOMContentLoaded', function() {{

    /* ── 1. Search Widget Crash ─────────────────────────────── */
    if (BREAK_SEARCH) {{
      var searchForms = document.querySelectorAll(
        'form[id*="Search"], form[id*="search"], .search-panel, .search-box, form[action*="search"]'
      );
      searchForms.forEach(function(el) {{
        var err = errorBox('⚡', 'Search service unavailable',
          'ChunkLoadError: Failed to load module "search-widget.js" — net::ERR_ABORTED 503');
        el.style.position = 'relative';
        el.style.pointerEvents = 'none';
        el.style.opacity = '0.35';
        el.style.filter = 'grayscale(0.8)';
        el.parentNode.insertBefore(err, el.nextSibling);
        console.error('[SnapTravels] SearchWidget: ChunkLoadError: Loading chunk search-widget failed. (Missing: search-widget.js)');
      }});
    }}

    /* ── 2. Results Section Crash ───────────────────────────── */
    if (BREAK_RESULTS) {{
      var resultContainers = document.querySelectorAll(
        '#flightResults, #hotelResults, .flight-card, .bus-result, .train-result, .cab-result, #resultsContainer'
      );
      if (resultContainers.length > 0) {{
        var parent = resultContainers[0].closest('.col-lg-9, .results-panel, [id*="Results"]')
          || resultContainers[0].parentElement;
        // Hide existing cards
        resultContainers.forEach(function(c) {{ c.style.display = 'none'; }});
        var err = errorBox('💥', 'Results component failed to render',
          'TypeError: Cannot read properties of undefined (reading "map") at ResultsList.render [chunk: results-list.abc123.js:47]');
        parent.appendChild(err);
        console.error('[SnapTravels] ResultsComponent: Uncaught TypeError: Cannot read properties of undefined (reading "map")');
        console.error('[SnapTravels] ResultsComponent: Component tree unmounted. Fallback UI not configured.');
      }}
    }}

    /* ── 3. Booking / CTA Buttons Crash ─────────────────────── */
    if (BREAK_BOOKING) {{
      var ctaSelectors = [
        '.btn-select', 'a[href*="seat"]', 'a[href*="booking"]',
        '.btn-book', 'button[type=submit]', 'a[class*="book"]'
      ];
      var ctaBtns = document.querySelectorAll(ctaSelectors.join(','));
      ctaBtns.forEach(function(btn) {{
        btn.addEventListener('click', function(e) {{
          e.preventDefault();
          e.stopPropagation();
          var tip = document.createElement('div');
          tip.style.cssText = 'position:fixed;top:24px;right:24px;z-index:9999;background:#dc2626;color:#fff;border-radius:10px;padding:14px 20px;font-size:.88rem;max-width:320px;box-shadow:0 4px 20px rgba(0,0,0,.2)';
          tip.innerHTML = '<strong>⚠️ Booking service error</strong><br>Failed to initialize checkout module. Error: MODULE_LOAD_FAIL (booking-flow.js). Please try again later.';
          document.body.appendChild(tip);
          setTimeout(function() {{ tip.remove(); }}, 5000);
          console.error('[SnapTravels] BookingModule: import() failed for booking-flow.js — ERR_ABORTED');
        }});
        btn.style.opacity = '0.5';
        btn.title = '503 — Booking service temporarily unavailable';
      }});
    }}

    /* ── 4. Pricing Display Corruption ──────────────────────── */
    if (BREAK_PRICING) {{
      var priceEls = document.querySelectorAll(
        '.price-main, .price-section .fw-bold, [class*="price"], .fare-amount'
      );
      var errors = ['₹ --', 'N/A', '₹ ???', 'ERR'];
      priceEls.forEach(function(el) {{
        if (el.textContent.includes('₹') || el.textContent.includes('per person')) {{
          el.textContent = errors[Math.floor(Math.random() * errors.length)];
          el.style.color = '#dc2626';
          el.style.fontStyle = 'italic';
        }}
      }});
      console.error('[SnapTravels] PriceFeed: WebSocket connection to pricing-feed.snaptravels.internal closed unexpectedly — prices unavailable');
    }}

    /* ── 5. CSS Load Failure (layout corruption) ─────────────── */
    if (BREAK_CSS) {{
      // Remove app.css stylesheet to simulate CSS chunk load failure
      document.querySelectorAll('link[rel="stylesheet"]').forEach(function(link) {{
        if (link.href && (link.href.includes('app.css') || link.href.includes('style'))) {{
          link.disabled = true;
        }}
      }});
      // Inject deliberately broken override CSS
      var style = document.createElement('style');
      style.textContent = [
        '.navbar, nav {{ position: static !important; z-index: 0 !important; }}',
        '.container {{ max-width: none !important; padding: 0 !important; }}',
        '.card, .flight-card, .hotel-card {{ border-radius: 0 !important; margin: 0 !important; box-shadow: none !important; }}',
        'img {{ filter: grayscale(1) !important; }}',
        '.btn {{ border-radius: 0 !important; }}',
      ].join(' ');
      document.head.appendChild(style);
      console.error('[SnapTravels] StyleLoader: Failed to load stylesheet chunk "app.css" — net::ERR_CONNECTION_REFUSED');
      console.warn('[SnapTravels] StyleLoader: Falling back to unstyled render. CSS cascade is incomplete.');
    }}

    /* ── 6. Navigation Component Crash ──────────────────────── */
    if (BREAK_NAV) {{
      var navLinks = document.querySelectorAll(
        'nav a, .navbar a, header a, .nav-link'
      );
      navLinks.forEach(function(link) {{
        link.addEventListener('click', function(e) {{
          // Allow admin links through
          if (link.href && link.href.includes('/admin')) return;
          e.preventDefault();
          var tip = document.createElement('div');
          tip.style.cssText = 'position:fixed;top:20px;right:20px;z-index:99999;background:#dc2626;color:#fff;border-radius:8px;padding:12px 18px;font-size:.85rem;max-width:340px;box-shadow:0 4px 20px rgba(0,0,0,.3)';
          tip.innerHTML = '<strong>⚡ Navigation Error</strong><br>ChunkLoadError: router-module.js — net::ERR_ABORTED 503<br><small style="opacity:.8">' + (link.textContent.trim() || link.pathname) + '</small>';
          document.body.appendChild(tip);
          setTimeout(function(){{ tip.remove(); }}, 4000);
          console.error('[SnapTravels] RouterModule: ChunkLoadError: Loading chunk router failed — route: ' + (link.textContent.trim() || link.href));
        }});
        link.style.color = '#9ca3af';
        link.style.textDecoration = 'line-through';
      }});
      console.error('[SnapTravels] RouterModule: ChunkLoadError: Loading chunk router failed — net::ERR_ABORTED 503');
    }}

    /* ── Autocomplete Crash ──────────────────────────────────────────────── */
    if ({js_bool(getattr(state, 'component_break_autocomplete', False))}) {{
      document.querySelectorAll('.st-ac-city').forEach(function(inp){{
        inp.addEventListener('input', function(){{
          if (this.value.length >= 2) {{
            console.error('[chaos] TypeError: Cannot read properties of undefined (reading "suggestions")');
            /* Destroy the dropdown if autocomplete module already built one */
            var dd = inp.parentElement && inp.parentElement.querySelector('.st-ac-dropdown');
            if (dd) dd.remove();
            throw new TypeError('Cannot read properties of undefined (reading "suggestions")');
          }}
        }});
      }});
    }}

    /* ── Date Picker Freeze ─────────────────────────────────────────────── */
    if ({js_bool(getattr(state, 'component_break_datepicker', False))}) {{
      document.querySelectorAll('input[type="date"], input[name="depart_date"], input[name="checkin"], input[name="checkout"], input[name="return_date"], input[name="travel_date"]').forEach(function(inp){{
        inp.setAttribute('max', new Date(Date.now() - 86400000).toISOString().split('T')[0]);
        inp.value = '';
        inp.setAttribute('placeholder', 'Invalid date');
        inp.style.color = '#ef4444';
        inp.addEventListener('change', function(e){{ e.preventDefault(); this.value = ''; }});
      }});
      console.error('[chaos] DateRangePicker: Invalid date range — all future dates disabled');
    }}

    /* ── Review/Rating Component Crash ──────────────────────────────────── */
    if ({js_bool(getattr(state, 'component_break_ratings', False))}) {{
      document.querySelectorAll('.stars, .rating, [class*="star"], [class*="rating"], [class*="review"]').forEach(function(el){{
        el.innerHTML = '<span style="color:#ef4444;font-size:.75rem;font-family:monospace">TypeError: rating.map is not a function</span>';
      }});
      console.error('[chaos] RatingComponent: TypeError: rating.map is not a function at ReviewWidget.render');
    }}

    /* ── Loyalty Points → Zero ───────────────────────────────────────────── */
    if ({js_bool(getattr(state, 'component_break_loyalty', False))}) {{
      document.querySelectorAll('[class*="point"], [class*="reward"], [class*="loyalty"], [class*="credit"]').forEach(function(el){{
        el.textContent = el.textContent.replace(/\d[\d,]+/g, '0');
      }});
      console.error('[chaos] LoyaltyService: balance sync failed — displaying cached fallback (0)');
    }}

  }});
}})();
</script>
"""
    return js_code


# ── Section 2: Functionality Failures Chaos ───────────────────────────────

def should_empty_search() -> bool:
    """Return True if search results should be forced empty. Call in search routes."""
    state = _get_state_raw()
    return bool(state and getattr(state, 'func_chaos', False)
                and getattr(state, 'func_search_empty', False))


def maybe_404_storm():
    """Randomly abort the request with 404. Call from a before_request hook."""
    state = _get_state_raw()
    if not state or not getattr(state, 'func_chaos', False):
        return
    rate = getattr(state, 'func_404_storm_rate', 0.0) or 0.0
    if _roll(rate):
        from flask import abort, request
        # Never 404-storm login/signup, admin, home, or static assets.
        # Chaos should only affect content pages (flights, hotels, etc.)
        safe_prefixes = ('/admin/', '/login', '/signup', '/logout',
                         '/static/', '/assets/', '/health', '/auth/')
        if request.path.startswith(safe_prefixes) or request.path == '/':
            return
        _log_event('INJECTED_ERROR', 'func_404_storm',
                   path=request.path, rate=rate)
        abort(404)


def maybe_kill_session():
    """Randomly expire the user session. Call from a before_request hook."""
    state = _get_state_raw()
    if not state or not getattr(state, 'func_chaos', False):
        return
    rate = getattr(state, 'func_session_kill_rate', 0.0) or 0.0
    if _roll(rate):
        from flask import session, request
        # Never kill session on login/signup/admin pages
        safe_prefixes = ('/login', '/signup', '/logout', '/admin/', '/auth/', '/health')
        if request.path.startswith(safe_prefixes) or request.path == '/':
            return
        if session.get('user_id'):
            _log_event('INJECTED_ERROR', 'func_session_kill',
                       path=request.path, rate=rate)
            session.clear()


# ── New Section 2 helpers ──────────────────────────────────────────────────────

def should_wrong_search() -> bool:
    """Return True if search results should show wrong destination data."""
    state = _get_state_raw()
    return bool(state and getattr(state, 'func_chaos', False)
                and getattr(state, 'func_wrong_search', False))


def should_fake_soldout() -> bool:
    """Return True if all flights/hotels should appear sold out."""
    state = _get_state_raw()
    return bool(state and getattr(state, 'func_chaos', False)
                and getattr(state, 'func_fake_soldout', False))


def should_otp_fail() -> bool:
    """Return True if all OTP/2FA codes should be rejected."""
    state = _get_state_raw()
    return bool(state and getattr(state, 'func_chaos', False)
                and getattr(state, 'func_otp_invalid', False))


def should_email_fail() -> bool:
    """Return True if outbound emails should be silently dropped."""
    state = _get_state_raw()
    return bool(state and getattr(state, 'func_chaos', False)
                and getattr(state, 'func_email_chaos', False))


def should_maintenance_flood() -> bool:
    """Return True ~25% of the time when maintenance flood is on."""
    state = _get_state_raw()
    if not (state and getattr(state, 'func_chaos', False)
            and getattr(state, 'func_maintenance_flood', False)):
        return False
    return random.random() < 0.25


# ── Section 4: A/B Test Chaos ──────────────────────────────────────────────────

def get_ab_test_js() -> str:
    """
    Inject A/B test chaos: pages look identical visually but internal
    identifiers (form IDs, button names, data attributes, CSS classes)
    are mutated — breaking analytics event tracking, synthetic monitor
    element selectors, and A/B testing tools.
    """
    state = _get_state_raw()
    if not state or not getattr(state, 'ab_test_chaos', False):
        return ''

    from flask import request
    path = request.path if request else '/'

    # Determine which targets are active
    do_login   = getattr(state, 'ab_test_login',   False)
    do_search  = getattr(state, 'ab_test_search',  False)
    do_booking = getattr(state, 'ab_test_booking', False)
    do_profile = getattr(state, 'ab_test_profile', False)

    # Skip admin/auth routes
    skip_paths = ('/admin/', '/static/', '/assets/', '/health', '/api/')
    if any(path.startswith(p) for p in skip_paths):
        return ''

    login_active   = do_login   and path in ('/login', '/auth/login')
    search_active  = do_search  and path in ('/', '/flights', '/hotels', '/buses', '/trains', '/cabs')
    booking_active = do_booking and ('booking' in path or 'confirm' in path)
    profile_active = do_profile and ('profile' in path or 'dashboard' in path)

    if not any([login_active, search_active, booking_active, profile_active]):
        return ''

    _log_event('INJECTED_ERROR', 'ab_test_chaos', path=path)

    return """<script>
/* SnapTravels Chaos: A/B Test Identifier Mutation */
(function(){
  var VARIANT = 'b_' + Math.random().toString(36).slice(2,6);

  /* Mutate form IDs and names */
  document.querySelectorAll('form').forEach(function(f, i){
    var orig = f.id || f.getAttribute('name') || ('form_' + i);
    f.setAttribute('data-orig-id', orig);
    f.id   = orig + '_variant_' + VARIANT;
    if (f.getAttribute('name')) f.setAttribute('name', f.getAttribute('name') + '_v2');
    f.setAttribute('data-ab-variant', VARIANT);
    /* Inject hidden variant marker instead of mutating action URL (which breaks POSTs) */
    var hid = document.createElement('input');
    hid.type = 'hidden'; hid.name = 'ab_variant'; hid.value = VARIANT;
    f.appendChild(hid);
  });

  /* Mutate button IDs and text variants */
  var btnMap = {
    'Sign In': 'Log in',      'Login': 'Sign In',
    'Book Now': 'Reserve Now', 'Confirm Booking': 'Complete Booking',
    'Search': 'Find',          'Search Flights': 'Find Flights',
    'Search Hotels': 'Find Hotels', 'Register': 'Create Account',
    'Submit': 'Send',          'Pay Now': 'Complete Payment',
  };
  document.querySelectorAll('button[type="submit"], input[type="submit"], .btn').forEach(function(btn, i){
    var orig = btn.textContent.trim();
    if (btnMap[orig]) btn.textContent = btnMap[orig];
    var origId = btn.id || ('btn_' + i);
    btn.setAttribute('data-orig-id', origId);
    btn.id = origId + '_variant_' + VARIANT;
    btn.setAttribute('data-ab-variant', VARIANT);
  });

  /* Mutate input IDs and placeholder text */
  var placeholderMap = {
    'Enter your email': 'Email address',
    'Enter your password': 'Password',
    'Full Name': 'Your full name',
    'Phone Number': 'Mobile number',
    'Card Number': 'Credit/debit card number',
  };
  document.querySelectorAll('input, select, textarea').forEach(function(inp, i){
    var origId = inp.id || ('inp_' + i);
    inp.setAttribute('data-orig-id', origId);
    inp.id = origId + '_v2';
    var ph = inp.getAttribute('placeholder');
    if (ph && placeholderMap[ph]) inp.setAttribute('placeholder', placeholderMap[ph]);
  });

  /* Mutate CSS class names on key interactive elements */
  document.querySelectorAll('[class*="btn-"], [class*="-btn"], [class*="submit"]').forEach(function(el){
    el.className = el.className
      .replace(/btn-primary/g, 'btn-variant-primary')
      .replace(/btn-success/g, 'btn-variant-success')
      .replace(/submit-btn/g, 'submit-btn-v2');
    el.setAttribute('data-ab-variant', VARIANT);
  });

  /* Inject invisible variant markers (breaks analytics tracking) */
  var marker = document.createElement('div');
  marker.style.cssText = 'display:none;visibility:hidden;position:absolute;left:-9999px';
  marker.setAttribute('data-ab-test-id', VARIANT);
  marker.setAttribute('data-ab-bucket', 'variant_b');
  marker.setAttribute('data-experiment', 'chaos_ab_' + Date.now());
  document.body.appendChild(marker);

  /* Fake analytics event for variant assignment */
  console.log('[AB Test] User assigned to variant:', VARIANT);
  console.log('[AB Test] Experiment: chaos_experiment_' + new Date().toISOString().slice(0,10));
  if (window.dataLayer) window.dataLayer.push({event: 'ab_variant_assigned', variant: VARIANT});

  /* Dispatch custom event that analytics listeners expect but with wrong data */
  document.dispatchEvent(new CustomEvent('ab:variant', { detail: { variant: VARIANT, experiment: 'chaos' } }));
})();
</script>"""


# ----------------------------------------------------------------------
# Outage lifecycle helpers (used by scheduler + admin UI)
# ----------------------------------------------------------------------
def start_outage(label: str, duration_minutes: int, **overrides):
    """
    Apply a named outage to the FailureMode singleton.
    `overrides` is a dict of column_name -> value, e.g.
        start_outage('login_storm', 20, login_failure_rate=0.6,
                     login_slowdown_ms=800)
    """
    from app.models import FailureMode
    from app import db
    from datetime import timedelta

    state = FailureMode.current()
    # Auto-enable core chaos so the outage profile actually fires
    state.enabled = True
    for k, v in overrides.items():
        if hasattr(state, k):
            setattr(state, k, v)
    state.outage_label = label
    state.outage_started_at = datetime.utcnow()
    state.outage_ends_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
    state.updated_by = 'chaos_scheduler'
    db.session.commit()

    _log_event('OUTAGE_START', label,
               duration_minutes=duration_minutes,
               overrides=overrides)
    return state


def end_outage(reason: str = 'scheduled'):
    """Clear every failure knob and close the outage window."""
    from app.models import FailureMode
    from app import db
    state = FailureMode.current()
    label = state.outage_label or 'manual'
    # Core chaos
    state.login_failure_rate = 0.0
    state.login_slowdown_ms = 0
    state.db_slowdown_ms = 0
    state.db_down = False
    state.search_timeout_rate = 0.0
    state.search_slowdown_ms = 0
    state.checkout_exception_rate = 0.0
    state.checkout_slowdown_ms = 0
    state.payment_gateway_down = False
    state.payment_failure_rate = 0.0
    state.api_5xx_rate = 0.0
    state.api_slowdown_ms = 0
    # Page load chaos
    state.page_load_chaos = False
    state.page_load_delay_ms = 0
    state.page_load_inject_js_errors = False
    state.page_load_inject_resource_failures = False
    state.page_load_inject_memory_pressure = False
    state.page_load_inject_render_blocking = False
    state.page_load_large_payload = False
    state.page_load_webfont_failure = False
    state.page_load_ttfb_spike = False
    state.page_load_cache_chaos = False
    # Functionality chaos
    state.func_chaos = False
    state.func_search_empty = False
    state.func_form_errors = False
    state.func_broken_images = False
    state.func_session_kill_rate = 0.0
    state.func_404_storm_rate = 0.0
    state.func_infinite_spin = False
    state.func_broken_cta = False
    state.func_wrong_search = False
    state.func_fake_soldout = False
    state.func_date_picker_broken = False
    state.func_otp_invalid = False
    state.func_email_chaos = False
    state.func_maintenance_flood = False
    # Component chaos
    state.component_chaos = False
    state.component_break_search  = False
    state.component_break_results = False
    state.component_break_booking = False
    state.component_break_pricing = False
    state.component_break_css     = False
    state.component_break_nav     = False
    state.component_break_autocomplete = False
    state.component_break_datepicker = False
    state.component_break_ratings = False
    state.component_break_loyalty = False
    # A/B test chaos
    state.ab_test_chaos = False
    state.ab_test_login = False
    state.ab_test_search = False
    state.ab_test_booking = False
    state.ab_test_profile = False
    # Outage window
    # Mobile App Chaos (Section 5)
    state.mobile_chaos                = False
    state.mobile_auth_failure_rate    = 0.0
    state.mobile_search_slow_ms       = 0
    state.mobile_search_empty_rate    = 0.0
    state.mobile_booking_decline_rate = 0.0
    state.mobile_cancel_failure_rate  = 0.0
    state.mobile_timeout_rate         = 0.0
    state.mobile_rate_limit_rate      = 0.0
    state.mobile_malform_rate         = 0.0
    # Outage window
    state.outage_label = None
    state.outage_started_at = None
    state.outage_ends_at = None
    state.updated_by = f'chaos_scheduler:{reason}'
    db.session.commit()

    _log_event('OUTAGE_END', label, reason=reason)
    return state
