import os
from flask import Flask, jsonify, send_from_directory, abort, render_template, g, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from config import Config

db = SQLAlchemy()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["100000 per day", "10000 per hour"])
mail = Mail()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Refuse to start in production with the default insecure dev secret key
    if app.config.get('APP_ENV', 'development').lower() == 'production':
        Config.validate_production(app)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)

    # ---- Observability (trace ids, JSON logging) -----------------------
    from app.services.observability import init_observability
    init_observability(app)

    # ---- Register blueprints -------------------------------------------
    from app.blueprints.auth import auth_bp
    from app.blueprints.public import public_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.mobile_api import mobile_api
    from app.blueprints.pwa import pwa_bp
    from app.blueprints.chaos_admin import chaos_admin_bp
    from app.blueprints.packages import packages_bp
    from app.blueprints.reviews import reviews_bp
    from app.blueprints.activities import activities_bp
    from app.blueprints.buses import buses_bp
    from app.blueprints.cabs import cabs_bp
    from app.blueprints.trains import trains_bp
    from app.blueprints.insurance import insurance_bp
    from app.blueprints.blog import blog_bp
    from app.blueprints.trips import trips_bp
    from app.blueprints.user_dashboard import user_bp
    from app.blueprints.admin_extended import admin_ext_bp
    from app.blueprints.two_factor import twofa_bp
    from app.blueprints.corporate import corporate_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(mobile_api)
    app.register_blueprint(pwa_bp)
    app.register_blueprint(chaos_admin_bp)
    app.register_blueprint(packages_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(buses_bp)
    app.register_blueprint(cabs_bp)
    app.register_blueprint(trains_bp)
    app.register_blueprint(insurance_bp)
    app.register_blueprint(blog_bp)
    app.register_blueprint(trips_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_ext_bp)
    app.register_blueprint(twofa_bp)
    app.register_blueprint(corporate_bp)

    # Register CLI seed commands
    from app.commands import seed_bp
    app.register_blueprint(seed_bp)

    # Expose Python builtins that templates occasionally need
    app.jinja_env.globals.update(min=min, max=max, abs=abs, len=len)

    # from_json filter — used by admin_chaos.html to parse auto_chaos_schedule_json
    import json as _json
    app.jinja_env.filters['from_json'] = lambda s: (_json.loads(s) if s else [])

    # ── Chaos: inject JS snippets into every template context ────────────
    @app.context_processor
    def inject_chaos_js():
        try:
            from app.services.chaos import get_page_chaos_js, get_component_chaos_js, get_ab_test_js
            return {
                'chaos_page_js': get_page_chaos_js(),
                'component_chaos_js': get_component_chaos_js(),
                'ab_test_js': get_ab_test_js(),
            }
        except Exception:
            return {'chaos_page_js': '', 'component_chaos_js': '', 'ab_test_js': ''}

    # ── IP Access Control ────────────────────────────────────────────────
    from app.services.ip_access import check_ip_access
    app.before_request(check_ip_access)

    # ── Chaos: server-side page delay + 404 storm + session kill ─────────
    @app.before_request
    def apply_page_chaos():
        try:
            from app.services.chaos import maybe_delay_page, maybe_404_storm, maybe_kill_session
            maybe_delay_page(request.path)
            maybe_404_storm()
            maybe_kill_session()
        except Exception as e:
            # Re-raise HTTPException (e.g. abort(404) from 404 storm) so
            # Flask handles it normally via the registered error handlers.
            from werkzeug.exceptions import HTTPException
            if isinstance(e, HTTPException):
                raise
            app.logger.error(f"[CHAOS HOOK ERROR] {e}", exc_info=True)

    # Exempt mobile API and PWA endpoints from CSRF (they use JWT auth)
    # Exempt corporate portal from CSRF (it uses HTTP Basic Auth)
    csrf.exempt(mobile_api)
    csrf.exempt(pwa_bp)
    csrf.exempt(corporate_bp)
    # Allow Site24x7 REST API monitor to poll the chaos state.json without CSRF
    csrf.exempt(chaos_admin_bp)
    # Wishlist toggle and promo validate are JSON AJAX calls from the browser
    # — they carry a CSRF token via the hidden form tag on pages that embed them.
    # Only exempt the specific JSON endpoints, not the whole blueprint.
    csrf.exempt(reviews_bp)   # /wishlist/toggle, /promo/validate are AJAX
    # Notification AJAX endpoints called from the navbar dropdown (fetch() with meta CSRF)
    from app.blueprints.user_dashboard import notifications_recent, notifications_mark_all_read
    csrf.exempt(notifications_recent)
    csrf.exempt(notifications_mark_all_read)

    # ---- Global error handlers -----------------------------------------
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        trace_id = getattr(g, 'trace_id', None)
        return render_template('errors/500.html', trace_id=trace_id), 500

    @app.errorhandler(429)
    def too_many_requests(e):
        retry_after = getattr(e, 'retry_after', None)
        # API requests get JSON, browser requests get the HTML page
        if request.path.startswith('/mobile-api/'):
            return jsonify({'error': 'Too many requests', 'retry_after': retry_after}), 429
        return render_template('errors/429.html', retry_after=retry_after), 429

    # ---- Serve /assets/ from project root assets/ directory ------------
    # Hotel/package images are stored under assets/images/ (outside Flask's
    # default /static) so they survive deploys and are easy for ops to drop
    # files into. Image paths in DB look like '/assets/images/taj_udaipur.jpg'.
    ASSETS_ROOT = os.path.abspath(os.path.join(app.root_path, '..', 'assets'))

    @app.route('/assets/<path:filename>')
    def serve_assets(filename):
        if not os.path.exists(os.path.join(ASSETS_ROOT, filename)):
            # Graceful fallback to default hotel image
            default = os.path.join(ASSETS_ROOT, 'images', 'default.jpg')
            if os.path.exists(default):
                return send_from_directory(
                    os.path.join(ASSETS_ROOT, 'images'), 'default.jpg'
                )
            abort(404)
        return send_from_directory(ASSETS_ROOT, filename)

    # ---- Health + metrics endpoints (Site24x7 / Docker / LB friendly) --
    @app.route('/health')
    def health_check():
        # Deliberately cheap — does NOT touch the DB so it still returns 200
        # during a `db_down` chaos window. That way Site24x7 Synthetic and
        # APM see "app container is up, but DB is gone" — a realistic RCA.
        return jsonify({
            'status': 'healthy',
            'app': app.config.get('APP_NAME', 'SnapTravels'),
            'env': app.config.get('APP_ENV', 'development'),
        }), 200

    @app.route('/health/deep')
    def health_deep():
        # Deep check that DOES touch the DB — this is the endpoint you
        # point a Site24x7 Synthetic browser check at if you want the
        # check itself to fail during a db_down outage.
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            return jsonify({'status': 'healthy', 'db': 'up'}), 200
        except Exception as e:
            return jsonify({'status': 'unhealthy', 'db': 'down',
                            'error': str(e)}), 503

    @app.route('/metrics')
    def metrics():
        """
        Tiny plain-text metrics endpoint suitable for a Site24x7
        REST API monitor. Not Prometheus-compliant on purpose — we
        only expose what the demo RCA needs.
        """
        from app.models import FailureMode, Booking, User
        state = FailureMode.current()
        lines = [
            f'snaptravels_users_total {User.query.count()}',
            f'snaptravels_bookings_total {Booking.query.count()}',
            f'snaptravels_chaos_enabled {1 if state.enabled else 0}',
            f'snaptravels_chaos_login_failure_rate {state.login_failure_rate}',
            f'snaptravels_chaos_db_down {1 if state.db_down else 0}',
            f'snaptravels_chaos_payment_down {1 if state.payment_gateway_down else 0}',
            f'snaptravels_chaos_api_5xx_rate {state.api_5xx_rate}',
        ]
        return '\n'.join(lines) + '\n', 200, {'Content-Type': 'text/plain'}

    # ---- DB bootstrap + chaos scheduler --------------------------------
    with app.app_context():
        db.create_all()
        # Auto-migrate new FailureMode columns (SQLite doesn't support
        # ALTER TABLE via ORM so we use raw SQL for additive migrations)
        try:
            from sqlalchemy import inspect as sa_inspect, text
            insp = sa_inspect(db.engine)
            existing_cols = {c['name'] for c in insp.get_columns('failure_mode')}
            new_columns = [
                ('page_load_chaos',                    'BOOLEAN NOT NULL DEFAULT 0'),
                ('page_load_delay_ms',                 'INTEGER NOT NULL DEFAULT 0'),
                ('page_load_target_pages',             'TEXT NOT NULL DEFAULT \'["all"]\''),
                ('page_load_inject_js_errors',         'BOOLEAN NOT NULL DEFAULT 0'),
                ('page_load_inject_resource_failures', 'BOOLEAN NOT NULL DEFAULT 0'),
                ('page_load_inject_memory_pressure',   'BOOLEAN NOT NULL DEFAULT 0'),
                ('page_load_inject_render_blocking',   'BOOLEAN NOT NULL DEFAULT 0'),
                ('page_load_large_payload',            'BOOLEAN NOT NULL DEFAULT 0'),
                ('func_chaos',                         'BOOLEAN NOT NULL DEFAULT 0'),
                ('func_search_empty',                  'BOOLEAN NOT NULL DEFAULT 0'),
                ('func_form_errors',                   'BOOLEAN NOT NULL DEFAULT 0'),
                ('func_broken_images',                 'BOOLEAN NOT NULL DEFAULT 0'),
                ('func_session_kill_rate',             'FLOAT NOT NULL DEFAULT 0.0'),
                ('func_404_storm_rate',                'FLOAT NOT NULL DEFAULT 0.0'),
                ('func_infinite_spin',                 'BOOLEAN NOT NULL DEFAULT 0'),
                ('func_broken_cta',                    'BOOLEAN NOT NULL DEFAULT 0'),
                # Section 3 — Component-Level Chaos
                ('component_chaos',                    'BOOLEAN NOT NULL DEFAULT 0'),
                ('component_chaos_rate',               'INTEGER NOT NULL DEFAULT 50'),
                ('component_target_pages',             'TEXT NOT NULL DEFAULT \'["all"]\''),
                ('component_break_search',             'BOOLEAN NOT NULL DEFAULT 0'),
                ('component_break_results',            'BOOLEAN NOT NULL DEFAULT 0'),
                ('component_break_booking',            'BOOLEAN NOT NULL DEFAULT 0'),
                ('component_break_pricing',            'BOOLEAN NOT NULL DEFAULT 0'),
                ('component_break_css',                'BOOLEAN NOT NULL DEFAULT 0'),
                ('component_break_nav',                'BOOLEAN NOT NULL DEFAULT 0'),
                # New Page Load additions
                ('page_load_webfont_failure',          'BOOLEAN NOT NULL DEFAULT 0'),
                ('page_load_ttfb_spike',               'BOOLEAN NOT NULL DEFAULT 0'),
                ('page_load_cache_chaos',              'BOOLEAN NOT NULL DEFAULT 0'),
                # New Functionality additions
                ('func_wrong_search',                  'BOOLEAN NOT NULL DEFAULT 0'),
                ('func_fake_soldout',                  'BOOLEAN NOT NULL DEFAULT 0'),
                ('func_date_picker_broken',            'BOOLEAN NOT NULL DEFAULT 0'),
                ('func_otp_invalid',                   'BOOLEAN NOT NULL DEFAULT 0'),
                ('func_email_chaos',                   'BOOLEAN NOT NULL DEFAULT 0'),
                ('func_maintenance_flood',             'BOOLEAN NOT NULL DEFAULT 0'),
                # New Component additions
                ('component_break_autocomplete',       'BOOLEAN NOT NULL DEFAULT 0'),
                ('component_break_datepicker',         'BOOLEAN NOT NULL DEFAULT 0'),
                ('component_break_ratings',            'BOOLEAN NOT NULL DEFAULT 0'),
                ('component_break_loyalty',            'BOOLEAN NOT NULL DEFAULT 0'),
                # Section 4 — A/B Test Chaos
                ('ab_test_chaos',                      'BOOLEAN NOT NULL DEFAULT 0'),
                ('ab_test_login',                      'BOOLEAN NOT NULL DEFAULT 0'),
                ('ab_test_search',                     'BOOLEAN NOT NULL DEFAULT 0'),
                ('ab_test_booking',                    'BOOLEAN NOT NULL DEFAULT 0'),
                ('ab_test_profile',                    'BOOLEAN NOT NULL DEFAULT 0'),
                # Engine settings
                ('chaos_intensity',                    'INTEGER NOT NULL DEFAULT 1'),
                ('webhook_url',                        'VARCHAR(500)'),
            ]
            for col_name, col_def in new_columns:
                if col_name not in existing_cols:
                    db.session.execute(
                        text(f'ALTER TABLE failure_mode ADD COLUMN {col_name} {col_def}')
                    )
            db.session.commit()
        except Exception as e:
            app.logger.warning(f"FailureMode migration warning (safe to ignore on fresh DB): {e}")

        # Auto-migrate User table: add email verification columns
        try:
            user_cols = {c['name'] for c in insp.get_columns('user')}
            user_new_columns = [
                ('email_confirmed',      'BOOLEAN NOT NULL DEFAULT 0'),
                ('confirmation_token',   'VARCHAR(128)'),
                ('confirmation_sent_at', 'DATETIME'),
            ]
            migrated_user = False
            for col_name, col_def in user_new_columns:
                if col_name not in user_cols:
                    db.session.execute(
                        text(f'ALTER TABLE user ADD COLUMN {col_name} {col_def}')
                    )
                    migrated_user = True
            if migrated_user:
                # Mark all existing users as confirmed (they signed up before verification existed)
                db.session.execute(text('UPDATE user SET email_confirmed = 1 WHERE email_confirmed = 0'))
                db.session.commit()
                app.logger.info("User table migrated: email verification columns added, existing users marked as confirmed.")
        except Exception as e:
            app.logger.warning(f"User migration warning (safe to ignore on fresh DB): {e}")

        # Ensure the FailureMode singleton row exists so hooks never crash
        try:
            from app.models import FailureMode
            row = FailureMode.current()
            # Patch NULL text fields on existing rows (ALTER TABLE DEFAULT
            # doesn't backfill NULLs on SQLite pre-existing rows)
            patched = False
            if not row.page_load_target_pages:
                row.page_load_target_pages = '["all"]'
                patched = True
            if not getattr(row, 'component_target_pages', None):
                row.component_target_pages = '["all"]'
                patched = True
            # Backfill NULL chaos_intensity (SQLite DEFAULT doesn't patch existing rows)
            if getattr(row, 'chaos_intensity', None) is None:
                row.chaos_intensity = 1
                patched = True
            if patched:
                db.session.commit()
        except Exception as e:
            app.logger.warning(f"FailureMode bootstrap deferred: {e}")

    if app.config.get('CHAOS_SCHEDULER_ENABLED'):
        from app.services.chaos_scheduler import init_scheduler
        init_scheduler(app)

    return app
