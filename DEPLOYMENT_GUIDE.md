# SnapTravels — Production Deployment Guide

## Architecture Overview

```
┌─────────────┐      ┌───────────┐      ┌──────────────────┐
│   Browser    │─────▶│   Nginx   │─────▶│    Gunicorn      │
│  (RUM JS)    │  80  │  reverse  │ 8000 │  4 workers       │
│              │ 443  │  proxy    │      │  wsgi:app         │
└─────────────┘      └───────────┘      └──────────────────┘
                           │                     │
                     static files          Flask app
                     /static/              + SQLite/Postgres
                                                 │
                                          Site24x7 APM Agent
                                                 │
                                     ┌───────────────────────┐
                                     │  Site24x7 Data        │
                                     │  Exporter Service     │
                                     │  (sends traces to     │
                                     │   Site24x7 cloud)     │
                                     └───────────────────────┘
```

## Quick Start (Automated)

```bash
# 1. Upload project files to your Debian 12 VPS
scp -r ./* root@YOUR_SERVER_IP:/opt/snaptravels/

# 2. SSH into the server
ssh root@YOUR_SERVER_IP

# 3. Run the deploy script
cd /opt/snaptravels
sudo bash deploy_production.sh --domain snaptravels.yourdomain.com
```

The script handles everything: system packages, Python venv, pip dependencies,
.env creation, database init, Gunicorn systemd service, Nginx reverse proxy,
HTTPS via Certbot, and Site24x7 Data Exporter installation.

---

## Manual Step-by-Step

### 1. System Packages

```bash
apt-get update
apt-get install -y python3 python3-venv python3-dev python3-pip \
    nginx certbot python3-certbot-nginx \
    lsof curl git build-essential \
    libffi-dev libssl-dev libpq-dev \
    libjpeg-dev zlib1g-dev libwebp-dev
```

### 2. Python Environment

```bash
cd /opt/snaptravels
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment File

Create `/opt/snaptravels/.env`:

| Variable                  | Required | Description                                    |
|---------------------------|----------|------------------------------------------------|
| `APP_ENV`                 | Yes      | Set to `production`                            |
| `APP_NAME`                | Yes      | `SnapTravels` (used in APM dashboard)          |
| `SECRET_KEY`              | Yes      | Random hex string — generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `PORT`                    | No       | Default `8000`                                 |
| `DATABASE_URL`            | No       | Postgres URI; defaults to SQLite if unset      |
| `SITE24X7_RUM_APP_KEY`   | Yes*     | Site24x7 RUM application key                   |
| `S247_LICENSE_KEY`        | Yes*     | Site24x7 APM license/device key                |
| `CHAOS_SCHEDULER_ENABLED` | No      | `1` to enable chaos scheduler                  |
| `MAIL_SERVER`             | No       | SMTP server for transactional email            |
| `MAIL_PORT`               | No       | Default `587`                                  |
| `MAIL_USERNAME`           | No       | SMTP username                                  |
| `MAIL_PASSWORD`           | No       | SMTP password                                  |
| `TOTP_ENCRYPTION_KEY`     | No       | Auto-generated if blank                        |

*Required for Site24x7 monitoring features.

### 4. Initialise Database

```bash
cd /opt/snaptravels
source venv/bin/activate
python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
"
# Optionally seed data:
python init_db.py
```

### 5. Gunicorn Systemd Service

Create `/etc/systemd/system/snaptravels.service`:

```ini
[Unit]
Description=SnapTravels (Gunicorn)
After=network.target

[Service]
Type=notify
User=root
Group=root
WorkingDirectory=/opt/snaptravels
EnvironmentFile=/opt/snaptravels/.env
ExecStart=/opt/snaptravels/venv/bin/gunicorn \
    --bind 127.0.0.1:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile /opt/snaptravels/logs/access.log \
    --error-logfile /opt/snaptravels/logs/error.log \
    --capture-output \
    wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
