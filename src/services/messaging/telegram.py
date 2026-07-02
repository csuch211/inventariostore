"""Telegram sender via Bot API.

Uses httpx.AsyncClient to call ``https://api.telegram.org/bot<TOKEN>/sendMessage``.
Config keys (stored in DB table ``configuracion``)::

    tg_bot_token     — Telegram bot token
    tg_chat_id       — target chat/group/channel ID
    tg_enabled       — "si" / "no"
"""

from services.messaging.base import MessageSender
from utils.crypto import decrypt_value
from utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

API_BASE = "https://api.telegram.org/bot"
REQUIRED_KEYS = frozenset({"tg_bot_token", "tg_chat_id"})
CONFIG_KEYS = frozenset({"tg_bot_token", "tg_chat_id", "tg_enabled"})


class TelegramSender(MessageSender):
    """Send messages via Telegram Bot API."""

    async def send(
        self, destinatario: str, asunto: str, cuerpo: str, config: dict
    ) -> dict:
        valid, msg = self.validate_config(config)
        if not valid:
            return {"sent": False, "reason": msg}
        if config.get("tg_enabled", "no") != "si":
            return {"sent": False, "reason": "Telegram channel disabled"}

        token = decrypt_value(config["tg_bot_token"])
        chat_id = destinatario or config.get("tg_chat_id", "")
        url = f"{API_BASE}{token}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": cuerpo,
            "parse_mode": "HTML",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, json=payload)
                data = resp.json()
                if resp.is_success and data.get("ok"):
                    msg_id = data.get("result", {}).get("message_id", "")
                    logger.info("Telegram msg sent to %s (id=%s)", chat_id, msg_id)
                    return {"sent": True, "message_id": str(msg_id)}
                else:
                    desc = data.get("description", resp.text)
                    logger.error("Telegram API error: %s", desc)
                    return {"sent": False, "reason": desc}
        except Exception as e:
            logger.error("Telegram send exception: %s", e)
            return {"sent": False, "reason": str(e)}

    def validate_config(self, config: dict) -> tuple[bool, str]:
        missing = REQUIRED_KEYS - set(config.keys())
        if missing:
            return False, f"Missing config keys: {', '.join(sorted(missing))}"
        if not config.get("tg_bot_token", "").strip():
            return False, "tg_bot_token is empty"
        if not config.get("tg_chat_id", "").strip():
            return False, "tg_chat_id is empty"
        return True, ""

    def get_channel_type(self) -> str:
        return "telegram"
