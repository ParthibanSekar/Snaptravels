# SnapTravels — Deployment & Operations Guide

A full-featured travel booking platform built with Flask. Supports flights, hotels, trains, buses, cabs, packages, activities, and travel insurance with a built-in chaos engineering console for monitoring demos.

---

## Quick Start (Fresh Server)

### Prerequisites

- Debian 12 / Ubuntu 22+ server
- Python 3.10+
- Root or sudo access

### Step 1 — Upload the build

From your local machine:

```bash
zip -r snaptravels.zip snaptravels-final-production-build-2/ -x "*/venv/*" "*/__pycache__/*" "*/instance/*" "*/.snaptravels.*" "*/logs/*"
scp snaptravels.zip root@YOUR_SERVER_IP:/root/
```

On the server:

```bash
cd /root
unzip snaptravels.zip
cd snaptravels-final-production-build-2
```

### Step 2 — Install system dependencies

```bash
bash deploy_debian12.sh
```

This installs Python 3, pip, venv, build tools, SQLite, image libraries, and Nginx.

### Step 3 — Configure .env

```bash
vi .env
```

Fill in your values:

```
SECRET_KEY=<generate-a-random-key>
S247_LICENSE_KEY=<your-apm-license-key>
SITE24X7_RUM_APP_KEY=<your-rum-app-key>
APP_NAME=SnapTravels
PORT=5000
```

Optional (email):

```
MAIL_SERVER=smtp.zoho.in
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your@email.com
MAIL_PASSWORD=your-password
MAIL_DEFAULT_SENDER=SnapTravels <your@email.com>
```

Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Step 4 — Start the app

```bash
PORT=5000 bash snaptravels.sh start
```

This will automatically create a Python venv, install dependencies, initialize the database, seed sample data, and start Flask on port 5000.

### Step 5 — Set up Nginx

```bash
bash setup_nginx.sh --domain yourdomain.com
```

Default: Nginx listens on port 8080, proxies to Flask on port 5000.

Options:

```bash
bash setup_nginx.sh --nginx-port 80 --flask-port 5000 --domain yourdomain.com
```

### Step 6 — Verify everything

```bash
bash verify.sh 5000
```

Runs 30+ checks: pages, RUM beacon, APM agent, Nginx proxy, database tables.

### Step 7 — Access the app

```
http://yourdomain.com:8080
```

Default login credentials:

| Role  | Email                        | Password  |
|-------|------------------------------|-----------|
| Admin | admin@snaptravels.online     | Admin@123 |
| User  | parthiban@snaptravels.online | Test@123  |

---

## Updating an Existing Server

### Option A — Full rebuild (recommended)

From your local machine:

```bash
zip -r snaptravels-new.zip snaptravels-final-production-build-2/ \
  -x "*/venv/*" "*/__pycache__/*" "*/instance/*" "*/.snaptravels.*" "*/logs/*" "*/.env"
scp snaptravels-new.zip root@YOUR_SERVER_IP:/root/
```

On the server:

```bash
cd /root/snaptravels-final-production-build-2
bash snaptravels.sh stop

# Backup .env and database
cp .env /root/.env.backup
cp instance/snaptravels.db /root/snaptravels.db.backup

# Extract new files (overwrites code, keeps .env excluded from zip)
cd /root
unzip -o snaptravels-new.zip -d .

# Restore .env
cp /root/.env.backup /root/snaptravels-final-production-build-2/.env

# Restart
cd snaptravels-final-production-build-2
PORT=5000 bash snaptravels.sh start

# Verify
bash verify.sh 5000
```

### Option B — Copy only changed files

```bash
scp app/blueprints/public.py root@SERVER:/root/snaptravels-final-production-build-2/app/blueprints/
scp app/templates/home.html root@SERVER:/root/snaptravels-final-production-build-2/app/templates/

# Then restart on server
PORT=5000 bash snaptravels.sh restart
```

---

## Daily Operations

### Start / Stop / Restart

```bash
PORT=5000 bash snaptravels.sh start
bash snaptravels.sh stop
PORT=5000 bash snaptravels.sh restart
bash snaptravels.sh status
bash snaptravels.sh logs
```

If `PORT=5000` is in your `.env`, you can just use `bash snaptravels.sh start`.

### Reset Database

Deletes all data and re-seeds from scratch:

```bash
bash snaptravels.sh reset-db
PORT=5000 bash snaptravels.sh start
```

### View Logs

```bash
bash snaptravels.sh logs          # Flask output
tail -f logs/app.log              # Application events
tail -f logs/error.log            # Errors only
```

---

## Scripts Reference

| Script | Purpose | When to run |
|--------|---------|-------------|
| `snaptravels.sh` | Start, stop, restart, logs, reset-db | Daily |
| `setup_nginx.sh` | Install and configure Nginx reverse proxy | Once per server |
| `verify.sh` | Post-deployment health check (30+ tests) | After every deploy |
| `deploy_debian12.sh` | Install system packages on Debian | Once per server |
| `deploy_production.sh` | Full production setup (Gunicorn + Nginx + HTTPS) | Optional |
| `site24x7_config.sh` | One-click APM + RUM setup | Once per server |

