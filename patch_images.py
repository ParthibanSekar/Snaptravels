#!/usr/bin/env python3
"""
SnapTravels — Image Path Patcher
Updates existing Package and Activity records in the database
to point to the local static images.

Run from the project root:
    python3 patch_images.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Package, Activity, Hotel

app = create_app()

PACKAGE_IMAGES = {
    'goa-beach-getaway':     '/static/images/packages/package-goa.jpg',
    'manali-snowscape':      '/static/images/packages/package-himalayas.jpg',
    'kerala-backwaters':     '/static/images/packages/package-kerala.jpg',
    'rajasthan-royal':       '/static/images/packages/package-rajasthan.jpg',
    'maldives-luxury':       '/static/images/packages/package-international.jpg',
    'bali-discovery':        '/static/images/packages/package-international.jpg',
}

# Category → image mapping for activities
ACTIVITY_CATEGORY_IMAGES = {
    'Water Sports': '/static/images/activities/beach.jpg',
    'Adventure':    '/static/images/activities/trekking.jpg',
    'Cultural':     '/static/images/activities/heritage.jpg',
    'Sightseeing':  '/static/images/activities/activity-1.jpg',
    'Food':         '/static/images/activities/activity-2.jpg',
    'Wildlife':     '/static/images/activities/wildlife.jpg',
}

# Round-robin hotel images
HOTEL_IMAGES = [
    '/static/images/hotels/hotel-1.jpg',
    '/static/images/hotels/hotel-2.jpg',
    '/static/images/hotels/hotel-3.jpg',
    '/static/images/hotels/hotel-4.jpg',
]

with app.app_context():
    # ── Packages ──────────────────────────────────────────────────────
    updated_p = 0
    for pkg in Package.query.all():
        new_img = PACKAGE_IMAGES.get(pkg.slug)
        if new_img and pkg.image_path != new_img:
            pkg.image_path = new_img
            updated_p += 1

    # ── Activities ────────────────────────────────────────────────────
    updated_a = 0
    for act in Activity.query.all():
        new_img = ACTIVITY_CATEGORY_IMAGES.get(act.category, '/static/images/activities/activity-1.jpg')
        if not act.image_path or act.image_path != new_img:
            act.image_path = new_img
            updated_a += 1

    # ── Hotels (only patch ones that still point to /assets/ or are empty) ──
    updated_h = 0
    for i, hotel in enumerate(Hotel.query.order_by(Hotel.id).all()):
        if not hotel.image_path or hotel.image_path.startswith('/assets/'):
            hotel.image_path = HOTEL_IMAGES[i % len(HOTEL_IMAGES)]
            updated_h += 1

    db.session.commit()
    print(f"✓  Packages updated : {updated_p}")
    print(f"✓  Activities updated: {updated_a}")
    print(f"✓  Hotels updated   : {updated_h}")
    print("Done! Restart the server to see changes.")
