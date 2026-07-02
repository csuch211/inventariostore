"""WhatsApp sender via Meta Cloud API (or Twilio).

Uses httpx.AsyncClient for HTTP calls.  Config keys (stored in DB table
``configuracion``)::

    wa_api_key      — permanent access token / API key
    wa_phone_id     — phone number ID (Meta) / from number (Twilio)
    wa_api_url      — base URL (default: https://graph.facebook.com/v18.0)
    wa_enabled      — "si" / "no"
"""

from services.messaging.base import MessageSender
from utils.crypto import decrypt_value
from utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

REQUIRED_KEYS = frozenset({"wa_api_key", "wa_phone_id"})
CONFIG_KEYS = frozenset({"wa_api_key", "wa_phone_id", "wa_api_url", "wa_enabled"})


class WhatsAppSender(MessageSender):
    """Send text / template messages via WhatsApp Business API."""

    DEFAULT_API_URL = "https://graph.facebook.com/v18.0"

    async def send(
        self, destinatario: str, asunto: str, cuerpo: str, config: dict
    ) -> dict:
        valid, msg = self.validate_config(config)
        if not valid:
            return {"sent": False, "reason": msg}
        if config.get("wa_enabled", "no") != "si":
            return {"sent": False, "reason": "WhatsApp channel disabled"}

        phone_id = config["wa_phone_id"]
        token = decrypt_value(config["wa_api_key"])
        base_url = config.get("wa_api_url", self.DEFAULT_API_URL).rstrip("/")
        url = f"{base_url}/{phone_id}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "to": destinatario,
            "type": "text",
            "text": {"body": cuerpo},
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                data = resp.json()
                if resp.is_success:
                    msg_id = data.get("messages", [{}])[0].get("id", "")
                    logger.info(
                        "WhatsApp msg sent to %s (id=%s)", destinatario, msg_id
                    )
                    return {"sent": True, "message_id": msg_id}
                else:
                    error = data.get("error", {}).get("message", resp.text)
                    logger.error("WhatsApp API error: %s", error)
                    return {"sent": False, "reason": error}
        except Exception as e:
            logger.error("WhatsApp send exception: %s", e)
            return {"sent": False, "reason": str(e)}

    def validate_config(self, config: dict) -> tuple[bool, str]:
        missing = REQUIRED_KEYS - set(config.keys())
        if missing:
            return False, f"Missing config keys: {', '.join(sorted(missing))}"
        if not config.get("wa_api_key", "").strip():
            return False, "wa_api_key is empty"
        if not config.get("wa_phone_id", "").strip():
            return False, "wa_phone_id is empty"
        return True, ""

    def get_channel_type(self) -> str:
        return "whatsapp"
