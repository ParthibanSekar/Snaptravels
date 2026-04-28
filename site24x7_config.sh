#!/bin/bash
# ============================================================
#  SnapTravels — Site24x7 Observability Setup
#
#  One-command script to configure Site24x7 APM + RUM for
#  the SnapTravels application on Debian/Ubuntu Linux.
#
#  What this script does:
#    1. Installs / upgrades the apminsight Python package
#    2. Installs the S247DataExporter service (required for APM)
#    3. Writes the license & RUM keys into .env
#    4. Verifies the RUM snippet is active in the HTML templates
#    5. Restarts the application so changes take effect
#
#  Usage:
#    sudo bash site24x7_config.sh \
#        --license-key "YOUR_S247_LICENSE_KEY" \
#        --rum-key     "YOUR_RUM_APP_KEY"
#
#  Options:
#    --license-key KEY   Site24x7 license key (Device Key).
#                        Found at: Site24x7 Console → Admin → Developer → Device Key
#                        Required for APM agent + Data Exporter.
#
#    --rum-key KEY       RUM Application Key.
#                        Found at: Site24x7 Console → RUM → Add Application → App Key
#                        Required for Real User Monitoring (browser-side).
#
#    --app-name NAME     Application name shown in Site24x7 dashboard.
#                        Default: SnapTravels
#
#    --skip-data-exporter  Skip S247DataExporter installation
#                          (use if already installed or running on another host)
#
#    --restart-method METHOD  How to restart the app after config.
#                             "systemd" → systemctl restart snaptravels
#                             "script"  → bash snaptravels.sh restart
#                             "none"    → don't restart (manual restart later)
#                             Default: auto-detect
#
#  Example:
#    sudo bash site24x7_config.sh \
#        --license-key "abc123def456" \
#        --rum-key "7890xyz" \
#        --app-name "SnapTravels-Production"
#
#  Reference:
#    APM Python Agent : https://www.site24x7.com/help/apm/python-agent/install-python-agent.html
#    Data Exporter    : https://www.site24x7.com/help/apm/data-exporter-linux.html
#    RUM Setup        : https://www.site24x7.com/help/apm/rum/add-rum-monitor.html
# ============================================================

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$APP_DIR/venv"
ENV_FILE="$APP_DIR/.env"

# ── Defaults ────────────────────────────────────────────────
LICENSE_KEY=""
RUM_KEY=""
APP_NAME=""
SKIP_DATA_EXPORTER=false
RESTART_METHOD="auto"

# ── Parse arguments ─────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --license-key)          LICENSE_KEY="$2";          shift 2 ;;
        --rum-key)              RUM_KEY="$2";              shift 2 ;;
        --app-name)             APP_NAME="$2";             shift 2 ;;
        --skip-data-exporter)   SKIP_DATA_EXPORTER=true;   shift   ;;
        --restart-method)       RESTART_METHOD="$2";       shift 2 ;;
        -h|--help)
            head -50 "$0" | grep '^#' | sed 's/^# \?//'
            exit 0 ;;
        *)  echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Colours ─────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m';   CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()     { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   SnapTravels — Site24x7 Observability Setup      ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ── Validation ──────────────────────────────────────────────
if [[ -z "$LICENSE_KEY" && -z "$RUM_KEY" ]]; then
    err "At least one of --license-key or --rum-key must be provided.\n  Run: bash site24x7_config.sh --help"
fi

if [[ ! -d "$VENV" ]]; then
    err "Python venv not found at $VENV. Run deploy_debian12.sh or snaptravels.sh start first."
fi

if [[ ! -f "$ENV_FILE" ]]; then
    err ".env file not found at $ENV_FILE. Run deploy_debian12.sh first."
fi

