# SnapTravels — Hotels Module

## Blueprint: public.py (partial)

### Routes
| Route | Method | Template | Notes |
|---|---|---|---|
| `/hotels` | GET/POST | `hotels.html` | Search + list results |
| `/hotel/<id>` | GET | `hotel_detail.html` | Hotel detail page |
| `/hotel/<id>/room-select` | GET/POST | `room_selection.html` | Room picker |
| `/book/hotel/<id>` | GET | `booking.html` | Booking form (shared with flights) |
| `/booking/confirmation/<code>` | GET | `booking_confirmation.html` | Post-payment confirmation |

### Search params (GET/POST to /hotels)
- `city`, `check_in`, `check_out`, `guests`, `rooms`

### Template context for booking.html (hotel)
```python
render_template('booking.html',
  form=form,
  flight=None,
  hotel=selected_hotel,        # Hotel model object
  total_amount=total_amount,
  nights=nights,               # Integer — number of nights
  user=current_user,
  selected_room_name=selected_room_name,  # String e.g. "Deluxe Double"
)
```

## Hotel Model (app/models.py)

```python
class Hotel(db.Model):
    id, name, city, rating      # rating Float 1.0-5.0
    price_per_night             # Float
    amenities                   # Comma-separated string e.g. "WiFi,Pool,Gym"
    image_url                   # Path or URL
    rooms_left                  # Integer
    description                 # Text
    address                     # String
```

## hotels.html — Design Pattern

**Color theme:** Teal — `linear-gradient(135deg, #022c22 0%, #0f766e 60%, #14b8a6 100%)`

**Structure:**
1. Teal gradient hero + search card (city, check-in/check-out, guests)
2. Sidebar filters (sticky): Sort By (price/rating), Star Rating checkboxes, Amenities toggles (WiFi/Pool/Gym/Parking), Price range slider
3. Search chips row — active search params
4. Sort bar — "X hotels found"
5. Result cards (list layout):
   - Hotel image thumbnail left-side
   - Name, city, star rating display
   - Amenity pills
   - Price/night + "per night" label right-aligned
   - Book Now button
6. Landing state: Popular cities grid + trust badges
7. Empty state with reset

**Card data attributes:** `data-price`, `data-rating`, `data-amenities`, `data-city`

## Room Selection (room_selection.html)
- Lists available room types (Standard/Deluxe/Suite etc.)
- Each card shows: room name, size, bed type, max guests, amenities, price/night
- Select button sets `selected_room_name` in session
- Redirects to `/book/hotel/<id>`

## Hotel Detail (hotel_detail.html)
- Full-width hero image
- Name, city, rating, address
- Amenities grid
- Review snippet
- "Check Availability" CTA → room-select
