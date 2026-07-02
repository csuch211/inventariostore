"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from services.export import ExportService

__all__ = ["ExportService"]
