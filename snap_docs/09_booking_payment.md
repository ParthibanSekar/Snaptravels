# SnapTravels — Booking Flow & Payment

## Booking Templates Reference

| Template | Used For | Key Variables |
|---|---|---|
| `booking.html` | Flights AND Hotels (shared) | `form`, `flight`, `hotel`, `total_amount`, `nights`, `user`, `selected_seats`, `selected_room_name` |
| `bus_booking.html` | Bus bookings | `bus`, `bus_search`, `passengers`, `total`, `user`, `selected_seats` |
| `train_booking.html` | Train bookings | `train`, `train_search`, `passengers`, `total`, `per_ticket`, `travel_class`, `class_name`, `user` |
| `cab_booking.html` | Cab bookings | `cab`, `cab_search`, `user` |
| `package_booking.html` | Holiday packages | `package`, `persons`, `travel_date`, `total`, `user` |

## Standard Booking Page Structure (Gold Standard)

All booking pages should follow this exact layout:

```
[HERO SECTION — gradient matching the transport mode color]
  ├── Step indicator (4 steps): Search ✓ → Select ✓ → Passenger & Payment ← → Confirmation
  └── Journey card: mode icon + operator/airline + route visualization + total fare

[MAIN CONTENT — Bootstrap row]
  ├── LEFT (col-lg-8): Forms
  │   ├── ① Passenger Details card
  │   │     name, email, phone, journey date (readonly), extra fields per mode
  │   ├── ② GST Invoice card (collapsible, chevron toggle)
  │   │     GSTIN + company name + address
  │   └── ③ Payment Method card
  │         4-tab selector: Card | UPI | Net Banking | Wallets
  │         Terms checkbox (required) + Submit button with loading state
  └── RIGHT (col-lg-4): Sticky summary panel
        Booking details rows → Price breakdown → Promo code → Grand Total
        What's Included list → Trust badges
```

## Color Themes by Mode

| Mode | Primary | Gradient |
|---|---|---|
| Flights | `#1d4ed8` (blue) | `#0f2044 → #1d4ed8 → #3b82f6` |
| Hotels | `#0f766e` (teal) | `#022c22 → #0f766e → #14b8a6` |
| Buses | `#7c3aed` (purple) | `#3b0764 → #7c3aed → #a78bfa` |
| Trains | `#1d4ed8` (indigo) | `#1e1b4b → #1d4ed8 → #3b82f6` |
| Cabs | `#0f766e` (teal) | `#134e4a → #0f766e → #14b8a6` |

## booking.html — Conditional Jinja2 Theming

```jinja2
{% set is_flight = flight is not none %}
{% set accent  = '#1d4ed8' if is_flight else '#0f766e' %}
{% set accent2 = '#3b82f6' if is_flight else '#14b8a6' %}
{% set bg_page = '#f0f4ff' if is_flight else '#f0fdfa' %}
```
All CSS vars and colors reference these Jinja2 variables — one template serves both flight and hotel with correct theming.

## Payment Tabs — Implementation Pattern

### Tab selector HTML
```html
<div class="d-flex gap-2 mb-4 flex-wrap">
  <div class="pay-tab active" onclick="switchPay('card',this)" id="tab-card">
    <div class="pay-tab-icon">💳</div>
    <div><div class="pay-tab-label">Card</div><div class="pay-tab-sub">Visa / MC / RuPay</div></div>
  </div>
  <!-- repeat for upi, netbanking, wallets -->
</div>
```

### Tab panels (id must match: pay-card, pay-upi, pay-netbanking, pay-wallets)
- `pay-upi` and others start with `display:none`
- `switchPay('upi', el)` shows the right panel, hides others, toggles `.active` class

### Card tab features
- Card number input with live formatter: groups of 4 digits (`formatCard()`)
- Brand detection: Visa (starts 4), MC (starts 5[1-5]), AMEX (starts 3[47]), RuPay (starts 6)
- Updates card icon emoji + highlights brand pill (`.card-brand-pill.active`)
- Month/Year as separate `<select>` elements (not a text field)
- CVV as `type="password"`, maxlength 4

### UPI tab features
- Text input for UPI ID
- 6-app shortcut grid: GPay, PhonePe, Paytm, BHIM, Amazon Pay, CRED
- `selectUpiApp(el)` — toggles `.selected` class

### Net Banking tab features
- 8 popular bank tiles grid: SBI, HDFC, ICICI, Axis, Kotak, PNB, BOB, Yes
- `selectBank(el)` — toggles `.selected` class
- Dropdown for other banks (10+ options)

### Wallets tab features
- 4 wallet tiles: Paytm Wallet, Amazon Pay, Mobikwik, Freecharge
- `selectWallet(el)` — toggles `.selected` class

## Promo Code — Implementation

### AJAX call pattern
```javascript
fetch('/promo/validate', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({ code: 'SAVE10', amount: 2500 })
})
.then(r => r.json())
.then(d => {
  if (d.valid) {
    // d.discount = amount saved
    // d.final    = new total
    // d.message  = "You saved ₹250!"
    document.getElementById('grandTotal').textContent = '₹' + Math.round(d.final).toLocaleString('en-IN');
    document.getElementById('btnText').textContent = 'Pay Securely — ₹...' + newTotal;
  }
})
```

### Backend route: reviews.py
`POST /promo/validate` — validates code against PromoCode model, checks expiry + usage limit + min amount

## Submit Button — Loading State Pattern

```html
<button type="submit" class="btn-confirm" id="submitBtn">
  <span class="spinner-border spinner-border-sm d-none" id="btnSpinner"></span>
  <i class="bi bi-lock-fill" id="btnIcon"></i>
  <span id="btnText">Pay Securely — ₹X,XXX</span>
</button>
```

```javascript
function handleSubmit(event) {
  if (!document.getElementById('termsChk').checked) {
    event.preventDefault(); return false;
  }
  document.getElementById('btnSpinner').classList.remove('d-none');
  document.getElementById('btnIcon').classList.add('d-none');
  document.getElementById('btnText').textContent = 'Processing payment…';
  document.getElementById('submitBtn').disabled = true;
  return true;
}
```

## Price Breakdown Pattern (right summary panel)

```
Base fare (₹X × N passengers)    ₹X,XXX
Convenience fee                   ₹XX
GST (5%)                          ₹XXX
─────────────────────────────────────
Total                             ₹X,XXX  ← id="grandTotal"
```

## Booking Confirmation

Route: `/booking/confirmation/<code>` (public.py)
Template: `booking_confirmation.html`
- Shows booking_code, item details, total paid, "What next" steps
- **Status: May need branding upgrade** — check if it still looks plain Bootstrap
