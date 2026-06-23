"""
Backup and restore service for the inventory system.
Creates compressed SQLite database backups and restores from them.
"""

import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from config.settings import BACKUP_PATH, DATABASE_FILE
from utils.logger import setup_logger

logger = setup_logger(__name__)


class BackupService:
    """Handles database backup creation, listing, and restoration."""

    @staticmethod
    def create_backup(usuario: str = "system") -> dict:
        """Create a compressed backup of the SQLite database.

        Returns:
            Dict with 'ruta', 'tamano', 'creado_en' keys on success,
            or 'error' on failure.
        """
        try:
            BACKUP_PATH.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}.zip"
            backup_file = BACKUP_PATH / backup_name

            if not DATABASE_FILE.exists():
                return {"error": f"Database file not found: {DATABASE_FILE}"}

            with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(DATABASE_FILE, "inventario.db")

            size_bytes = backup_file.stat().st_size

            logger.info(f"Backup created: {backup_name} ({size_bytes} bytes) by {usuario}")
            return {
                "ruta": str(backup_file),
                "tamano": size_bytes,
                "creado_en": datetime.now().isoformat(),
                "nombre": backup_name,
            }
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def list_backups() -> list[dict]:
        """List all backup ZIP files in the backup directory."""
        try:
            BACKUP_PATH.mkdir(parents=True, exist_ok=True)
            backups = []
            for f in sorted(
                BACKUP_PATH.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True
            ):
                backups.append(
                    {
                        "ruta": str(f),
                        "nombre": f.name,
                        "tamano": f.stat().st_size,
                        "creado_en": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    }
                )
            return backups
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []

    @staticmethod
    def restore_backup(backup_path: str) -> dict:
        """Restore the database from a backup ZIP file.

        Args:
            backup_path: Full path to the backup ZIP file.

        Returns:
            Dict with 'message' on success, or 'error' on failure.
        """
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                return {"error": f"Backup file not found: {backup_path}"}

            if not DATABASE_FILE.exists():
                return {"error": f"Database file not found: {DATABASE_FILE}"}

            # Create a safety backup of the current database before restoring
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safety_backup = BACKUP_PATH / f"pre_restore_{timestamp}.zip"
            with zipfile.ZipFile(safety_backup, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(DATABASE_FILE, "inventario.db")
            logger.info(f"Pre-restore safety backup: {safety_backup}")

            # Extract the backup over the current database
            with zipfile.ZipFile(backup_file, "r") as zf:
                # Verify the zip contains the db file
                if "inventario.db" not in zf.namelist():
                    return {"error": "Invalid backup: inventario.db not found in archive"}
                # Extract to a temp file first, then replace
                temp_db = DATABASE_FILE.with_suffix(".tmp")
                with zf.open("inventario.db") as source:
                    with open(temp_db, "wb") as target:
                        shutil.copyfileobj(source, target)
                shutil.move(str(temp_db), str(DATABASE_FILE))

            logger.info(f"Database restored from: {backup_path}")
            return {"message": "Base de datos restaurada correctamente"}
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def delete_backup_file(backup_path: str) -> bool:
        """Delete a backup file from disk."""
        try:
            path = Path(backup_path)
            if path.exists() and path.parent == BACKUP_PATH:
                path.unlink()
                logger.info(f"Backup deleted: {backup_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False
