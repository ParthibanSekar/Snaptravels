"""
migrate_mobile_chaos.py
-----------------------
One-time migration: adds the 9 Mobile App Chaos columns to the
failure_mode table (SQLite). Safe to run multiple times — skips
columns that already exist.

Usage (run from the project root on the server):
    python migrate_mobile_chaos.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'snaptravels.db')

NEW_COLUMNS = [
    ('mobile_chaos',               'BOOLEAN NOT NULL DEFAULT 0'),
    ('mobile_auth_failure_rate',   'FLOAT    NOT NULL DEFAULT 0.0'),
    ('mobile_search_slow_ms',      'INTEGER  NOT NULL DEFAULT 0'),
    ('mobile_search_empty_rate',   'FLOAT    NOT NULL DEFAULT 0.0'),
    ('mobile_booking_decline_rate','FLOAT    NOT NULL DEFAULT 0.0'),
    ('mobile_cancel_failure_rate', 'FLOAT    NOT NULL DEFAULT 0.0'),
    ('mobile_timeout_rate',        'FLOAT    NOT NULL DEFAULT 0.0'),
    ('mobile_rate_limit_rate',     'FLOAT    NOT NULL DEFAULT 0.0'),
    ('mobile_malform_rate',        'FLOAT    NOT NULL DEFAULT 0.0'),
]

def main():
    if not os.path.exists(DB_PATH):
        print(f'❌  Database not found at {DB_PATH}')
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # Get existing columns
    cur.execute('PRAGMA table_info(failure_mode)')
    existing = {row[1] for row in cur.fetchall()}

    added = []
    for col_name, col_def in NEW_COLUMNS:
        if col_name in existing:
            print(f'⚠️   Column already exists — skipping: {col_name}')
        else:
            cur.execute(f'ALTER TABLE failure_mode ADD COLUMN {col_name} {col_def}')
            added.append(col_name)
            print(f'✅  Added column: {col_name}')

    conn.commit()
    conn.close()

    if added:
        print(f'\n✅  Migration complete — {len(added)} column(s) added.')
    else:
        print('\nℹ️   Nothing to do — all columns already present.')

if __name__ == '__main__':
    main()
