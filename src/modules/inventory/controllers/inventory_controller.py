"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.inventory_controller import InventoryController

__all__ = ["InventoryController"]
