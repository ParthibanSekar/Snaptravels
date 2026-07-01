"""
SnapTravels — Two-Factor Authentication Blueprint.

Routes (all under /security):
  GET  /security                          — Security settings page
  POST /security/2fa/start               — Generate TOTP secret + QR (step 1)
  GET  /security/2fa/setup               — Show QR code page (step 2)
  POST /security/2fa/verify-setup        — Verify OTP and activate 2FA (step 3)
  GET  /security/2fa/backup-codes        — View / download backup codes
  POST /security/2fa/regenerate          — Regenerate backup codes (requires OTP)
  POST /security/2fa/disable             — Disable 2FA (requires password + OTP)
  GET  /security/2fa/activity            — View 2FA event log

  POST /security/email-otp/enable        — Send verification code and enable Email OTP (step 1)
  GET  /security/email-otp/verify        — Show email OTP verify form (step 2)
  POST /security/email-otp/verify-setup  — Confirm code and activate Email OTP (step 3)
  POST /security/email-otp/disable       — Disable Email OTP (requires password)

Login OTP routes (no prefix, called from auth flow):
  GET  /auth/2fa                         — Show OTP entry form (TOTP or Email OTP)
  POST /auth/2fa                         — Verify OTP / backup code and complete login
  GET  /auth/email-otp                   — Trigger email OTP send + show verify form
  POST /auth/email-otp                   — Verify email OTP and complete login
"""

from __future__ import annotations

import json
import random
import secrets
import string
from datetime import datetime, timedelta

from flask import (Blueprint, current_app, flash, jsonify, redirect,
                   render_template, request, session, url_for, make_response)
from app import db
from app.models import BackupCode, TwoFactorLog, User
from app.services.auth import get_current_user, login_required
from app.services.two_factor import (
    REMEMBER_DEVICE_DAYS,
    clear_otp_attempts,
    decrypt_secret,
    encrypt_secret,
    generate_backup_codes,
    generate_qr_b64,
    generate_totp_secret,
    get_totp_uri,
    is_otp_locked,
    make_remember_device_token,
    otp_lockout_remaining,
    record_otp_attempt,
    verify_backup_code,
    verify_remember_device_token,
    verify_totp,
)

