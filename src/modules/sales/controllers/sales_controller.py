"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.sales_controller import SalesController

__all__ = ["SalesController"]
