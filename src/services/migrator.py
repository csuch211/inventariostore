"""
Simple versioned database migrator.

Each migration is a Python file in the `migrations` directory named
``V<number>_<description>.py`` that exposes an async or sync ``run(db)``
function receiving a ``DatabaseManager`` instance.

The migrator tracks applied versions in a ``_migrations`` table and
runs pending migrations in version order on every ``upgrade()`` call.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import re
from pathlib import Path

from utils.logger import setup_logger

logger = setup_logger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _ensure_tracking_table(db):
    """Create the migration tracking table if it doesn't exist."""
    with db._get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS _migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _applied_versions(db) -> set:
    """Return the set of already-applied version numbers."""
    with db._get_connection() as conn:
        rows = conn.execute("SELECT version FROM _migrations ORDER BY version").fetchall()
        return {r["version"] for r in rows}


def _discover_migrations() -> list[tuple[int, str, Path]]:
    """Scan the migrations directory and return (version, name, path) tuples sorted by version."""
    if not MIGRATIONS_DIR.is_dir():
        logger.info("Migrations directory not found, creating: %s", MIGRATIONS_DIR)
        MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
        return []

    pattern = re.compile(r"^V(\d+)_(.+)\.py$")
    migrations = []
    for f in sorted(MIGRATIONS_DIR.iterdir()):
        m = pattern.match(f.name)
        if m:
            migrations.append((int(m.group(1)), m.group(2), f))
    return migrations


def upgrade(db, target_version: int | None = None) -> int:
    """Run all pending migrations up to (and including) target_version.

    Args:
        db: DatabaseManager instance.
        target_version: If None, run all pending migrations.

    Returns:
        Number of migrations applied.
    """
    _ensure_tracking_table(db)
    applied = _applied_versions(db)
    migrations = _discover_migrations()

    if not migrations:
        logger.debug("No migrations found in %s", MIGRATIONS_DIR)
        return 0

    count = 0
    for version, name, path in migrations:
        if target_version is not None and version > target_version:
            break
        if version in applied:
            continue

        logger.info("Applying migration V%d_%s ...", version, name)

        spec = importlib.util.spec_from_file_location(f"migration_{version}", path)
        if spec is None or spec.loader is None:
            logger.error("Could not load migration V%d_%s", version, name)
            continue

        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        if not hasattr(mod, "run"):
            logger.error("Migration V%d_%s has no run() function", version, name)
            continue

        try:
            if inspect.iscoroutinefunction(mod.run):
                import asyncio

                asyncio.run(mod.run(db))
            else:
                mod.run(db)

            # Record the migration
            from datetime import datetime

            with db._get_connection() as conn:
                conn.execute(
                    "INSERT INTO _migrations (version, name, applied_at) VALUES (?, ?, ?)",
                    (version, name, datetime.now().isoformat()),
                )
                conn.commit()

            logger.info("Migration V%d_%s applied successfully", version, name)
            count += 1
        except Exception as e:
            logger.exception("Migration V%d_%s FAILED: %s", version, name, e)
            raise

    return count
