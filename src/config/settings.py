"""
Configuration settings for the Inventory System
Follows 12-factor app principles
"""

import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
DEBUG = ENVIRONMENT == "development"

# Database
DATABASE_PATH = PROJECT_ROOT / "data"
DATABASE_FILE = DATABASE_PATH / "inventario.db"

# Logging
LOG_PATH = PROJECT_ROOT / "logs"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if not DEBUG else "DEBUG")
LOG_FILE = LOG_PATH / "application.log"

# Application
APP_NAME = "Sistema de Inventario Empresarial"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Development Team"

# UI - Light theme
THEME_PRIMARY_COLOR = "#2563EB"  # blue-600 — modern primary
THEME_PRIMARY_LIGHT = "#DBEAFE"  # blue-100 — light tint for highlights
THEME_PRIMARY_DARK = "#1D4ED8"  # blue-700 — darker shade
THEME_ACCENT_COLOR = "#DC2626"  # red-600 — accent
THEME_ACCENT_LIGHT = "#FEE2E2"  # red-100 — light accent tint
THEME_DANGER = THEME_ACCENT_COLOR  # alias used by stock alerts & critical UI
THEME_BACKGROUND_COLOR = "#F1F5F9"  # slate-100 — page bg
THEME_SURFACE_COLOR = "#FFFFFF"  # white — card/surface
THEME_SUCCESS_COLOR = "#16A34A"  # green-600
THEME_SUCCESS_LIGHT = "#DCFCE7"  # green-100
THEME_WARNING_COLOR = "#D97706"  # amber-600
THEME_WARNING_LIGHT = "#FEF3C7"  # amber-100

# Light theme — text/UI tokens
THEME_TEXT_PRIMARY = "#0F172A"  # slate-900 — body text
THEME_TEXT_SECONDARY = "#475569"  # slate-600 — captions / labels
THEME_TEXT_MUTED = "#64748B"  # slate-500 — hints
THEME_INPUT_FILL = "#F8FAFC"  # slate-50 — TextField/Dropdown fill
THEME_TABLE_HEADING = THEME_PRIMARY_COLOR
THEME_TABLE_ROW = "#FFFFFF"
THEME_TABLE_ROW_ALT = "#F8FAFC"
THEME_DIVIDER = "#CBD5E1"  # slate-300
THEME_SHADOW = "rgba(15,23,42,0.08)"

# UI - Dark theme
THEME_DARK_PRIMARY_COLOR = "#60A5FA"  # blue-400
THEME_DARK_PRIMARY_LIGHT = "#1E3A5F"  # blue-900 tint
THEME_DARK_ACCENT_COLOR = "#F87171"  # red-400
THEME_DARK_ACCENT_LIGHT = "#3B1C1C"  # red-900 tint
THEME_DARK_BACKGROUND_COLOR = "#0F172A"  # slate-900
THEME_DARK_SURFACE_COLOR = "#1E293B"  # slate-800
THEME_DARK_CARD_COLOR = "#334155"  # slate-700

# Dark theme — text/UI tokens (tuned for AA contrast on slate-900/slate-800)
THEME_DARK_TEXT_PRIMARY = "#F1F5F9"  # slate-100 — body text
THEME_DARK_TEXT_SECONDARY = "#CBD5E1"  # slate-300 — captions / labels
THEME_DARK_TEXT_MUTED = "#94A3B8"  # slate-400 — hints
THEME_DARK_INPUT_FILL = "#0B1220"  # near-black with blue tint — input fill
THEME_DARK_INPUT_BORDER = "#334155"  # slate-700 — unfocused border
THEME_DARK_TABLE_HEADING = "#1E3A5F"  # blue-900 tint — header row
THEME_DARK_TABLE_ROW = "#1E293B"  # slate-800 — data row
THEME_DARK_TABLE_ROW_ALT = "#172033"  # slightly darker — zebra
THEME_DARK_TABLE_ROW_HOVER = "#2A3F5F"  # slate-700-ish blue — hover
THEME_DARK_DIVIDER = "#334155"  # slate-700
THEME_DARK_SHADOW = "rgba(0,0,0,0.40)"
THEME_DARK_SHADOW_STRONG = "rgba(0,0,0,0.60)"
THEME_DARK_OVERLAY = "rgba(0,0,0,0.55)"  # dialog scrim
THEME_DARK_FOCUS_RING = "#60A5FA"  # blue-400 — keyboard focus outline
THEME_DARK_HOVER_TINT = "#1E3A5F"  # blue-900 — hover surface
THEME_DARK_PRIMARY_TINT = "#1E3A5F"  # blue-900 — active item background (sidebar)
THEME_DARK_SIDEBAR_BG = "#1E293B"  # slate-800 — sidebar background in dark mode
THEME_DARK_SCROLLBAR = "#475569"  # slate-600 — scrollbar thumb
THEME_DARK_SCROLLBAR_TRACK = "#0F172A"  # slate-900 — scrollbar track
THEME_DARK_SUCCESS = "#4ADE80"  # green-400 — brighter on dark
THEME_DARK_WARNING = "#FBBF24"  # amber-400 — brighter on dark
THEME_DARK_DANGER = "#F87171"  # red-400 — matches accent

