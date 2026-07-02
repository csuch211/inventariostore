"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from services.backup import BackupService

__all__ = ["BackupService"]
