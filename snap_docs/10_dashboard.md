# SnapTravels — User Dashboard

## Blueprint: user_dashboard.py

All routes require `@login_required`.

| Route | Template | Description |
|---|---|---|
| `/dashboard` | `dashboard.html` | Main dashboard — stats, recent bookings, quick actions |
| `/my-bookings` | `my_bookings.html` | Full booking history with status filters |
| `/profile` | `profile.html` | Edit name, phone, profile photo |
| `/security` | `security.html` | Change password, 2FA settings, backup codes |
| `/wishlist` | `wishlist.html` | Saved flights/hotels/packages |
| `/travelers` | `travelers.html` | Saved traveler profiles (for quick checkout) |
| `/rewards` | `rewards.html` | Loyalty points / rewards page |

## Blueprint: trips.py

| Route | Template | Description |
|---|---|---|
| `/trips` | `trips.html` | Trip planner / itinerary builder |
| `/trips/new` | `trip_form.html` | Create new trip |
| `/trips/<id>` | `trip_detail.html` | View trip itinerary |
| `/trips/<id>/edit` | `trip_form.html` | Edit trip |

## Dashboard Page (dashboard.html)

**Sections:**
1. Welcome banner — user name + avatar initial
2. Stats row — Total Trips / Miles Flown / Hotels Stayed / Rewards Points (all dynamic from DB)
3. Recent Bookings table — last 5 bookings with status badges (Confirmed/Cancelled)
4. Quick Actions grid — Search Flights / Book Hotel / View Packages / Plan Trip
5. Wishlist preview — first 3 saved items
6. Upcoming trips from trip planner

## My Bookings (my_bookings.html)

- Filter tabs: All / Flights / Hotels / Buses / Trains / Cabs / Packages
- Each booking card shows:
  - Booking code (badge)
  - Item type icon + name/route
  - Date, passengers, total
  - Status badge (Confirmed=green / Cancelled=red / Pending=amber)
  - Action buttons: View Details / Download Ticket / Cancel

## Profile (profile.html)

- Form fields: Full Name, Phone, Date of Birth, Gender, Nationality
- Profile photo upload
- Email (readonly — cannot change email)

## Security (security.html)

- Change password form (current + new + confirm)
- 2FA section: enable TOTP / enable Email OTP / view/regenerate backup codes
- Recent login activity table (IP, device, timestamp)
- "Remember This Device" sessions list with revoke option

## Wishlist

- `POST /wishlist/toggle` (reviews.py blueprint) — adds/removes item
- Body: `{item_type: 'FLIGHT'/'HOTEL'/'PACKAGE', item_id: 123}`
- Wishlist model: `Wishlist(user_id, item_type, item_id)`

## Reviews

- `POST /reviews` — submit a review
- Fields: `item_type`, `item_id`, `rating` (1-5), `comment`
- Reviews displayed on hotel detail, package detail pages

## Admin — User Management

- `/admin/users` (admin_extended.py) — list all users, toggle role, view bookings per user
- `/admin/refunds` — process refund requests, change booking status to Cancelled
