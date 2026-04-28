# SnapTravels — Holiday Packages & Activities

## Blueprint: packages.py

### Routes
| Route | Method | Template | Notes |
|---|---|---|---|
| `/packages` | GET | `packages.html` | List all holiday packages |
| `/packages/<id>` | GET | `package_detail.html` | Package detail page |
| `/packages/<id>/book` | GET/POST | `package_booking.html` | Package booking form |

## Package Model (app/models.py)

```python
class Package(db.Model):
    id, name, destination
    duration_days        # Integer
    price                # Float (per person)
    inclusions           # Text (comma or newline separated)
    itinerary            # Text (day-by-day description)
    image_url            # Path or URL
    max_persons          # Integer
    available_from       # Date
    available_to         # Date
    category             # 'Beach' / 'Hill' / 'Cultural' / 'Adventure' / 'Honeymoon'
```

### Template context for package_booking.html
```python
render_template('package_booking.html',
  package=package,
  persons=persons,          # Integer from session
  travel_date=travel_date,  # Date string
  total=total,              # package.price * persons
  user=current_user,
)
```

## packages.html — Design Notes

**Color theme:** Orange/Amber — gradient hero with warm travel vibes

**Structure:**
1. Hero with tagline + destination search input
2. Category filter pills (All / Beach / Hill / Cultural / Adventure / Honeymoon)
3. Package cards — 3-column grid layout:
   - Full hero image (card-img-top)
   - Destination badge + Category badge
   - Package name, duration (X nights/Y days)
   - Price per person with "onwards" label
   - Star rating + review count
   - "View Details" button → package_detail.html

**Note:** Packages page uses card GRID layout (not sidebar + list cards) — this is intentional; packages are more visual/inspirational vs transactional like flights/buses.

## package_detail.html
- Full-width banner image
- Package highlights / inclusions grid
- Day-by-day itinerary accordion
- Sticky booking widget (persons selector + date picker + CTA)

## package_booking.html — Status: **NEEDS REVIEW**
Check if this template has been upgraded to the production booking standard. If it looks like the old basic Bootstrap card layout, apply the same treatment as `bus_booking.html`:
- Purple/orange hero + step indicator
- Journey card (package name, destination, duration, date, persons)
- Passenger form + GST panel + 4-tab payment
- Sticky summary with price breakdown + promo + inclusions

---

## Blueprint: activities.py

### Routes
| Route | Method | Template | Notes |
|---|---|---|---|
| `/activities` | GET | `activities.html` | List tours & activities |
| `/activities/<id>` | GET | `activity_detail.html` | Activity detail |
| `/activities/<id>/book` | GET/POST | `activity_booking.html` | Activity booking |

## Activity Model

```python
class Activity(db.Model):
    id, name, city, category
    price               # Float (per person)
    duration_hrs        # Float
    image_url
    description
    max_participants
    available_days      # e.g. 'Daily' or 'Mon-Sat'
```

## Admin Management
- `/admin/activities` — CRUD for activities (admin_extended.py)
- `/admin/packages` — CRUD for packages (admin_extended.py)
