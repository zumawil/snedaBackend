"""
utils/sendEmail.py
Email helpers that use Django's built-in send_mail (SMTP via Gmail).
All SMTP credentials come from Django settings (configured in settings.py / .env).
"""

import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)


def _send_html_email(to: str, subject: str, html: str) -> None:
    """
    Internal helper: send a single HTML email via Django's email backend.
    Raises on error so callers (or Celery tasks) can retry.
    """
    msg = EmailMultiAlternatives(
        subject=subject,
        body="Please view this email in an HTML-capable client.",  # plain-text fallback
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to],
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)
    logger.info("Email sent | to=%s | subject=%s", to, subject)


def send_otp_email(to: str, subject: str, html: str) -> None:
    """Send a one-time-password email."""
    _send_html_email(to, subject, html)


def send_order_confirmation_email(to: str, subject: str, html: str) -> None:
    """Send an order-confirmation email."""
    _send_html_email(to, subject, html)


def send_admin_notification_email(to: str, subject: str, html: str) -> None:
    """Send admin-generated notification email (approval, rejection, shipping updates)."""
    _send_html_email(to, subject, html)