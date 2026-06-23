"""
User and RBAC repository.
"""

import sqlite3
from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class UserRepository(BaseRepository):
    def crear_usuario(self, username, password_hash, nombre, rol, usuario="system") -> int:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO usuarios (username, password_hash, nombre, rol, creado_en, actualizado_en) VALUES (?, ?, ?, ?, ?, ?)",
                (username, password_hash, nombre, rol, now, now),
            )
            conn.commit()
            return cursor.lastrowid

    def obtener_usuarios(self) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, username, nombre, rol, activo FROM usuarios ORDER BY nombre"
            )
            return [dict(r) for r in cursor.fetchall()]

    def obtener_usuario_por_username(self, username) -> dict | None:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM usuarios WHERE username = ?", (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def obtener_permisos_catalogo(self) -> list[dict]:
        """Return the full permission catalog."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM permisos ORDER BY modulo, accion")
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch permission catalog: {e}")

    def obtener_roles(self) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM roles ORDER BY nombre")
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch roles: {e}")

    def obtener_rol_por_nombre(self, nombre: str) -> dict | None:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM roles WHERE nombre = ?", (nombre,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch role: {e}")

    def obtener_permisos_de_rol(self, rol_id: int) -> list[str]:
        """Return permission keys for a given role."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT p.clave FROM permisos p
                       JOIN rol_permisos rp ON rp.permiso_id = p.id
                       WHERE rp.rol_id = ?
                       ORDER BY p.clave""",
                    (rol_id,),
                )
                return [r["clave"] for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch role permissions: {e}")

    def obtener_roles_de_usuario(self, usuario_id: int) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT r.* FROM roles r
                       JOIN usuario_roles ur ON ur.rol_id = r.id
                       WHERE ur.usuario_id = ?
                       ORDER BY r.nombre""",
                    (usuario_id,),
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch user roles: {e}")

    def obtener_permisos_de_usuario(self, usuario_id: int) -> list[str]:
        """Resolve the full permission set for a user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT DISTINCT p.clave FROM permisos p
                       JOIN rol_permisos rp ON rp.permiso_id = p.id
                       JOIN usuario_roles ur ON ur.rol_id = rp.rol_id
                       WHERE ur.usuario_id = ?
                       UNION
                       SELECT DISTINCT p.clave FROM permisos p
                       JOIN usuario_permisos_extra upe ON upe.permiso_id = p.id
                       WHERE upe.usuario_id = ?
                       ORDER BY 1""",
                    (usuario_id, usuario_id),
                )
                return [r["clave"] for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to resolve user permissions: {e}")

    def asignar_rol_a_usuario(
        self, usuario_id: int, rol_id: int, usuario_actor: str = "system"
    ) -> bool:
        """Assign a role to a user (replaces previous roles)."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM usuario_roles WHERE usuario_id = ?", (usuario_id,))
                conn.execute(
                    "INSERT INTO usuario_roles (usuario_id, rol_id) VALUES (?, ?)",
                    (usuario_id, rol_id),
                )
                cursor = conn.execute("SELECT nombre FROM roles WHERE id = ?", (rol_id,))
                row = cursor.fetchone()
                if row:
                    conn.execute(
                        "UPDATE usuarios SET rol = ?, actualizado_en = ? WHERE id = ?",
                        (row["nombre"], datetime.now().isoformat(), usuario_id),
                    )
                conn.commit()
                self._audit_log(
                    conn,
                    "UPDATE",
                    "usuarios",
                    usuario_id,
                    usuario_actor,
                    f"Rol asignado (id={rol_id})",
                )
                return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to assign role: {e}")

    def actualizar_tema_usuario(self, usuario_id: int, tema: str) -> None:
        """Update the theme preference for a user."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE usuarios SET theme_mode = ? WHERE id = ?",
                    (tema, usuario_id),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to update user theme: {e}")

    def obtener_permisos_extra(self, usuario_id: int) -> list[str]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT p.clave FROM permisos p
                       JOIN usuario_permisos_extra upe ON upe.permiso_id = p.id
                       WHERE upe.usuario_id = ?
                       ORDER BY p.clave""",
                    (usuario_id,),
                )
                return [r["clave"] for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch user extra perms: {e}")

    def agregar_permiso_extra(
        self, usuario_id: int, permiso_clave: str, usuario_actor: str = "system"
    ) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT id FROM permisos WHERE clave = ?", (permiso_clave,))
                row = cursor.fetchone()
                if not row:
                    raise DatabaseException(f"Unknown permission: {permiso_clave}")
                conn.execute(
                    """INSERT OR IGNORE INTO usuario_permisos_extra
                       (usuario_id, permiso_id) VALUES (?, ?)""",
                    (usuario_id, row["id"]),
                )
                conn.commit()
                self._audit_log(
                    conn,
                    "UPDATE",
                    "usuarios",
                    usuario_id,
                    usuario_actor,
                    f"Permiso extra: {permiso_clave}",
                )
                return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to add extra permission: {e}")

    def quitar_permiso_extra(
        self, usuario_id: int, permiso_clave: str, usuario_actor: str = "system"
    ) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT id FROM permisos WHERE clave = ?", (permiso_clave,))
                row = cursor.fetchone()
                if not row:
                    return False
                conn.execute(
                    """DELETE FROM usuario_permisos_extra
                       WHERE usuario_id = ? AND permiso_id = ?""",
                    (usuario_id, row["id"]),
                )
                conn.commit()
                self._audit_log(
                    conn,
                    "UPDATE",
                    "usuarios",
                    usuario_id,
                    usuario_actor,
                    f"Permiso extra removido: {permiso_clave}",
                )
                return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to remove extra permission: {e}")

    def obtener_usuario_por_username_full(self, username: str) -> dict | None:
        """Get a user row by username (used for RBAC login resolution)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM usuarios WHERE username = ?", (username,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch user: {e}")
