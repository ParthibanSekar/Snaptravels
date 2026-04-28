"""
Observability helpers for SnapTravels.

Provides:
  - per-request trace IDs stored in flask.g
  - file-based application logging (RotatingFileHandler → logs/app.log)
  - optional JSON-formatted log handler for APM log ingestion
  - echo of trace IDs into response headers so Site24x7 Synthetic can
    grab them and correlate to APM traces

Trace header conventions supported (first match wins):
    X-Site24x7-Trace-Id
    X-Request-ID
    traceparent (W3C)

If none are present we mint a new UUID. The chosen id is echoed back as
both X-Request-ID and X-Site24x7-Trace-Id on the response.
"""

import json
import logging
from logging.handlers import RotatingFileHandler
import os
import threading
import uuid
import time
from flask import g, request


# ── Log format ───────────────────────────────────────────────────────────────
#  Readable format for file logs:
#    2026-04-20 14:32:05 [INFO ] snaptravels.email  | Email sent subject='Verify…' (trace=abc123)
FILE_LOG_FORMAT = (
    '%(asctime)s [%(levelname)-5s] %(name)-30s | %(message)s'
    '%(trace_suffix)s'
)
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


class TraceFormatter(logging.Formatter):
    """Adds trace_id suffix when available inside a request context."""
    def format(self, record):
        tid = getattr(record, 'trace_id', None)
        record.trace_suffix = f'  (trace={tid})' if tid else ''
        return super().format(record)


class JsonFormatter(logging.Formatter):
    """
    Structured JSON log formatter. Site24x7 APM / log management can
    parse this cleanly and use the trace_id field to jump from a log
    line to the matching trace.
    """
    def format(self, record):
        payload = {
            'ts': time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(record.created)),
            'level': record.levelname,
            'logger': record.name,
            'msg': record.getMessage(),
        }
        trace_id = getattr(record, 'trace_id', None)
        if trace_id:
            payload['trace_id'] = trace_id
        if record.exc_info:
            payload['exc'] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class TraceIdFilter(logging.Filter):
    """Injects the current request's trace_id (if any) into every log record."""
    def filter(self, record):
        try:
            record.trace_id = getattr(g, 'trace_id', None)
        except Exception:
            record.trace_id = None
        return True


def _pick_trace_id():
    for h in ('X-Site24x7-Trace-Id', 'X-Request-ID', 'traceparent'):
        v = request.headers.get(h)
        if v:
            return v
    return uuid.uuid4().hex


def _setup_file_logging(app):
    """
    Configure RotatingFileHandler for all application logs.

    Writes to:
      logs/app.log      — all INFO+ application logs (auth, email, booking, chaos, …)
      logs/error.log    — ERROR+ only (quick view of problems)

    Each file rotates at 10 MB, keeping 10 backups (≈100 MB max per file).
    """
    log_dir = os.path.join(app.root_path, '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)

    trace_filter = TraceIdFilter()

    # ── Main app log (INFO+) ─────────────────────────────────────────────
    app_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,   # 10 MB
        backupCount=10,
        encoding='utf-8'
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(TraceFormatter(FILE_LOG_FORMAT, datefmt=DATE_FORMAT))
    app_handler.addFilter(trace_filter)

    # ── Error-only log (ERROR+) ──────────────────────────────────────────
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=10 * 1024 * 1024,   # 10 MB
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(TraceFormatter(FILE_LOG_FORMAT, datefmt=DATE_FORMAT))
    error_handler.addFilter(trace_filter)

    # ── Attach to root logger so ALL snaptravels.* loggers inherit ───────
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(app_handler)
    root.addHandler(error_handler)

    # ── Also ensure Flask's own logger uses the file handlers ────────────
    app.logger.addHandler(app_handler)
    app.logger.addHandler(error_handler)
    app.logger.setLevel(logging.INFO)

    # ── Console handler for dev convenience (keeps stdout output) ────────
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
               for h in root.handlers):
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(TraceFormatter(FILE_LOG_FORMAT, datefmt=DATE_FORMAT))
        console.addFilter(trace_filter)
        root.addHandler(console)

    app.logger.info('Logging initialised → logs/app.log + logs/error.log (10 MB rotation × 10 backups)')


