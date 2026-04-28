"""
WSGI entry point for production (Gunicorn).

Usage:
    gunicorn --bind 127.0.0.1:8000 --workers 4 wsgi:app

The Site24x7 APM agent is initialised here BEFORE the Flask app
is created so it can instrument all frameworks and DB drivers.
"""
import os

# ── Site24x7 Python APM Agent ────────────────────────────────
# Only activate when the license key is present in the environment.
# Uses initialize_agent() as per Site24x7 docs for Python agent.
# Ref: https://www.site24x7.com/help/apm/python-agent/install-python-agent.html
_apm_key = os.environ.get('S247_LICENSE_KEY')
if _apm_key:
    try:
        from apminsight import initialize_agent
        # Override the reported host so it matches the public URL used by the
        # synthetic monitor (snaptravels.online). Required for APM <-> synthetic
        # auto-correlation in Site24x7. Falls back to the system hostname.
        _apm_host = os.environ.get('APM_HOST_NAME') or os.environ.get('HOSTNAME')
        _apm_config = {
            'license_key': _apm_key,
            'appname': os.environ.get('APP_NAME', 'SnapTravels'),
            'exporter_status_port': os.environ.get('APM_EXPORTER_STATUS_PORT', '20021'),
            'exporter_data_port': os.environ.get('APM_EXPORTER_DATA_PORT', '20022'),
        }
        if _apm_host:
            # Different agent versions use different keys; pass all common ones.
            _apm_config['host_name'] = _apm_host
            _apm_config['fqdn'] = _apm_host
            _apm_config['host_type'] = _apm_host
        initialize_agent(_apm_config)
        print('[Site24x7 APM] Agent initialised — appname=%s' %
              os.environ.get('APP_NAME', 'SnapTravels'))
    except ImportError:
        print('[Site24x7 APM] apminsight package not installed — skipping.')
    except Exception as e:
        print('[Site24x7 APM] Failed to initialise: %s' % e)

# ── Flask application ────────────────────────────────────────
from app import create_app  # noqa: E402

app = create_app()
