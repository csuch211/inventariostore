"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.product_controller import ProductController

__all__ = ["ProductController"]
