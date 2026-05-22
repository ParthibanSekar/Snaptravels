"""
Safe migration: adds 4 corporate portal chaos columns to the failure_mode table.
Skips any column that already exists — safe to re-run at any time.
"""
import sqlite3, os, sys

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'snaptravels.db')

NEW_COLUMNS = [
    ('corp_chaos',             'BOOLEAN NOT NULL DEFAULT 0'),
    ('corp_auth_failure_rate', 'FLOAT NOT NULL DEFAULT 0.0'),
    ('corp_slow_ms',           'INTEGER NOT NULL DEFAULT 0'),
    ('corp_maintenance_rate',  'FLOAT NOT NULL DEFAULT 0.0'),
]

def migrate():
    if not os.path.exists(DB_PATH):
        print(f'[migrate_corp_chaos] DB not found at {DB_PATH} — skipping.')
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # Get existing columns
    cur.execute('PRAGMA table_info(failure_mode)')
    existing = {row[1] for row in cur.fetchall()}

    added = []
    for col_name, col_def in NEW_COLUMNS:
        if col_name in existing:
            print(f'[migrate_corp_chaos] Column "{col_name}" already exists — skipping.')
        else:
            cur.execute(f'ALTER TABLE failure_mode ADD COLUMN {col_name} {col_def}')
            added.append(col_name)
            print(f'[migrate_corp_chaos] Added column "{col_name}".')

    conn.commit()
    conn.close()

    if added:
        print(f'[migrate_corp_chaos] Done — added {len(added)} column(s): {", ".join(added)}')
    else:
        print('[migrate_corp_chaos] No changes needed.')

if __name__ == '__main__':
    migrate()
