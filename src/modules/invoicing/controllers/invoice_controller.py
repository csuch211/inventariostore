"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.invoice_controller import InvoiceController

__all__ = ["InvoiceController"]