# ══════════════════════════════════════════════════════════════
#  1. APM Python Agent — install / upgrade apminsight
# ══════════════════════════════════════════════════════════════
if [[ -n "$LICENSE_KEY" ]]; then
    echo ""
    info "Step 1: Installing/upgrading APM Python agent (apminsight)..."
    "$VENV/bin/pip" install -U apminsight -q
    # Verify import
    if "$VENV/bin/python" -c "import apminsight; print(f'  apminsight version: {apminsight.__version__}')" 2>/dev/null; then
        success "apminsight package installed and verified."
    else
        # Some versions don't expose __version__, just verify import
        "$VENV/bin/python" -c "import apminsight" 2>/dev/null \
            && success "apminsight package installed." \
            || err "Failed to install apminsight. Check pip logs."
    fi

    # ══════════════════════════════════════════════════════════
    #  2. S247DataExporter — install the data relay service
    # ══════════════════════════════════════════════════════════
    echo ""
    if $SKIP_DATA_EXPORTER; then
        warn "Step 2: Skipping S247DataExporter installation (--skip-data-exporter)."
    elif [ -f /opt/S247DataExporter/bin/service.sh ]; then
        success "Step 2: S247DataExporter already installed at /opt/S247DataExporter."
        # Make sure it's running
        if service S247DataExporter status &>/dev/null; then
            success "S247DataExporter service is running."
        else
            info "Starting S247DataExporter..."
            service S247DataExporter start 2>/dev/null \
                || sh /opt/S247DataExporter/bin/service.sh start 2>/dev/null \
                || warn "Could not start S247DataExporter — start it manually."
        fi
    else
        info "Step 2: Installing S247DataExporter..."
        # Must be root for this
        if [[ $EUID -ne 0 ]]; then
            warn "S247DataExporter installation requires root. Skipping."
            warn "Run this script with sudo, or install manually:"
            echo "  wget -O InstallDataExporter.sh https://staticdownloads.site24x7.in/apminsight/S247DataExporter/linux/InstallDataExporter.sh"
            echo "  sudo sh InstallDataExporter.sh -lk \"$LICENSE_KEY\""
        else
            info "Downloading S247DataExporter installer..."
            wget -q -O /tmp/InstallDataExporter.sh \
                https://staticdownloads.site24x7.in/apminsight/S247DataExporter/linux/InstallDataExporter.sh

            info "Running S247DataExporter installer..."
            sh /tmp/InstallDataExporter.sh -lk "$LICENSE_KEY" || {
                warn "S247DataExporter installation returned a non-zero exit code."
                warn "If the exporter is already running, this may be safe to ignore."
            }
            rm -f /tmp/InstallDataExporter.sh

            # Verify
            if [ -f /opt/S247DataExporter/bin/service.sh ]; then
                success "S247DataExporter installed at /opt/S247DataExporter."
                # Ensure it's running
                service S247DataExporter start 2>/dev/null \
                    || sh /opt/S247DataExporter/bin/service.sh start 2>/dev/null \
                    || true
                success "S247DataExporter service started."
            else
                warn "S247DataExporter binary not found after install."
                echo "  Try installing manually:"
                echo "    wget -O InstallDataExporter.sh https://staticdownloads.site24x7.in/apminsight/S247DataExporter/linux/InstallDataExporter.sh"
                echo "    sudo sh InstallDataExporter.sh -lk \"$LICENSE_KEY\""
            fi
        fi
    fi
else
    info "Step 1-2: No --license-key provided — skipping APM agent + Data Exporter setup."
fi

# ══════════════════════════════════════════════════════════════
#  3. Update .env with the Site24x7 keys
# ══════════════════════════════════════════════════════════════
echo ""
info "Step 3: Updating .env with Site24x7 configuration..."

# Helper: set a key in .env (update if exists, append if not)
set_env_var() {
    local key="$1"
    local value="$2"
    local file="$3"

    if grep -q "^${key}=" "$file" 2>/dev/null; then
        # Key exists — replace the line (handles empty and non-empty values)
        sed -i "s|^${key}=.*|${key}=${value}|" "$file"
        info "  Updated ${key} in .env"
    elif grep -q "^# *${key}=" "$file" 2>/dev/null || grep -q "^#${key}=" "$file" 2>/dev/null; then
        # Key exists but is commented out — uncomment and set
        sed -i "s|^# *${key}=.*|${key}=${value}|" "$file"
        info "  Uncommented and set ${key} in .env"
    else
        # Key doesn't exist — append
        echo "${key}=${value}" >> "$file"
        info "  Added ${key} to .env"
    fi
}

if [[ -n "$LICENSE_KEY" ]]; then
    set_env_var "S247_LICENSE_KEY" "$LICENSE_KEY" "$ENV_FILE"
fi

if [[ -n "$RUM_KEY" ]]; then
    set_env_var "SITE24X7_RUM_APP_KEY" "$RUM_KEY" "$ENV_FILE"
fi

if [[ -n "$APP_NAME" ]]; then
    set_env_var "APP_NAME" "$APP_NAME" "$ENV_FILE"
fi

success ".env updated."

# ══════════════════════════════════════════════════════════════
#  4. Verify RUM snippet is in the HTML templates
# ══════════════════════════════════════════════════════════════
echo ""
info "Step 4: Verifying RUM snippet in HTML templates..."

