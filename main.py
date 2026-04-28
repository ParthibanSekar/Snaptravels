import os

# ── Site24x7 Python APM Agent ────────────────────────────────
# Must be initialised BEFORE the Flask app is created so it can
# instrument all frameworks and DB drivers.
_apm_key = os.environ.get('S247_LICENSE_KEY')
if _apm_key:
    try:
        from apminsight import initialize_agent
        initialize_agent({
            'license_key': _apm_key,
            'appname': os.environ.get('APP_NAME', 'SnapTravels'),
            'exporter_status_port': os.environ.get('APM_EXPORTER_STATUS_PORT', '20021'),
            'exporter_data_port': os.environ.get('APM_EXPORTER_DATA_PORT', '20022'),
        })
        print('[Site24x7 APM] Agent initialised — appname=%s' %
              os.environ.get('APP_NAME', 'SnapTravels'))
    except ImportError:
        print('[Site24x7 APM] apminsight package not installed — skipping.')
    except Exception as e:
        print('[Site24x7 APM] Failed to initialise: %s' % e)

# ── Flask application ────────────────────────────────────────
from app import create_app  # noqa: E402

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('APP_ENV', 'production').lower() == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)