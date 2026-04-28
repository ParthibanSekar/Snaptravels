# SnapTravels — Cabs Module

## Blueprint: cabs.py

### Routes
| Route | Method | Template | Notes |
|---|---|---|---|
| `/cabs` | GET/POST | `cabs.html` | Search + list cab options |
| `/cab-book/<cab_id>` | GET | `cab_booking.html` | Booking form |
| `/cab-book/<cab_id>/confirm` | POST | — | Processes booking |

### Template context for cab_booking.html
```python
render_template('cab_booking.html',
  cab=cab,               # Cab model object
  cab_search=cab_search, # Dict: {pickup, drop, travel_date, travel_time, passengers, distance_km}
  user=current_user,
)
```
Note: cab_booking.html calculates total as `cab.base_fare + (distance_km * cab.per_km_fare)` — no `total` variable passed directly.

## Cab Model (app/models.py)

```python
class Cab(db.Model):
    id
    vehicle_name   # e.g. "Swift Dzire", "Toyota Innova"
    brand          # e.g. "Maruti", "Toyota"
    vehicle_type   # 'Hatchback' / 'Sedan' / 'SUV' / 'Premium' / 'Tempo Traveller'
    capacity       # Integer — number of passengers
    per_km_fare    # Float — per km charge
    base_fare      # Float — minimum/base charge
    ac             # Boolean
    image_url      # Optional
```

## cabs.html — Design (UPGRADED in Part 2 session)

**Color theme:** Teal — `linear-gradient(135deg, #134e4a 0%, #0f766e 60%, #14b8a6 100%)`

**Structure (matches trains gold standard):**
1. Teal gradient hero + 🚗 icon + search card (pickup, drop, date, time, passengers, distance km)
2. **Sticky sidebar filters:**
   - Sort By: Price: Low-High / Capacity: High-Low / Per-KM Rate
   - Vehicle Type buttons: All / Hatchback / Sedan / SUV / Premium / Tempo Traveller (data-vcat)
   - AC Only checkbox
   - Capacity filters: 4+ / 6+ checkboxes
3. Search chips row — pickup, drop, date, time, passengers, distance km as teal badges
4. Sort bar — "X cabs available"
5. **Cab result cards (list layout — changed from original 3-col grid):**
   - 80×80 teal vehicle icon block on left
   - Vehicle name + brand + AC/Non-AC label
   - Vehicle type badge (color-coded by category)
   - Stat row: Seats 👥 / km 📍 / ₹per-km 💰 / Rating ⭐
   - Feature pills: AC / GPS / Sanitized / 24/7 Available
   - Right-aligned: estimated total + "Book" CTA
   - Footer row: ✓ Verified Driver / ✓ Free Cancellation / ✓ No Hidden Charges
6. Landing state: 6 popular route cards + 4 trust badges
7. Empty state with reset

**JS functions:** `sortCabs(key, btn)`, `filterCabType(vcat, btn)`, `applyCabFilters()`, `updateCabCount()`, `resetCabFilters()`

**Card data attributes:** `data-price`, `data-capacity`, `data-perkm`, `data-vcat`, `data-ac`

## cab_booking.html — Design (Already production-ready before Part 3, no changes made)

**Color theme:** Teal (`#134e4a → #0f766e`)

**Structure:**
1. Teal gradient hero + step indicator (3 steps: Search ✓ → Select Cab ✓ → Passenger & Payment)
2. Journey card: car emoji + vehicle name + brand + route (pickup → drop) + estimated distance + total fare
3. Left col: Passenger form (name, email, phone) + 3-tab payment (Card / UPI / Cash on Arrival)
4. Right col: Sticky summary — vehicle details, distance, price breakdown (base + per-km calculation), inclusions, trust badges
5. Note: Cabs have a **"Cash on Arrival"** payment option (not in flights/buses/trains)
