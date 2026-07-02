"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.hr_controller import HRController

__all__ = ["HRController"]
