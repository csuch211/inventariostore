"""
Client and sales repository.
"""

import sqlite3
from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SaleRepository(BaseRepository):
    def crear_cliente(self, nombre, telefono="", email="", direccion="", usuario="system") -> int:
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO clientes (nombre, telefono, email, direccion, creado_en, actualizado_en)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (nombre, telefono, email, direccion, now, now),
                )
                conn.commit()
                self._audit_log(
                    conn,
                    "CREATE",
                    "clientes",
                    cursor.lastrowid,
                    usuario,
                    f"Cliente creado: {nombre}",
                )
                return cursor.lastrowid
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create customer: {e}")

    def obtener_clientes(self) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM clientes WHERE activo = 1 ORDER BY nombre")
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch customers: {e}")

    def obtener_cliente_por_id(self, cliente_id: int) -> dict | None:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch customer: {e}")

    def actualizar_cliente(
        self, cliente_id, nombre, telefono="", email="", direccion="", usuario="system"
    ) -> int:
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """UPDATE clientes SET nombre=?, telefono=?, email=?, direccion=?, actualizado_en=?
                       WHERE id=?""",
                    (nombre, telefono, email, direccion, now, cliente_id),
                )
                conn.commit()
                self._audit_log(
                    conn,
                    "UPDATE",
                    "clientes",
                    cliente_id,
                    usuario,
                    f"Cliente actualizado: {nombre}",
                )
                return cliente_id
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to update customer: {e}")

    def eliminar_cliente(self, cliente_id: int, usuario="system") -> None:
        """Soft-delete a customer (mark inactive)."""
        try:
            with self._get_connection() as conn:
                conn.execute("UPDATE clientes SET activo = 0 WHERE id = ?", (cliente_id,))
                conn.commit()
                self._audit_log(
                    conn, "DELETE", "clientes", cliente_id, usuario, "Cliente eliminado"
                )
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete customer: {e}")

    def crear_venta(
        self,
        cliente_id,
        total,
        items: list[dict],
        metodo_pago="efectivo",
        referencia="",
        usuario="system",
    ) -> int:
        """Create a sale with details, payment, and stock deduction in a transaction."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO ventas (cliente_id, total, estado, creado_en, creado_por) VALUES (?, ?, 'completada', ?, ?)",
                    (cliente_id, total, now, usuario),
                )
                venta_id = cursor.lastrowid

                for item in items:
                    conn.execute(
                        """INSERT INTO ventas_detalle (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            venta_id,
                            item["producto_id"],
                            item["cantidad"],
                            item["precio_unitario"],
                            item["subtotal"],
                        ),
                    )
                    conn.execute(
                        """UPDATE productos SET cantidad = cantidad - ?, actualizado_en = ?, actualizado_por = ?
                           WHERE id = ? AND cantidad >= ?""",
                        (item["cantidad"], now, usuario, item["producto_id"], item["cantidad"]),
                    )
                    conn.execute(
                        """INSERT INTO historial_stock (producto_id, cantidad_anterior, cantidad_nueva, tipo_movimiento, razon, creado_en, usuario)
                           VALUES (?, (SELECT cantidad + ? FROM productos WHERE id = ?), (SELECT cantidad FROM productos WHERE id = ?), 'salida', ?, ?, ?)""",
                        (
                            item["producto_id"],
                            item["cantidad"],
                            item["producto_id"],
                            item["producto_id"],
                            f"Venta #{venta_id}",
                            now,
                            usuario,
                        ),
                    )

                conn.execute(
                    "INSERT INTO pagos (venta_id, metodo, monto, referencia, creado_en) VALUES (?, ?, ?, ?, ?)",
                    (venta_id, metodo_pago, total, referencia, now),
                )

                conn.commit()
                self._audit_log(
                    conn, "CREATE", "ventas", venta_id, usuario, f"Venta creada: ${total:.2f}"
                )
                return venta_id
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create sale: {e}")

    def obtener_ventas(self, limit=100) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT v.*, c.nombre as cliente_nombre
                    FROM ventas v
                    LEFT JOIN clientes c ON v.cliente_id = c.id
                    ORDER BY v.creado_en DESC LIMIT ?
                """,
                    (limit,),
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch sales: {e}")

    def obtener_venta_por_id(self, venta_id: int) -> dict | None:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT v.*, c.nombre as cliente_nombre, c.telefono as cliente_telefono
                    FROM ventas v
                    LEFT JOIN clientes c ON v.cliente_id = c.id
                    WHERE v.id = ?
                """,
                    (venta_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                venta = dict(row)
                cursor2 = conn.execute(
                    """
                    SELECT vd.*, p.nombre as producto_nombre, p.codigo as producto_codigo
                    FROM ventas_detalle vd
                    LEFT JOIN productos p ON vd.producto_id = p.id
                    WHERE vd.venta_id = ?
                """,
                    (venta_id,),
                )
                venta["detalles"] = [dict(r) for r in cursor2.fetchall()]
                cursor3 = conn.execute("SELECT * FROM pagos WHERE venta_id = ?", (venta_id,))
                venta["pagos"] = [dict(r) for r in cursor3.fetchall()]
                return venta
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch sale: {e}")

    def cancelar_venta(self, venta_id: int, usuario="system") -> None:
        """Cancel a sale and reverse stock."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                venta = self.obtener_venta_por_id(venta_id)
                if not venta:
                    raise DatabaseException("Venta no encontrada")
                if venta["estado"] == "cancelada":
                    raise DatabaseException("La venta ya fue cancelada")

                conn.execute(
                    "UPDATE ventas SET estado = 'cancelada', actualizado_en = ? WHERE id = ?",
                    (now, venta_id),
                )

                for det in venta.get("detalles", []):
                    conn.execute(
                        "UPDATE productos SET cantidad = cantidad + ?, actualizado_en = ? WHERE id = ?",
                        (det["cantidad"], now, det["producto_id"]),
                    )
                    conn.execute(
                        """INSERT INTO historial_stock (producto_id, cantidad_anterior, cantidad_nueva, tipo_movimiento, razon, creado_en, usuario)
                           VALUES (?, (SELECT cantidad - ? FROM productos WHERE id = ?), (SELECT cantidad FROM productos WHERE id = ?), 'entrada', ?, ?, ?)""",
                        (
                            det["producto_id"],
                            det["cantidad"],
                            det["producto_id"],
                            det["producto_id"],
                            f"Devolución venta #{venta_id}",
                            now,
                            usuario,
                        ),
                    )

                conn.commit()
                self._audit_log(
                    conn, "CANCEL", "ventas", venta_id, usuario, f"Venta cancelada #{venta_id}"
                )
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to cancel sale: {e}")

    def obtener_ventas_estadisticas(self) -> dict:
        """Get sales statistics for dashboard."""
        try:
            with self._get_connection() as conn:
                today = datetime.now().isoformat()[:10]
                cursor = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total_ventas,
                        COALESCE(SUM(total), 0) as ingresos_totales,
                        COALESCE(SUM(CASE WHEN substr(creado_en,1,10) = ? THEN total ELSE 0 END), 0) as ingresos_hoy,
                        COALESCE(COUNT(CASE WHEN substr(creado_en,1,10) = ? THEN 1 END), 0) as ventas_hoy
                    FROM ventas WHERE estado = 'completada'
                """,
                    (today, today),
                )
                return dict(cursor.fetchone())
        except sqlite3.Error:
            return {"total_ventas": 0, "ingresos_totales": 0, "ingresos_hoy": 0, "ventas_hoy": 0}
