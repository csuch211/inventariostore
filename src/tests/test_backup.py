"""Tests for BackupService: create, list, restore, delete backups."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from services.backup import BackupService


@pytest.fixture
def backup_service():
    """Set up BackupService with temp dirs for DB and backups."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="inv_backup_test_"))
    db_path = tmp_dir / "inventario.db"
    db_path.write_text("fake-sqlite-content")
    backup_dir = tmp_dir / "backups"
    backup_dir.mkdir()

    with (
        patch("services.backup.DATABASE_FILE", db_path),
        patch("services.backup.BACKUP_PATH", backup_dir),
    ):
        yield BackupService()

    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)


class TestCreateBackup:
    def test_create_backup_success(self, backup_service):
        result = backup_service.create_backup(usuario="tester")
        assert "error" not in result
        assert "ruta" in result
        assert result["nombre"].startswith("backup_")
        assert result["nombre"].endswith(".zip")
        assert result["tamano"] > 0

    def test_create_backup_returns_metadata(self, backup_service):
        result = backup_service.create_backup()
        assert "creado_en" in result
        assert Path(result["ruta"]).exists()


class TestListBackups:
    def test_list_backups_empty_initially(self, backup_service):
        backups = backup_service.list_backups()
        assert isinstance(backups, list)

    def test_list_backups_after_creation(self, backup_service):
        backup_service.create_backup()
        backups = backup_service.list_backups()
        assert len(backups) >= 1
        assert backups[0]["nombre"].startswith("backup_")

    def test_list_backups_ordered_by_date(self, backup_service):
        backup_service.create_backup(usuario="first")
        import time
        time.sleep(1.1)
        backup_service.create_backup(usuario="second")
        backups = backup_service.list_backups()
        assert len(backups) >= 2


class TestRestoreBackup:
    def test_restore_nonexistent_backup(self, backup_service):
        result = backup_service.restore_backup("/nonexistent/file.zip")
        assert "error" in result

    def test_restore_invalid_backup(self, backup_service):
        # Create a zip without the db file
        import zipfile
        bad_zip = Path(tempfile.mkdtemp()) / "bad.zip"
        with zipfile.ZipFile(bad_zip, "w") as zf:
            zf.writestr("other.txt", "data")
        result = backup_service.restore_backup(str(bad_zip))
        assert "error" in result
        bad_zip.unlink(missing_ok=True)


class TestDeleteBackup:
    def test_delete_backup_success(self, backup_service):
        result = backup_service.create_backup()
        backup_path = result["ruta"]
        assert backup_service.delete_backup_file(backup_path) is True
        assert not Path(backup_path).exists()

    def test_delete_nonexistent_backup(self, backup_service):
        assert backup_service.delete_backup_file("/nonexistent.zip") is False

    def test_delete_outside_backup_dir(self, backup_service):
        tmp = Path(tempfile.mkdtemp()) / "outside.zip"
        tmp.write_text("data")
        assert backup_service.delete_backup_file(str(tmp)) is False
        tmp.unlink(missing_ok=True)
