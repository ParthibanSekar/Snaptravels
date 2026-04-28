#!/bin/bash
# ============================================================
#  SnapTravels — Server Management Script
#  Usage:
#    bash snaptravels.sh start      → install deps + init DB + start server
#    bash snaptravels.sh stop       → stop the running server
#    bash snaptravels.sh restart    → stop then start
#    bash snaptravels.sh status     → check if server is running
#    bash snaptravels.sh logs       → tail the server logs
#    bash snaptravels.sh reset-db   → delete DB and re-seed from scratch
# ============================================================

# ── Config ──────────────────────────────────────────────────
PORT=${PORT:-8080}
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/venv"
PID_FILE="$APP_DIR/.snaptravels.pid"
LOG_FILE="$APP_DIR/.snaptravels.log"
DB_FILE="$APP_DIR/instance/snaptravels.db"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

# ── Colours ─────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ── Helper: check if server is running ──────────────────────
is_running() {
    [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

# ── clear_cache ──────────────────────────────────────────────
clear_cache() {
    info "Clearing Python bytecode cache..."
    find "$APP_DIR" -type d -name __pycache__ -not -path "*/venv/*" -exec rm -rf {} + 2>/dev/null
    find "$APP_DIR" -name "*.pyc" -not -path "*/venv/*" -delete 2>/dev/null
    success "Cache cleared."
}

# ── migrate_columns ──────────────────────────────────────────
# Adds any columns that are in models.py but missing from the live SQLite DB.
# Uses only Python's built-in sqlite3 — no Flask/venv needed.
migrate_columns() {
    info "Running column migrations (ALTER TABLE if needed)..."
    python3 - "$DB_FILE" <<'PYEOF'
import sys, sqlite3

DB   = sys.argv[1]
COLS = [
    # table          column            SQLite type
    ('activity',  'original_price',  'FLOAT'),
    ('activity',  'includes_json',   'TEXT'),
    ('train',     'train_type',      "VARCHAR(50) DEFAULT 'Express'"),
    ('train',     'run_days',        "VARCHAR(50) DEFAULT 'Daily'"),
    # 2FA columns
    ('user',      'totp_secret_enc', 'TEXT'),
    ('user',      'totp_enabled',    'BOOLEAN DEFAULT 0 NOT NULL'),
    ('user',      'totp_verified_at','DATETIME'),
    # ── FailureMode — Page Load additions ──────────────────────────
    ('failure_mode', 'page_load_webfont_failure',             'BOOLEAN NOT NULL DEFAULT 0'),
    ('failure_mode', 'page_load_ttfb_spike',                  'BOOLEAN NOT NULL DEFAULT 0'),
    ('failure_mode', 'page_load_cache_chaos',                 'BOOLEAN NOT NULL DEFAULT 0'),
    # ── FailureMode — Functionality additions ──────────────────────
    ('failure_mode', 'func_wrong_search',                     'BOOLEAN NOT NULL DEFAULT 0'),
    ('failure_mode', 'func_fake_soldout',                     'BOOLEAN NOT NULL DEFAULT 0'),
    ('failure_mode', 'func_date_picker_broken',               'BOOLEAN NOT NULL DEFAULT 0'),
    ('failure_mode', 'func_otp_invalid',                      'BOOLEAN NOT NULL DEFAULT 0'),
    ('failure_mode', 'func_email_chaos',                      'BOOLEAN NOT NULL DEFAULT 0'),
    ('failure_mode', 'func_maintenance_flood',                'BOOLEAN NOT NULL DEFAULT 0'),
    # ── FailureMode — Component additions ─────────────────────────
    ('failure_mode', 'component_break_autocomplete',          'BOOLEAN NOT NULL DEFAULT 0'),
    ('failure_mode', 'component_break_datepicker',            'BOOLEAN NOT NULL DEFAULT 0'),
    ('failure_mode', 'component_break_ratings',               'BOOLEAN NOT NULL DEFAULT 0'),
    ('failure_mode', 'component_break_loyalty',               'BOOLEAN NOT NULL DEFAULT 0'),
    # ── FailureMode — A/B Test Chaos (Section 4) ──────────────────
    ('failure_mode', 'ab_test_chaos',                         'BOOLEAN NOT NULL DEFAULT 0'),
    ('failure_mode', 'ab_test_login',                         'BOOLEAN NOT NULL DEFAULT 0'),
    ('failure_mode', 'ab_test_search',                        'BOOLEAN NOT NULL DEFAULT 0'),
    ('failure_mode', 'ab_test_booking',                       'BOOLEAN NOT NULL DEFAULT 0'),
    ('failure_mode', 'ab_test_profile',                       'BOOLEAN NOT NULL DEFAULT 0'),
    # ── FailureMode — Engine settings ─────────────────────────────
    ('failure_mode', 'chaos_intensity',                       'INTEGER NOT NULL DEFAULT 1'),
    ('failure_mode', 'webhook_url',                           'VARCHAR(500)'),
    # ── Booking — payment method ──────────────────────────────────
    ('booking',      'payment_method',                        "VARCHAR(20) DEFAULT 'card'"),
]

conn = sqlite3.connect(DB)
cur  = conn.cursor()
added = 0
for table, col, col_type in COLS:
    cur.execute(f"PRAGMA table_info({table})")
    if col not in [r[1] for r in cur.fetchall()]:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        print(f"  + {table}.{col}")
        added += 1
conn.commit()
conn.close()
print(f"Column migration done — {added} column(s) added.")
PYEOF
}

# ── kill_port ────────────────────────────────────────────────
kill_port() {
    local port=$1
    local pids
    pids=$(lsof -ti:"$port" 2>/dev/null)
    if [ -n "$pids" ]; then
        info "Freeing port $port (killing PID $pids)..."
        echo "$pids" | xargs kill -9 2>/dev/null
        sleep 1
    fi
}

# ── install_deps ─────────────────────────────────────────────
install_deps() {
    # Remove stale/broken venvs (e.g. copied from macOS dev machine)
    for STALE_VENV in "$VENV_DIR" "$APP_DIR/venv_new"; do
        if [ -d "$STALE_VENV" ]; then
            if [ ! -x "$STALE_VENV/bin/python" ]; then
                warn "Removing broken venv (missing python): $STALE_VENV"
                rm -rf "$STALE_VENV"
            elif ! "$STALE_VENV/bin/python" --version &>/dev/null; then
                warn "Removing broken venv (python not functional): $STALE_VENV"
                rm -rf "$STALE_VENV"
            elif head -1 "$STALE_VENV/bin/pip" 2>/dev/null | grep -q "Users/\|C:\\\\"; then
                warn "Removing dev-machine venv (wrong platform): $STALE_VENV"
                rm -rf "$STALE_VENV"
            fi
        fi
    done

    if [ ! -d "$VENV_DIR" ]; then
        info "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        success "Virtual environment created."
    fi

    info "Checking dependencies..."
    "$PIP" install --quiet --upgrade pip 2>/dev/null
    "$PIP" install --quiet -r "$APP_DIR/requirements.txt"
    success "Dependencies are up to date."
}

# ── init_db ──────────────────────────────────────────────────
init_db() {
    mkdir -p "$APP_DIR/instance"

    if [ -f "$DB_FILE" ] && [ -s "$DB_FILE" ]; then
        success "Existing database found."
        # Step 1 — add any missing columns (ALTER TABLE)
        migrate_columns
        # Step 2 — create any brand-new tables
        info "Running migration to add any new tables..."
        cd "$APP_DIR"
        "$PYTHON" - <<'PYEOF'
import sys, os
sys.path.insert(0, os.getcwd())
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
print("Table migration done.")
PYEOF
        # Step 3 — seed transport/activities/insurance if not yet present
        info "Seeding transport, activities and insurance data (if needed)..."
        cd "$APP_DIR"
        FLASK_APP=main.py "$PYTHON" -m flask seed-transport 2>/dev/null || true
        FLASK_APP=main.py "$PYTHON" -m flask seed-all 2>/dev/null || true
        # Step 4 — seed travel guide blog posts if none exist
        cd "$APP_DIR"
        "$PYTHON" - <<'PYEOF'
import sys, os; sys.path.insert(0, os.getcwd())
from app import create_app, db
app = create_app()
with app.app_context():
    from app.services.seeder import seed_blog
    seed_blog()
PYEOF
        # Step 5 — ensure images are in the correct Flask static folder
        if [ -d "$APP_DIR/static/images" ] && [ ! -f "$APP_DIR/app/static/images/.synced" ]; then
            info "Syncing images to app/static/images..."
            mkdir -p "$APP_DIR/app/static/images"
            cp -rn "$APP_DIR/static/images/." "$APP_DIR/app/static/images/" 2>/dev/null || true
            touch "$APP_DIR/app/static/images/.synced"
        fi
        # Step 5 — patch image paths for packages, activities and hotels
        info "Patching image paths..."
        "$PYTHON" "$APP_DIR/patch_images.py" 2>/dev/null || true
    else
        info "Initialising fresh database and seeding all data..."
        cd "$APP_DIR"
        "$PYTHON" - <<'PYEOF'
import sys, os
sys.path.insert(0, os.getcwd())
from app import create_app, db
from app.services.seeder import seed_database
app = create_app()
with app.app_context():
    db.create_all()
    seed_database()
print("Database ready.")
PYEOF
        # Ensure all columns exist even on fresh DB (handles race conditions)
        migrate_columns
        # Seed packages + transport on top of core seed
        cd "$APP_DIR"
        FLASK_APP=main.py "$PYTHON" -m flask seed-all 2>/dev/null || true
        FLASK_APP=main.py "$PYTHON" -m flask seed-transport 2>/dev/null || true
        # Seed travel guide blog posts
        cd "$APP_DIR"
        "$PYTHON" - <<'PYEOF'
import sys, os; sys.path.insert(0, os.getcwd())
from app import create_app, db
app = create_app()
with app.app_context():
    from app.services.seeder import seed_blog
    seed_blog()
PYEOF
        # Sync images to Flask static folder
        if [ -d "$APP_DIR/static/images" ]; then
            mkdir -p "$APP_DIR/app/static/images"
            cp -rn "$APP_DIR/static/images/." "$APP_DIR/app/static/images/" 2>/dev/null || true
            touch "$APP_DIR/app/static/images/.synced"
        fi
        # Patch image paths
        "$PYTHON" "$APP_DIR/patch_images.py" 2>/dev/null || true
        success "Database initialised and seeded."
    fi
}

# ── start ────────────────────────────────────────────────────
cmd_start() {
    echo ""
    echo -e "${BOLD}🚀  SnapTravels — Starting up${NC}"
    echo "    Port : $PORT"
    echo "    Dir  : $APP_DIR"
    echo ""

    if is_running; then
        warn "Server is already running (PID $(cat "$PID_FILE")). Use 'restart' to reload."
        exit 0
    fi

    # Load environment variables from .env (Site24x7 keys, PORT, etc.)
    if [ -f "$APP_DIR/.env" ]; then
        set -a
        source "$APP_DIR/.env" 2>/dev/null || true
        set +a
        success "Loaded environment from .env"
    else
        warn "No .env file found — Site24x7 APM/RUM keys will not be available."
    fi

    # Re-read PORT in case .env overrides it
    PORT=${PORT:-8080}

    # Free the port if something else is using it
    kill_port "$PORT"

    clear_cache
    install_deps
    init_db

    # Ensure logs directory exists before starting
    mkdir -p "$APP_DIR/logs"

    info "Starting Flask server on http://localhost:$PORT ..."
    cd "$APP_DIR"
    PORT=$PORT nohup "$PYTHON" main.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"

    for i in 1 2 3 4 5; do
        sleep 1
        if is_running && grep -q "Running on" "$LOG_FILE" 2>/dev/null; then
            break
        fi
    done

    if is_running; then
        echo ""
        success "Server started! (PID $(cat "$PID_FILE"))"
        echo ""
        echo -e "  ${BOLD}🌐  Open in browser:${NC}  http://localhost:$PORT"
        echo ""
        echo -e "  ${BOLD}Login credentials:${NC}"
        echo "    Admin  →  admin@snaptravels.online  /  Admin@123"
        echo "    User   →  parthiban@snaptravels.online  /  Test@123"
        echo ""
        echo -e "  Logs : bash snaptravels.sh logs"
        echo -e "  Stop : bash snaptravels.sh stop"
        echo ""
    else
        error "Server failed to start. Check logs:"
        tail -20 "$LOG_FILE"
        exit 1
    fi
}

# ── stop ─────────────────────────────────────────────────────
cmd_stop() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        info "Stopping server (PID $PID)..."
        kill "$PID" 2>/dev/null
        sleep 1
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" 2>/dev/null
        fi
        rm -f "$PID_FILE"
        success "Server stopped."
    else
        warn "Server is not running."
    fi
}

# ── restart ──────────────────────────────────────────────────
cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

# ── status ───────────────────────────────────────────────────
cmd_status() {
    if is_running; then
        success "Server is running (PID $(cat "$PID_FILE")) on http://localhost:$PORT"
    else
        warn "Server is NOT running."
    fi
}

# ── logs ─────────────────────────────────────────────────────
cmd_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        warn "No log file found. Start the server first."
    fi
}

