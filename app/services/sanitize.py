"""
app/services/sanitize.py
------------------------
Shared input sanitization and server-side validation helpers.
Used by BOTH the mobile API (mobile_api.py) and all web booking blueprints
(public.py, trains.py, buses.py, cabs.py, packages.py, activities.py,
insurance.py).

Rules mirror the client-side validators in the Android app
(src/utils/validators.ts) exactly so the same bad input is rejected at both
layers.
"""

import re
import html as _html

__all__ = [
    'sanitize_str',
    'sanitize_int',
    'validate_name_server',
    'validate_email_server',
    'validate_phone_server',
    'sanitize_booking_customer',
]


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def sanitize_str(value, max_len=200):
    """
    Strip HTML/script tags, HTML-escape special characters, enforce max length.
    Always returns a plain string — never None.
    """
    if not value:
        return ''
    # Remove any HTML tags  (<script>, <img onerror=...>, etc.)
    cleaned = re.sub(r'<[^>]+>', '', str(value))
    # Escape &, <, >, ", ' so the stored value is safe to render anywhere
    cleaned = _html.escape(cleaned.strip())
    return cleaned[:max_len]


def sanitize_int(value, default=0, min_val=None, max_val=None):
    """Safely cast to int with optional bounds, returning *default* on failure."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    if min_val is not None:
        v = max(min_val, v)
    if max_val is not None:
        v = min(max_val, v)
    return v


# ---------------------------------------------------------------------------
# Field validators — return (clean_value, error_string_or_None)
# ---------------------------------------------------------------------------

def validate_name_server(name):
    """
    Letters, spaces, hyphens, apostrophes, dots only. 2–100 chars.
    Returns (sanitized_name, None) on success or (None, error_message) on fail.
    """
    s = str(name or '').strip()
    if not s:
        return None, 'Name is required'
    if len(s) < 2:
        return None, 'Name must be at least 2 characters'
    if len(s) > 100:
        return None, 'Name must be under 100 characters'
    if re.search(r'\d', s):
        return None, 'Name must not contain numbers'
    if not re.match(r"^[A-Za-z\s\-'.]+$", s):
        return None, 'Name contains invalid characters'
    return sanitize_str(s, 100), None


def validate_email_server(email):
    """Standard email format. Returns (lowercased_email, None) or (None, error)."""
    s = str(email or '').strip().lower()
    if not s:
        return None, 'Email is required'
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$', s):
        return None, 'Enter a valid email address'
    return sanitize_str(s, 120), None


def validate_phone_server(phone):
    """
    Indian mobile: exactly 10 digits, starts with 6–9.
    Returns (digits_only_string, None) or (None, error).
    Phone is optional in some web forms — pass '' to skip.
    """
    digits = re.sub(r'\D', '', str(phone or ''))
    if not digits:
        # Return empty string (not an error) — callers decide if required
        return '', None
    if len(digits) != 10:
        return None, 'Phone must be exactly 10 digits'
    if not re.match(r'^[6-9]', digits):
        return None, 'Enter a valid Indian mobile number (starts with 6–9)'
    return digits, None


# ---------------------------------------------------------------------------
# Combined customer block validator (used by booking handlers)
# ---------------------------------------------------------------------------

def sanitize_booking_customer(data, phone_required=True):
    """
    Validate and sanitize customer_name / customer_email / customer_phone
    from a dict (request.form or request.get_json()).

    Returns (clean_dict, errors_dict).
    *clean_dict* contains sanitized values for keys that passed.
    *errors_dict* maps field names to error messages for failed keys.
    If errors_dict is non-empty the caller should abort the booking.

    phone_required=True  → empty phone is an error
    phone_required=False → empty phone is accepted (web forms where optional)
    """
    errors = {}
    clean = {}

    name, err = validate_name_server(data.get('customer_name', ''))
    if err:
        errors['customer_name'] = err
    else:
        clean['customer_name'] = name

    email, err = validate_email_server(data.get('customer_email', ''))
    if err:
        errors['customer_email'] = err
    else:
        clean['customer_email'] = email

    phone, err = validate_phone_server(data.get('customer_phone', ''))
    if err:
        errors['customer_phone'] = err
    elif not phone and phone_required:
        errors['customer_phone'] = 'Phone number is required'
    else:
        clean['customer_phone'] = phone or ''

    return clean, errors