mkdir -p /opt/snaptravels/logs
systemctl daemon-reload
systemctl enable snaptravels
systemctl start snaptravels
systemctl status snaptravels
```

### 6. Nginx Reverse Proxy

Create `/etc/nginx/sites-available/snaptravels`:

```nginx
server {
    listen 80;
    server_name snaptravels.yourdomain.com;

    client_max_body_size 20M;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location /static/ {
        alias /opt/snaptravels/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }

    location = /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

```bash
ln -sf /etc/nginx/sites-available/snaptravels /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

### 7. HTTPS via Let's Encrypt

```bash
certbot --nginx -d snaptravels.yourdomain.com \
    --non-interactive --agree-tos --email admin@yourdomain.com --redirect

# Test automatic renewal
certbot renew --dry-run
```

---

## Site24x7 Integration

SnapTravels is wired for all three Site24x7 monitoring products out of the box.

### RUM (Real User Monitoring)

The base template (`app/templates/layouts/base.html`) automatically injects the
Site24x7 RUM JavaScript beacon when `SITE24X7_RUM_APP_KEY` is set.

**Setup:**

1. Log in to Site24x7 Console
2. Go to **Admin > RUM Application** and create a new application
3. Copy the **App Key**
4. Set it in `.env`:
   ```
   SITE24X7_RUM_APP_KEY=your_rum_app_key_here
   ```
5. Restart Gunicorn:
   ```bash
   systemctl restart snaptravels
   ```

RUM will track page load times, Ajax calls, JS errors, and user sessions
for every page view automatically.

### APM (Application Performance Monitoring)

The Python APM agent (`apminsight`) is initialised in `wsgi.py` before the
Flask application starts, ensuring all frameworks, DB drivers, and HTTP
clients are instrumented.

**Setup:**

1. Set the license key in `.env`:
   ```
   S247_LICENSE_KEY=your_apm_license_key_here
   ```

2. Install the Site24x7 APM Data Exporter service (the Python agent sends
   traces to this local service, which forwards them to Site24x7 cloud):
   ```bash
   bash -c "$(curl -sL https://staticdownloads.site24x7.com/apminsight/agents/apm-dataexporter-install.sh)" \
       -- -key YOUR_S247_LICENSE_KEY
   ```

3. Verify the Data Exporter is running:
   ```bash
   systemctl status s247DataExporter
   ```

4. Restart Gunicorn:
   ```bash
   systemctl restart snaptravels
   ```

5. Verify in Site24x7 Console > **APM** — your application should appear
   within a few minutes.

### Synthetic Monitors

Synthetic monitors are configured entirely in the **Site24x7 Console UI**.
No configuration files are needed in the codebase.

**Recommended monitors to create:**

| Monitor Type       | Name                        | Target / URL                                      | Interval |
|--------------------|-----------------------------|---------------------------------------------------|----------|
| URL Monitor        | Homepage Uptime             | `https://yourdomain.com/`                         | 1 min    |
| URL Monitor        | Health Endpoint             | `https://yourdomain.com/health`                   | 1 min    |
| URL Monitor        | API — Destinations          | `https://yourdomain.com/api/destinations`         | 5 min    |
| Web Page Speed     | Homepage Speed (Browser)    | `https://yourdomain.com/`                         | 10 min   |
| Web Page Speed     | Destinations Page Speed     | `https://yourdomain.com/destinations`             | 10 min   |
| REST API Monitor   | Login API                   | `POST /api/auth/login`                            | 5 min    |
| REST API Monitor   | Bookings API                | `GET /api/bookings`                               | 5 min    |
| Web Transaction    | Full Booking Flow           | Login > Search > Select > Book                    | 15 min   |

**Steps to create in Site24x7 Console:**

1. Go to **Admin > Add Monitor**
2. Select the monitor type (URL, Web Page Speed, REST API, or Web Transaction)
3. Enter the target URL and configuration
4. Set check frequency, locations, and alert thresholds
5. Assign to a monitor group (e.g., "SnapTravels Production")
6. Save and verify the first poll succeeds

---

## DNS Setup

Point your domain to the VPS IP address:

| Record Type | Host                          | Value           | TTL  |
|-------------|-------------------------------|-----------------|------|
| A           | snaptravels.yourdomain.com    | YOUR_SERVER_IP  | 300  |

If using Cloudflare, set the proxy status to **DNS only** (grey cloud) initially
so Certbot can validate. You can enable the orange cloud proxy after HTTPS is
configured.

---

## Management Commands

```bash
# Service control
systemctl start snaptravels
systemctl stop snaptravels
systemctl restart snaptravels
systemctl status snaptravels

# View logs
journalctl -u snaptravels -f              # systemd journal
tail -f /opt/snaptravels/logs/access.log  # Gunicorn access log
tail -f /opt/snaptravels/logs/error.log   # Gunicorn error log

# Nginx
systemctl reload nginx
nginx -t                                   # test config

# SSL certificate
certbot renew --dry-run                    # test renewal
certbot certificates                       # list certificates

# Site24x7 Data Exporter
systemctl status s247DataExporter
systemctl restart s247DataExporter
```

---

## Default Credentials

| Email                           | Password    | Role    |
|---------------------------------|-------------|---------|
| admin@snaptravels.online        | Admin@123   | Admin   |
| parthiban@snaptravels.online    | Test@123    | User    |

> Change these immediately after first login in production.
