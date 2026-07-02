"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.store_controller import StoreController

__all__ = ["StoreController"]
