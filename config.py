import os
from datetime import timedelta


_DEFAULT_DEV_KEY = 'snaptravels-dev-key-2024'

# Known weak placeholder values that operators forget to change
_WEAK_KEY_PATTERNS = {
    _DEFAULT_DEV_KEY,
    'change-this-in-production',
    'secret',
    'your-secret-key',
    'development',
}


class Config:
    # Secrets — must be provided via environment in production.
    # The app will refuse to start in production mode if the default key is used.
    SECRET_KEY = os.environ.get('SECRET_KEY') or _DEFAULT_DEV_KEY

    @staticmethod
    def validate_production(app):
        """Call this inside create_app() when APP_ENV=production."""
        key = app.config.get('SECRET_KEY', '')
        if key in _WEAK_KEY_PATTERNS or len(key) < 32:
            raise RuntimeError(
                "\n\n[SECURITY] SECRET_KEY is weak or set to a well-known placeholder value.\n"
                "Set a strong random key via the SECRET_KEY environment variable before\n"
                "running in production:\n"
                "  export SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')\n"
                f"Current key length: {len(key)} (minimum 32 required)\n"
            )

    # Database — defaults to SQLite for local dev; set DATABASE_URL for Postgres
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL')
        or 'sqlite:///snaptravels.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600          # CSRF tokens expire after 1 hour
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # ---- Rate limiting (Flask-Limiter) ------------------------------------
    RATELIMIT_DEFAULT         = '200 per day;60 per hour'
    RATELIMIT_STORAGE_URL     = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_HEADERS_ENABLED = True     # X-RateLimit-* headers in responses

    # ---- Email (Flask-Mail) -----------------------------------------------
    MAIL_SERVER   = os.environ.get('MAIL_SERVER',   'smtp.gmail.com')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS  = os.environ.get('MAIL_USE_TLS',  'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get(
        'MAIL_DEFAULT_SENDER', 'SnapTravels <noreply@snaptravels.com>'
    )
    MAIL_ENABLED  = bool(os.environ.get('MAIL_USERNAME'))  # off unless configured

    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # ---- Chaos engineering --------------------------------------------
    # Set CHAOS_SCHEDULER_ENABLED=1 to run the background scheduler that
    # fires daily login_storm and service_outage windows automatically.
    CHAOS_SCHEDULER_ENABLED = os.environ.get('CHAOS_SCHEDULER_ENABLED', '0') == '1'

    # ---- Site24x7 observability ---------------------------------------
    # RUM: paste your Site24x7 RUM app key here to inject the beacon
    # into the base layout for every page view.
    SITE24X7_RUM_APP_KEY = os.environ.get('SITE24X7_RUM_APP_KEY')

    # APM: the Python apminsight agent reads S247_LICENSE_KEY from the
    # environment. It is initialised in wsgi.py before the app starts.
    # Set S247_LICENSE_KEY in .env — the config here is for reference only.
    S247_LICENSE_KEY = os.environ.get('S247_LICENSE_KEY')

    # Friendly app name used in /health, /metrics, and the APM dashboard
    APP_NAME = os.environ.get('APP_NAME', 'SnapTravels')
    APP_ENV = os.environ.get('APP_ENV', 'development')
