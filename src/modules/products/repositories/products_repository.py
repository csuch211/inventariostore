"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from services.repository.product_repo import ProductRepository

__all__ = ["ProductRepository"]
