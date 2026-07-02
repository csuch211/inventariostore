"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.document_controller import DocumentController

__all__ = ["DocumentController"]
