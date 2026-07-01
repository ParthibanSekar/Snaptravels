/**
 * SnapTravels — Payment Form Validation
 * Validates card number, name, expiry, CVV on all booking & checkout forms.
 *
 * Usage: add data-payment-form="true" to the <form>
 * Field markers (add to inputs/selects):
 *   data-card-field="number"        — card number input
 *   data-card-field="name"          — cardholder name input
 *   data-card-field="expiry"        — single MM/YY text input
 *   data-card-field="expiry-month"  — month select
 *   data-card-field="expiry-year"   — year select
 *   data-card-field="cvv"           — CVV input
 *
 * Payment method detection: reads hidden input name="payment_method"
 * Validation only runs when payment_method === "card" (or no method field).
 */

(function () {
  'use strict';

  /* ── Helpers ─────────────────────────────────────────────────── */
  function digits(s) { return (s || '').replace(/\D/g, ''); }

  function showErr(el, msg) {
    clearErr(el);
    var err = document.createElement('div');
    err.className = 'snap-card-err';
    err.style.cssText = 'color:#ef4444;font-size:.75rem;margin-top:4px;display:flex;align-items:center;gap:4px;';
    err.innerHTML = '<i class="bi bi-exclamation-circle-fill" style="flex-shrink:0"></i><span>' + msg + '</span>';
    el.parentNode.appendChild(err);
    el.style.borderColor = '#ef4444';
    el.style.boxShadow   = '0 0 0 3px rgba(239,68,68,.15)';
  }

  function clearErr(el) {
    var existing = el.parentNode.querySelector('.snap-card-err');
    if (existing) existing.remove();
    el.style.borderColor = '';
    el.style.boxShadow   = '';
  }

  function markOk(el) {
    clearErr(el);
    el.style.borderColor = '#10b981';
    el.style.boxShadow   = '0 0 0 3px rgba(16,185,129,.12)';
  }

  /* ── Validators ──────────────────────────────────────────────── */
  function validateNumber(el) {
    var raw = digits(el.value);
    if (!raw)           { showErr(el, 'Card number is required'); return false; }
    if (raw.length < 13){ showErr(el, 'Card number is too short'); return false; }
    if (raw.length > 19){ showErr(el, 'Card number is too long'); return false; }
    if (raw.length !== 16 && raw.length !== 15 && raw.length !== 13) {
      showErr(el, 'Enter a valid 16-digit card number'); return false;
    }
    markOk(el); return true;
  }

  function validateName(el) {
    var v = (el.value || '').trim();
    if (!v)                     { showErr(el, 'Name on card is required'); return false; }
    if (v.length < 2)           { showErr(el, 'Name must be at least 2 characters'); return false; }
    if (/\d/.test(v))           { showErr(el, 'Name must not contain numbers'); return false; }
    if (!/^[a-zA-Z\s\-'\.]+$/.test(v)) { showErr(el, 'Name contains invalid characters'); return false; }
    markOk(el); return true;
  }

  function validateExpiryText(el) {
    var v = (el.value || '').replace(/\s/g, '');
    if (!v) { showErr(el, 'Expiry date is required'); return false; }
    var match = v.match(/^(\d{1,2})[\/\-](\d{2,4})$/);
    if (!match) { showErr(el, 'Use MM/YY format (e.g. 08/27)'); return false; }
    var month = parseInt(match[1], 10);
    var yearStr = match[2];
    var year = yearStr.length === 2 ? 2000 + parseInt(yearStr, 10) : parseInt(yearStr, 10);
    if (month < 1 || month > 12) { showErr(el, 'Invalid month (01–12)'); return false; }
    var now = new Date();
    var expDate = new Date(year, month, 0);  // last day of expiry month
    if (expDate < now) { showErr(el, 'Card has expired'); return false; }
    markOk(el); return true;
  }

  function validateExpirySelects(monthEl, yearEl) {
    var m = monthEl ? parseInt(monthEl.value, 10) : 0;
    var y = yearEl  ? parseInt(yearEl.value,  10) : 0;
    var ok = true;
    if (!m) { showErr(monthEl, 'Select month'); ok = false; }
    else if (m < 1 || m > 12) { showErr(monthEl, 'Invalid month'); ok = false; }
    else markOk(monthEl);
    if (!y) { if (yearEl) showErr(yearEl, 'Select year'); ok = false; }
    else {
      var fullYear = y < 100 ? 2000 + y : y;
      var now = new Date();
      var expDate = new Date(fullYear, m, 0);
      if (expDate < now) { if (yearEl) showErr(yearEl, 'Card has expired'); ok = false; }
      else if (yearEl) markOk(yearEl);
    }
    return ok;
  }

  function validateCvv(el) {
    var v = digits(el.value);
    if (!v)       { showErr(el, 'CVV is required'); return false; }
    if (v.length < 3) { showErr(el, 'CVV must be 3 or 4 digits'); return false; }
    if (v.length > 4) { showErr(el, 'CVV must be 3 or 4 digits'); return false; }
    markOk(el); return true;
  }

  /* ── Real-time formatting ────────────────────────────────────── */
  function attachFormatting(form) {
    var numEl = form.querySelector('[data-card-field="number"]');
    if (numEl) {
      numEl.addEventListener('input', function () {
        var pos = this.selectionStart;
        var raw = digits(this.value).slice(0, 16);
        var formatted = raw.match(/.{1,4}/g) ? raw.match(/.{1,4}/g).join(' ') : raw;
        this.value = formatted;
        clearErr(this);
      });
      numEl.addEventListener('blur', function () { validateNumber(this); });
    }

    var nameEl = form.querySelector('[data-card-field="name"]');
    if (nameEl) {
      nameEl.addEventListener('input', function () {
        // Remove digits in real time
        this.value = this.value.replace(/[0-9]/g, '');
        clearErr(this);
      });
      nameEl.addEventListener('blur', function () { validateName(this); });
    }

    var expiryEl = form.querySelector('[data-card-field="expiry"]');
    if (expiryEl) {
      expiryEl.addEventListener('input', function () {
        var v = this.value.replace(/[^0-9\/]/g, '');
        // Auto-insert slash after 2 digits
        if (v.length === 2 && !v.includes('/') && this._lastLen !== 3) {
          v += '/';
        }
        this._lastLen = v.length;
        this.value = v;
        clearErr(this);
      });
      expiryEl.addEventListener('blur', function () { validateExpiryText(this); });
    }

    var cvvEl = form.querySelector('[data-card-field="cvv"]');
    if (cvvEl) {
      cvvEl.addEventListener('input', function () {
        this.value = digits(this.value).slice(0, 4);
        clearErr(this);
      });
      cvvEl.addEventListener('blur', function () { validateCvv(this); });
    }
  }

  /* ── Submit handler ──────────────────────────────────────────── */
  function isCardPayment(form) {
    var pmField = form.querySelector('[name="payment_method"]');
    if (!pmField) return true;  // no payment method field = always validate
    return pmField.value === 'card';
  }

  function validateCardFields(form) {
    var ok = true;

    var numEl = form.querySelector('[data-card-field="number"]');
    if (numEl && !validateNumber(numEl)) ok = false;

    var nameEl = form.querySelector('[data-card-field="name"]');
    if (nameEl && !validateName(nameEl)) ok = false;

    var expiryEl = form.querySelector('[data-card-field="expiry"]');
    if (expiryEl && !validateExpiryText(expiryEl)) ok = false;

    var monthEl = form.querySelector('[data-card-field="expiry-month"]');
    var yearEl  = form.querySelector('[data-card-field="expiry-year"]');
    if (monthEl || yearEl) {
      if (!validateExpirySelects(monthEl, yearEl)) ok = false;
    }

    var cvvEl = form.querySelector('[data-card-field="cvv"]');
    if (cvvEl && !validateCvv(cvvEl)) ok = false;

    if (!ok) {
      // Scroll to first error
      var firstErr = form.querySelector('.snap-card-err');
      if (firstErr) firstErr.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    return ok;
  }

  /* ── Init — wire all payment forms ──────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    var forms = document.querySelectorAll('[data-payment-form="true"]');
    forms.forEach(function (form) {
      attachFormatting(form);

      form.addEventListener('submit', function (e) {
        if (!isCardPayment(form)) return true;  // non-card — skip

        // Clear previous errors first
        form.querySelectorAll('.snap-card-err').forEach(function (el) { el.remove(); });
        form.querySelectorAll('[data-card-field]').forEach(function (el) {
          el.style.borderColor = '';
          el.style.boxShadow   = '';
        });

        if (!validateCardFields(form)) {
          e.preventDefault();
          e.stopImmediatePropagation();
          return false;
        }
      }, true);  // capture phase — runs before existing handlers
    });
  });

})();