---

## Folder Structure

```
snaptravels-final-production-build-2/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── models.py             # Database models
│   ├── forms.py              # WTForms for booking
│   ├── blueprints/           # Route handlers
│   │   ├── public.py         # Flights, hotels, booking
│   │   ├── trains.py         # Train search and booking
│   │   ├── buses.py          # Bus search and booking
│   │   ├── cabs.py           # Cab search and booking
│   │   ├── packages.py       # Holiday packages
│   │   ├── activities.py     # Activities booking
│   │   ├── insurance.py      # Travel insurance
│   │   ├── chaos_admin.py    # Chaos control panel
│   │   └── ...
│   ├── services/
│   │   ├── chaos.py          # Chaos injection engine
│   │   ├── chaos_scheduler.py # Auto chaos scheduler
│   │   ├── booking.py        # Booking service
│   │   ├── data_cleanup.py   # Daily DB cleanup
│   │   └── ...
│   ├── templates/            # Jinja2 HTML templates
│   └── static/               # CSS, JS, images
├── main.py                   # Dev entry point (with APM)
├── wsgi.py                   # Production entry point (Gunicorn)
├── config.py                 # Flask configuration
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables
├── snaptravels.sh            # App manager script
├── setup_nginx.sh            # Nginx setup script
├── verify.sh                 # Post-deployment verification
└── README.md                 # This file
```

---

## APM & RUM Setup

### Prerequisites

1. A Site24x7 account
2. APM License Key (Admin → Developer → Device Key)
3. RUM App Key (Admin → RUM Application → App Key)
4. Data Exporter installed on the server

### Configure

Add keys to `.env`:

```
S247_LICENSE_KEY=in_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SITE24X7_RUM_APP_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
APP_NAME=SnapTravels
```

### Install Data Exporter

```bash
bash site24x7_config.sh --license-key YOUR_LICENSE_KEY --rum-key YOUR_RUM_KEY
```

Or manually:

```bash
curl -sL https://staticdownloads.site24x7.in/apminsight/S247DataExporter/linux/InstallDataExporter.sh | bash -s -- -key YOUR_LICENSE_KEY
```

### Verify

```bash
bash verify.sh 5000
```

Look for:
- `[PASS] RUM beacon found in HTML`
- `[PASS] APM agent initialized`
- `[PASS] Data Exporter service is running`

---

## Chaos Engineering

### Access

Login as Admin → Chaos Control (`/admin/chaos/`)

### Sections

| Section | What it does |
|---------|-------------|
| Core Engine (§0) | Login failures, DB issues, payment crashes, API errors |
| Page Load (§1) | Server delays, JS errors, resource failures, memory pressure |
| Functionality (§2) | Broken images, forms, buttons, sessions, 404 storms |
| Component (§3) | Random UI component breakage |
| A/B Test (§4) | DOM identifier mutation (breaks monitors, invisible to users) |

### Auto Chaos Mode

Continuous loop of all 5 types with 3-hour cooling gaps. Toggle from the chaos console or visit `/admin/chaos/auto` for the full schedule timeline.

### Named Outage Profiles

One-click presets: Login Storm, DB Down, Payment Down, Checkout Chaos, Search Timeout, API 5xx Storm, CDN Failure, and more.

### API Endpoint

```
GET /admin/chaos/state.json
```

Unauthenticated — use for REST API monitors.

### Full Documentation

Available at `/admin/chaos/docs` — explains every setting and what monitoring tools detect.

---

## Data Cleanup

Runs automatically at midnight UTC to prevent DB growth from synthetic monitors.

| Data | Limit |
|------|-------|
| Bookings per user | 500 (1,000 for admin accounts) |
| Chaos events | 2,000 total |
| Notifications per user | 200 |

Configure in `app/services/data_cleanup.py`.

---

## Troubleshooting

### App won't start

```bash
cat .snaptravels.log | tail -30
bash snaptravels.sh stop
PORT=5000 bash snaptravels.sh start
```

### .env not loading

Every non-comment line must be `KEY=VALUE`. No stray text, no meeting notes. Comments must start with `#`.

### Chaos page shows 500

Server has old build — redeploy updated files and restart.

### APM not working

```bash
bash verify.sh 5000
```

Common issues: `S247_LICENSE_KEY` empty in `.env`, Data Exporter not running, `.env` has broken lines.

### RUM not showing data

Browse a few pages, wait 5-10 minutes. Verify with:

```bash
curl -s http://localhost:5000/ | grep site24x7rum
```

### Port 80 blocked

Use `setup_nginx.sh` with default port 8080:

```
http://yourdomain.com:8080
```

Ask your hosting provider to open ports 80 and 443 for direct domain access and HTTPS.

---

## Tech Stack

- **Backend**: Python 3.10+, Flask 3.x, SQLAlchemy, APScheduler
- **Database**: SQLite
- **Frontend**: Bootstrap 5, Bootstrap Icons, vanilla JS
- **Monitoring**: Site24x7 APM (Python agent) + RUM (JS beacon)
- **Server**: Nginx reverse proxy + Flask (or Gunicorn for production)
