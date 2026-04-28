# SnapTravels — Trains Module

## Blueprint: trains.py

### Routes
| Route | Method | Template | Notes |
|---|---|---|---|
| `/trains` | GET/POST | `trains.html` | Search + list (THE GOLD STANDARD page) |
| `/train-book/<train_id>` | GET | `train_booking.html` | Booking form |
| `/train-book/<train_id>/confirm` | POST | — | Processes booking |

### Template context for train_booking.html
```python
render_template('train_booking.html',
  train=train,               # Train model object
  train_search=train_search, # Dict: {origin, destination, travel_date, passengers, travel_class}
  passengers=passengers,     # Integer
  total=total,               # Float (class fare × passengers + fees)
  per_ticket=per_ticket,     # Float (fare for selected class)
  travel_class=travel_class, # String: 'SL', '3AC', '2AC', '1AC'
  class_name=class_name,     # String: 'Sleeper', '3-Tier AC', '2-Tier AC', '1st AC'
  user=current_user,
)
```

## Train Model (app/models.py)

```python
class Train(db.Model):
    id, train_no, train_name
    train_type              # 'Superfast' / 'Express' / 'Passenger'
    run_days                # 'Daily' / 'Mon-Sat' / 'Mon Wed Fri'
    origin, destination
    depart_time, arrive_time  # String "HH:MM"
    duration_mins             # Integer (default 480)
    distance_km               # Integer (default 500)
    sl_fare                   # Float — Sleeper class fare
    ac3_fare                  # Float — 3-Tier AC
    ac2_fare                  # Float — 2-Tier AC
    ac1_fare                  # Float — 1st AC
    # (availability fields per class)
```

## trains.html — Design (THE GOLD STANDARD — copy this pattern for all search pages)

**Color theme:** Indigo/Blue — `linear-gradient(135deg, #1e1b4b 0%, #1d4ed8 60%, #3b82f6 100%)`

**Structure:**
1. Deep indigo/blue gradient hero + 🚆 icon + search card (origin/dest, date, class, passengers)
2. **Sticky sidebar filters:**
   - Sort By: Departure Time / Price: Low-High / Duration
   - Train Class buttons: All / Sleeper / 3-Tier AC / 2-Tier AC / 1st AC
   - Departure Time slots: Early Morning / Morning / Afternoon / Evening
   - Train Type filter
   - Available only toggle
3. Search chips row — active search params as blue badges
4. Sort bar — "X trains found"
5. **Train result cards (list layout) — THE REFERENCE DESIGN:**
   - Blue top accent bar (border-top: 4px solid #1d4ed8)
   - Train name + train_no + type badge (Superfast/Express)
   - Class badges row (SL / 3AC / 2AC / 1AC with fare for each)
   - Route visualization: depart_time → [gradient line] → 🚆 → [gradient line] → arrive_time
   - Duration pill (center, overlaid on route bar)
   - Origin station name (below depart time) / Destination station name (below arrive time)
   - "Run days" label (Daily / Mon-Sat etc.)
   - Seat availability bar per class
   - Footer: distance km / amenities / cancellation info
   - Right-aligned: lowest available fare + "View Fares" button
6. Landing state: Popular routes grid + trust badges (PNR Tracking / Confirmed Seats / Instant Refunds / 24×7 Support)
7. Empty state with reset

**JS functions:** `sortTrains(key, btn)`, `filterTrainClass(cls, btn)`, `applyTrainFilters()`, `updateTrainCount()`, `resetFilters()`

**Card data attributes:** `data-price`, `data-depart`, `data-duration`, `data-class`, `data-type`

## train_booking.html — Design (Production-ready, no changes needed)

**Color theme:** Indigo/Blue (`#1e1b4b → #1d4ed8 → #3b82f6`)

**Class badge CSS:** `cb-sl` (amber/sleeper), `cb-3ac` (blue), `cb-2ac` (purple), `cb-1ac` (gold)

**Payment tabs:** 3 tabs — Card / UPI / Net Banking (does NOT have Wallets tab, unlike bus_booking.html)

**Notable:** train_booking.html is the original reference implementation — bus_booking.html and booking.html were built to match its pattern.
