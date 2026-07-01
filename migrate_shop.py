"""
Safe migration: creates shop tables (product, cart_item, shop_order, shop_order_item)
and seeds 20 sample products across 4 categories.
Safe to re-run — skips existing tables and already-seeded products.
"""
import sqlite3, os, json, sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'snaptravels.db')

TABLES = {
    'product': """
        CREATE TABLE IF NOT EXISTS product (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            category        TEXT NOT NULL,
            subcategory     TEXT,
            description     TEXT,
            price           REAL NOT NULL,
            original_price  REAL,
            image_url       TEXT,
            badge           TEXT,
            sizes_json      TEXT DEFAULT '[]',
            in_stock        INTEGER NOT NULL DEFAULT 1,
            rating          REAL NOT NULL DEFAULT 4.2,
            review_count    INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT
        )
    """,
    'cart_item': """
        CREATE TABLE IF NOT EXISTS cart_item (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT,
            user_id     INTEGER REFERENCES user(id),
            product_id  INTEGER NOT NULL REFERENCES product(id),
            size        TEXT,
            quantity    INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT
        )
    """,
    'shop_order': """
        CREATE TABLE IF NOT EXISTS shop_order (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code       TEXT UNIQUE NOT NULL,
            user_id          INTEGER REFERENCES user(id),
            customer_name    TEXT NOT NULL,
            customer_email   TEXT NOT NULL,
            customer_phone   TEXT,
            shipping_address TEXT NOT NULL,
            total_amount     REAL NOT NULL,
            payment_method   TEXT DEFAULT 'card',
            status           TEXT DEFAULT 'CONFIRMED',
            created_at       TEXT
        )
    """,
    'shop_order_item': """
        CREATE TABLE IF NOT EXISTS shop_order_item (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id     INTEGER NOT NULL REFERENCES shop_order(id),
            product_id   INTEGER NOT NULL REFERENCES product(id),
            product_name TEXT NOT NULL,
            size         TEXT,
            quantity     INTEGER NOT NULL,
            unit_price   REAL NOT NULL
        )
    """,
}

