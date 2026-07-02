"""Tests for StockMonitor: polling, callback, dedup, lifecycle."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.stock_monitor import StockMonitor


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.obtener_productos_con_stock_bajo.return_value = [
        {"id": 1, "codigo": "LOW-001", "nombre": "Low Stock", "cantidad": 3, "alert_level": "low"},
    ]
    return db


@pytest.fixture
def mock_callback():
    return AsyncMock()


@pytest.fixture
def monitor(mock_db, mock_callback):
    return StockMonitor(db=mock_db, callback=mock_callback, interval_seconds=3600, low_threshold=10)


class TestStockMonitorInit:
    def test_initial_state_not_running(self, monitor):
        assert monitor.is_running is False
        assert monitor._task is None

    def test_interval_minimum(self, mock_db, mock_callback):
        m = StockMonitor(db=mock_db, callback=mock_callback, interval_seconds=5)
        assert m._interval == 15  # min 15s


class TestStockMonitorLifecycle:
    @pytest.mark.asyncio
    async def test_start_runs_check_once(self, monitor, mock_callback):
        await monitor.start()
        assert monitor.is_running is True
        # Allow the initial check to complete
        await asyncio.sleep(0.05)
        mock_callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_idempotent(self, monitor):
        await monitor.start()
        task = monitor._task
        await monitor.start()
        assert monitor._task is task  # same task

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self, monitor):
        await monitor.start()
        assert monitor.is_running is True
        await monitor.stop()
        assert monitor.is_running is False
        assert monitor._task is None

    @pytest.mark.asyncio
    async def test_stop_noop_if_not_running(self, monitor):
        await monitor.stop()  # should not raise
        assert monitor.is_running is False


class TestStockMonitorCheckOnce:
    @pytest.mark.asyncio
    async def test_check_once_returns_alerts(self, monitor):
        alerts = await monitor.check_once()
        assert len(alerts) == 1
        assert alerts[0]["codigo"] == "LOW-001"

    @pytest.mark.asyncio
    async def test_check_once_fires_callback(self, monitor, mock_callback):
        await monitor.check_once()
        mock_callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_once_dedup_no_callback(self, monitor, mock_callback):
        """Same snapshot should not fire callback twice."""
        await monitor.check_once()
        mock_callback.reset_mock()
        await monitor.check_once()
        mock_callback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_check_once_new_data_fires_callback(self, monitor, mock_db, mock_callback):
        await monitor.check_once()
        mock_callback.reset_mock()
        # Change the data
        mock_db.obtener_productos_con_stock_bajo.return_value = [
            {"id": 2, "codigo": "LOW-002", "nombre": "Another", "cantidad": 2, "alert_level": "critical"},
        ]
        await monitor.check_once()
        mock_callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_once_db_error_returns_empty(self, monitor, mock_db, mock_callback):
        mock_db.obtener_productos_con_stock_bajo.side_effect = Exception("DB error")
        alerts = await monitor.check_once()
        assert alerts == []

    @pytest.mark.asyncio
    async def test_check_once_callback_error_caught(self, monitor, mock_callback):
        mock_callback.side_effect = Exception("Callback error")
        # Should not raise
        alerts = await monitor.check_once()
        assert len(alerts) == 1


class TestStockMonitorSignature:
    def test_signature_empty(self):
        sig = StockMonitor._signature([])
        assert sig == frozenset()

    def test_signature_content(self):
        alerts = [{"id": 1, "cantidad": 5, "alert_level": "low"}]
        sig = StockMonitor._signature(alerts)
        assert (1, 5, "low") in sig

    def test_signature_order_independent(self):
        a = [{"id": 1, "cantidad": 5, "alert_level": "low"}, {"id": 2, "cantidad": 3, "alert_level": "critical"}]
        b = [{"id": 2, "cantidad": 3, "alert_level": "critical"}, {"id": 1, "cantidad": 5, "alert_level": "low"}]
        assert StockMonitor._signature(a) == StockMonitor._signature(b)
