"""Tests for database migrations: apply each V1-V16 migration."""

from __future__ import annotations

import contextlib
import importlib
import tempfile
from pathlib import Path

import pytest

from services.database import DatabaseManager


@pytest.fixture
def db():
    """Create a fresh DatabaseManager with a temp DB for migration testing."""
    tmp = Path(tempfile.mktemp(suffix=".db"))
    db = DatabaseManager(tmp)
    yield db
    db.close_connections()
    with contextlib.suppress(PermissionError):
        tmp.unlink(missing_ok=True)


MIGRATION_NAMES = [
    "V1_unify_soft_delete",
    "V2_create_sessions",
    "V3_drop_estado_column",
    "V4_refresh_tokens",
    "V5_password_reset_tokens",
    "V6_email_verification_tokens",
    "V7_invoicing",
    "V8_accounting",
    "V9_hr_module",
    "V10_purchasing",
    "V11_crm",
    "V12_document_management",
    "V13_notifications",
    "V14_sales_enhanced",
    "V15_cart_and_store",
    "V16_automation",
]


class TestMigrations:
    @pytest.mark.parametrize("migration_name", MIGRATION_NAMES)
    def test_migration_up_does_not_crash(self, db, migration_name):
        """Each migration's run() function runs without error on a fresh DB."""
        try:
            mod = importlib.import_module(f"services.migrations.{migration_name}")
        except ImportError:
            pytest.skip(f"Migration {migration_name} not found (may not exist yet)")
            return
        try:
            mod.run(db)
        except Exception as e:
            pytest.fail(f"Migration {migration_name}.run() failed: {e}")

    @pytest.mark.parametrize("migration_name", MIGRATION_NAMES)
    def test_migration_idempotent(self, db, migration_name):
        """Running run() twice should not crash."""
        try:
            mod = importlib.import_module(f"services.migrations.{migration_name}")
        except ImportError:
            pytest.skip(f"Migration {migration_name} not found")
            return
        try:
            mod.run(db)
            mod.run(db)
        except Exception as e:
            pytest.fail(f"Migration {migration_name} not idempotent: {e}")

    def test_migrator_upgrade_does_not_crash(self):
        """Run migrator.upgrade() on a temp DB to verify the full chain."""
        tmp = Path(tempfile.mktemp(suffix=".db"))
        from services.migrator import upgrade as run_migrations

        db = DatabaseManager(tmp)
        try:
            run_migrations(db)
        except Exception as e:
            pytest.fail(f"Migrator upgrade failed: {e}")
        finally:
            db.close_connections()
            with contextlib.suppress(PermissionError):
                tmp.unlink(missing_ok=True)

    def test_migrations_table_created(self):
        """After upgrade, the _migrations tracking table should exist."""
        from services.migrator import upgrade as run_migrations

        tmp = Path(tempfile.mktemp(suffix=".db"))
        db = DatabaseManager(tmp)
        try:
            run_migrations(db)
            with db._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations'"
                )
                assert cursor.fetchone() is not None, "_migrations table not found"
        finally:
            db.close_connections()
            with contextlib.suppress(PermissionError):
                tmp.unlink(missing_ok=True)
