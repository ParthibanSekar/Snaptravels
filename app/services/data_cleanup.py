"""
Data Sampling & Cleanup — SnapTravels

Prevents unbounded DB growth from synthetic monitors and automated testing.
Runs daily at midnight UTC via APScheduler.

Limits:
  - Bookings:      Keep last 100 per user (deletes oldest + BookingItems + Notifications)
  - ChaosEvents:   Keep last 2,000 rows total
  - Notifications:  Keep last 200 per user
  - AuditLog:      Keep last 2,000 rows total (if table exists)
"""

import logging
from datetime import datetime

logger = logging.getLogger('snaptravels.data_cleanup')

# ── Configurable limits ──────────────────────────────────────────────────────
MAX_BOOKINGS_PER_USER = 500
MAX_BOOKINGS_PREMIUM  = 1000   # Higher limit for admin/primary accounts
MAX_CHAOS_EVENTS      = 2000
MAX_NOTIFICATIONS_PER_USER = 200

# Accounts that get the higher booking limit
PREMIUM_ACCOUNTS = {
    'admin@snaptravels.online',
    'parthiban@snaptravels.online',
}


def run_cleanup(app):
    """
    Master cleanup function. Called by APScheduler daily at midnight UTC.
    Each step is wrapped in its own try/except so one failure doesn't block others.
    """
    logger.info("[cleanup] Daily data cleanup starting...")
    stats = {}

    stats['bookings'] = _cleanup_bookings(app)
    stats['chaos_events'] = _cleanup_chaos_events(app)
    stats['notifications'] = _cleanup_notifications(app)

    total = sum(v for v in stats.values() if isinstance(v, int))
    logger.info(
        "[cleanup] Done — deleted %d rows total (bookings=%s, chaos_events=%s, notifications=%s)",
        total, stats['bookings'], stats['chaos_events'], stats['notifications']
    )
    return stats


def _cleanup_bookings(app):
    """Keep only the last MAX_BOOKINGS_PER_USER bookings per user."""
    try:
        with app.app_context():
            from app.models import Booking, BookingItem, Notification, User
            from app import db

            deleted = 0
            users = db.session.query(User.id, User.email).all()

            for user_id, email in users:
                # Premium accounts get a higher limit
                limit = MAX_BOOKINGS_PREMIUM if email in PREMIUM_ACCOUNTS else MAX_BOOKINGS_PER_USER

                # Count bookings for this user
                count = Booking.query.filter_by(user_id=user_id).count()
                if count <= limit:
                    continue

                # Find the cutoff — the Nth newest booking's created_at
                cutoff_booking = (
                    Booking.query
                    .filter_by(user_id=user_id)
                    .order_by(Booking.created_at.desc())
                    .offset(limit)
                    .first()
                )
                if not cutoff_booking:
                    continue

                # Get IDs of bookings to delete
                old_bookings = (
                    Booking.query
                    .filter_by(user_id=user_id)
                    .filter(Booking.created_at <= cutoff_booking.created_at)
                    .all()
                )
                old_ids = [b.id for b in old_bookings]
                if not old_ids:
                    continue

                # Delete BookingItems for these bookings
                BookingItem.query.filter(BookingItem.booking_id.in_(old_ids)).delete(
                    synchronize_session=False
                )

                # Delete the bookings themselves
                Booking.query.filter(Booking.id.in_(old_ids)).delete(
                    synchronize_session=False
                )

                deleted += len(old_ids)
                logger.info(
                    "[cleanup] user_id=%d (%s): deleted %d old bookings (kept %d)",
                    user_id, email, len(old_ids), limit
                )

            db.session.commit()
            return deleted

    except Exception as e:
        logger.exception("[cleanup] Booking cleanup failed: %s", e)
        return 0


def _cleanup_chaos_events(app):
    """Keep only the last MAX_CHAOS_EVENTS chaos event rows."""
    try:
        with app.app_context():
            from app.models import ChaosEvent
            from app import db

            total = ChaosEvent.query.count()
            if total <= MAX_CHAOS_EVENTS:
                return 0

            # Find the cutoff event
            cutoff = (
                ChaosEvent.query
                .order_by(ChaosEvent.created_at.desc())
                .offset(MAX_CHAOS_EVENTS)
                .first()
            )
            if not cutoff:
                return 0

            deleted = (
                ChaosEvent.query
                .filter(ChaosEvent.created_at <= cutoff.created_at)
                .delete(synchronize_session=False)
            )
            db.session.commit()

            logger.info("[cleanup] Deleted %d old chaos events (kept %d)", deleted, MAX_CHAOS_EVENTS)
            return deleted

    except Exception as e:
        logger.exception("[cleanup] Chaos event cleanup failed: %s", e)
        return 0


def _cleanup_notifications(app):
    """Keep only the last MAX_NOTIFICATIONS_PER_USER notifications per user."""
    try:
        with app.app_context():
            from app.models import Notification, User
            from app import db

            deleted = 0
            users = db.session.query(User.id).all()

            for (user_id,) in users:
                count = Notification.query.filter_by(user_id=user_id).count()
                if count <= MAX_NOTIFICATIONS_PER_USER:
                    continue

                cutoff = (
                    Notification.query
                    .filter_by(user_id=user_id)
                    .order_by(Notification.created_at.desc())
                    .offset(MAX_NOTIFICATIONS_PER_USER)
                    .first()
                )
                if not cutoff:
                    continue

                batch = (
                    Notification.query
                    .filter_by(user_id=user_id)
                    .filter(Notification.created_at <= cutoff.created_at)
                    .delete(synchronize_session=False)
                )
                deleted += batch

            db.session.commit()
            if deleted:
                logger.info("[cleanup] Deleted %d old notifications", deleted)
            return deleted

    except Exception as e:
        logger.exception("[cleanup] Notification cleanup failed: %s", e)
        return 0
