"""Gửi cảnh báo qua Telegram và/hoặc Email khi giá biến động mạnh."""

import os
import smtplib
from email.mime.text import MIMEText

import requests


def send_telegram(message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=15,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[telegram][LỖI] {e}")


def send_email(subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST")
    to = os.getenv("ALERT_EMAIL_TO")
    if not host or not to:
        return
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = os.getenv("SMTP_USER", "noreply@masterbatch-monitor")
        msg["To"] = to
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587"))) as server:
            server.starttls()
            user = os.getenv("SMTP_USER")
            pwd = os.getenv("SMTP_PASSWORD")
            if user and pwd:
                server.login(user, pwd)
            server.send_message(msg)
    except Exception as e:  # noqa: BLE001
        print(f"[email][LỖI] {e}")


def notify(message: str, subject: str = "Cảnh báo giá NVL masterbatch") -> None:
    print("[ALERT] " + message.replace("<b>", "").replace("</b>", ""))
    send_telegram(message)
    send_email(subject, message.replace("<b>", "").replace("</b>", ""))