twofa_bp = Blueprint('twofa', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _log(user_id: int, event: str) -> None:
    """Insert a TwoFactorLog row (best-effort — never crashes a request)."""
    try:
        log = TwoFactorLog(
            user_id    = user_id,
            event      = event,
            ip_address = request.remote_addr,
            user_agent = request.headers.get('User-Agent', '')[:400],
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


def _delete_pending_codes(user_id: int) -> None:
    """Remove any unused backup codes for a user (called before regenerating)."""
    BackupCode.query.filter_by(user_id=user_id, used=False).delete()
    db.session.commit()


def _save_backup_codes(user_id: int, hashed_codes: list[str]) -> None:
    """Persist a list of hashed backup codes for a user."""
    for h in hashed_codes:
        db.session.add(BackupCode(user_id=user_id, code_hash=h))
    db.session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Security settings hub
# ─────────────────────────────────────────────────────────────────────────────

@twofa_bp.route('/security')
@login_required
def security():
    user = get_current_user()
    # Recent 2FA activity (last 10 events)
    logs = (TwoFactorLog.query
            .filter_by(user_id=user.id)
            .order_by(TwoFactorLog.created_at.desc())
            .limit(10).all())
    unused_codes = BackupCode.query.filter_by(user_id=user.id, used=False).count()
    return render_template('security.html', user=user,
                           logs=logs, unused_backup_codes=unused_codes)


# ─────────────────────────────────────────────────────────────────────────────
# 2FA Enable — Step 1: generate secret
# ─────────────────────────────────────────────────────────────────────────────

@twofa_bp.route('/security/2fa/start', methods=['POST'])
@login_required
def start_2fa_setup():
    user = get_current_user()
    if user.totp_enabled:
        flash('Two-factor authentication is already enabled.', 'info')
        return redirect(url_for('twofa.security'))

    # Generate a fresh secret for this setup attempt
    secret = generate_totp_secret()
    # Temporarily store in session — only persisted after verification
    session['pending_totp_secret'] = secret
    session['pending_totp_user_id'] = user.id

    _log(user.id, '2FA_SETUP_STARTED')
    return redirect(url_for('twofa.setup_2fa'))


# ─────────────────────────────────────────────────────────────────────────────
# 2FA Enable — Step 2: show QR code
# ─────────────────────────────────────────────────────────────────────────────

@twofa_bp.route('/security/2fa/setup')
@login_required
def setup_2fa():
    user = get_current_user()
    if user.totp_enabled:
        flash('2FA is already active on your account.', 'info')
        return redirect(url_for('twofa.security'))

    secret = session.get('pending_totp_secret')
    if not secret or session.get('pending_totp_user_id') != user.id:
        flash('Setup session expired. Please start again.', 'warning')
        return redirect(url_for('twofa.security'))

    uri    = get_totp_uri(secret, user.email)
    qr_b64 = generate_qr_b64(uri)
    return render_template('2fa_setup.html', user=user,
                           qr_b64=qr_b64, secret=secret)


# ─────────────────────────────────────────────────────────────────────────────
# 2FA Enable — Step 3: verify OTP and activate
# ─────────────────────────────────────────────────────────────────────────────

@twofa_bp.route('/security/2fa/verify-setup', methods=['POST'])
@login_required
def verify_setup():
    user   = get_current_user()
    secret = session.get('pending_totp_secret')
    token  = request.form.get('otp', '').strip()

    if not secret or session.get('pending_totp_user_id') != user.id:
        flash('Setup session expired. Please start again.', 'warning')
        return redirect(url_for('twofa.security'))

    if is_otp_locked(session):
        secs = otp_lockout_remaining(session)
        flash(f'Too many failed attempts. Try again in {secs // 60}m {secs % 60}s.', 'danger')
        return redirect(url_for('twofa.setup_2fa'))

    if not verify_totp(secret, token):
        record_otp_attempt(session)
        remaining = max(0, 5 - len(session.get('otp_attempts', [])))
        flash(f'Invalid code. {remaining} attempt(s) remaining.', 'danger')
        return redirect(url_for('twofa.setup_2fa'))

    # ── OTP valid → persist secret, generate backup codes ──────────────────
    clear_otp_attempts(session)
    session.pop('pending_totp_secret', None)
    session.pop('pending_totp_user_id', None)

    plain_codes, hashed_codes = generate_backup_codes()

    # Remove any stale backup codes first
    _delete_pending_codes(user.id)

    user.totp_secret_enc = encrypt_secret(secret, current_app._get_current_object())
    user.totp_enabled    = True
    user.totp_verified_at = datetime.utcnow()
    db.session.commit()

    _save_backup_codes(user.id, hashed_codes)
    _log(user.id, '2FA_ENABLED')

    # Pass plain backup codes to template ONCE — never stored again
    flash('Two-factor authentication enabled successfully!', 'success')
    return render_template('2fa_backup_codes.html', user=user,
                           backup_codes=plain_codes, just_enabled=True)


# ─────────────────────────────────────────────────────────────────────────────
# Backup codes — view & regenerate
# ─────────────────────────────────────────────────────────────────────────────

@twofa_bp.route('/security/2fa/backup-codes')
@login_required
def backup_codes():
    user = get_current_user()
    if not user.totp_enabled:
        flash('Enable 2FA first to view backup codes.', 'warning')
        return redirect(url_for('twofa.security'))
    unused_count = BackupCode.query.filter_by(user_id=user.id, used=False).count()
    return render_template('2fa_backup_codes.html', user=user,
                           backup_codes=None, just_enabled=False,
                           unused_count=unused_count)


@twofa_bp.route('/security/2fa/regenerate', methods=['POST'])
@login_required
def regenerate_backup_codes():
    user  = get_current_user()
    token = request.form.get('otp', '').strip()

    if not user.totp_enabled:
        flash('2FA is not enabled.', 'warning')
        return redirect(url_for('twofa.security'))

    if is_otp_locked(session):
        secs = otp_lockout_remaining(session)
        flash(f'Too many attempts. Try again in {secs // 60}m {secs % 60}s.', 'danger')
        return redirect(url_for('twofa.backup_codes'))

    secret = decrypt_secret(user.totp_secret_enc, current_app._get_current_object())
    if not verify_totp(secret, token):
        record_otp_attempt(session)
        flash('Invalid OTP. Please try again.', 'danger')
        return redirect(url_for('twofa.backup_codes'))

    clear_otp_attempts(session)
    plain_codes, hashed_codes = generate_backup_codes()
    _delete_pending_codes(user.id)
    _save_backup_codes(user.id, hashed_codes)
    _log(user.id, '2FA_BACKUP_REGENERATED')

    flash('Backup codes regenerated. Save them securely — they will only be shown once.', 'warning')
    return render_template('2fa_backup_codes.html', user=user,
                           backup_codes=plain_codes, just_enabled=False,
                           unused_count=len(plain_codes))


# ─────────────────────────────────────────────────────────────────────────────
# Disable 2FA — requires current password + valid OTP
# ─────────────────────────────────────────────────────────────────────────────

@twofa_bp.route('/security/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    user     = get_current_user()
    password = request.form.get('password', '')
    token    = request.form.get('otp', '').strip()

    if not user.totp_enabled:
        flash('2FA is not currently enabled.', 'info')
        return redirect(url_for('twofa.security'))

    if is_otp_locked(session):
        secs = otp_lockout_remaining(session)
        flash(f'Too many failed attempts. Try again in {secs // 60}m {secs % 60}s.', 'danger')
        return redirect(url_for('twofa.security'))

    if not user.check_password(password):
        record_otp_attempt(session)
        flash('Incorrect password.', 'danger')
        return redirect(url_for('twofa.security'))

    secret = decrypt_secret(user.totp_secret_enc, current_app._get_current_object())
    if not verify_totp(secret, token):
        record_otp_attempt(session)
        flash('Invalid OTP code. Please try again.', 'danger')
        return redirect(url_for('twofa.security'))

    clear_otp_attempts(session)

    # Wipe all 2FA data
    user.totp_secret_enc  = None
    user.totp_enabled     = False
    user.totp_verified_at = None
    BackupCode.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    _log(user.id, '2FA_DISABLED')
    flash('Two-factor authentication has been disabled.', 'success')
    return redirect(url_for('twofa.security'))


# ─────────────────────────────────────────────────────────────────────────────
# 2FA Activity Log
# ─────────────────────────────────────────────────────────────────────────────

@twofa_bp.route('/security/2fa/activity')
@login_required
def activity_log():
    user = get_current_user()
    logs = (TwoFactorLog.query
            .filter_by(user_id=user.id)
            .order_by(TwoFactorLog.created_at.desc())
            .limit(50).all())
    return render_template('2fa_activity.html', user=user, logs=logs)


# ─────────────────────────────────────────────────────────────────────────────
# Login 2FA check — called after password auth succeeds
# ─────────────────────────────────────────────────────────────────────────────

@twofa_bp.route('/auth/2fa', methods=['GET', 'POST'])
def login_otp():
    """
    Shown when a user with 2FA enabled completes password auth.
    Session key 'pending_2fa_user_id' holds the authenticated user's ID.
    """
    user_id = session.get('pending_2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user or not user.totp_enabled:
        session.pop('pending_2fa_user_id', None)
        return redirect(url_for('auth.login'))

    if request.method == 'GET':
        return render_template('2fa_login.html', user=None)

    # ── POST: verify token ───────────────────────────────────────────────────
    if is_otp_locked(session):
        secs = otp_lockout_remaining(session)
        flash(f'Too many failed attempts. Try again in {secs // 60}m {secs % 60}s.', 'danger')
        return render_template('2fa_login.html', user=None)

    token       = request.form.get('otp', '').strip()
    use_backup  = request.form.get('use_backup', '') == '1'
    remember_me = request.form.get('remember_device', '') == '1'

    secret = decrypt_secret(user.totp_secret_enc, current_app._get_current_object())

    verified = False

    if use_backup:
        # Try every unused backup code
        unused = BackupCode.query.filter_by(user_id=user.id, used=False).all()
        for code_row in unused:
            if verify_backup_code(token, code_row.code_hash):
                code_row.used    = True
                code_row.used_at = datetime.utcnow()
                db.session.commit()
                _log(user.id, '2FA_BACKUP_USED')
                verified = True
                break
    else:
        if verify_totp(secret, token):
            verified = True

    # Chaos: force OTP failure even for correct codes
    from app.services.chaos import should_otp_fail
    if should_otp_fail():
        verified = False

    if not verified:
        record_otp_attempt(session)
        remaining = max(0, 5 - len(session.get('otp_attempts', [])))
        _log(user.id, '2FA_FAILED')
        flash(f'Invalid code. {remaining} attempt(s) remaining.', 'danger')
        return render_template('2fa_login.html', user=None)

    # ── Success: complete login ──────────────────────────────────────────────
    clear_otp_attempts(session)
    session.pop('pending_2fa_user_id', None)
    session['user_id'] = user.id
    session.permanent  = True

    _log(user.id, '2FA_LOGIN')

    # Remember this device?
    response = redirect(url_for('public.home'))
    if remember_me:
        token_val = make_remember_device_token(
            user.id,
            request.headers.get('User-Agent', ''),
            current_app.config['SECRET_KEY'],
        )
        response.set_cookie(
            'remember_device',
            token_val,
            max_age  = REMEMBER_DEVICE_DAYS * 86400,
            httponly = True,
            samesite = 'Lax',
            secure   = True,    # HTTPS only — prevents transmission over plain HTTP
        )

    flash(f'Welcome back, {user.name}!', 'success')
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Email OTP helpers
# ─────────────────────────────────────────────────────────────────────────────

EMAIL_OTP_EXPIRY_MINUTES = 10


def _generate_email_otp() -> str:
    """Generate a cryptographically random 6-digit numeric OTP."""
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def _store_email_otp(otp: str) -> None:
    """Store OTP + expiry in session."""
    session['email_otp_code']    = otp
    session['email_otp_expires'] = (
        datetime.utcnow() + timedelta(minutes=EMAIL_OTP_EXPIRY_MINUTES)
    ).isoformat()


def _validate_email_otp(submitted: str) -> bool:
    """Return True if submitted code matches session OTP and hasn't expired."""
    code    = session.get('email_otp_code')
    expires = session.get('email_otp_expires')
    if not code or not expires:
        return False
    if datetime.utcnow() > datetime.fromisoformat(expires):
        return False
    return submitted.strip() == code


def _clear_email_otp() -> None:
    session.pop('email_otp_code', None)
    session.pop('email_otp_expires', None)


# ─────────────────────────────────────────────────────────────────────────────
# Email OTP — Enable (Security Settings)
# ─────────────────────────────────────────────────────────────────────────────

@twofa_bp.route('/security/email-otp/enable', methods=['POST'])
@login_required
def enable_email_otp():
    """Step 1 — send a verification code to the user's email."""
    user = get_current_user()
    if user.email_otp_enabled:
        flash('Email OTP is already enabled.', 'info')
        return redirect(url_for('twofa.security'))

    otp = _generate_email_otp()
    _store_email_otp(otp)
    session['email_otp_setup_user_id'] = user.id

    try:
        from app.services.email import send_email_otp
        send_email_otp(user, otp, EMAIL_OTP_EXPIRY_MINUTES)
        flash(f'A verification code has been sent to {user.email}.', 'info')
    except Exception:
        flash('Could not send email. Please check your mail configuration.', 'danger')
        return redirect(url_for('twofa.security'))

    _log(user.id, 'EMAIL_OTP_SETUP_STARTED')
    return redirect(url_for('twofa.verify_email_otp_setup'))


@twofa_bp.route('/security/email-otp/verify', methods=['GET'])
@login_required
def verify_email_otp_setup():
    """Step 2 — show the code entry form."""
    user = get_current_user()
    if user.email_otp_enabled:
        return redirect(url_for('twofa.security'))
    if session.get('email_otp_setup_user_id') != user.id:
        flash('Session expired. Please start again.', 'warning')
        return redirect(url_for('twofa.security'))
    return render_template('email_otp_setup.html', user=user,
                           expires_minutes=EMAIL_OTP_EXPIRY_MINUTES)


@twofa_bp.route('/security/email-otp/verify-setup', methods=['POST'])
@login_required
def confirm_email_otp_setup():
    """Step 3 — validate code and activate Email OTP."""
    user  = get_current_user()
    token = request.form.get('otp', '').strip()

    if session.get('email_otp_setup_user_id') != user.id:
        flash('Session expired. Please start again.', 'warning')
        return redirect(url_for('twofa.security'))

    if not _validate_email_otp(token):
        flash('Invalid or expired code. Please try again.', 'danger')
        return redirect(url_for('twofa.verify_email_otp_setup'))

    _clear_email_otp()
    session.pop('email_otp_setup_user_id', None)

    user.email_otp_enabled = True
    db.session.commit()

    _log(user.id, 'EMAIL_OTP_ENABLED')
    flash('Email OTP has been enabled. You will receive a code by email on each login.', 'success')
    return redirect(url_for('twofa.security'))


@twofa_bp.route('/security/email-otp/disable', methods=['POST'])
@login_required
def disable_email_otp():
    """Disable Email OTP — requires current password."""
    user     = get_current_user()
    password = request.form.get('password', '')

    if not user.email_otp_enabled:
        flash('Email OTP is not currently enabled.', 'info')
        return redirect(url_for('twofa.security'))

    if not user.check_password(password):
        flash('Incorrect password.', 'danger')
        return redirect(url_for('twofa.security'))

    user.email_otp_enabled = False
    db.session.commit()

    _log(user.id, 'EMAIL_OTP_DISABLED')
    flash('Email OTP has been disabled.', 'success')
    return redirect(url_for('twofa.security'))


# ─────────────────────────────────────────────────────────────────────────────
# Email OTP — Login flow
# ─────────────────────────────────────────────────────────────────────────────

@twofa_bp.route('/auth/email-otp', methods=['GET', 'POST'])
def login_email_otp():
    """
    GET  — send OTP to email, show code entry form.
    POST — verify submitted code and complete login.
    """
    user_id = session.get('pending_2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user or not user.email_otp_enabled:
        session.pop('pending_2fa_user_id', None)
        return redirect(url_for('auth.login'))

    # ── GET: send code ───────────────────────────────────────────────────────
    if request.method == 'GET':
        otp = _generate_email_otp()
        _store_email_otp(otp)
        try:
            from app.services.email import send_email_otp
            send_email_otp(user, otp, EMAIL_OTP_EXPIRY_MINUTES)
        except Exception:
            flash('Could not send verification email. Please try again.', 'danger')
            return redirect(url_for('auth.login'))
        _log(user.id, 'EMAIL_OTP_SENT')
        return render_template('email_otp_login.html', user=None,
                               email=user.email,
                               expires_minutes=EMAIL_OTP_EXPIRY_MINUTES)

    # ── POST: verify code ────────────────────────────────────────────────────
    token = request.form.get('otp', '').strip()

    # Allow resend
    if request.form.get('resend') == '1':
        _clear_email_otp()
        return redirect(url_for('twofa.login_email_otp'))

    if not _validate_email_otp(token):
        _log(user.id, 'EMAIL_OTP_FAILED')
        flash('Invalid or expired code. Please try again.', 'danger')
        return render_template('email_otp_login.html', user=None,
                               email=user.email,
                               expires_minutes=EMAIL_OTP_EXPIRY_MINUTES)

    # ── Success ──────────────────────────────────────────────────────────────
    _clear_email_otp()
    session.pop('pending_2fa_user_id', None)
    session['user_id'] = user.id
    session.permanent  = True

    _log(user.id, 'EMAIL_OTP_LOGIN')
    flash(f'Welcome back, {user.name}!', 'success')
    return redirect(url_for('public.home'))
