"""Tests for the EventBus notification integration.

Verifies that events can be emitted and handlers receive them,
which is how the notification system dispatches in-app alerts.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from core.events import EventBus, event_bus


@pytest.fixture
def bus():
    return EventBus()


class TestEventBus:
    @pytest.mark.asyncio
    async def test_emit_triggers_handler(self, bus: EventBus):
        handler = AsyncMock()
        bus.on("notification.created", handler)
        await bus.emit("notification.created", titulo="Test", mensaje="Hello")
        handler.assert_awaited_once_with(titulo="Test", mensaje="Hello")

    @pytest.mark.asyncio
    async def test_multiple_handlers(self, bus: EventBus):
        h1 = AsyncMock()
        h2 = AsyncMock()
        bus.on("low_stock", h1)
        bus.on("low_stock", h2)
        await bus.emit("low_stock", producto_id=1, cantidad=3)
        h1.assert_awaited_once_with(producto_id=1, cantidad=3)
        h2.assert_awaited_once_with(producto_id=1, cantidad=3)

    @pytest.mark.asyncio
    async def test_handler_not_called_for_unregistered_event(self, bus: EventBus):
        handler = AsyncMock()
        bus.on("notification.created", handler)
        await bus.emit("other.event", data="x")
        handler.assert_not_awaited()

    def test_handler_count(self, bus: EventBus):
        assert bus.handler_count("test.event") == 0
        bus.on("test.event", AsyncMock())
        assert bus.handler_count("test.event") == 1
        bus.on("test.event", AsyncMock())
        assert bus.handler_count("test.event") == 2

    def test_off_removes_handler(self, bus: EventBus):
        handler = AsyncMock()
        bus.on("e", handler)
        assert bus.handler_count("e") == 1
        bus.off("e", handler)
        assert bus.handler_count("e") == 0

    @pytest.mark.asyncio
    async def test_handler_error_does_not_crash_bus(self, bus: EventBus):
        failing = AsyncMock(side_effect=ValueError("fail"))
        ok = AsyncMock()
        bus.on("event", failing)
        bus.on("event", ok)
        await bus.emit("event", data="x")
        ok.assert_awaited_once_with(data="x")

    def test_module_singleton_exists(self):
        assert event_bus is not None
        assert isinstance(event_bus, EventBus)
