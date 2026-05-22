#!/bin/bash
# ============================================================
#  SnapTravels — Deploy from GitHub
#
#  First time:   bash deploy_from_github.sh setup
#  Update:       bash deploy_from_github.sh update
#  Full restart: bash deploy_from_github.sh restart
# ============================================================

set -euo pipefail

REPO_URL="https://github.com/ParthibanSekar/Snaptravels.git"
INSTALL_DIR="/root/DemoApp/snaptravels"
FLASK_PORT=5000

GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()     { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ══════════════════════════════════════════════════════════════
#  SETUP — First-time clone + install
# ══════════════════════════════════════════════════════════════
cmd_setup() {
    echo ""
    echo -e "${BOLD}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║   SnapTravels — First-Time Setup from GitHub       ║${NC}"
    echo -e "${BOLD}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""

    # Check if git is installed
    if ! command -v git &>/dev/null; then
        info "Installing git..."
        apt-get update -qq && apt-get install -y -qq git
    fi

    # Backup existing .env if folder exists
    if [ -d "$INSTALL_DIR" ]; then
        if [ -f "$INSTALL_DIR/.env" ]; then
            cp "$INSTALL_DIR/.env" /tmp/.env.snaptravels.backup
            success "Backed up existing .env to /tmp/.env.snaptravels.backup"
        fi
        # Stop the app if running
        if [ -f "$INSTALL_DIR/snaptravels.sh" ]; then
            cd "$INSTALL_DIR"
            bash snaptravels.sh stop 2>/dev/null || true
        fi
        warn "Removing old installation at $INSTALL_DIR"
        rm -rf "$INSTALL_DIR"
    fi

    # Clone
    info "Cloning from GitHub..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    success "Repository cloned to $INSTALL_DIR"

    cd "$INSTALL_DIR"

    # Restore .env if we backed it up
    if [ -f /tmp/.env.snaptravels.backup ]; then
        cp /tmp/.env.snaptravels.backup "$INSTALL_DIR/.env"
        success "Restored .env from backup"
    else
        warn ".env is empty — edit it now:"
        echo "    vi $INSTALL_DIR/.env"
        echo ""
        echo "  Required keys:"
        echo "    SECRET_KEY=<random-key>"
        echo "    S247_LICENSE_KEY=<your-apm-key>"
        echo "    SITE24X7_RUM_APP_KEY=<your-rum-key>"
        echo "    PORT=$FLASK_PORT"
        echo ""
    fi

    # Ensure PORT is set
    if ! grep -q "^PORT=" "$INSTALL_DIR/.env" 2>/dev/null; then
        echo "PORT=$FLASK_PORT" >> "$INSTALL_DIR/.env"
        success "Added PORT=$FLASK_PORT to .env"
    fi

    # Install dependencies and start
    info "Starting SnapTravels..."
    PORT=$FLASK_PORT bash snaptravels.sh start

    # Setup Nginx
    if [ -f "$INSTALL_DIR/setup_nginx.sh" ]; then
        info "Setting up Nginx..."
        bash setup_nginx.sh --domain snaptravels.online
    fi

    # Verify
    if [ -f "$INSTALL_DIR/verify.sh" ]; then
        echo ""
        info "Running verification..."
        bash verify.sh $FLASK_PORT
    fi

    echo ""
    echo -e "${BOLD}${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║   Setup Complete!                                  ║${NC}"
    echo -e "${BOLD}${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}URL:${NC}  http://snaptravels.online:8080"
    echo -e "  ${BOLD}Dir:${NC}  $INSTALL_DIR"
    echo ""
}

# ══════════════════════════════════════════════════════════════
#  UPDATE — Pull latest changes and restart
# ══════════════════════════════════════════════════════════════
cmd_update() {
    echo ""
    echo -e "${BOLD}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║   SnapTravels — Update from GitHub                 ║${NC}"
    echo -e "${BOLD}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ ! -d "$INSTALL_DIR/.git" ]; then
        err "$INSTALL_DIR is not a git repo. Run 'bash deploy_from_github.sh setup' first."
    fi

    cd "$INSTALL_DIR"

    # Stop the app
    info "Stopping app..."
    bash snaptravels.sh stop 2>/dev/null || true

    # Pull latest
    info "Pulling latest from GitHub..."
    git stash 2>/dev/null || true  # Stash any local changes (like .env edits)
    git pull origin main
    git stash pop 2>/dev/null || true  # Restore local changes

    success "Code updated to latest version"

    # Run DB migrations — adds new columns safely, skips if already present
    if [ -f "$INSTALL_DIR/migrate_mobile_chaos.py" ]; then
        info "Running mobile chaos migration..."
        python3 "$INSTALL_DIR/migrate_mobile_chaos.py" \
            && success "Mobile chaos migration complete" \
            || warn "Migration had warnings — check output above"
    fi
    if [ -f "$INSTALL_DIR/migrate_corp_chaos.py" ]; then
        info "Running corporate chaos migration..."
        python3 "$INSTALL_DIR/migrate_corp_chaos.py" \
            && success "Corporate chaos migration complete" \
            || warn "Migration had warnings — check output above"
    fi

    # Restart
    info "Restarting app..."
    PORT=$FLASK_PORT bash snaptravels.sh start

    success "Update complete — app running on port $FLASK_PORT"
    echo ""
}

# ══════════════════════════════════════════════════════════════
#  RESTART — Just restart without pulling
# ══════════════════════════════════════════════════════════════
cmd_restart() {
    if [ ! -d "$INSTALL_DIR" ]; then
        err "$INSTALL_DIR does not exist. Run setup first."
    fi
    cd "$INSTALL_DIR"
    PORT=$FLASK_PORT bash snaptravels.sh restart
}

# ══════════════════════════════════════════════════════════════
#  STATUS — Check if everything is running
# ══════════════════════════════════════════════════════════════
cmd_status() {
    if [ ! -d "$INSTALL_DIR" ]; then
        err "$INSTALL_DIR does not exist."
    fi
    cd "$INSTALL_DIR"
    bash snaptravels.sh status
    echo ""
    if systemctl is-active nginx >/dev/null 2>&1; then
        success "Nginx is running"
    else
        warn "Nginx is NOT running"
    fi
}

# ══════════════════════════════════════════════════════════════
#  Router
# ══════════════════════════════════════════════════════════════
case "${1:-help}" in
    setup)   cmd_setup   ;;
    update)  cmd_update  ;;
    restart) cmd_restart ;;
    status)  cmd_status  ;;
    *)
        echo ""
        echo -e "${BOLD}Usage:${NC}  bash deploy_from_github.sh <command>"
        echo ""
        echo "  setup     First-time clone from GitHub + install + start"
        echo "  update    Pull latest changes from GitHub + restart"
        echo "  restart   Restart without pulling"
        echo "  status    Check if app and Nginx are running"
        echo ""
        ;;
esac
