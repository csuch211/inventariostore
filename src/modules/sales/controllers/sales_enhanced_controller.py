"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.sales_enhanced_controller import SalesEnhancedController

__all__ = ["SalesEnhancedController"]
