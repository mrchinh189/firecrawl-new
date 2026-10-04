"""Alert channels: Telegram bot and/or SMTP email. Both are optional."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText

import requests

log = logging.getLogger(__name__)


def send_telegram(text: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=30,
    )
    if not resp.ok:
        log.error("Telegram send failed: %s %s", resp.status_code, resp.text[:200])
    return resp.ok


def send_email(subject: str, text: str) -> bool:
    host = os.getenv("SMTP_HOST")
    to_addrs = [a.strip() for a in os.getenv("ALERT_EMAIL_TO", "").split(",") if a.strip()]
    if not host or not to_addrs:
        return False
    user = os.getenv("SMTP_USER", "")
    sender = os.getenv("ALERT_EMAIL_FROM") or user
    msg = MIMEText(text, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to_addrs)
    try:
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=30) as smtp:
            smtp.starttls()
            if user:
                smtp.login(user, os.getenv("SMTP_PASSWORD", ""))
            smtp.sendmail(sender, to_addrs, msg.as_string())
        return True
    except (smtplib.SMTPException, OSError) as exc:
        log.error("Email send failed: %s", exc)
        return False


def notify(subject: str, text: str) -> bool:
    sent_tg = send_telegram(f"{subject}\n\n{text}")
    sent_mail = send_email(subject, text)
    if not (sent_tg or sent_mail):
        log.warning("No alert channel configured (TELEGRAM_* or SMTP_*); alert only logged:\n%s", text)
    return sent_tg or sent_mail
