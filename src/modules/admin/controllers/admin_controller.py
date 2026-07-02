"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.admin_controller import AdminController

__all__ = ["AdminController"]
