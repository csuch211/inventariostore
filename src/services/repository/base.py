"""
Base repository with shared database connection and audit logging.
"""

import contextlib
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from config.settings import DATABASE_FILE, ENABLE_AUDIT_LOG
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class BaseRepository:
    """Base repository providing thread-local connections and audit logging."""

    _local = threading.local()

    def __init__(self, db_path: Path = DATABASE_FILE) -> None:
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.execute("SELECT 1")
                return self._local.conn
            except sqlite3.Error:
                with contextlib.suppress(Exception):
                    self._local.conn.close()
                self._local.conn = None
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
            return conn
        except sqlite3.Error as e:
            logger.exception(f"Database connection error: {e}")
            raise DatabaseException(f"Connection failed: {e}")

    def close_connections(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn is not None:
            with contextlib.suppress(Exception):
                self._local.conn.close()
            self._local.conn = None

    def _audit_log(
        self,
        conn: sqlite3.Connection,
        accion: str,
        tabla: str,
        registro_id: int,
        usuario: str,
        detalles: str,
    ):
        if ENABLE_AUDIT_LOG:
            try:
                now = datetime.now().isoformat()
                conn.execute(
                    """
                    INSERT INTO auditoria (accion, tabla, registro_id, usuario, detalles, creado_en)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (accion, tabla, registro_id, usuario, detalles, now),
                )
            except sqlite3.Error as e:
                logger.warning(f"Failed to record audit log: {e}")
