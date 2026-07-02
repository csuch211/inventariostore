"""Unified dispatcher for messaging channels.

Factory + registry pattern so new channels can be added without touching
existing code.  Integrates with the push queue via ``create_push_sender_func``
which returns a ``Callable`` compatible with
``extended_features_db.despachar_jobs_pendientes(sender=...)``.
"""

from collections.abc import Callable

from services.messaging.base import MessageSender
from services.messaging.telegram import TelegramSender
from services.messaging.whatsapp import WhatsAppSender
from utils.logger import setup_logger

logger = setup_logger(__name__)

_senders: dict[str, type[MessageSender]] = {
    "whatsapp": WhatsAppSender,
    "telegram": TelegramSender,
}


def register_sender(tipo: str, sender_cls: type[MessageSender]) -> None:
    """Register a new sender type at runtime."""
    _senders[tipo] = sender_cls
    logger.info("Registered sender type '%s'", tipo)


def get_sender(tipo: str) -> MessageSender:
    """Factory — return an instance for *tipo* (e.g. ``'whatsapp'``)."""
    cls = _senders.get(tipo)
    if cls is None:
        msg = f"Unknown channel type '{tipo}'. Known: {', '.join(sorted(_senders))}"
        raise ValueError(msg)
    return cls()


async def send_via_channel(
    tipo: str,
    destinatario: str,
    asunto: str,
    cuerpo: str,
    config: dict | None = None,
) -> dict:
    """High-level helper: get sender, validate config, send."""
    sender = get_sender(tipo)
    cfg = config or {}
    valid, err = sender.validate_config(cfg)
    if not valid:
        return {"sent": False, "reason": err}
    return await sender.send(destinatario, asunto, cuerpo, cfg)


def create_push_sender_func(
    tipo: str, get_config: Callable[[], dict]
) -> Callable[[dict, str, str], dict]:
    """Return a synchronous ``Callable`` for use with
    ``extended_features_db.despachar_jobs_pendientes``.

    ``get_config`` is a zero-argument callable that returns the channel
    config dict (usually from the DB).  The returned callable satisfies
    the ``sender`` signature ``(ignored_cfg: dict, asunto: str, cuerpo: str) -> dict``
    expected by ``despachar_jobs_pendientes``.
    """

    def sender(_cfg_ignored: dict, asunto: str, cuerpo: str) -> dict:
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        cfg = get_config()
        s = get_sender(tipo)
        valid, err = s.validate_config(cfg)
        if not valid:
            return {"sent": False, "reason": err}

        dest = cfg.get("tg_chat_id") if tipo == "telegram" else cfg.get("wa_phone_id", "")
        coro = s.send(dest, asunto, cuerpo, cfg)

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return asyncio.run(coro)

    return sender
