"""Notifications repository for notification management."""

import sqlite3
from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class NotificationRepository(BaseRepository):
    """Repository for notification operations."""

    # ============ Plantillas ============

    def crear_plantilla(
        self,
        nombre: str,
        asunto: str,
        cuerpo: str,
        tipo: str = "email",
        variables: str = "",
        usuario: str = "system",
    ) -> dict:
        """Create a notification template."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO plantillas_notificacion
                       (nombre, asunto, cuerpo, tipo, variables, creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (nombre, asunto, cuerpo, tipo, variables, now, usuario),
                )
                plantilla_id = cursor.lastrowid
                self._audit_log(conn, "CREATE", "plantillas_notificacion", plantilla_id, usuario,
                               f"Plantilla '{nombre}' creada")
                conn.commit()
            return {"id": plantilla_id}
        except sqlite3.IntegrityError:
            raise DatabaseException(f"Template '{nombre}' already exists")
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create template: {e}")

    def obtener_plantillas(self, tipo: str | None = None) -> list[dict]:
        """List notification templates."""
        try:
            with self._get_connection() as conn:
                if tipo:
                    cursor = conn.execute(
                        "SELECT * FROM plantillas_notificacion WHERE tipo = ? AND activo = 1 ORDER BY nombre",
                        (tipo,),
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM plantillas_notificacion WHERE activo = 1 ORDER BY nombre"
                    )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch templates: {e}")

    def eliminar_plantilla(self, plantilla_id: int, usuario: str = "system") -> bool:
        """Soft-delete notification template."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE plantillas_notificacion SET activo = 0 WHERE id = ?",
                    (plantilla_id,),
                )
                self._audit_log(conn, "DELETE", "plantillas_notificacion", plantilla_id, usuario,
                               "Plantilla eliminada")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete template: {e}")

    # ============ Canales ============

    def crear_canal(
        self, nombre: str, tipo: str, configuracion: str = "", usuario: str = "system"
    ) -> dict:
        """Create a notification channel."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO canales_notificacion
                       (nombre, tipo, configuracion, creado_en)
                       VALUES (?, ?, ?, ?)""",
                    (nombre, tipo, configuracion, now),
                )
                canal_id = cursor.lastrowid
                self._audit_log(conn, "CREATE", "canales_notificacion", canal_id, usuario,
                               f"Canal '{nombre}' creado")
                conn.commit()
            return {"id": canal_id}
        except sqlite3.IntegrityError:
            raise DatabaseException(f"Channel '{nombre}' already exists")
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create channel: {e}")

    def obtener_canales(self) -> list[dict]:
        """List notification channels."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM canales_notificacion WHERE activo = 1 ORDER BY nombre"
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch channels: {e}")

    # ============ Notificaciones ============

    def crear_notificacion(
        self,
        titulo: str,
        mensaje: str,
        tipo: str = "info",
        canal: str = "sistema",
        destinatario: str = "",
        referencia_tipo: str = "",
        referencia_id: int | None = None,
        usuario: str = "system",
    ) -> dict:
        """Create a notification."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO notificaciones
                       (titulo, mensaje, tipo, canal, destinatario,
                        referencia_tipo, referencia_id, creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (titulo, mensaje, tipo, canal, destinatario,
                     referencia_tipo, referencia_id, now, usuario),
                )
                notificacion_id = cursor.lastrowid
                conn.commit()
            return {"id": notificacion_id}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create notification: {e}")

    def obtener_notificaciones(
        self, destinatario: str | None = None, tipo: str | None = None,
        estado: str | None = None, limit: int = 50
    ) -> list[dict]:
        """List notifications."""
        try:
            with self._get_connection() as conn:
                where = []
                params = []
                if destinatario:
                    where.append("destinatario = ?")
                    params.append(destinatario)
                if tipo:
                    where.append("tipo = ?")
                    params.append(tipo)
                if estado:
                    where.append("estado = ?")
                    params.append(estado)

                where_clause = " AND ".join(where) if where else "1=1"
                cursor = conn.execute(
                    f"""SELECT * FROM notificaciones
                        WHERE {where_clause}
                        ORDER BY creado_en DESC
                        LIMIT ?""",
                    [*params, limit],
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch notifications: {e}")

    def marcar_leido(self, notificacion_id: int) -> bool:
        """Mark notification as read."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE notificaciones SET estado = 'leido', leido_en = ? WHERE id = ?",
                    (datetime.now().isoformat(), notificacion_id),
                )
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to mark notification: {e}")

    def marcar_todas_leidas(self, destinatario: str | None = None) -> int:
        """Mark all notifications as read. Returns count."""
        try:
            with self._get_connection() as conn:
                params = [datetime.now().isoformat()]
                if destinatario:
                    params.append(destinatario)
                    cursor = conn.execute(
                        """UPDATE notificaciones SET estado = 'leido', leido_en = ?
                            WHERE destinatario = ? AND estado != 'leido'""",
                        params,
                    )
                else:
                    cursor = conn.execute(
                        """UPDATE notificaciones SET estado = 'leido', leido_en = ?
                            WHERE estado != 'leido'""",
                        params,
                    )
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to mark notifications: {e}")

    def contar_no_leidas(self, destinatario: str | None = None) -> int:
        """Count unread notifications."""
        try:
            with self._get_connection() as conn:
                if destinatario:
                    row = conn.execute(
                        "SELECT COUNT(*) as cnt FROM notificaciones WHERE estado != 'leido' AND destinatario = ?",
                        (destinatario,),
                    ).fetchone()
                else:
                    row = conn.execute(
                        "SELECT COUNT(*) as cnt FROM notificaciones WHERE estado != 'leido'"
                    ).fetchone()
                return row["cnt"] or 0
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to count notifications: {e}")

    def eliminar_notificacion(self, notificacion_id: int) -> bool:
        """Delete a notification."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM notificaciones WHERE id = ?", (notificacion_id,))
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete notification: {e}")

    # ============ Preferencias ============

    def obtener_preferencias(self, usuario_id: int) -> dict:
        """Get user notification preferences."""
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM preferencias_notificacion WHERE usuario_id = ?",
                    (usuario_id,),
                ).fetchone()
                if row:
                    return dict(row)
                # Return defaults
                return {
                    "email_enabled": 1, "push_enabled": 1,
                    "stock_alertas": 1, "ventas_notif": 1, "sistema_notif": 1,
                    "frecuencia": "inmediato",
                }
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch preferences: {e}")

    def guardar_preferencias(self, usuario_id: int, preferencias: dict) -> bool:
        """Save user notification preferences."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO preferencias_notificacion
                       (usuario_id, email_enabled, push_enabled, stock_alertas,
                        ventas_notif, sistema_notif, frecuencia)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (usuario_id,
                     preferencias.get("email_enabled", 1),
                     preferencias.get("push_enabled", 1),
                     preferencias.get("stock_alertas", 1),
                     preferencias.get("ventas_notif", 1),
                     preferencias.get("sistema_notif", 1),
                     preferencias.get("frecuencia", "inmediato")),
                )
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to save preferences: {e}")