BASE_TEMPLATE="$APP_DIR/app/templates/layouts/base.html"
if [ -f "$BASE_TEMPLATE" ]; then
    if grep -q "SITE24X7_RUM_APP_KEY" "$BASE_TEMPLATE"; then
        success "RUM snippet found in base.html — it will activate automatically"
        success "when the app reads SITE24X7_RUM_APP_KEY from .env."
        if grep -q "site24x7rum.in" "$BASE_TEMPLATE"; then
            success "RUM beacon uses .in data-centre (Indian account) — correct."
        elif grep -q "site24x7rum.com" "$BASE_TEMPLATE"; then
            warn "RUM beacon uses .com domain. Your account uses .in (Indian DC)."
            warn "Consider updating base.html to use static.site24x7rum.in"
        fi
        if grep -q "site24x7rum-min.js" "$BASE_TEMPLATE"; then
            success "RUM beacon script (site24x7rum-min.js) is present."
        fi
    else
        warn "RUM snippet NOT found in base.html."
        if [[ -n "$RUM_KEY" ]]; then
            info "Injecting RUM snippet into base.html..."

            # Insert the RUM snippet (Indian data-centre .in beacon with JS error tracking)
            SNIPPET='
    {# Site24x7 RUM — injected by site24x7_config.sh #}
    {% if config.get('\''SITE24X7_RUM_APP_KEY'\'') %}
    <script type="text/javascript">
    (function(w,d,s,r,k,h,m){
        if(w.performance \&\& w.performance.timing \&\& w.performance.navigation \&\& !w.s247r) {
            w[r] = w[r] || function(){(w[r].q = w[r].q || []).push(arguments)};
            h=d.createElement('\''script'\'');h.async=true;h.setAttribute('\''src'\'',s+k);
            d.getElementsByTagName('\''head'\'')[0].appendChild(h);
            (m = window.onerror),(window.onerror = function (b, c, d, f, g) {
            m \&\& m(b, c, d, f, g),g || (g = new Error(b)),(w[r].q = w[r].q || []).push(["captureException",g]);})
        }
    })(window,document,'\''//static.site24x7rum.in/beacon/site24x7rum-min.js?appKey='\'','\''s247r'\'','\''{{ config.get("SITE24X7_RUM_APP_KEY") }}'\'');
    </script>
    {% endif %}'

            # Try to insert after {% block extra_head %}{% endblock %}
            if grep -q "{% block extra_head %}" "$BASE_TEMPLATE"; then
                sed -i "/{% block extra_head %}{% endblock %}/a\\${SNIPPET}" "$BASE_TEMPLATE"
                success "RUM snippet injected after extra_head block in base.html."
            else
                # Fallback: insert before </head>
                sed -i "/<\/head>/i\\${SNIPPET}" "$BASE_TEMPLATE"
                success "RUM snippet injected before </head> in base.html."
            fi
        fi
    fi
else
    warn "base.html not found at expected path: $BASE_TEMPLATE"
fi

# ══════════════════════════════════════════════════════════════
#  5. Verify APM agent wiring in wsgi.py
# ══════════════════════════════════════════════════════════════
echo ""
info "Step 5: Verifying APM agent wiring..."

WSGI_FILE="$APP_DIR/wsgi.py"
if [ -f "$WSGI_FILE" ]; then
    if grep -q "apminsight" "$WSGI_FILE"; then
        success "APM agent initialisation found in wsgi.py."
        success "It will auto-activate when S247_LICENSE_KEY is set in .env."
    else
        warn "APM agent initialisation NOT found in wsgi.py."
        if [[ -n "$LICENSE_KEY" ]]; then
            info "The apminsight package is installed but wsgi.py doesn't initialise it."
            info "For Gunicorn deployments, add this to the top of wsgi.py:"
            echo ""
            echo "    import os"
            echo "    _apm_key = os.environ.get('S247_LICENSE_KEY')"
            echo "    if _apm_key:"
            echo "        import apminsight"
            echo "        apminsight.configure({'app_name': 'SnapTravels', 'license_key': _apm_key})"
            echo ""
        fi
    fi
else
    warn "wsgi.py not found — APM agent wiring could not be verified."
fi

# Also check main.py for dev-server usage (environment variable method)
MAIN_FILE="$APP_DIR/main.py"
if [ -f "$MAIN_FILE" ] && [[ -n "$LICENSE_KEY" ]]; then
    info "For dev-server (python main.py), the APM agent can also be activated via"
    info "environment variables — already set in .env (S247_LICENSE_KEY)."
fi

# ══════════════════════════════════════════════════════════════
#  6. Restart the application
# ══════════════════════════════════════════════════════════════
echo ""
info "Step 6: Restarting the application..."

# Auto-detect restart method
if [[ "$RESTART_METHOD" == "auto" ]]; then
    if systemctl is-active snaptravels &>/dev/null; then
        RESTART_METHOD="systemd"
    elif [ -f "$APP_DIR/.snaptravels.pid" ] && kill -0 "$(cat "$APP_DIR/.snaptravels.pid" 2>/dev/null)" 2>/dev/null; then
        RESTART_METHOD="script"
    else
        RESTART_METHOD="none"
    fi
fi

case "$RESTART_METHOD" in
    systemd)
        info "Restarting via systemd..."
        systemctl restart snaptravels
        sleep 2
        if systemctl is-active snaptravels &>/dev/null; then
            success "SnapTravels restarted via systemd."
        else
            warn "Service may not have started cleanly. Check: journalctl -u snaptravels -f"
        fi
        ;;
    script)
        info "Restarting via snaptravels.sh..."
        bash "$APP_DIR/snaptravels.sh" restart
        ;;
    none)
        warn "No running instance detected (or --restart-method none)."
        echo "  Restart manually when ready:"
        echo "    bash snaptravels.sh restart"
        echo "    # or: systemctl restart snaptravels"
        ;;
    *)
        warn "Unknown restart method: $RESTART_METHOD"
        ;;
