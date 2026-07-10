from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, current_app
from app.models import User
from app.forms import LoginForm, SignupForm
from app import db, limiter
from app.services.chaos import maybe_fail_login, LoginChaosError
from urllib.parse import urlparse
from datetime import datetime, timedelta
import logging
import secrets
import re

logger = logging.getLogger('snaptravels.auth')


def _safe_next(next_url: str | None) -> str:
    """Return next_url only if it is a safe internal relative path.
    Rejects absolute URLs (http://evil.com) and protocol-relative URLs (//evil.com)
    to prevent open-redirect attacks."""
    if not next_url:
        return url_for('public.home')
    parsed = urlparse(next_url)
    # Allow only relative paths — no scheme, no netloc
    if parsed.scheme or parsed.netloc:
        return url_for('public.home')
    return next_url

auth_bp = Blueprint('auth', __name__)

# ── Token helpers ──────────────────────────────────────────────────────────

TOKEN_EXPIRY_HOURS = 24

def _generate_confirmation_token():
    """Generate a cryptographically secure URL-safe token."""
    return secrets.token_urlsafe(48)


def _is_token_expired(sent_at):
    """Check if a confirmation token has expired (24 hours)."""
    if not sent_at:
        return True
    return datetime.utcnow() > sent_at + timedelta(hours=TOKEN_EXPIRY_HOURS)


