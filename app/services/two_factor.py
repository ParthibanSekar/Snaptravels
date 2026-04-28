"""
SnapTravels — Two-Factor Authentication service layer.

Handles:
  * TOTP secret generation, encryption at rest, and verification (pyotp)
  * QR code generation (qrcode)
  * Backup code generation and hashing (pbkdf2)
  * Fernet-based symmetric encryption of the TOTP secret
  * Rate-limit helpers (session-based)
  * Remember-device cookie signing (HMAC)

All crypto primitives use standard library or well-audited packages.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import secrets
import time
from datetime import datetime, timedelta
from typing import Tuple, List

import pyotp
import qrcode
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash, check_password_hash


# ── Constants ────────────────────────────────────────────────────────────────

ISSUER_NAME       = 'SnapTravels'
TOTP_WINDOW       = 1          # ±1 time-step tolerance (30 s each → ±60 s)
BACKUP_CODE_COUNT = 10
MAX_OTP_ATTEMPTS  = 5
OTP_LOCKOUT_SECS  = 900        # 15 minutes
REMEMBER_DEVICE_DAYS = 30


# ── Fernet key derivation ─────────────────────────────────────────────────────

def _get_fernet(app) -> Fernet:
    """
    Derive a Fernet key from the Flask app's SECRET_KEY.
    SHA-256 of the key gives a 32-byte value which Fernet needs
    encoded as URL-safe base64.
    """
    raw = hashlib.sha256(app.config['SECRET_KEY'].encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


# ── Secret management ─────────────────────────────────────────────────────────

def generate_totp_secret() -> str:
    """Return a fresh random base32 TOTP secret."""
    return pyotp.random_base32()


def encrypt_secret(secret: str, app) -> str:
    """Encrypt the TOTP secret for storage in the DB."""
    return _get_fernet(app).encrypt(secret.encode()).decode()


def decrypt_secret(enc_secret: str, app) -> str:
    """Decrypt a stored TOTP secret."""
    return _get_fernet(app).decrypt(enc_secret.encode()).decode()


# ── TOTP provisioning URI & QR code ──────────────────────────────────────────

def get_totp_uri(secret: str, email: str) -> str:
    """Return the otpauth:// URI used to provision an authenticator app."""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=ISSUER_NAME,
    )


def generate_qr_b64(uri: str) -> str:
    """
    Render the provisioning URI as a QR code.
    Returns a base64-encoded PNG string ready for <img src="data:image/png;base64,...">
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


# ── TOTP verification ─────────────────────────────────────────────────────────

def verify_totp(secret: str, token: str) -> bool:
    """
    Verify a 6-digit TOTP token.
    Allows ±TOTP_WINDOW steps to handle small clock drift.
    Strips spaces/dashes so users can enter '123 456' or '123-456'.
    """
    token = token.strip().replace(' ', '').replace('-', '')
    if not token.isdigit() or len(token) != 6:
        return False
    return pyotp.TOTP(secret).verify(token, valid_window=TOTP_WINDOW)


# ── Backup codes ──────────────────────────────────────────────────────────────

def generate_backup_codes() -> Tuple[List[str], List[str]]:
    """
    Generate BACKUP_CODE_COUNT one-time backup codes.

    Returns:
        plain_codes  — list of user-visible 'XXXX-XXXX' strings
        hashed_codes — list of pbkdf2:sha256 hashes to store in DB
    """
    plain_codes:  List[str] = []
    hashed_codes: List[str] = []
    for _ in range(BACKUP_CODE_COUNT):
        raw = secrets.token_hex(4).upper()           # 8 hex chars = 32 bits
        formatted = f"{raw[:4]}-{raw[4:]}"           # 'A3F8-B21C'
        plain_codes.append(formatted)
        # Hash the normalized (no dash) version
        hashed_codes.append(
            generate_password_hash(raw, method='pbkdf2:sha256', salt_length=16)
        )
    return plain_codes, hashed_codes


def verify_backup_code(plain: str, hashed: str) -> bool:
    """
    Check a user-supplied backup code against a stored hash.
    Normalizes input by removing dashes and uppercasing.
    """
    normalized = plain.strip().replace('-', '').replace(' ', '').upper()
    return check_password_hash(hashed, normalized)


# ── Rate-limiting helpers (session-based) ─────────────────────────────────────

def record_otp_attempt(session: dict) -> None:
    """Increment the OTP attempt counter in the Flask session."""
    now = int(time.time())
    attempts = session.get('otp_attempts', [])
    # Keep only attempts within the lockout window
    attempts = [t for t in attempts if now - t < OTP_LOCKOUT_SECS]
    attempts.append(now)
    session['otp_attempts'] = attempts


def is_otp_locked(session: dict) -> bool:
    """Return True if the user has exceeded MAX_OTP_ATTEMPTS in the window."""
    now = int(time.time())
    attempts = session.get('otp_attempts', [])
    recent = [t for t in attempts if now - t < OTP_LOCKOUT_SECS]
    return len(recent) >= MAX_OTP_ATTEMPTS


def otp_lockout_remaining(session: dict) -> int:
    """Return seconds until the oldest attempt ages out of the window (0 if not locked)."""
    if not is_otp_locked(session):
        return 0
    now = int(time.time())
    attempts = sorted(session.get('otp_attempts', []))
    recent = [t for t in attempts if now - t < OTP_LOCKOUT_SECS]
    if not recent:
        return 0
    return OTP_LOCKOUT_SECS - (now - recent[0])


def clear_otp_attempts(session: dict) -> None:
    session.pop('otp_attempts', None)


# ── Remember-device cookie ────────────────────────────────────────────────────

def make_remember_device_token(user_id: int, user_agent: str, secret_key: str) -> str:
    """
    Create an HMAC-signed token embedding user_id and a nonce.
    Format: <nonce>.<user_id>.<hmac>
    """
    nonce    = secrets.token_hex(16)
    payload  = f"{nonce}.{user_id}"
    sig      = hmac.new(
        secret_key.encode(),
        f"{payload}.{user_agent[:100]}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{sig}"


def verify_remember_device_token(token: str, user_id: int,
                                  user_agent: str, secret_key: str) -> bool:
    """
    Verify the remember-device token matches the current user and user-agent.
    Returns True only if the token is valid and belongs to user_id.
    """
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return False
        nonce, tid, sig = parts
        if int(tid) != user_id:
            return False
        payload = f"{nonce}.{tid}"
        expected = hmac.new(
            secret_key.encode(),
            f"{payload}.{user_agent[:100]}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False
