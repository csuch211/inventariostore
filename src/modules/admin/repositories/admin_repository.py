"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from services.repository.config_repo import ConfigRepository

__all__ = ["ConfigRepository"]