# ── Login ──────────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.exempt
def login():
    if 'user_id' in session:
        return redirect(url_for('public.home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        # ── Chaos injection: login failure rate & login slowness ──────────
        # Admin accounts are exempt so they can always reach the chaos panel.
        is_admin = user and getattr(user, 'role', None) == 'admin'
        if not is_admin:
            try:
                maybe_fail_login(email=form.email.data)
            except LoginChaosError as e:
                flash(str(e), 'error')
                return render_template('login.html', form=form, user=None)

        if user and user.check_password(form.password.data):
            # ── Email verification check ────────────────────────────────────
            if not user.email_confirmed and user.role != 'admin':
                logger.warning('LOGIN_BLOCKED_UNVERIFIED email=%s ip=%s', user.email, request.remote_addr)
                flash('Please verify your email address before signing in. '
                      'Check your inbox for the verification link.', 'warning')
                return render_template('login.html', form=form, user=None,
                                       show_resend=True, resend_email=user.email)

            # ── 2FA check ────────────────────────────────────────────────────
            if user.totp_enabled:
                # Check if this device is trusted (remember-device cookie)
                from app.services.two_factor import verify_remember_device_token
                rd_token = request.cookies.get('remember_device', '')
                ua       = request.headers.get('User-Agent', '')
                if rd_token and verify_remember_device_token(
                        rd_token, user.id, ua, current_app.config['SECRET_KEY']):
                    # Trusted device — skip OTP
                    session['user_id'] = user.id
                    session.permanent  = form.remember_me.data
                    flash(f'Welcome back, {user.name}!', 'success')
                    return redirect(_safe_next(request.args.get('next')))
                else:
                    # Require authenticator OTP
                    session['pending_2fa_user_id'] = user.id
                    session['pending_2fa_remember'] = form.remember_me.data
                    return redirect(url_for('twofa.login_otp'))
            elif user.email_otp_enabled:
                # Require email OTP
                session['pending_2fa_user_id'] = user.id
                session['pending_2fa_remember'] = form.remember_me.data
                return redirect(url_for('twofa.login_email_otp'))
            # ── No 2FA: normal login ─────────────────────────────────────────
            session['user_id'] = user.id
            session.permanent = form.remember_me.data

            logger.info('LOGIN_SUCCESS email=%s user_id=%d ip=%s', user.email, user.id, request.remote_addr)
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(_safe_next(request.args.get('next')))
        else:
            logger.warning('LOGIN_FAILED email=%s ip=%s reason=invalid_credentials', form.email.data, request.remote_addr)
            flash('Invalid email or password.', 'error')

    return render_template('login.html', form=form, user=None)


# ── Signup ─────────────────────────────────────────────────────────────────

@auth_bp.route('/signup', methods=['GET', 'POST'])
@limiter.limit("10 per minute; 30 per hour")
def signup():
    if 'user_id' in session:
        return redirect(url_for('public.home'))

    form = SignupForm()

    if form.validate_on_submit():
        # Create user — NOT confirmed yet
        token = _generate_confirmation_token()
        user = User(
            email=form.email.data,
            email_confirmed=False,
            confirmation_token=token,
            confirmation_sent_at=datetime.utcnow()
        )
        user.set_password(form.password.data)

        try:
            db.session.add(user)
            db.session.commit()

            logger.info('SIGNUP email=%s user_id=%d ip=%s', user.email, user.id, request.remote_addr)

            # Send verification email (non-blocking)
            try:
                from app.services.email import send_verification_email
                send_verification_email(user, token)
                logger.info('VERIFICATION_EMAIL_SENT email=%s', user.email)
            except Exception as email_err:
                logger.error('VERIFICATION_EMAIL_FAILED email=%s error=%s', user.email, email_err)

            flash('Account created! Please check your email to verify your address.', 'success')
            return redirect(url_for('auth.check_email', email=user.email))

        except Exception as e:
            db.session.rollback()
            logger.error('SIGNUP_FAILED email=%s error=%s ip=%s', form.email.data, e, request.remote_addr)
            flash('Registration failed. Please try again.', 'error')

    return render_template('signup.html', form=form, user=None)


# ── Email confirmation ─────────────────────────────────────────────────────

@auth_bp.route('/confirm-email/<token>')
def confirm_email(token):
    """Validate the token and mark the user as confirmed."""
    user = User.query.filter_by(confirmation_token=token).first()

    if not user:
        logger.warning('EMAIL_CONFIRM_INVALID_TOKEN token=%s… ip=%s', token[:12], request.remote_addr)
        flash('Invalid or expired verification link.', 'error')
        return redirect(url_for('auth.login'))

    if user.email_confirmed:
        logger.info('EMAIL_CONFIRM_ALREADY_VERIFIED email=%s', user.email)
        flash('Your email is already verified. Please sign in.', 'info')
        return redirect(url_for('auth.login'))

    if _is_token_expired(user.confirmation_sent_at):
        logger.warning('EMAIL_CONFIRM_EXPIRED email=%s', user.email)
        flash('This verification link has expired. Please request a new one.', 'warning')
        return redirect(url_for('auth.check_email', email=user.email))

    # Confirm the user
    user.email_confirmed = True
    user.confirmation_token = None  # Invalidate token after use
    db.session.commit()

    logger.info('EMAIL_CONFIRMED email=%s user_id=%d ip=%s', user.email, user.id, request.remote_addr)

    # Send welcome email now that they're verified
    try:
        from app.services.email import send_signup_welcome
        send_signup_welcome(user)
    except Exception:
        pass

    flash('Email verified successfully! You can now sign in.', 'success')
    return redirect(url_for('auth.login'))


# ── Check-your-email page ─────────────────────────────────────────────────

@auth_bp.route('/check-email')
def check_email():
    """Post-signup page instructing the user to check their inbox."""
    email = request.args.get('email', '')
    return render_template('check_email.html', email=email, user=None)


# ── Resend verification email ─────────────────────────────────────────────

@auth_bp.route('/resend-confirmation', methods=['POST'])
@limiter.limit("5 per minute; 20 per hour")
def resend_confirmation():
    """Resend the verification email with a fresh token."""
    email = request.form.get('email', '').strip()
    user = User.query.filter_by(email=email).first()

    if user and not user.email_confirmed:
        # Generate a fresh token
        token = _generate_confirmation_token()
        user.confirmation_token = token
        user.confirmation_sent_at = datetime.utcnow()
        db.session.commit()

        try:
            from app.services.email import send_verification_email
            send_verification_email(user, token)
            logger.info('RESEND_VERIFICATION email=%s ip=%s', email, request.remote_addr)
        except Exception as e:
            logger.error('RESEND_VERIFICATION_FAILED email=%s error=%s', email, e)

    # Always show success to prevent email enumeration
    flash('If that email is registered, a new verification link has been sent.', 'info')
    return redirect(url_for('auth.check_email', email=email))


# ── Logout ─────────────────────────────────────────────────────────────────

@auth_bp.route('/logout')
def logout():
    uid = session.get('user_id', '?')
    session.clear()
    logger.info('LOGOUT user_id=%s ip=%s', uid, request.remote_addr)
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.home'))