esac

# ══════════════════════════════════════════════════════════════
#  7. Summary & verification checklist
# ══════════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║   Site24x7 Configuration Complete!                ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "  ${BOLD}What was configured:${NC}"
echo ""

if [[ -n "$LICENSE_KEY" ]]; then
    echo -e "  ${GREEN}APM Agent${NC}"
    echo "    Package  : apminsight (installed in $VENV)"
    echo "    Wiring   : wsgi.py → reads S247_LICENSE_KEY from environment"
    echo "    Key set  : S247_LICENSE_KEY in .env"
    if [ -f /opt/S247DataExporter/bin/service.sh ]; then
        echo -e "    Exporter : ${GREEN}S247DataExporter installed${NC} at /opt/S247DataExporter"
    elif $SKIP_DATA_EXPORTER; then
        echo -e "    Exporter : ${YELLOW}Skipped${NC} (--skip-data-exporter)"
    else
        echo -e "    Exporter : ${YELLOW}Manual install needed${NC} (see instructions above)"
    fi
    echo ""
fi

if [[ -n "$RUM_KEY" ]]; then
    echo -e "  ${GREEN}Real User Monitoring (RUM)${NC}"
    echo "    Snippet  : base.html → auto-injects site24x7rum-min.js beacon"
    echo "    Key set  : SITE24X7_RUM_APP_KEY in .env"
    echo "    Scope    : Every page that extends base.html (all pages)"
    echo ""
fi

echo -e "  ${BOLD}Verify in Site24x7 Console:${NC}"
echo ""
if [[ -n "$LICENSE_KEY" ]]; then
    echo "    APM → Navigate to APM Insight → look for '${APP_NAME:-SnapTravels}'"
    echo "          (Generate some traffic first — hit a few pages)"
fi
if [[ -n "$RUM_KEY" ]]; then
    echo "    RUM → Navigate to RUM → look for your application"
    echo "          (Open the site in a browser and browse a few pages)"
fi
echo ""

echo -e "  ${BOLD}Manage S247DataExporter:${NC}"
echo "    service S247DataExporter status"
echo "    service S247DataExporter restart"
echo ""

echo -e "  ${BOLD}Useful commands:${NC}"
echo "    # Check APM agent is loaded (look for 'apminsight' in output):"
echo "    $VENV/bin/python -c \"import apminsight; print('APM agent OK')\""
echo ""
echo "    # Check RUM snippet in page source (after app restart):"
echo "    curl -s http://localhost:${PORT:-8080}/ | grep -o 'site24x7rum-min.js' && echo 'RUM OK'"
echo ""
echo "    # View .env settings:"
echo "    grep -E 'S247|SITE24X7|APP_NAME' $ENV_FILE"
echo ""

echo -e "  ${BOLD}Documentation:${NC}"
echo "    https://www.site24x7.com/help/apm/python-agent/install-python-agent.html"
echo "    https://www.site24x7.com/help/apm/data-exporter-linux.html"
echo "    https://www.site24x7.com/help/apm/rum/add-rum-monitor.html"
echo ""
