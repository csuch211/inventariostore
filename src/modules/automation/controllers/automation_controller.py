"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.automation_controller import AutomationController

__all__ = ["AutomationController"]
