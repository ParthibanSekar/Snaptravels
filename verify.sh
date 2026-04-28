#!/bin/bash
# ============================================================
#  SnapTravels — Post-Deployment Verification
#  Run after starting the app to check everything is working.
#
#  Usage:  bash verify.sh [port]
#  Default port: 5000 (Flask direct) or 8080 (via Nginx)
# ============================================================

PORT=${1:-5000}
BASE="http://localhost:$PORT"
PASS=0
FAIL=0
WARN=0

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

pass() { echo -e "  ${GREEN}[PASS]${NC} $*"; PASS=$((PASS+1)); }
fail() { echo -e "  ${RED}[FAIL]${NC} $*"; FAIL=$((FAIL+1)); }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $*"; WARN=$((WARN+1)); }

APP_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo -e "${BOLD}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   SnapTravels — Post-Deployment Verification      ║${NC}"
echo -e "${BOLD}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

# ══════════════════════════════════════════════════════════════
#  1. Environment
# ══════════════════════════════════════════════════════════════
echo -e "${CYAN}── Environment ──────────────────────────────────────${NC}"

if [ -f "$APP_DIR/.env" ]; then
    pass ".env file exists"
    # Check for broken .env (meeting notes, non-shell lines)
    if grep -qP '^[^#=\s].*\s' "$APP_DIR/.env" 2>/dev/null | head -1; then
        warn ".env may have non-shell lines — check for stray text"
    fi
else
    fail ".env file missing — create one from .env.example"
fi

if grep -q "S247_LICENSE_KEY=.\+" "$APP_DIR/.env" 2>/dev/null; then
    pass "S247_LICENSE_KEY is set"
else
    warn "S247_LICENSE_KEY is empty — APM won't work"
fi

if grep -q "SITE24X7_RUM_APP_KEY=.\+" "$APP_DIR/.env" 2>/dev/null; then
    pass "SITE24X7_RUM_APP_KEY is set"
else
    warn "SITE24X7_RUM_APP_KEY is empty — RUM won't work"
fi

if [ -d "$APP_DIR/venv" ] && [ -x "$APP_DIR/venv/bin/python" ]; then
    pass "Python venv exists and is functional"
else
    fail "Python venv missing or broken — run: bash snaptravels.sh start"
fi

# ══════════════════════════════════════════════════════════════
#  2. App Health
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}── App Health ───────────────────────────────────────${NC}"

HEALTH=$(curl -s --max-time 5 "$BASE/health" 2>/dev/null)
if [ -n "$HEALTH" ]; then
    pass "App responding on port $PORT"
else
    fail "App NOT responding on port $PORT — is it running?"
    echo ""
    echo -e "  ${RED}Cannot continue without the app running.${NC}"
    echo "  Start it with: PORT=$PORT bash snaptravels.sh start"
    echo ""
    exit 1
fi

# Check key pages
for page in "/" "/flights" "/hotels" "/trains/" "/buses/" "/cabs/" "/activities/" "/packages/" "/insurance/" "/login"; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BASE$page")
    if [ "$STATUS" = "200" ] || [ "$STATUS" = "302" ]; then
        pass "GET $page → $STATUS"
    else
        fail "GET $page → $STATUS"
    fi
done

# Admin pages (may redirect to login — 302 is ok)
for page in "/admin/" "/admin/chaos/" "/admin/chaos/auto" "/admin/chaos/docs"; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BASE$page")
    if [ "$STATUS" = "200" ] || [ "$STATUS" = "302" ]; then
        pass "GET $page → $STATUS"
    else
        fail "GET $page → $STATUS"
    fi
done

# State JSON (unauthenticated)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BASE/admin/chaos/state.json")
if [ "$STATUS" = "200" ]; then
    pass "Chaos state.json → 200 (unauthenticated OK)"
else
    fail "Chaos state.json → $STATUS"
fi

# ══════════════════════════════════════════════════════════════
#  3. RUM Beacon
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}── RUM (Real User Monitoring) ───────────────────────${NC}"

RUM_CHECK=$(curl -s --max-time 5 "$BASE/" | grep -o "site24x7rum")
if [ -n "$RUM_CHECK" ]; then
    pass "RUM beacon found in HTML"
    RUM_KEY=$(curl -s --max-time 5 "$BASE/" | grep -oP "appKey=.*?s247r.*?'\\K[^']+")
    if [ -n "$RUM_KEY" ]; then
        pass "RUM App Key: ${RUM_KEY:0:12}..."
    fi
else
    fail "RUM beacon NOT found in HTML — check SITE24X7_RUM_APP_KEY in .env"
