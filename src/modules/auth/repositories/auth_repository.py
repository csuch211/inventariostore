"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from services.repository.user_repo import UserRepository

__all__ = ["UserRepository"]