# ── reset-db ─────────────────────────────────────────────────
cmd_reset_db() {
    warn "This will DELETE the existing database and re-seed from scratch."
    read -rp "Are you sure? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        cmd_stop 2>/dev/null
        rm -f "$DB_FILE" "$DB_FILE-journal" "$DB_FILE-wal" "$DB_FILE-shm"
        success "Database deleted."
        clear_cache
        install_deps
        info "Re-initialising database..."
        cd "$APP_DIR"
        "$PYTHON" - <<'PYEOF'
import sys, os
sys.path.insert(0, os.getcwd())
from app import create_app, db
from app.services.seeder import seed_database
app = create_app()
with app.app_context():
    db.create_all()
    seed_database()
print("Database re-seeded.")
PYEOF
        cd "$APP_DIR"
        FLASK_APP=main.py "$PYTHON" -m flask seed-all 2>/dev/null || true
        FLASK_APP=main.py "$PYTHON" -m flask seed-transport 2>/dev/null || true
        success "Database reset complete. Run 'bash snaptravels.sh start' to launch."
    else
        info "Reset cancelled."
    fi
}

# ── Router ───────────────────────────────────────────────────
case "${1:-help}" in
    start)    cmd_start   ;;
    stop)     cmd_stop    ;;
    restart)  cmd_restart ;;
    status)   cmd_status  ;;
    logs)     cmd_logs    ;;
    reset-db) cmd_reset_db ;;
    *)
        echo ""
        echo -e "${BOLD}Usage:${NC}  bash snaptravels.sh <command>"
        echo ""
        echo "  start      Clear cache + install deps + migrate DB + seed + start server"
        echo "  stop       Stop the running server"
        echo "  restart    Stop then start"
        echo "  status     Check if server is running"
        echo "  logs       Tail live server logs"
        echo "  reset-db   Wipe DB and re-seed everything from scratch"
        echo ""
        echo -e "  ${BOLD}Custom port:${NC}  PORT=9000 bash snaptravels.sh start"
        echo ""
        ;;
esac
