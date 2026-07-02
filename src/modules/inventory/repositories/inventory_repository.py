"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from services.repository.inventory_repo import InventoryRepository

__all__ = ["InventoryRepository"]
