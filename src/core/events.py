"""Event bus for decoupled communication between components.

Follows the Observer pattern: components register handlers for specific
events, and the bus dispatches events to all registered handlers without
the sender knowing about the receivers.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Coroutine

from utils.logger import setup_logger

logger = setup_logger(__name__)

# Type alias for event handlers
EventHandler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """In-process event bus for decoupled component communication.

    Usage:
        events = EventBus()

        async def on_product_created(product_id: int, **kwargs):
            await notify_stock_monitor(product_id)

        events.on("product_created", on_product_created)
        await events.emit("product_created", product_id=42)
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def on(self, event: str, handler: EventHandler) -> None:
        """Register a handler for an event."""
        self._handlers[event].append(handler)

    def off(self, event: str, handler: EventHandler) -> None:
        """Unregister a handler from an event."""
        handlers = self._handlers.get(event, [])
        if handler in handlers:
            handlers.remove(handler)

    async def emit(self, event: str, **kwargs: Any) -> None:
        """Dispatch an event to all registered handlers."""
        handlers = self._handlers.get(event, [])
        if not handlers:
            return

        logger.debug("Emitting event '%s' to %d handlers", event, len(handlers))
        for handler in handlers:
            try:
                await handler(**kwargs)
            except Exception as e:
                logger.error(
                    "Handler %s failed for event '%s': %s",
                    handler.__name__,
                    event,
                    e,
                )

    def handler_count(self, event: str) -> int:
        """Return the number of handlers registered for an event."""
        return len(self._handlers.get(event, []))


# Module-level singleton
event_bus = EventBus()
