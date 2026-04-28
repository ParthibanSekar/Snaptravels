"""
Admin audit logging service.

Every admin action (create / edit / delete on any entity, user management,
refund approvals, chaos toggles) is logged to the AdminAuditLog table with:
  - which admin did it (id + email)
  - the action label  (e.g. FLIGHT_CREATE, HOTEL_DELETE, USER_DISABLE)
  - the target object (type + id + human-readable name)
  - a JSON snapshot of the changed/submitted data
  - the caller's IP and User-Agent

Usage
-----
1. Decorator on a route:

    @admin_bp.route('/flights/<int:flight_id>/delete', methods=['POST'])
    @roles_required('admin')
    @audit_action('FLIGHT_DELETE', target_type='FLIGHT', get_label=lambda: 'Flight #{}'.format(flight_id))
    def delete_flight(flight_id):
        ...

2. Inline call anywhere:

    log_audit('USER_DISABLE', target_type='USER', target_id=uid,
              target_label=user.email, detail={'reason': 'manual'})
"""

import logging
from functools import wraps
from datetime import datetime
from flask import request, session, g, has_request_context

logger = logging.getLogger('snaptravels.audit')


def log_audit(action: str, *,
              target_type: str = None,
              target_id: int = None,
              target_label: str = None,
              detail: dict = None):
    """
    Write one AdminAuditLog row.  Safe to call anywhere inside an app context;
    silently no-ops if the DB is unavailable so it never breaks real functionality.
    """
    try:
        from app.models import AdminAuditLog
        from app import db

        admin_id = session.get('user_id') if has_request_context() else None
        admin_email = None
        if admin_id:
            from app.models import User
            u = User.query.get(admin_id)
            admin_email = u.email if u else None

        entry = AdminAuditLog(
            admin_id=admin_id,
            admin_email=admin_email,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_label=str(target_label)[:200] if target_label else None,
            ip_address=request.remote_addr if has_request_context() else None,
            user_agent=(request.headers.get('User-Agent', '')[:400]
                        if has_request_context() else None),
        )
        if detail:
            entry.detail = detail

        db.session.add(entry)
        db.session.commit()

        logger.info(
            "ADMIN_AUDIT action=%s target_type=%s target_id=%s admin=%s",
            action, target_type, target_id, admin_email
        )
    except Exception as e:
        logger.warning("audit log failed (non-fatal): %s", e)


def audit_action(action: str, *,
                 target_type: str = None,
                 get_target_id=None,
                 get_target_label=None,
                 get_detail=None):
    """
    Route decorator.  Logs an audit entry AFTER the wrapped function runs
    successfully (i.e. only if it doesn't raise an exception).

    get_target_id   — zero-arg callable returning the int id, or None
    get_target_label — zero-arg callable returning a string label, or None
    get_detail      — zero-arg callable returning a dict of extra context
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            try:
                t_id    = get_target_id()    if callable(get_target_id)    else None
                t_label = get_target_label() if callable(get_target_label) else None
                detail  = get_detail()       if callable(get_detail)       else None
                # Merge route kwargs as fallback for id
                if t_id is None:
                    for k in ('id', 'flight_id', 'hotel_id', 'act_id', 'uid',
                              'booking_id', 'aid', 'post_id'):
                        if k in kwargs:
                            t_id = kwargs[k]
                            break
                log_audit(action, target_type=target_type,
                          target_id=t_id, target_label=t_label, detail=detail)
            except Exception as e:
                logger.warning("audit decorator failed: %s", e)
            return result
        return wrapper
    return decorator
