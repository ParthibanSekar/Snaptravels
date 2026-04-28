"""
Email service for SnapTravels.

Sends transactional emails via Flask-Mail (SMTP).  When MAIL_ENABLED is False
(MAIL_USERNAME env var not set) every call is a silent no-op so the app works
fine in development without any SMTP configuration.

Configure in .env:
    MAIL_SERVER=smtp.gmail.com
    MAIL_PORT=587
    MAIL_USE_TLS=true
    MAIL_USERNAME=your@gmail.com
    MAIL_PASSWORD=app-password
    MAIL_DEFAULT_SENDER=SnapTravels <noreply@snaptravels.com>
"""

import logging
from flask import current_app, render_template_string
from flask_mail import Message

logger = logging.getLogger('snaptravels.email')


def _send(subject: str, recipients: list, html: str, text: str = None):
    """Internal helper — sends one email, swallows all errors so a mail
    failure never crashes the main request."""
    if not current_app.config.get('MAIL_ENABLED'):
        logger.debug("Mail disabled — skipping: %s → %s", subject, recipients)
        return

    # Chaos: silently drop all emails when email chaos is active
    try:
        from app.services.chaos import should_email_fail
        if should_email_fail():
            logger.warning("[chaos] Email chaos active — silently dropped: %s → %s", subject, recipients)
            return
    except Exception:
        pass

    try:
        from app import mail
        msg = Message(subject=subject,
                      recipients=recipients,
                      html=html,
                      body=text or '')
        mail.send(msg)
        logger.info("Email sent subject=%r to=%s", subject, recipients)
    except Exception as e:
        logger.error("Email send failed subject=%r error=%s", subject, e)


# ── Booking confirmation ────────────────────────────────────────────────────

