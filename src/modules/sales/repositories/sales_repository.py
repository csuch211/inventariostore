"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from services.repository.sale_repo import SaleRepository

__all__ = ["SaleRepository"]
