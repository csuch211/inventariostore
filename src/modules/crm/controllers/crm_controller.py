"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.crm_controller import CRMController

__all__ = ["CRMController"]