fi

# ══════════════════════════════════════════════════════════════
#  4. APM Agent
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}── APM (Application Performance Monitoring) ─────────${NC}"

if [ -f "$APP_DIR/.snaptravels.log" ]; then
    if grep -qi "APM.*initialised\|APM.*initialized\|agent initialized" "$APP_DIR/.snaptravels.log" 2>/dev/null; then
        pass "APM agent initialized (found in startup log)"
    else
        fail "APM agent NOT initialized — check S247_LICENSE_KEY in .env"
    fi

    if grep -qi "Successfully pushed data\|Successfully constructed" "$APP_DIR/.snaptravels.log" 2>/dev/null; then
        pass "APM data flowing to Data Exporter"
    else
        warn "No APM data push logged yet — may need a few minutes"
    fi
else
    warn "No .snaptravels.log found — can't check APM status"
fi

# Check apminsight installed
if [ -x "$APP_DIR/venv/bin/pip" ]; then
    if "$APP_DIR/venv/bin/pip" show apminsight >/dev/null 2>&1; then
        APM_VER=$("$APP_DIR/venv/bin/pip" show apminsight 2>/dev/null | grep "Version:" | awk '{print $2}')
        pass "apminsight package installed (v$APM_VER)"
    else
        fail "apminsight package NOT installed — run: venv/bin/pip install apminsight"
    fi
fi

# Check Data Exporter
if pgrep -f "S247DataExporter\|s247DataExporter" >/dev/null 2>&1; then
    pass "Data Exporter service is running"
else
    fail "Data Exporter NOT running — APM data can't reach Site24x7"
    echo "       Install: bash site24x7_config.sh --license-key <YOUR_KEY>"
fi

# ══════════════════════════════════════════════════════════════
#  5. Nginx
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}── Nginx ────────────────────────────────────────────${NC}"

if command -v nginx &>/dev/null; then
    pass "Nginx is installed"
    if systemctl is-active nginx >/dev/null 2>&1; then
        pass "Nginx service is running"
    else
        fail "Nginx is installed but NOT running — run: systemctl start nginx"
    fi

    if [ -f /etc/nginx/sites-available/snaptravels ]; then
        pass "Nginx config exists at /etc/nginx/sites-available/snaptravels"
        NGX_PORT=$(grep -oP 'listen\s+\K\d+' /etc/nginx/sites-available/snaptravels | head -1)
        NGX_PROXY=$(grep -oP 'proxy_pass\s+http://127\.0\.0\.1:\K\d+' /etc/nginx/sites-available/snaptravels | head -1)
        pass "Nginx listens on :$NGX_PORT → proxies to :$NGX_PROXY"

        # Test Nginx is proxying
        NGX_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:$NGX_PORT/")
        if [ "$NGX_STATUS" = "200" ] || [ "$NGX_STATUS" = "302" ]; then
            pass "Nginx proxy working: localhost:$NGX_PORT → $NGX_STATUS"
        else
            fail "Nginx proxy NOT working: localhost:$NGX_PORT → $NGX_STATUS"
        fi
    else
        fail "Nginx config missing — run: bash setup_nginx.sh"
    fi
else
    warn "Nginx not installed — app accessible only on direct port"
fi

# ══════════════════════════════════════════════════════════════
#  6. Database
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}── Database ─────────────────────────────────────────${NC}"

DB_FILE="$APP_DIR/instance/snaptravels.db"
if [ -f "$DB_FILE" ]; then
    DB_SIZE=$(du -h "$DB_FILE" | awk '{print $1}')
    pass "Database exists ($DB_SIZE)"

    # Check key tables
    TABLES=$(sqlite3 "$DB_FILE" ".tables" 2>/dev/null)
    for tbl in user flight hotel booking booking_item failure_mode chaos_event; do
        if echo "$TABLES" | grep -qw "$tbl"; then
            pass "Table '$tbl' exists"
        else
            fail "Table '$tbl' MISSING"
        fi
    done
else
    fail "Database file not found at $DB_FILE"
fi

# ══════════════════════════════════════════════════════════════
#  Summary
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════${NC}"
TOTAL=$((PASS + FAIL + WARN))
echo -e "  ${GREEN}PASS: $PASS${NC}  ${RED}FAIL: $FAIL${NC}  ${YELLOW}WARN: $WARN${NC}  (Total: $TOTAL checks)"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "  ${GREEN}${BOLD}✓ All critical checks passed — ready for production!${NC}"
else
    echo -e "  ${RED}${BOLD}✗ $FAIL check(s) failed — fix before going live.${NC}"
fi
echo ""
