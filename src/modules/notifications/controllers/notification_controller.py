"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.notification_controller import NotificationController

__all__ = ["NotificationController"]
