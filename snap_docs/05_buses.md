# SnapTravels — Buses Module

## Blueprint: buses.py

### Routes
| Route | Method | Template | Notes |
|---|---|---|---|
| `/buses` | GET/POST | `buses.html` | Search + list results |
| `/bus-book/<bus_id>` | GET | `bus_booking.html` | Booking form |
| `/bus-book/<bus_id>/confirm` | POST | — | Processes booking, redirects to confirmation |

### Template context for bus_booking.html
```python
render_template('bus_booking.html',
  bus=bus,                # Bus model object
  bus_search=bus_search,  # Dict from session: {origin, destination, travel_date, passengers}
  passengers=passengers,  # Integer
  total=total,            # Float = bus.price * passengers
  user=current_user,
  selected_seats=selected_seats,  # Comma-separated e.g. "A1,A2" (optional)
)
```

## Bus Model (app/models.py)

```python
class Bus(db.Model):
    id, bus_no, operator
    origin, destination
    depart_time, arrive_time    # String "HH:MM"
    duration_mins               # Integer (default 300)
    bus_type                    # 'AC Sleeper' / 'Volvo' / 'Non-AC' / 'Luxury'
    price                       # Float (per seat)
    seats_left                  # Integer (default 40)
    amenities                   # Comma-separated e.g. "WiFi,Snacks,GPS"
```

## buses.html — Design (UPGRADED in Part 2 session)

**Color theme:** Deep purple — `linear-gradient(135deg, #3b0764 0%, #7c3aed 60%, #a78bfa 100%)`

**Structure (matches trains gold standard):**
1. Purple gradient hero + bus icon + search card (origin/dest, date, passengers)
2. **Sticky sidebar filters:**
   - Sort By: Departure Time / Price: Low-High / Price: High-Low / Seats Available
   - Bus Type buttons: All / Volvo / Sleeper / Seater / Non-AC / Luxury (data-btype)
   - Departure Time slots: Morning (6-12) / Afternoon (12-18) / Evening (18-24) (data-slot checkboxes)
   - Seats Available toggle (min 5 seats)
3. Search chips row — origin, dest, date, passengers as colored purple badges
4. Sort bar — "X buses found" + active filter summary
5. **Bus result cards (list layout):**
   - Purple top accent bar
   - Operator name + bus_no · bus_type
   - Type badge (color-coded: Volvo=purple, Sleeper=amber, Seater=blue, Non-AC=grey, Luxury=gold)
   - Route visualization: depart_time → [road dots] → 🚌 icon → [road dots] → arrive_time with duration pill
   - "Direct" badge
   - Amenity pills: WiFi / Snacks / GPS / Charging
   - Seat availability bar (color-coded: red < 5, amber < 15, green ≥ 15)
   - Footer row: ⭐ rating / Wi-Fi / Snacks / GPS Tracked / seats_left seats left
   - Right-aligned: price + "per seat" + Book button
6. Landing state (pre-search): 6 popular route cards + 4 trust badges (Verified Operators / GPS Tracked / 24×7 Support / Free Cancellation)
7. Empty state with reset button

**JS functions:** `sortBuses(key, btn)`, `filterBusType(btype, btn)`, `applyBusFilters()`, `updateBusCount()`, `resetBusFilters()`

**Card data attributes:** `data-depart`, `data-price`, `data-seats`, `data-duration`, `data-btype`, `data-ac`

## bus_booking.html — Design (UPGRADED in Part 3 session)

**Color theme:** Same deep purple as buses.html

**Structure:**
1. Purple gradient hero + 4-step indicator (Search ✓ → Select Bus ✓ → Passenger & Payment ← here → Confirmation)
2. Journey card in hero: bus emoji + operator name + bus_no + bus_type badge + route visualization with duration pill + total fare
3. Left col (col-lg-8):
   - ① Passenger Details: name, email, phone, journey date (readonly), selected seat chips
   - ② GST Invoice: collapsible panel (chevron toggle) with GSTIN + company name + address
   - ③ Payment: 4-tab — Card (with brand detection) / UPI (6-app grid) / Net Banking (8-bank tiles + dropdown) / Wallets (4 tiles)
   - Terms checkbox (required) + submit with loading spinner
4. Right col (col-lg-4): Sticky summary panel
   - Operator / bus no / type / date / depart / arrive / duration / passengers / seats
   - Price breakdown: base fare × passengers + ₹30/seat convenience fee + 5% GST
   - Live promo code AJAX (updates total + Pay button text)
   - What's Included list
   - Trust badges

**Bus type badge CSS classes:** `btype-volvo`, `btype-sleeper`, `btype-seater`, `btype-nonac`, `btype-luxury`, `btype-default`