# Light theme — companion tokens for parity
THEME_INPUT_BORDER = "#CBD5E1"  # slate-300 — unfocused border
THEME_TABLE_ROW_HOVER = "#EFF6FF"  # blue-50 — hover
THEME_SHADOW_STRONG = "rgba(15,23,42,0.16)"
THEME_OVERLAY = "rgba(15,23,42,0.45)"
THEME_FOCUS_RING = "#2563EB"  # blue-600 — keyboard focus outline
THEME_HOVER_TINT = "#DBEAFE"  # blue-100 — hover surface
THEME_PRIMARY_TINT = "#EFF6FF"  # blue-50 — active item background (sidebar)
THEME_SIDEBAR_BG = "#FFFFFF"  # white — sidebar background in light mode
THEME_SCROLLBAR = "#94A3B8"  # slate-400 — scrollbar thumb
THEME_SCROLLBAR_TRACK = "#F1F5F9"  # slate-100 — scrollbar track

# Security
SESSION_TIMEOUT_MINUTES = 30
PASSWORD_MIN_LENGTH = 8

# JWT Configuration
# IMPORTANT: In production, JWT_SECRET_KEY MUST be set via environment variable.
# If not set, a random key is generated per process (tokens won't survive restart).
_jwt_secret = os.getenv("JWT_SECRET_KEY")
if not _jwt_secret:
    import secrets as _secrets
    _jwt_secret = _secrets.token_hex(32)
    import warnings as _warnings
    _warnings.warn(
        "JWT_SECRET_KEY not set! Generating random key. "
        "Tokens will not persist across restarts. "
        "Set JWT_SECRET_KEY environment variable for production.",
        UserWarning,
        stacklevel=2,
    )
JWT_SECRET_KEY = _jwt_secret
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Pagination
ITEMS_PER_PAGE = 50

# Export formats
EXPORT_FORMATS = ["CSV", "PDF", "Excel"]

# Stock alert thresholds
# Critical: product is out of stock (cantidad == 0).
# Low: product has stock_min > 0 AND cantidad <= stock_min, OR
#      stock_min == 0 (legacy default) AND cantidad <= STOCK_LOW_DEFAULT.
# Used by alerts view, sidebar badge and email notifier.
STOCK_LOW_DEFAULT = 5

# How often (in seconds) the background monitor polls for stock changes.
# The monitor only fires the alert callback when the snapshot actually
# changes, so a short interval is safe — UI updates stay rare.
STOCK_MONITOR_INTERVAL_SECONDS = 300  # 5 min

# Features
ENABLE_AUDIT_LOG = True
ENABLE_BACKUP = True
BACKUP_PATH = PROJECT_ROOT / "backups"

# Default credentials (MUST be set via environment variables in production)
# WARNING: Using default values is only for development. Change immediately in production.
import secrets as _secrets

DEFAULT_ADMIN_USER = os.getenv("INV_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("INV_ADMIN_PASSWORD") or _secrets.token_urlsafe(16)
DEFAULT_OPERATOR_USER = os.getenv("INV_OPERATOR_USER", "usuario")
DEFAULT_OPERATOR_PASSWORD = os.getenv("INV_OPERATOR_PASSWORD") or _secrets.token_urlsafe(16)


def ensure_dirs() -> None:
    """Create required directories. Call once at app startup."""
    DATABASE_PATH.mkdir(parents=True, exist_ok=True)
    LOG_PATH.mkdir(parents=True, exist_ok=True)
    BACKUP_PATH.mkdir(parents=True, exist_ok=True)