def send_booking_confirmation(booking):
    """
    Sent immediately after a successful booking (flight, train, bus, cab, hotel).
    `booking` is a Booking model instance with .items loaded.
    """
    items_html = ""
    for item in (booking.items or []):
        d = item.details or {}
        route = ""
        if item.type in ('FLIGHT', 'TRAIN', 'BUS', 'CAB'):
            origin = d.get('origin', d.get('pickup', ''))
            dest   = d.get('destination', d.get('drop', ''))
            route  = f"{origin} → {dest}" if origin else item.title
        elif item.type == 'HOTEL':
            route = f"{d.get('city', '')} · {d.get('nights', 1)} night(s)"
        else:
            route = item.title
        items_html += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #f1f5f9">{item.type}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f1f5f9">{route}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f1f5f9;text-align:right">
            ₹{item.amount:,.0f}
          </td>
        </tr>"""

    html = f"""
    <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f8fafc;margin:0;padding:20px">
    <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;
                box-shadow:0 4px 24px rgba(0,0,0,.08)">
      <!-- Header -->
      <div style="background:linear-gradient(135deg,#16a34a,#15803d);padding:32px 32px 24px;text-align:center">
        <div style="font-size:42px;margin-bottom:8px">✅</div>
        <h1 style="color:#fff;margin:0;font-size:24px">Booking Confirmed!</h1>
        <p style="color:#bbf7d0;margin:8px 0 0;font-size:14px">Your journey is all set</p>
      </div>
      <!-- Body -->
      <div style="padding:32px">
        <p style="color:#374151;margin-top:0">Hi <strong>{booking.customer_name}</strong>,</p>
        <p style="color:#6b7280;font-size:14px">
          Your booking has been confirmed and your e-ticket is ready.
          Keep this email as your reference.
        </p>
        <!-- Booking code pill -->
        <div style="text-align:center;margin:24px 0">
          <div style="display:inline-block;background:#f0fdf4;border:1.5px dashed #86efac;
                      border-radius:10px;padding:10px 24px;font-family:monospace;
                      font-size:20px;font-weight:700;color:#166534;letter-spacing:2px">
            {booking.booking_code}
          </div>
        </div>
        <!-- Journey table -->
        <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
          <thead>
            <tr style="background:#f8fafc">
              <th style="padding:8px 12px;text-align:left;font-size:12px;color:#6b7280;
                         text-transform:uppercase;letter-spacing:.5px">Type</th>
              <th style="padding:8px 12px;text-align:left;font-size:12px;color:#6b7280;
                         text-transform:uppercase;letter-spacing:.5px">Details</th>
              <th style="padding:8px 12px;text-align:right;font-size:12px;color:#6b7280;
                         text-transform:uppercase;letter-spacing:.5px">Amount</th>
            </tr>
          </thead>
          <tbody>{items_html}</tbody>
          <tfoot>
            <tr style="background:#f0fdf4">
              <td colspan="2" style="padding:10px 12px;font-weight:700;color:#166534">Total Paid</td>
              <td style="padding:10px 12px;font-weight:700;color:#166534;text-align:right">
                ₹{booking.total_amount:,.0f}
              </td>
            </tr>
          </tfoot>
        </table>
        <!-- Passenger -->
        <div style="background:#f8fafc;border-radius:10px;padding:16px;margin-bottom:20px">
          <p style="margin:0 0 6px;font-size:13px;color:#6b7280;font-weight:600">PASSENGER</p>
          <p style="margin:0;font-size:15px;color:#1e293b">
            {booking.customer_name} · {booking.customer_email}
            {(' · ' + booking.customer_phone) if booking.customer_phone else ''}
          </p>
        </div>
        <p style="font-size:13px;color:#6b7280;margin-bottom:24px">
          Booked on {booking.created_at.strftime('%B %d, %Y at %I:%M %p UTC')}
        </p>
        <div style="text-align:center">
          <a href="https://snaptravels.com/my-bookings"
             style="background:#16a34a;color:#fff;text-decoration:none;border-radius:30px;
                    padding:12px 28px;font-weight:600;font-size:15px;display:inline-block">
            View My Bookings
          </a>
        </div>
      </div>
      <!-- Footer -->
      <div style="background:#f8fafc;padding:20px 32px;text-align:center;
                  border-top:1px solid #f1f5f9">
        <p style="font-size:12px;color:#94a3b8;margin:0">
          Questions? Email us at
          <a href="mailto:support@snaptravels.com" style="color:#16a34a">support@snaptravels.com</a>
          &nbsp;|&nbsp; SnapTravels, India
        </p>
      </div>
    </div>
    </body></html>
    """

    _send(
        subject=f"✅ Booking Confirmed — {booking.booking_code}",
        recipients=[booking.customer_email],
        html=html,
        text=(f"Booking Confirmed!\n\nCode: {booking.booking_code}\n"
              f"Total: ₹{booking.total_amount:,.0f}\n"
              f"Name: {booking.customer_name}\n\n"
              "View your booking at https://snaptravels.com/my-bookings")
    )


# ── Payment failure alert ───────────────────────────────────────────────────

def send_payment_failed_alert(customer_email: str, customer_name: str,
                               error_type: str, trace_id: str = None):
    """Sent when a booking attempt fails due to a payment/checkout error."""
    html = f"""
    <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#fff5f5;margin:0;padding:20px">
    <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;
                box-shadow:0 4px 24px rgba(239,68,68,.1);border-top:4px solid #ef4444">
      <div style="padding:32px;text-align:center">
        <div style="font-size:48px;margin-bottom:12px">⚠️</div>
        <h1 style="color:#dc2626;margin:0 0 8px;font-size:22px">Payment Not Processed</h1>
        <p style="color:#6b7280;font-size:14px;margin:0">
          Hi {customer_name}, your recent booking attempt did not go through.
        </p>
      </div>
      <div style="padding:0 32px 32px">
        <div style="background:#fef2f2;border-radius:10px;padding:16px;margin-bottom:20px">
          <p style="margin:0 0 6px;font-size:13px;color:#dc2626;font-weight:600">ERROR DETAILS</p>
          <p style="margin:0;font-size:14px;color:#7f1d1d">{error_type}</p>
          {f'<p style="margin:6px 0 0;font-size:12px;color:#9ca3af;font-family:monospace">Ref: {trace_id}</p>' if trace_id else ''}
        </div>
        <div style="background:#f0fdf4;border-radius:10px;padding:14px;margin-bottom:24px">
          <p style="margin:0;font-size:14px;color:#166534">
            ✅ <strong>No charge was made</strong> to your payment method.
            Any pending authorization will clear within 2–3 business days.
          </p>
        </div>
        <div style="text-align:center">
          <a href="https://snaptravels.com"
             style="background:#dc2626;color:#fff;text-decoration:none;border-radius:30px;
                    padding:12px 28px;font-weight:600;font-size:15px;display:inline-block">
            Try Again
          </a>
        </div>
      </div>
      <div style="background:#f8fafc;padding:16px 32px;text-align:center;border-top:1px solid #fef2f2">
        <p style="font-size:12px;color:#94a3b8;margin:0">
          Need help? <a href="mailto:support@snaptravels.com" style="color:#dc2626">support@snaptravels.com</a>
        </p>
      </div>
    </div>
    </body></html>
    """
    _send(
        subject="⚠️ Your SnapTravels Payment Could Not Be Processed",
        recipients=[customer_email],
        html=html,
        text=(f"Hi {customer_name},\n\nYour payment could not be processed ({error_type}).\n"
              "No charge was made. Please try again at https://snaptravels.com\n\n"
              "Support: support@snaptravels.com")
    )


# ── 2FA enabled/disabled alert ──────────────────────────────────────────────

def send_2fa_status_email(user, enabled: bool):
    """Security alert when 2FA is toggled on/off."""
    action = "enabled" if enabled else "disabled"
    icon   = "🔐" if enabled else "🔓"
    color  = "#16a34a" if enabled else "#dc2626"
    html = f"""
    <!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f8fafc;margin:0;padding:20px">
    <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;
                box-shadow:0 4px 24px rgba(0,0,0,.08);border-top:4px solid {color}">
      <div style="padding:28px 32px;text-align:center">
        <div style="font-size:40px">{icon}</div>
        <h2 style="color:{color};margin:10px 0 4px">Two-Factor Auth {action.title()}</h2>
        <p style="color:#6b7280;font-size:14px;margin:0">
          Hi {user.name}, 2FA has been <strong>{action}</strong> on your SnapTravels account.
        </p>
      </div>
      <div style="padding:0 32px 28px">
        {'<p style="font-size:14px;color:#374151">Your account is now more secure. You will need your authenticator app on every login.</p>' if enabled else
         '<p style="font-size:14px;color:#dc2626"><strong>Not you?</strong> Secure your account immediately by resetting your password and re-enabling 2FA.</p>'}
        <div style="text-align:center;margin-top:16px">
          <a href="https://snaptravels.com/security"
             style="background:{color};color:#fff;text-decoration:none;border-radius:30px;
                    padding:10px 24px;font-weight:600;font-size:14px;display:inline-block">
            Security Settings
          </a>
        </div>
      </div>
    </div>
    </body></html>
    """
    _send(
        subject=f"{icon} Two-Factor Authentication {action.title()} — SnapTravels",
        recipients=[user.email],
        html=html
    )


# ── Email OTP ────────────────────────────────────────────────────────────────

def send_email_otp(user, code: str, expires_minutes: int = 10):
    """
    Send a 6-digit OTP to the user's email for Email-OTP 2FA verification.
    `code` is the plain 6-digit string generated by the caller.
    """
    display_name = getattr(user, 'name', None) or user.email.split('@')[0].title()
    html = f"""
    <!DOCTYPE html><html>
    <body style="font-family:Arial,sans-serif;background:#f8fafc;margin:0;padding:20px">
    <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;
                box-shadow:0 4px 24px rgba(0,0,0,.08);border-top:4px solid #6366f1">

      <!-- Header -->
      <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:28px 32px;text-align:center">
        <div style="font-size:40px;margin-bottom:6px">🔐</div>
        <h2 style="color:#fff;margin:0;font-size:20px;font-weight:700">Login Verification Code</h2>
        <p style="color:#c7d2fe;margin:6px 0 0;font-size:13px">SnapTravels account security</p>
      </div>

      <!-- Body -->
      <div style="padding:28px 32px;text-align:center">
        <p style="color:#374151;font-size:14px;margin:0 0 20px;text-align:left">
          Hi <strong>{display_name}</strong>, use the code below to complete your login.
          It expires in <strong>{expires_minutes} minutes</strong>.
        </p>

        <!-- OTP pill -->
        <div style="background:#f5f3ff;border:2px dashed #8b5cf6;border-radius:12px;
                    padding:18px 24px;margin:0 auto 20px;display:inline-block;min-width:200px">
          <div style="font-size:36px;font-weight:800;letter-spacing:10px;color:#6366f1;
                      font-family:monospace">{code}</div>
        </div>

        <p style="color:#9ca3af;font-size:12px;margin:0 0 8px">
          Enter this code on the SnapTravels login page.
        </p>
        <p style="color:#dc2626;font-size:12px;font-weight:600;margin:0">
          ⚠️ Never share this code with anyone — SnapTravels will never ask for it.
        </p>
      </div>

      <!-- Footer -->
      <div style="background:#f9fafb;padding:14px 32px;border-top:1px solid #e5e7eb;text-align:center">
        <p style="color:#9ca3af;font-size:12px;margin:0">
          If you didn't try to log in, your password may be compromised.<br>
          Please reset it immediately at snaptravels.online.
        </p>
      </div>

    </div>
    </body></html>
    """
    _send(
        subject=f"🔐 {code} is your SnapTravels login code",
        recipients=[user.email],
        html=html,
        text=(
            f"Hi {display_name},\n\n"
            f"Your SnapTravels login verification code is: {code}\n\n"
            f"This code expires in {expires_minutes} minutes.\n\n"
            "Never share this code with anyone.\n\n"
            "If you didn't attempt to log in, please reset your password immediately."
        )
    )


# ── Email verification ───────────────────────────────────────────────────────

def send_verification_email(user, token: str):
    """
    Sent after signup to verify the user's email address.
    `token` is the confirmation token stored on the user record.
    """
    display_name = getattr(user, 'name', None) or user.email.split('@')[0].title()
    # Build the confirm URL — uses request context host for production correctness
    from flask import request
    base_url = request.host_url.rstrip('/')
    confirm_url = f"{base_url}/confirm-email/{token}"

    html = f"""
    <!DOCTYPE html><html>
    <body style="font-family:Arial,sans-serif;background:#f0f4ff;margin:0;padding:20px">
    <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;
                box-shadow:0 4px 24px rgba(0,0,0,.08);border-top:4px solid #2563eb">

      <!-- Header -->
      <div style="background:linear-gradient(135deg,#2563eb,#1d4ed8);padding:32px;text-align:center">
        <div style="width:56px;height:56px;margin:0 auto 12px;background:rgba(255,255,255,.2);
                    border-radius:50%;display:flex;align-items:center;justify-content:center">
          <span style="font-size:28px;color:#fff"><i class="bi bi-envelope-check"></i></span>
        </div>
        <h1 style="color:#fff;margin:0;font-size:22px;font-weight:700">Verify Your Email</h1>
        <p style="color:#bfdbfe;margin:6px 0 0;font-size:13px">One click to activate your SnapTravels account</p>
      </div>

      <!-- Body -->
      <div style="padding:28px 32px">
        <p style="color:#374151;font-size:15px;margin:0 0 16px">
          Hi <strong>{display_name}</strong>,
        </p>
        <p style="color:#6b7280;font-size:14px;line-height:1.6;margin:0 0 24px">
          Thanks for signing up! Please verify your email address to activate your
          account and start booking.
        </p>

        <!-- CTA button -->
        <div style="text-align:center;margin:28px 0">
          <a href="{confirm_url}"
             style="background:#2563eb;color:#fff;text-decoration:none;border-radius:30px;
                    padding:14px 36px;font-weight:700;font-size:15px;display:inline-block;
                    letter-spacing:.3px">
            Verify My Email
          </a>
        </div>

        <p style="color:#9ca3af;font-size:12px;text-align:center;margin:0 0 16px">
          Or copy and paste this link into your browser:
        </p>
        <div style="background:#f1f5f9;border-radius:8px;padding:10px 14px;
                    word-break:break-all;font-family:monospace;font-size:12px;color:#475569;
                    margin-bottom:24px">
          {confirm_url}
        </div>

        <div style="background:#fef3c7;border:1px solid #fde68a;border-radius:10px;
                    padding:12px 16px;font-size:13px;color:#92400e">
          This link expires in <strong>24 hours</strong>. If you didn't create a
          SnapTravels account, you can safely ignore this email.
        </div>
      </div>

      <!-- Footer -->
      <div style="background:#f9fafb;padding:14px 32px;text-align:center;border-top:1px solid #e5e7eb">
        <p style="color:#9ca3af;font-size:12px;margin:0">
          &copy; 2025 SnapTravels. All rights reserved.
        </p>
      </div>

    </div>
    </body></html>
    """
    _send(
        subject="Verify your email — SnapTravels",
        recipients=[user.email],
        html=html,
        text=(
            f"Hi {display_name},\n\n"
            "Thanks for signing up at SnapTravels! Please verify your email:\n\n"
            f"{confirm_url}\n\n"
            "This link expires in 24 hours.\n\n"
            "If you didn't create an account, ignore this email.\n\n"
            "— The SnapTravels Team"
        )
    )


# ── Signup welcome email ─────────────────────────────────────────────────────

def send_signup_welcome(user):
    """
    Sent immediately after a new account is created.
    `user` is a User model instance with .email and .name attributes.
    """
    display_name = getattr(user, 'name', None) or user.email.split('@')[0].title()
    html = f"""
    <!DOCTYPE html><html>
    <body style="font-family:Arial,sans-serif;background:#f0fdf4;margin:0;padding:20px">
    <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;
                box-shadow:0 4px 24px rgba(0,0,0,.08);border-top:4px solid #16a34a">

      <!-- Header -->
      <div style="background:linear-gradient(135deg,#16a34a,#15803d);padding:32px;text-align:center">
        <div style="font-size:48px;margin-bottom:8px">✈️</div>
        <h1 style="color:#fff;margin:0;font-size:24px;font-weight:700">Welcome to SnapTravels!</h1>
        <p style="color:#bbf7d0;margin:6px 0 0;font-size:14px">Your journey starts here</p>
      </div>

      <!-- Body -->
      <div style="padding:28px 32px">
        <p style="color:#374151;font-size:15px;margin:0 0 16px">
          Hi <strong>{display_name}</strong>, great to have you on board!
        </p>
        <p style="color:#6b7280;font-size:14px;line-height:1.6;margin:0 0 24px">
          Your SnapTravels account is all set. You can now search and book flights,
          trains, buses, cabs, and hotels — all in one place.
        </p>

        <!-- Feature chips -->
        <table cellspacing="0" cellpadding="0" width="100%"
               style="margin-bottom:24px;border-collapse:collapse">
          <tr>
            <td style="padding:4px">
              <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
                          padding:10px 14px;font-size:13px;color:#166534">
                🛫 &nbsp;Flights
              </div>
            </td>
            <td style="padding:4px">
              <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
                          padding:10px 14px;font-size:13px;color:#166534">
                🚆 &nbsp;Trains
              </div>
            </td>
            <td style="padding:4px">
              <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
                          padding:10px 14px;font-size:13px;color:#166534">
                🚌 &nbsp;Buses
              </div>
            </td>
            <td style="padding:4px">
              <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
                          padding:10px 14px;font-size:13px;color:#166534">
                🏨 &nbsp;Hotels
              </div>
            </td>
          </tr>
        </table>

        <!-- CTA -->
        <div style="text-align:center;margin:24px 0 8px">
          <a href="https://snaptravels.com"
             style="background:#16a34a;color:#fff;text-decoration:none;border-radius:30px;
                    padding:12px 32px;font-weight:700;font-size:15px;display:inline-block;
                    letter-spacing:0.3px">
            Start Exploring
          </a>
        </div>
      </div>

      <!-- Footer -->
      <div style="background:#f9fafb;padding:16px 32px;text-align:center;
                  border-top:1px solid #e5e7eb">
        <p style="color:#9ca3af;font-size:12px;margin:0">
          You're receiving this because you signed up at SnapTravels.<br>
          &copy; 2025 SnapTravels. All rights reserved.
        </p>
      </div>

    </div>
    </body></html>
    """
    _send(
        subject="Welcome to SnapTravels — your account is ready!",
        recipients=[user.email],
        html=html,
        text=(
            f"Hi {display_name},\n\n"
            "Welcome to SnapTravels! Your account is all set.\n\n"
            "You can now search and book flights, trains, buses, cabs, and hotels "
            "all in one place.\n\n"
            "Start exploring: https://snaptravels.com\n\n"
            "— The SnapTravels Team"
        )
    )
