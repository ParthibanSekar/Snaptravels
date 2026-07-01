"""
Safe migration: adds 5 ad popup chaos columns to the failure_mode table.
Safe to re-run — skips columns that already exist.
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'snaptravels.db')

NEW_COLUMNS = [
    ('ad_popup_chaos',          'BOOLEAN NOT NULL DEFAULT 0'),
    ('ad_popup_rate',           'FLOAT NOT NULL DEFAULT 0.3'),
    ('ad_popup_delay_ms',       'INTEGER NOT NULL DEFAULT 1500'),
    ('ad_popup_close_delay_ms', 'INTEGER NOT NULL DEFAULT 0'),
    ('ad_popup_target_pages',   "TEXT NOT NULL DEFAULT '[\"all\"]'"),
]

def migrate():
    if not os.path.exists(DB_PATH):
        print(f'[migrate_ad_popup] DB not found at {DB_PATH} — skipping.')
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute('PRAGMA table_info(failure_mode)')
    existing = {row[1] for row in cur.fetchall()}

    added = []
    for col_name, col_def in NEW_COLUMNS:
        if col_name in existing:
            print(f'[migrate_ad_popup] Column "{col_name}" already exists — skipping.')
        else:
            cur.execute(f'ALTER TABLE failure_mode ADD COLUMN {col_name} {col_def}')
            added.append(col_name)
            print(f'[migrate_ad_popup] Added column "{col_name}".')

    conn.commit()
    conn.close()
    if added:
        print(f'[migrate_ad_popup] Done — added {len(added)} column(s).')
    else:
        print('[migrate_ad_popup] No changes needed.')

if __name__ == '__main__':
    migrate()
