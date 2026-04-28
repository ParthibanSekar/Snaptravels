# SnapTravels — Flights Module

## Blueprint: public.py (partial)

### Routes
| Route | Method | Template | Notes |
|---|---|---|---|
| `/flights` | GET/POST | `flights.html` | Search + list results |
| `/flight/<id>/seat-select` | GET/POST | `seat_selection.html` | Seat map picker |
| `/book/flight/<id>` | GET | `booking.html` | Booking form (shared with hotels) |
| `/booking/confirmation/<code>` | GET | `booking_confirmation.html` | Post-payment confirmation |

### Search params (GET/POST to /flights)
- `origin`, `destination`, `travel_date`, `return_date`, `cabin_class`, `passengers`, `trip_type` (one-way/round)

### Template context for booking.html (flight)
```python
render_template('booking.html',
  form=form,              # Flask-WTF form
  flight=selected_flight, # Flight model object (or None for hotel)
  hotel=None,
  total_amount=total_amount,
  user=current_user,
  selected_seats=selected_seats,  # Comma-separated seat labels e.g. "12A,12B"
)
```

## Flight Model (app/models.py)

```python
class Flight(db.Model):
    id, airline, flight_no, origin, destination
    depart_time, arrive_time   # String "HH:MM"
    duration_mins              # Integer
    cabin_class                # 'Economy' / 'Business' / 'First'
    price                      # Float (per seat)
    seats_left                 # Integer
    travel_date                # Date
```

## flights.html — Design Pattern

**Color theme:** Blue — `linear-gradient(135deg, #0f2044 0%, #1d4ed8 60%, #3b82f6 100%)`

**Structure:**
1. Blue gradient hero with plane icon + search card (origin/dest swapper, date, class, passengers)
2. Sidebar filters (sticky): Sort By (price/duration/depart), Cabin Class buttons, Departure time slots, Stops toggle
3. Search chips row — active search params as colored badges
4. Sort bar — shows "X flights found" + secondary info
5. Result cards (list layout):
   - Blue top accent bar + airline logo/name block
   - Route visualization: depart time → animated blue gradient bar with duration pill → arrive time
   - Cabin class badge, stops badge, amenity pills
   - Seat availability bar (red/amber/green)
   - Footer: baggage info, flight no, refund policy
   - Right-aligned price + Book button
6. Landing state (pre-search): Popular routes grid + trust badges
7. Empty state: "No flights found" with reset button

**JS functions:** `sortFlights()`, `filterCabinClass()`, `applyFlightFilters()`, `updateFlightCount()`, `resetFilters()`

**Card data attributes:** `data-price`, `data-duration`, `data-seats`, `data-depart`, `data-cabin`, `data-stops`

## Seat Selection (seat_selection.html)
- Grid of seat buttons colored by class (economy/business/first)
- Already-taken seats disabled (grey)
- Click toggles selected state, updates hidden input
- Max seats = passengers count
