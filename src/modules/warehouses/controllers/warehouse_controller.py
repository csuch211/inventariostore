"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.warehouse_controller import WarehouseController

__all__ = ["WarehouseController"]
