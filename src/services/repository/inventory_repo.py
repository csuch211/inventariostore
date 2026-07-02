"""
Warehouse and inventory repository.
"""

import sqlite3
from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class InventoryRepository(BaseRepository):
    def crear_almacen(self, nombre: str, ubicacion: str = "", usuario: str = "system") -> int:
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO almacenes (nombre, ubicacion, creado_en, actualizado_en) VALUES (?, ?, ?, ?)",
                    (nombre, ubicacion, now, now),
                )
                conn.commit()
                self._audit_log(
                    conn,
                    "CREATE",
                    "almacenes",
                    cursor.lastrowid,
                    usuario,
                    f"Almacén creado: {nombre}",
                )
                return cursor.lastrowid
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create warehouse: {e}")

    def obtener_almacenes(self) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM almacenes WHERE activo = 1 ORDER BY nombre")
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch warehouses: {e}")

    def obtener_almacen_por_id(self, almacen_id: int) -> dict | None:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM almacenes WHERE id = ?", (almacen_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch warehouse: {e}")

    def actualizar_almacen(
        self,
        almacen_id: int,
        nombre: str | None = None,
        ubicacion: str | None = None,
        usuario: str = "system",
    ) -> None:
        now = datetime.now().isoformat()
        try:
            updates = []
            values = []
            if nombre is not None:
                updates.append("nombre = ?")
                values.append(nombre)
            if ubicacion is not None:
                updates.append("ubicacion = ?")
                values.append(ubicacion)
            if not updates:
                return
            updates.append("actualizado_en = ?")
            values.append(now)
            values.append(almacen_id)
            _allowed_columns = {"nombre", "ubicacion", "actualizado_en"}
            for upd in updates:
                col_name = upd.split(" = ")[0]
                if col_name not in _allowed_columns:
                    raise ValueError(f"Columna no permitida: {col_name}")
            with self._get_connection() as conn:
                conn.execute(f"UPDATE almacenes SET {', '.join(updates)} WHERE id = ?", values)
                conn.commit()
                self._audit_log(
                    conn, "UPDATE", "almacenes", almacen_id, usuario, "Almacén actualizado"
                )
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to update warehouse: {e}")

    def eliminar_almacen(self, almacen_id: int, usuario: str = "system") -> None:
        """Soft-delete a warehouse (mark inactive)."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE almacenes SET activo = 0, actualizado_en = ? WHERE id = ?",
                    (datetime.now().isoformat(), almacen_id),
                )
                conn.commit()
                self._audit_log(
                    conn, "DELETE", "almacenes", almacen_id, usuario, "Almacén desactivado"
                )
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete warehouse: {e}")

    def obtener_inventario_almacen(self, almacen_id: int) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT ia.*, p.nombre as producto_nombre, p.codigo as producto_codigo, p.precio
                    FROM inventario_almacen ia
                    JOIN productos p ON ia.producto_id = p.id
                    WHERE ia.almacen_id = ? AND p.activo = 1
                    ORDER BY p.nombre
                """,
                    (almacen_id,),
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch warehouse inventory: {e}")

    def ajustar_stock_almacen(
        self, producto_id: int, almacen_id: int, cantidad: int, usuario: str = "system"
    ) -> int:
        try:
            datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT cantidad FROM inventario_almacen WHERE producto_id = ? AND almacen_id = ?",
                    (producto_id, almacen_id),
                )
                row = cursor.fetchone()
                old_cantidad = row["cantidad"] if row else 0
                conn.execute(
                    """
                    INSERT INTO inventario_almacen (producto_id, almacen_id, cantidad)
                    VALUES (?, ?, ?)
                    ON CONFLICT(producto_id, almacen_id) DO UPDATE SET cantidad = ?
                """,
                    (producto_id, almacen_id, cantidad, cantidad),
                )
                conn.commit()
                return old_cantidad
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to adjust warehouse stock: {e}")

    def obtener_todo_stock_almacenes(self) -> list[dict]:
        """Get full warehouse inventory list with product + warehouse names."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT ia.*, p.nombre as producto_nombre, p.codigo as producto_codigo,
                           a.nombre as almacen_nombre
                    FROM inventario_almacen ia
                    JOIN productos p ON ia.producto_id = p.id
                    JOIN almacenes a ON ia.almacen_id = a.id
                    WHERE p.activo = 1 AND a.activo = 1
                    ORDER BY a.nombre, p.nombre
                """)
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch all warehouse inventory: {e}")
