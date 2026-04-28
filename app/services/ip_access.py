"""
IP Access Control — SnapTravels

Supports two modes:
  - WHITELIST: Only listed IPs can access the site. Everyone else gets 403.
  - BLACKLIST: Listed IPs are blocked. Everyone else can access normally.
  - DISABLED:  No IP filtering (default).

Config is stored in SiteConfig (key-value DB table):
  - ip_access_mode:  'disabled' | 'whitelist' | 'blacklist'
  - ip_access_list:  Comma-separated IPs/CIDRs (e.g. "1.2.3.4,10.0.0.0/8")

Admin endpoints (/admin/chaos/ and /admin/) are ALWAYS accessible
regardless of IP rules, so you can't lock yourself out.
"""

import logging
from ipaddress import ip_address, ip_network
from flask import request, abort

logger = logging.getLogger('snaptravels.ip_access')

# Paths that are NEVER blocked (so admin can't lock themselves out)
EXEMPT_PREFIXES = (
    '/admin/',
    '/login',
    '/static/',
    '/health',
    '/admin/chaos/state.json',
)


def _get_client_ip():
    """Get the real client IP, respecting X-Forwarded-For from Nginx."""
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'


def _parse_ip_list(ip_string):
    """Parse comma-separated IP string into a list of IPs/networks."""
    if not ip_string:
        return []
    entries = []
    for part in ip_string.split(','):
        part = part.strip()
        if not part or part.startswith('#'):
            continue
        entries.append(part)
    return entries


def _ip_matches(client_ip, ip_list):
    """Check if client_ip matches any entry in ip_list (supports CIDR)."""
    try:
        addr = ip_address(client_ip)
    except ValueError:
        return False

    for entry in ip_list:
        try:
            if '/' in entry:
                if addr in ip_network(entry, strict=False):
                    return True
            else:
                if addr == ip_address(entry):
                    return True
        except ValueError:
            continue
    return False


def check_ip_access():
    """
    Flask before_request hook. Call from app factory.
    Returns None to allow, or aborts with 403.
    """
    # Always allow exempt paths
    path = request.path
    if any(path.startswith(p) for p in EXEMPT_PREFIXES):
        return None

    try:
        from app.models import SiteConfig
        mode = SiteConfig.get('ip_access_mode', 'disabled')

        if mode == 'disabled':
            return None

        ip_list_str = SiteConfig.get('ip_access_list', '')
        ip_list = _parse_ip_list(ip_list_str)

        if not ip_list:
            return None  # No IPs configured — don't block anyone

        client_ip = _get_client_ip()

        if mode == 'whitelist':
            # Only listed IPs allowed
            if not _ip_matches(client_ip, ip_list):
                logger.warning(f"[ip-access] BLOCKED {client_ip} — not in whitelist")
                abort(403)

        elif mode == 'blacklist':
            # Listed IPs blocked
            if _ip_matches(client_ip, ip_list):
                logger.warning(f"[ip-access] BLOCKED {client_ip} — in blacklist")
                abort(403)

    except Exception as e:
        # Never break the site due to IP check errors
        logger.error(f"[ip-access] Error checking IP: {e}")

    return None