def _setup_json_logging(app):
    """Replace all handlers with JSON formatter for APM log ingestion."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(TraceIdFilter())
    # Replace Flask's default handler
    app.logger.handlers = [handler]
    app.logger.setLevel(logging.INFO)
    # Attach to root so chaos + booking loggers also get JSON
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


# ── Log folder size cap ─────────────────────────────────────────────────────
MAX_LOG_FOLDER_BYTES = 1 * 1024 * 1024 * 1024   # 1 GB
LOG_CLEANUP_INTERVAL = 300                        # check every 5 minutes

_cleanup_logger = logging.getLogger('snaptravels.log_cleanup')


def _get_folder_size(folder):
    """Return total size in bytes of all files in *folder* (non-recursive)."""
    total = 0
    try:
        for entry in os.scandir(folder):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
    except OSError:
        pass
    return total


def _cleanup_logs(log_dir):
    """
    If the logs/ folder exceeds MAX_LOG_FOLDER_BYTES (1 GB), delete the
    oldest rotated backup files until the folder is back under the cap.

    Only rotated backups (files ending with .1, .2, … or .log.1, etc.)
    are candidates for deletion — active log files (app.log, error.log)
    are never removed.
    """
    folder_size = _get_folder_size(log_dir)
    if folder_size <= MAX_LOG_FOLDER_BYTES:
        return

    _cleanup_logger.info(
        'Log folder size %.1f MB exceeds 1 GB cap — starting cleanup',
        folder_size / (1024 * 1024),
    )

    # Collect all rotated backup files (e.g. app.log.1, app.log.2, error.log.3)
    # Active log files (app.log, error.log) are kept.
    backup_files = []
    try:
        for entry in os.scandir(log_dir):
            if not entry.is_file(follow_symlinks=False):
                continue
            name = entry.name
            # Rotated files have a numeric suffix like .log.1, .log.2, etc.
            # Skip the active (current) log files
            if name in ('app.log', 'error.log'):
                continue
            # Only touch known log-related files
            if name.startswith(('app.log.', 'error.log.')):
                stat = entry.stat()
                backup_files.append((entry.path, stat.st_mtime, stat.st_size))
    except OSError:
        return

    if not backup_files:
        return

    # Sort oldest first (lowest mtime)
    backup_files.sort(key=lambda x: x[1])

    for path, _mtime, size in backup_files:
        if folder_size <= MAX_LOG_FOLDER_BYTES:
            break
        try:
            os.remove(path)
            folder_size -= size
            _cleanup_logger.info('Deleted old log backup: %s (%.1f MB freed)',
                                 os.path.basename(path), size / (1024 * 1024))
        except OSError as exc:
            _cleanup_logger.warning('Failed to delete %s: %s', path, exc)

    _cleanup_logger.info(
        'Log cleanup complete — folder now %.1f MB',
        folder_size / (1024 * 1024),
    )


def _start_log_cleanup_thread(log_dir):
    """
    Spawn a daemon thread that checks the logs/ folder size every
    LOG_CLEANUP_INTERVAL seconds and removes oldest backups if it
    exceeds 1 GB.
    """
    def _loop():
        while True:
            try:
                _cleanup_logs(log_dir)
            except Exception:
                _cleanup_logger.exception('Error during log cleanup')
            time.sleep(LOG_CLEANUP_INTERVAL)

    t = threading.Thread(target=_loop, name='log-cleanup', daemon=True)
    t.start()
    _cleanup_logger.info(
        'Log cleanup thread started — checking every %ds, cap %d MB',
        LOG_CLEANUP_INTERVAL,
        MAX_LOG_FOLDER_BYTES // (1024 * 1024),
    )


def init_observability(app):
    """Attach the observability middleware + logging to the app."""

    # ---- File-based logging (always on) --------------------------------
    _setup_file_logging(app)

    # ---- Automatic log cleanup (1 GB cap) ------------------------------
    log_dir = os.path.join(app.root_path, '..', 'logs')
    _cleanup_logs(log_dir)          # run once at startup
    _start_log_cleanup_thread(log_dir)  # then periodically

    # ---- JSON logging (optional, overrides file logging on stdout) -----
    if os.environ.get('SNAPTRAVELS_JSON_LOGS', '0') == '1':
        _setup_json_logging(app)

    # ---- Trace id propagation ------------------------------------------
    @app.before_request
    def _start_trace():
        g.trace_id = _pick_trace_id()
        g._req_start = time.time()

    @app.after_request
    def _end_trace(response):
        tid = getattr(g, 'trace_id', None)
        if tid:
            response.headers['X-Request-ID'] = tid
            response.headers['X-Site24x7-Trace-Id'] = tid
        started = getattr(g, '_req_start', None)
        if started:
            response.headers['X-Response-Time-Ms'] = str(int((time.time() - started) * 1000))
        return response

    # ---- Request logging (every request → logs/app.log) ----------------
    @app.after_request
    def _log_request(response):
        # Skip static files and health checks to reduce noise
        path = request.path
        if path.startswith('/static/') or path == '/health' or path == '/favicon.ico':
            return response
        duration = ''
        started = getattr(g, '_req_start', None)
        if started:
            duration = f' [{int((time.time() - started) * 1000)}ms]'
        app.logger.info(
            '%s %s → %s%s',
            request.method, path, response.status_code, duration
        )
        return response
