"""Abstract base class for messaging senders."""

from abc import ABC, abstractmethod


class MessageSender(ABC):
    """Interface for sending messages via a specific channel (WhatsApp, Telegram, etc.)."""

    @abstractmethod
    async def send(
        self, destinatario: str, asunto: str, cuerpo: str, config: dict
    ) -> dict:
        ...

    @abstractmethod
    def validate_config(self, config: dict) -> tuple[bool, str]:
        ...

    def get_channel_type(self) -> str:
        ...
