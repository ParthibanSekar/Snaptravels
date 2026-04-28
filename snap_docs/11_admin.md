# SnapTravels — Admin Panel

## Access

- Role: `admin` only (`@roles_required('admin')`)
- Login as: `admin@snaptravels.online` / `Admin@123`
- Base URL: `/admin/`

---

## Blueprint: admin.py — Core Admin

| Route | Template | Description |
|---|---|---|
| `/admin/` | `admin/dashboard.html` | Stats overview (total users, bookings, revenue, chaos state) |
| `/admin/flights` | `admin/flights.html` | List + CRUD flights |
| `/admin/flights/new` | `admin/flight_form.html` | Add new flight |
| `/admin/flights/<id>/edit` | `admin/flight_form.html` | Edit flight |
| `/admin/flights/<id>/delete` | — (POST) | Delete flight |
| `/admin/hotels` | `admin/hotels.html` | List + CRUD hotels |
| `/admin/hotels/new` | `admin/hotel_form.html` | Add hotel |
| `/admin/hotels/<id>/edit` | `admin/hotel_form.html` | Edit hotel |
| `/admin/bookings` | `admin/bookings.html` | All bookings, filter by status/type |
| `/admin/bookings/<id>` | `admin/booking_detail.html` | Booking detail + status change |

---

## Blueprint: admin_extended.py — Extended Admin

| Route | Description |
|---|---|
| `/admin/users` | List all users, search, role toggle (promote/demote) |
| `/admin/users/<id>` | User detail — profile + all their bookings |
| `/admin/refunds` | Refund requests — cancel booking + process refund |
| `/admin/revenue` | Revenue analytics — total revenue, by mode, by period, charts |
| `/admin/packages` | CRUD for holiday packages |
| `/admin/activities` | CRUD for tours & activities |
| `/admin/promos` | CRUD for promo codes |
| `/admin/promos/new` | Create promo code (PERCENT or FLAT, with expiry + usage limit) |
| `/admin/blog` | CRUD for blog posts |
| `/admin/insurance` | Manage insurance plans |

---

## Admin Dashboard (admin/dashboard.html)

**Stats cards:**
- Total Users / New Today
- Total Bookings / Revenue (this month)
- Active Chaos Modes (red badge if any active)
- Avg Booking Value

**Charts:** Revenue over last 30 days (line chart), Bookings by mode (pie/bar)

**Recent Bookings table** — last 10 bookings with quick status update

---

## PromoCode Management

PromoCode model:
```python
class PromoCode(db.Model):
    code            # Unique string e.g. "SAVE10"
    discount_type   # 'PERCENT' or 'FLAT'
    discount_value  # Float (10 = 10% or ₹10 flat)
    max_uses        # Integer (0 = unlimited)
    times_used      # Integer
    expiry_date     # Date
    min_amount      # Float — minimum order amount to apply
    is_active       # Boolean
```

Validation route (used by frontend booking pages):
- `POST /promo/validate` (reviews.py) — returns `{valid, discount, final, message}`

---

## Admin Template Location

All admin templates are in `app/templates/admin/`:
- `dashboard.html` — Admin home
- `flights.html` / `flight_form.html` — Flight management
- `hotels.html` / `hotel_form.html` — Hotel management
- `bookings.html` / `booking_detail.html` — Booking management
- `users.html` — User list
- `revenue.html` — Revenue analytics
- `chaos.html` — Chaos control panel (see `12_chaos.md`)

---

## Admin Navigation (base layout)

Admin pages extend `layouts/admin_base.html` (or similar) which includes:
- Sidebar with all admin nav links
- Breadcrumb trail
- Flash message display
- Active chaos indicator (red badge in sidebar if any mode is active)

---

## Bookings Data Model (for admin queries)

```python
class Booking(db.Model):
    id, booking_code    # booking_code = unique 8-char alphanumeric
    user_id
    total               # Float — final amount paid
    status              # 'confirmed' / 'cancelled' / 'pending'
    payment_method      # 'card' / 'upi' / 'netbanking' / 'wallet' / 'cash'
    created_at          # DateTime

class BookingItem(db.Model):
    booking_id
    item_type   # 'FLIGHT' / 'HOTEL' / 'BUS' / 'TRAIN' / 'CAB' / 'PACKAGE'
    item_id     # FK to the respective model
    quantity    # passengers/nights/persons
    unit_price  # price at time of booking
```
