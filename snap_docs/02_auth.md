# SnapTravels — Authentication & Security

## Auth Mechanism

- **Session-based:** `session['user_id']` set on login, cleared on logout
- **Password hashing:** Werkzeug `generate_password_hash` / `check_password_hash`
- **CSRF:** Flask-WTF protects ALL forms via `{{ csrf_token() }}` hidden field — EXCEPT `mobile_api.py` and `pwa.py` blueprints (explicitly CSRF-exempt)
- **Rate limiting:** Flask-Limiter — login POST: 10/minute, 30/hour

## Route Guards (app/services/auth.py)

```python
@login_required          # Redirects to /login if not logged in
@roles_required('admin') # 403 if not admin role; stacks on top of @login_required
```

## Blueprint: auth.py — Routes

| Route | Method | Description |
|---|---|---|
| `/login` | GET/POST | Login form — passes through chaos `maybe_fail_login()` |
| `/signup` | GET/POST | Register new user |
| `/logout` | GET | Clears session |

## Two-Factor Authentication (blueprint: two_factor.py)

### Setup flow
- `/2fa/setup` — Shows QR code for TOTP; user scans with Google Authenticator / Authy
- `/2fa/setup/verify` — POST: validates first TOTP code, stores encrypted secret in DB
- `/2fa/disable` — Turns off 2FA

### Login flow (when 2FA is enabled)
1. Normal login succeeds → session flag `2fa_pending = True`
2. Redirected to `/2fa/login` — user enters 6-digit TOTP code
3. OR user can request `/2fa/email-otp` — receives OTP via email

### Storage
- TOTP secret: Fernet-encrypted, stored in `User.totp_secret`
- "Remember this device" cookie: HMAC-signed, 30-day expiry, bypasses 2FA on trusted devices
- 8 single-use **backup codes** stored as `pbkdf2` hashes in `BackupCode` table
- Full event audit log in `TwoFactorLog` (event_type, IP, timestamp)

## Templates

| Template | Purpose |
|---|---|
| `login.html` | Login page (uses `auth_base.html` layout) |
| `signup.html` | Registration page |
| `2fa_setup.html` | QR code + secret display |
| `2fa_login.html` | TOTP entry during login |
| `2fa_email_otp.html` | Email OTP entry |
| `backup_codes.html` | Show backup codes after setup |

## User Model Fields (auth-relevant)

```python
User.email          # Unique, login identifier
User.password_hash  # Werkzeug hash
User.role           # 'user' or 'admin'
User.name           # Display name
User.totp_secret    # Fernet-encrypted TOTP secret (null if 2FA off)
User.email_otp_enabled  # Boolean
User.is_verified    # Email verified flag
```

## Security Settings Page

- Route: `/security` (user_dashboard.py)
- Allows: change password, enable/disable TOTP 2FA, view backup codes, see recent login activity
