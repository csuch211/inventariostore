"""
Stock alert monitor management.

All functions receive the AppView instance as first parameter.
"""

import flet as ft

from config.settings import STOCK_LOW_DEFAULT, STOCK_MONITOR_INTERVAL_SECONDS
from core.theme_manager import theme_manager
from services.stock_monitor import StockMonitor
from ui.components import SnackBarHelper
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def start_monitor(app_view) -> None:
    """Boot the background stock monitor and run an immediate check."""
    if app_view._stock_monitor is None:
        app_view._stock_monitor = StockMonitor(
            db=app_view.controller.db,
            callback=lambda alertas: on_alerts_changed(app_view, alertas),
            interval_seconds=STOCK_MONITOR_INTERVAL_SECONDS,
            low_threshold=STOCK_LOW_DEFAULT,
        )
    await app_view._stock_monitor.start()


async def stop_monitor(app_view) -> None:
    """Cancel the background monitor on logout / app close."""
    if app_view._stock_monitor and app_view._stock_monitor.is_running:
        await app_view._stock_monitor.stop()
    app_view._stock_monitor = None


def on_alerts_changed(app_view, alertas: list[dict]) -> None:
    """Handle a new snapshot of low-stock products."""
    try:
        C = theme_manager.palette(page=app_view.page)
        criticas = sum(1 for a in alertas if a.get("alert_level") == "critical")
        bajas = sum(1 for a in alertas if a.get("alert_level") == "low")
        app_view._stock_alert_count = len(alertas)
        if app_view._sidebar_nav is not None:
            app_view._refresh_nav_badges_sync()
        if alertas:
            msg = t(
                "stock_alerts.snapshot_toast",
                criticals=criticas,
                lows=bajas,
                total=len(alertas),
            )
            if criticas > 0:
                SnackBarHelper.error(app_view.page, msg)
            else:
                SnackBarHelper._show(
                    app_view.page,
                    ft.SnackBar(
                        ft.Row(
                            [
                                ft.Icon(ft.icons.Icons.WARNING_AMBER, color="white"),
                                ft.Text(msg, color="white"),
                            ],
                            spacing=10,
                        ),
                        bgcolor=C["warning"],
                    ),
                )
    except Exception as e:
        logger.exception(f"stock alert callback failed: {e}")
