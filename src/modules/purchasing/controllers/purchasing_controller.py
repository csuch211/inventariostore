"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.purchasing_controller import PurchasingController

__all__ = ["PurchasingController"]
