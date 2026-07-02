"""
Email notification service for low stock alerts (F2.3).
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from services.database import DatabaseManager
from utils.crypto import decrypt_value
from utils.logger import setup_logger

logger = setup_logger(__name__)


def get_smtp_config(db: DatabaseManager) -> dict[str, str]:
    return {
        "host": db.obtener_config("smtp_host", ""),
        "port": db.obtener_config("smtp_port", "587"),
        "user": db.obtener_config("smtp_user", ""),
        "password": decrypt_value(db.obtener_config("smtp_password", "")),
        "from_email": db.obtener_config("smtp_from_email", ""),
        "to_email": db.obtener_config("smtp_to_email", ""),
        "enabled": db.obtener_config("notify_low_stock", "no"),
    }


def is_configured(cfg: dict[str, str]) -> bool:
    return bool(cfg.get("host") and cfg.get("user") and cfg.get("password") and cfg.get("to_email"))


def send_low_stock_alert(db: DatabaseManager) -> dict:
    """Check low stock products and send email alert if configured."""
    cfg = get_smtp_config(db)
    if cfg.get("enabled") != "si" or not is_configured(cfg):
        return {"sent": False, "reason": "Not configured or disabled"}

    low_stock = db.obtener_productos_stock_bajo()
    if not low_stock:
        return {"sent": False, "reason": "No low stock products"}

    return _send_email(cfg, low_stock)


def send_custom_alert(db: DatabaseManager, subject: str, body: str) -> dict:
    cfg = get_smtp_config(db)
    if not is_configured(cfg):
        return {"sent": False, "reason": "SMTP not configured"}
    return _send_email_raw(cfg, subject, body)


def _send_email(cfg: dict[str, str], low_stock: list[dict]) -> dict:
    rows = "\n".join(
        f"- {p.get('nombre', '?')} (código: {p.get('codigo', '?')}): "
        f"{p.get('cantidad', 0)} / min: {p.get('stock_min', 0)}"
        for p in low_stock
    )
    subject = f"Alerta de stock bajo - {len(low_stock)} producto(s)"
    body = f"Los siguientes productos tienen stock bajo:\n\n{rows}\n\n-- InventarioStore"
    return _send_email_raw(cfg, subject, body)


def _send_email_raw(cfg: dict[str, str], subject: str, body: str) -> dict:
    try:
        msg = MIMEMultipart()
        msg["From"] = cfg["from_email"] or cfg["user"]
        msg["To"] = cfg["to_email"]
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP(cfg["host"], int(cfg["port"]), timeout=15) as server:
            server.starttls(context=context)
            server.login(cfg["user"], cfg["password"])
            server.send_message(msg)

        logger.info(f"Email alert sent to {cfg['to_email']}: {subject}")
        return {"sent": True, "subject": subject, "to": cfg["to_email"]}
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return {"sent": False, "reason": str(e)}