PRODUCTS = [
    # (name, category, subcategory, description, price, original_price, image_url, badge, sizes_json, rating, review_count)

    # ── Travel Clothing ──────────────────────────────────────────────────
    ('DryFit Trek Tee', 'clothing', 'Tops',
     'Lightweight moisture-wicking tee perfect for long haul travel and trekking. Anti-odour fabric keeps you fresh.',
     799, 1299, 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&q=80',
     'Bestseller', '["XS","S","M","L","XL","XXL"]', 4.6, 312),

    ('Breeze Travel Dress', 'clothing', 'Dresses',
     'Wrinkle-resistant, breathable travel dress. Looks great from airport to dinner. Available in solid colours.',
     1499, 2199, 'https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=600&q=80',
     'New', '["XS","S","M","L","XL"]', 4.5, 187),

    ('WindShield Jacket', 'clothing', 'Outerwear',
     'Packable windproof jacket with a hidden hood. Folds into its own pocket — weighs just 280g.',
     2999, 4499, 'https://images.unsplash.com/photo-1551698618-1dfe5d97d256?w=600&q=80',
     'Sale', '["S","M","L","XL","XXL"]', 4.7, 428),

    ('FlexCore Travel Pants', 'clothing', 'Bottoms',
     '4-way stretch trousers with hidden zip pockets. Quick-dry fabric, smart enough for meetings.',
     1799, None, 'https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=600&q=80',
     None, '["28","30","32","34","36","38"]', 4.4, 203),

    ('Merino Wool Henley', 'clothing', 'Tops',
     'Temperature-regulating merino wool henley. Perfect for layering on flights and cold destinations.',
     2499, 3299, 'https://images.unsplash.com/photo-1618354691373-d851c5c3a990?w=600&q=80',
     'Sale', '["XS","S","M","L","XL"]', 4.8, 156),

    ('Compression Leggings', 'clothing', 'Activewear',
     'High-waist compression leggings with phone pocket. Ideal for long flights and hikes.',
     1299, None, 'https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=600&q=80',
     'New', '["XS","S","M","L","XL"]', 4.3, 94),

    # ── Bags & Luggage ───────────────────────────────────────────────────
    ('AeroGlide Cabin Trolley', 'bags', 'Luggage',
     '20-inch hardshell spinner trolley. TSA-approved lock, fits in all overhead bins. 36L capacity.',
     5999, 8999, 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&q=80',
     'Bestseller', '["One Size"]', 4.7, 521),

    ('TrailBlazer 40L Backpack', 'bags', 'Backpacks',
     'Ventilated 40L trekking backpack with laptop sleeve, rain cover and ergonomic hip belt.',
     3499, 4999, 'https://images.unsplash.com/photo-1622260614927-f6e2ecaaf5a0?w=600&q=80',
     'Sale', '["One Size"]', 4.6, 389),

    ('SlimPack Day Bag', 'bags', 'Backpacks',
     'Compact 18L anti-theft backpack with USB charging port and hidden back pocket.',
     1999, None, 'https://images.unsplash.com/photo-1581605405669-fcdf81165afa?w=600&q=80',
     'New', '["One Size"]', 4.4, 211),

    ('Organiser Pouch Set (3-in-1)', 'bags', 'Pouches',
     'Set of 3 packing cubes in S/M/L. Compression zips keep clothes compact and wrinkle-free.',
     899, 1299, 'https://images.unsplash.com/photo-1584534736773-6fd07b2b1b97?w=600&q=80',
     'Sale', '["One Size"]', 4.5, 634),

    ('Crossbody Travel Sling', 'bags', 'Sling Bags',
     'RFID-blocking sling bag with slash-proof strap. Holds passport, phone, cards and a water bottle.',
     1499, None, 'https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=600&q=80',
     None, '["One Size"]', 4.3, 178),

    # ── Travel Accessories ───────────────────────────────────────────────
    ('Universal Travel Adapter', 'accessories', 'Electronics',
     'All-in-one adapter for 150+ countries. 4 USB ports + 1 USB-C PD. Compact and surge-protected.',
     1199, 1799, 'https://images.unsplash.com/photo-1598759003894-e5ca1f2c9e36?w=600&q=80',
     'Bestseller', '["One Size"]', 4.8, 892),

    ('Memory Foam Neck Pillow', 'accessories', 'Comfort',
     'Ergonomic memory foam neck pillow with snap closure. Compresses to 1/3 its size in carry pouch.',
     799, None, 'https://images.unsplash.com/photo-1559599238-308793637427?w=600&q=80',
     None, '["One Size"]', 4.5, 443),

    ('Contour Sleep Mask', 'accessories', 'Comfort',
     '3D contoured sleep mask with total blackout. Adjustable strap, includes ear plugs.',
     449, 699, 'https://images.unsplash.com/photo-1541781774459-bb2af2f05b55?w=600&q=80',
     'Sale', '["One Size"]', 4.4, 267),

    ('TSA Combo Lock (2-pack)', 'accessories', 'Security',
     'TSA-approved resettable combination lock. Zinc alloy shackle. Set your own 3-digit code.',
     599, None, 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&q=80',
     'New', '["One Size"]', 4.6, 318),

    ('Dry Bag 10L', 'accessories', 'Outdoors',
     'Waterproof roll-top dry bag. Float test certified. Great for beach days, kayaking and rain.',
     699, 999, 'https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=600&q=80',
     'Sale', '["One Size"]', 4.3, 142),

    # ── Footwear ─────────────────────────────────────────────────────────
    ('Summit Trek Shoes', 'footwear', 'Trekking',
     'Mid-cut waterproof trekking shoes with Vibram sole. Breathable mesh upper, ankle support.',
     4999, 6999, 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80',
     'Bestseller', '["6","7","8","9","10","11","12"]', 4.7, 376),

    ('CloudWalk Travel Sneakers', 'footwear', 'Casual',
     'Ultra-lightweight travel sneakers. Memory foam insole, foldable heel for easy packing.',
     2799, 3999, 'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600&q=80',
     'New', '["6","7","8","9","10","11"]', 4.5, 234),

    ('FlipFlop Pro', 'footwear', 'Sandals',
     'Cushioned flip flops with non-slip grip. Anti-microbial footbed — perfect for hostels and pools.',
     499, 799, 'https://images.unsplash.com/photo-1562273138-f46be4ebdf33?w=600&q=80',
     'Sale', '["5","6","7","8","9","10","11"]', 4.2, 521),

    ('AeroStep Travel Sandal', 'footwear', 'Sandals',
     'Adjustable sport sandal with arch support. Quick-dry straps, suitable for city walks and light trails.',
     1599, None, 'https://images.unsplash.com/photo-1491553895911-0055eca6402d?w=600&q=80',
     None, '["5","6","7","8","9","10","11","12"]', 4.4, 189),
]


EXTRA_COLUMNS = [
    # (table, column, definition)
    ('product',    'stock_qty',      'INTEGER NOT NULL DEFAULT 100'),
    ('shop_order', 'cancel_reason',  'TEXT'),
    ('shop_order', 'return_reason',  'TEXT'),
    ('shop_order', 'actioned_at',    'TEXT'),
]

def migrate():
    if not os.path.exists(DB_PATH):
        print(f'[migrate_shop] DB not found at {DB_PATH} — skipping.')
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    now  = datetime.utcnow().isoformat()

    # Create tables
    for tname, ddl in TABLES.items():
        cur.execute(ddl)
        print(f'[migrate_shop] Table "{tname}" ensured.')

    # Add new columns safely
    for table, col, defn in EXTRA_COLUMNS:
        cur.execute(f'PRAGMA table_info({table})')
        existing = {row[1] for row in cur.fetchall()}
        if col not in existing:
            cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {defn}')
            print(f'[migrate_shop] Added column {table}.{col}')
        else:
            print(f'[migrate_shop] Column {table}.{col} already exists — skipping.')

    # Seed products (skip if already seeded)
    cur.execute('SELECT COUNT(*) FROM product')
    existing = cur.fetchone()[0]
    if existing >= len(PRODUCTS):
        print(f'[migrate_shop] Products already seeded ({existing} rows) — skipping.')
    else:
        for p in PRODUCTS:
            name, cat, subcat, desc, price, orig, img, badge, sizes, rating, rev_count = p
            cur.execute('''
                INSERT OR IGNORE INTO product
                (name,category,subcategory,description,price,original_price,image_url,
                 badge,sizes_json,in_stock,rating,review_count,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,1,?,?,?)
            ''', (name, cat, subcat, desc, price, orig, img, badge, sizes, rating, rev_count, now))
        conn.commit()
        print(f'[migrate_shop] Seeded {len(PRODUCTS)} products.')

    conn.commit()
    conn.close()
    print('[migrate_shop] Done.')


if __name__ == '__main__':
    migrate()
