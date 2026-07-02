"""
Temporary facade - re-exports from original location during migration.
"""

# Re-export from original location during migration
from core.controllers.report_controller import ReportController

__all__ = ["ReportController"]
