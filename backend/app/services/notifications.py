"""Optional email alert when a customer newly becomes high risk.

Disabled unless SMTP_HOST, ALERT_EMAIL_FROM and ALERT_EMAIL_TO are set. Alerts
carry the customer ID and score only, never personal details.
"""

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger(__name__)


def email_enabled() -> bool:
    s = get_settings()
    return bool(s.smtp_host and s.alert_email_from and s.alert_email_to)


def notify_new_high_risk(customer_id: str, score: int) -> bool:
    if not email_enabled():
        return False
    s = get_settings()
    msg = EmailMessage()
    msg["Subject"] = f"[Return Risk] {customer_id} flagged for manual review (score {score})"
    msg["From"] = s.alert_email_from
    msg["To"] = s.alert_email_to
    msg.set_content(
        f"Customer {customer_id} now has a HIGH return risk score of {score}.\n"
        "This is a prompt to review the customer's return history, not a finding of fraud.\n"
    )
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if s.smtp_username:
                smtp.login(s.smtp_username, s.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception:  # noqa: BLE001 - an alert failure must never break scoring
        logger.exception("Failed to send high-risk alert for %s", customer_id)
        return False
