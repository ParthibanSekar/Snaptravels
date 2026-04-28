/**
 * SnapTravels City Autocomplete v3
 * Uses position:fixed to escape overflow:hidden parents.
 * Selects inputs by class AND by name as fallback.
 */
(function () {
  'use strict';

  var DEBOUNCE_MS = 220;
  var MIN_CHARS   = 2;
  var API_URL     = '/api/autocomplete';

  /* ── Inject CSS ─────────────────────────────────────────────── */
  function injectCSS() {
    if (document.getElementById('st-ac-css')) return;
    var s = document.createElement('style');
    s.id = 'st-ac-css';
    s.innerHTML = [
      '#st-ac-dd{position:fixed;z-index:999999;background:#fff;border:1px solid #d1d5db;',
      'border-radius:8px;box-shadow:0 8px 28px rgba(0,0,0,.18);max-height:220px;',
      'overflow-y:auto;display:none;min-width:180px}',
      '#st-ac-dd.on{display:block}',
      '.st-ac-i{padding:9px 14px;cursor:pointer;font-size:.875rem;color:#374151;',
      'display:flex;align-items:center;gap:8px;transition:background .09s}',
      '.st-ac-i:hover,.st-ac-i.hi{background:#eff6ff;color:#1d4ed8}',
      '.st-ac-i .ico{color:#9ca3af;font-size:.78rem}',
      '.st-ac-i.hi .ico{color:#1d4ed8}',
      '.st-ac-none{padding:9px 14px;font-size:.82rem;color:#9ca3af;text-align:center}'
    ].join('');
    document.head.appendChild(s);
  }

  /* ── Single shared dropdown on <body> ───────────────────────── */
  var el = null;
  function dd() {
    if (!el) {
      el = document.createElement('div');
      el.id = 'st-ac-dd';
      document.body.appendChild(el);
    }
    return el;
  }

  /* ── Position under input (fixed coords) ────────────────────── */
  function place(inp) {
    var r = inp.getBoundingClientRect();
    var d = dd();
    d.style.top   = (r.bottom + window.scrollY - window.scrollY + 2) + 'px';  // fixed ignores scroll
    d.style.left  = r.left + 'px';
    d.style.width = r.width + 'px';
    d.style.top   = (r.bottom + 2) + 'px';
  }

  /* ── State ──────────────────────────────────────────────────── */
  var items = [], cursor = -1, curInp = null;

  function close() {
    dd().classList.remove('on');
    cursor = -1; items = [];
  }

  function show(inp) {
    place(inp);
    dd().classList.add('on');
  }

  function highlight(n) {
    items.forEach(function(i,x){ i.classList.toggle('hi', x===n); });
    if (items[n]) items[n].scrollIntoView({block:'nearest'});
    cursor = n;
  }

  function pick(inp, city) {
    inp.value = city;
    close();
    inp.dispatchEvent(new Event('change', {bubbles:true}));
    /* advance focus to next field */
    var form = inp.closest('form');
    if (form) {
      var all = Array.from(form.querySelectorAll('input:not([type=hidden]),select,button[type=submit]'));
      var i = all.indexOf(inp);
      if (i >= 0 && all[i+1]) all[i+1].focus();
    }
  }

  /* ── Render list ─────────────────────────────────────────────── */
  function render(inp, cities) {
    var d = dd();
    d.innerHTML = '';
    items = []; cursor = -1;

    if (!cities.length) {
      d.innerHTML = '<div class="st-ac-none">No results</div>';
      show(inp); return;
    }
    cities.forEach(function(city) {
      var row = document.createElement('div');
      row.className = 'st-ac-i';
      row.innerHTML = '<span class="ico bi bi-geo-alt"></span><span>' + city + '</span>';
      row.addEventListener('mousedown', function(e) {
        e.preventDefault();
        pick(inp, city);
      });
      d.appendChild(row);
      items.push(row);
    });
    show(inp);
  }

  /* ── Debounce ────────────────────────────────────────────────── */
  function debounce(fn, ms) {
    var t;
    return function(){ var a=arguments,c=this; clearTimeout(t); t=setTimeout(function(){ fn.apply(c,a); }, ms); };
  }

  /* ── Wire one input ──────────────────────────────────────────── */
  function wire(inp) {
    console.log('[st-ac] wiring input:', inp.name || inp.id || inp.className);

    function go(q) {
      fetch(API_URL + '?q=' + encodeURIComponent(q))
        .then(function(r){ return r.ok ? r.json() : []; })
        .then(function(data){ console.log('[st-ac] results for', q, data); render(inp, data); })
        .catch(function(e){ console.warn('[st-ac] fetch error', e); close(); });
    }

    var dgo = debounce(go, DEBOUNCE_MS);

    inp.setAttribute('autocomplete', 'off');

    inp.addEventListener('input', function() {
      curInp = inp;
      var q = inp.value.trim();
      if (q.length < MIN_CHARS) { close(); return; }
      dgo(q);
    });

    inp.addEventListener('keydown', function(e) {
      if (!dd().classList.contains('on')) return;
      if (e.key==='ArrowDown'){ e.preventDefault(); highlight(Math.min(cursor+1, items.length-1)); }
      else if (e.key==='ArrowUp'){ e.preventDefault(); highlight(Math.max(cursor-1, 0)); }
      else if (e.key==='Enter' && cursor>=0){ e.preventDefault(); pick(inp, items[cursor].querySelector('span:last-child').textContent); }
      else if (e.key==='Escape'){ close(); }
    });

    inp.addEventListener('focus', function() {
      curInp = inp;
      var q = inp.value.trim();
      if (q.length >= MIN_CHARS) dgo(q);
    });

    inp.addEventListener('blur', function() {
      setTimeout(close, 180);
    });
  }

  /* ── Find all city inputs ────────────────────────────────────── */
  function init() {
    injectCSS();

    /* Primary: class-based selector */
    var found = document.querySelectorAll('.st-ac-city');

    /* Fallback: name-based for known city fields */
    if (!found.length) {
      console.warn('[st-ac] .st-ac-city not found, falling back to name selectors');
      found = document.querySelectorAll(
        'input[name="origin"], input[name="destination"], input[name="city"],' +
        'input[name="pickup"], input[name="drop"]'
      );
    }

    console.log('[st-ac] found', found.length, 'input(s)');
    found.forEach(wire);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
