#!/usr/bin/env python3
"""
migrate_db.py — Safely migrate an existing SnapTravels database.

Steps performed:
  1. CREATE TABLE IF NOT EXISTS for any brand-new models (db.create_all)
  2. ALTER TABLE ADD COLUMN for any new columns on existing tables
     (SQLite does not support adding columns via create_all)

Safe to run multiple times — existing data and tables are never dropped.

Usage:
    python migrate_db.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
from app import create_app, db

# ── Columns to add when they are missing ─────────────────────────────────────
# Format: (table_name, column_name, sqlite_type_definition)
NEW_COLUMNS = [
    # Activity — new pricing / detail columns
    ('activity', 'original_price',  'FLOAT'),
    ('activity', 'includes_json',   'TEXT'),
    # Train — classification columns
    ('train',    'train_type',      "VARCHAR(50) DEFAULT 'Express'"),
    ('train',    'run_days',        "VARCHAR(50) DEFAULT 'Daily'"),
]

# ─────────────────────────────────────────────────────────────────────────────

app = create_app()

with app.app_context():
    db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
    if not os.path.isabs(db_path):
        db_path = os.path.join(app.root_path, '..', db_path)
    db_path = os.path.normpath(db_path)

    # 1. Create any completely new tables
    print("Step 1: Creating missing tables (db.create_all)…")
    db.create_all()

    # 2. Add missing columns to existing tables via raw SQLite
    print("Step 2: Adding missing columns…")
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    added = 0
    for table, column, col_type in NEW_COLUMNS:
        cur.execute(f"PRAGMA table_info({table})")
        existing = [row[1] for row in cur.fetchall()]
        if column not in existing:
            print(f"  ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            added += 1
        else:
            print(f"  {table}.{column} already exists — skipped")

    conn.commit()
    conn.close()

    # 3. Summary
    inspector = db.inspect(db.engine)
    tables = sorted(inspector.get_table_names())
    print(f"\nDone. {added} column(s) added.")
    print(f"Tables in DB ({len(tables)}): {', '.join(tables)}")
    print("\nNow run:  flask seed-transport   (to populate new rows with demo data)")
