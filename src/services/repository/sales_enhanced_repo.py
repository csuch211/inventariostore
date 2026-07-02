"""Sales repository for discounts and promotions."""

import sqlite3
from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SalesEnhancedRepository(BaseRepository):
    """Repository for enhanced sales operations (discounts, promotions)."""

    # ============ Descuentos ============

    def crear_descuento(
        self,
        codigo: str,
        nombre: str,
        tipo: str = "porcentaje",
        valor: float = 0,
        fecha_inicio: str = "",
        fecha_fin: str = "",
        uso_maximo: int = 0,
        usuario: str = "system",
    ) -> dict:
        """Create a discount code."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO descuentos
                       (codigo, nombre, tipo, valor, fecha_inicio, fecha_fin,
                        uso_maximo, creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (codigo, nombre, tipo, valor, fecha_inicio, fecha_fin,
                     uso_maximo, now, usuario),
                )
                descuento_id = cursor.lastrowid
                self._audit_log(conn, "CREATE", "descuentos", descuento_id, usuario,
                               f"Descuento '{codigo}' creado")
                conn.commit()
            return {"id": descuento_id}
        except sqlite3.IntegrityError:
            raise DatabaseException(f"Discount code '{codigo}' already exists")
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create discount: {e}")

    def obtener_descuentos(self, activo: bool = True) -> list[dict]:
        """List discounts."""
        try:
            with self._get_connection() as conn:
                if activo:
                    cursor = conn.execute(
                        "SELECT * FROM descuentos WHERE activo = 1 ORDER BY codigo"
                    )
                else:
                    cursor = conn.execute("SELECT * FROM descuentos ORDER BY codigo")
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch discounts: {e}")

    def aplicar_descuento(self, codigo: str) -> dict | None:
        """Validate and apply a discount code. Returns discount info or None."""
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    """SELECT * FROM descuentos
                       WHERE codigo = ? AND activo = 1""",
                    (codigo,),
                ).fetchone()
                if not row:
                    return None

                descuento = dict(row)

                # Check expiry
                if descuento.get("fecha_fin"):
                    try:
                        fecha_fin = datetime.fromisoformat(descuento["fecha_fin"])
                        if datetime.now() > fecha_fin:
                            return None
                    except (ValueError, TypeError):
                        pass

                # Check usage limit
                if (descuento.get("uso_maximo", 0) > 0
                        and descuento.get("uso_actual", 0) >= descuento["uso_maximo"]):
                    return None

                return descuento
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to apply discount: {e}")

    def registrar_uso_descuento(self, descuento_id: int) -> bool:
        """Increment usage counter for a discount."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE descuentos SET uso_actual = uso_actual + 1 WHERE id = ?",
                    (descuento_id,),
                )
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to register discount usage: {e}")

    def eliminar_descuento(self, descuento_id: int, usuario: str = "system") -> bool:
        """Soft-delete discount."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE descuentos SET activo = 0 WHERE id = ?",
                    (descuento_id,),
                )
                self._audit_log(conn, "DELETE", "descuentos", descuento_id, usuario,
                               "Descuento desactivado")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete discount: {e}")

    # ============ Promociones ============

    def crear_promocion(
        self,
        nombre: str,
        tipo: str = "descuento",
        descripcion: str = "",
        valor: float = 0,
        fecha_inicio: str = "",
        fecha_fin: str = "",
        usuario: str = "system",
    ) -> dict:
        """Create a promotion."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO promociones
                       (nombre, tipo, descripcion, valor, fecha_inicio, fecha_fin,
                        creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (nombre, tipo, descripcion, valor, fecha_inicio, fecha_fin,
                     now, usuario),
                )
                promocion_id = cursor.lastrowid
                self._audit_log(conn, "CREATE", "promociones", promocion_id, usuario,
                               f"Promoción '{nombre}' creada")
                conn.commit()
            return {"id": promocion_id}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create promotion: {e}")

    def obtener_promociones(self, activo: bool = True) -> list[dict]:
        """List promotions."""
        try:
            with self._get_connection() as conn:
                if activo:
                    cursor = conn.execute(
                        "SELECT * FROM promociones WHERE activo = 1 ORDER BY fecha_inicio DESC"
                    )
                else:
                    cursor = conn.execute("SELECT * FROM promociones ORDER BY fecha_inicio DESC")
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch promotions: {e}")

    def eliminar_promocion(self, promocion_id: int, usuario: str = "system") -> bool:
        """Soft-delete promotion."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE promociones SET activo = 0 WHERE id = ?",
                    (promocion_id,),
                )
                self._audit_log(conn, "DELETE", "promociones", promocion_id, usuario,
                               "Promoción desactivada")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete promotion: {e}")

    # ============ Reportes de Ventas ============

    def ventas_por_periodo(self, fecha_inicio: str, fecha_fin: str) -> dict:
        """Get sales summary for a period."""
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    """SELECT
                       COUNT(*) as total_ventas,
                       COALESCE(SUM(total), 0) as ingresos_totales,
                       COALESCE(AVG(total), 0) as venta_promedio
                       FROM ventas
                       WHERE estado = 'completada'
                       AND date(creado_en) BETWEEN ? AND ?""",
                    (fecha_inicio, fecha_fin),
                ).fetchone()
                return dict(row) if row else {}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch sales report: {e}")

    def ventas_por_producto(self, fecha_inicio: str, fecha_fin: str) -> list[dict]:
        """Get sales by product for a period."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT p.codigo, p.nombre, SUM(vd.cantidad) as unidades,
                       SUM(vd.subtotal) as ingresos
                       FROM ventas_detalle vd
                       JOIN productos p ON vd.producto_id = p.id
                       JOIN ventas v ON vd.venta_id = v.id
                       WHERE v.estado = 'completada'
                       AND date(v.creado_en) BETWEEN ? AND ?
                       GROUP BY p.codigo, p.nombre
                       ORDER BY ingresos DESC""",
                    (fecha_inicio, fecha_fin),
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch sales by product: {e}")

    def ventas_por_cliente(self, fecha_inicio: str, fecha_fin: str) -> list[dict]:
        """Get sales by client for a period."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT c.nombre, c.apellido, COUNT(*) as num_ventas,
                       SUM(v.total) as total_compras
                       FROM ventas v
                       JOIN clientes c ON v.cliente_id = c.id
                       WHERE v.estado = 'completada'
                       AND date(v.creado_en) BETWEEN ? AND ?
                       GROUP BY c.id
                       ORDER BY total_compras DESC""",
                    (fecha_inicio, fecha_fin),
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch sales by client: {e}")
