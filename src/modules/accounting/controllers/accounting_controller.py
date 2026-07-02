"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.accounting_controller import AccountingController

__all__ = ["AccountingController"]
