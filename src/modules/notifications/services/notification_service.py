"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from services.notifier import (
    get_smtp_config,
    is_configured,
    send_custom_alert,
    send_low_stock_alert,
)

__all__ = [
    "get_smtp_config",
    "is_configured",
    "send_custom_alert",
    "send_low_stock_alert",
]
