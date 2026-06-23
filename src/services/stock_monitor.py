"""
Background stock-alert monitor.

Runs a periodic task that polls the database for low-stock products and
notifies the host application via a registered callback. The host decides
how to surface the alert (SnackBar, banner, email, etc.) — this module
only owns the timing, deduplication, and lifecycle.

Lifecycle:
    monitor = StockMonitor(db, interval_seconds=300, callback=cb)
    await monitor.start()
    ...
    await monitor.stop()
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable

from config.settings import STOCK_LOW_DEFAULT
from services.database import DatabaseManager
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Callback receives the full list of alerts whenever the snapshot changes.
AlertCallback = Callable[[list[dict]], Awaitable[None]]


class StockMonitor:
    """Polls low-stock products on an interval and notifies on change."""

    def __init__(
        self,
        db: DatabaseManager,
        callback: AlertCallback,
        interval_seconds: int = 300,
        low_threshold: int = STOCK_LOW_DEFAULT,
    ) -> None:
        self._db = db
        self._callback = callback
        self._interval = max(15, interval_seconds)  # never poll faster than 15s
        self._low_threshold = low_threshold
        self._task: asyncio.Task | None = None
        # Cache by product id so we only fire the callback when the snapshot
        # actually changes (avoids spamming the UI on every poll).
        self._last_signature: frozenset | None = None

    async def start(self) -> None:
        """Start the polling task. No-op if already running."""
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="stock-monitor")
        logger.info(f"StockMonitor started (interval={self._interval}s)")

    async def stop(self) -> None:
        """Cancel the polling task and wait for clean shutdown."""
        if not self._task:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        logger.info("StockMonitor stopped")

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def check_once(self) -> list[dict]:
        """Run a single poll, fire the callback if the snapshot changed, and
        return the current alerts. Useful for the on-login kick."""
        try:
            alerts = self._db.obtener_productos_con_stock_bajo(
                low_threshold=self._low_threshold,
            )
        except Exception as e:
            logger.error(f"StockMonitor poll failed: {e}")
            return []
        sig = self._signature(alerts)
        if sig != self._last_signature:
            self._last_signature = sig
            try:
                await self._callback(alerts)
            except Exception as e:
                logger.error(f"StockMonitor callback raised: {e}")
        return alerts

    async def _run(self) -> None:
        """Main loop. Sleeps `_interval` seconds between polls."""
        # Run an initial check immediately on start so the UI sees fresh data
        # without waiting for the first tick.
        await self.check_once()
        while True:
            try:
                await asyncio.sleep(self._interval)
                await self.check_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"StockMonitor loop error: {e}")

    @staticmethod
    def _signature(alerts: list[dict]) -> frozenset:
        """Build a deduplication key from (id, cantidad, alert_level)."""
        return frozenset((a.get("id"), a.get("cantidad"), a.get("alert_level")) for a in alerts)
