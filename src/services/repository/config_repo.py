"""
Configuration and backup repository.
"""

import sqlite3
from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ConfigRepository(BaseRepository):
    def obtener_config(self, clave: str, default: str = "") -> str:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
                row = cursor.fetchone()
                return row["valor"] if row else default
        except sqlite3.Error:
            return default

    def guardar_config(self, clave: str, valor: str) -> None:
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """INSERT INTO configuracion (clave, valor, actualizado_en)
                       VALUES (?, ?, ?)
                       ON CONFLICT(clave) DO UPDATE SET valor = ?, actualizado_en = ?""",
                    (clave, valor, now, valor, now),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to save config: {e}")

    def registrar_backup(
        self, ruta: str, tamano: int, tipo: str = "manual", usuario: str = "system"
    ) -> None:
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO backups (ruta, tamano, tipo, creado_en, creado_por) VALUES (?, ?, ?, ?, ?)",
                    (ruta, tamano, tipo, now, usuario),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to register backup: {e}")

    def obtener_backups(self, limit=50) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM backups ORDER BY creado_en DESC LIMIT ?", (limit,)
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch backups: {e}")

    def eliminar_backup(self, backup_id: int) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM backups WHERE id = ?", (backup_id,))
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete backup record: {e}")
