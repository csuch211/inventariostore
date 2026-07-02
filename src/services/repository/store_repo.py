"""Online store repository."""

import sqlite3
from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class StoreRepository(BaseRepository):
    def obtener_config(self) -> dict[str, str]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT clave, valor FROM tienda_config")
                return {r["clave"]: r["valor"] for r in cursor.fetchall()}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch store config: {e}")

    def guardar_config(self, clave: str, valor: str) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO tienda_config (clave, valor) VALUES (?, ?) ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
                    (clave, valor),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to save store config: {e}")

    def listar_productos_tienda(self, solo_visibles: bool = True) -> list[dict]:
        try:
            with self._get_connection() as conn:
                query = """
                    SELECT tp.*, p.codigo, p.nombre, p.precio, p.cantidad as stock,
                           p.descripcion, p.categoria
                    FROM tienda_productos tp
                    JOIN productos p ON tp.producto_id = p.id
                """
                params: list = []
                if solo_visibles:
                    query += " WHERE tp.visible = 1"
                query += " ORDER BY tp.orden, p.nombre"
                cursor = conn.execute(query, params)
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch store products: {e}")

    def sincronizar_producto(self, producto_id: int, visible: bool = False,
                             descripcion_larga: str = "", imagen_url: str = "",
                             destacado: bool = False, orden: int = 0) -> int:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO tienda_productos (producto_id, visible, descripcion_larga, imagen_url, destacado, orden)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(producto_id) DO UPDATE SET
                        visible = excluded.visible,
                        descripcion_larga = excluded.descripcion_larga,
                        imagen_url = excluded.imagen_url,
                        destacado = excluded.destacado,
                        orden = excluded.orden
                """, (producto_id, int(visible), descripcion_larga, imagen_url, int(destacado), orden))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to sync store product: {e}")

    def eliminar_producto_tienda(self, producto_id: int) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM tienda_productos WHERE producto_id = ?", (producto_id,))
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete store product: {e}")

    def obtener_productos_destacados(self, limit: int = 8) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT tp.*, p.codigo, p.nombre, p.precio, p.cantidad as stock,
                           p.descripcion, p.categoria
                    FROM tienda_productos tp
                    JOIN productos p ON tp.producto_id = p.id
                    WHERE tp.visible = 1 AND tp.destacado = 1
                    ORDER BY tp.orden, p.nombre
                    LIMIT ?
                """, (limit,))
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch featured products: {e}")

    def crear_pedido(self, cliente_nombre: str, cliente_email: str,
                     cliente_telefono: str, direccion_envio: str,
                     notas: str, total: float, items: list[dict],
                     metodo_pago: str = "pendiente") -> int:
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO tienda_pedidos (cliente_nombre, cliente_email, cliente_telefono,
                        direccion_envio, notas, total, estado, metodo_pago, creado_en, actualizado_en)
                    VALUES (?, ?, ?, ?, ?, ?, 'pendiente', ?, ?, ?)
                """, (cliente_nombre, cliente_email, cliente_telefono,
                      direccion_envio, notas, total, metodo_pago, now, now))
                pedido_id = cursor.lastrowid

                for item in items:
                    conn.execute("""
                        INSERT INTO tienda_pedidos_items (pedido_id, producto_id, cantidad, precio_unitario, subtotal)
                        VALUES (?, ?, ?, ?, ?)
                    """, (pedido_id, item["producto_id"], item["cantidad"],
                          item["precio_unitario"], item["subtotal"]))

                conn.commit()
                return pedido_id
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create store order: {e}")

    def obtener_pedidos(self, estado: str | None = None) -> list[dict]:
        try:
            with self._get_connection() as conn:
                _allowed_columns = {"estado"}
                where_clauses = []
                params: list = []
                if estado:
                    where_clauses.append("estado = ?")
                    params.append(estado)
                for clause in where_clauses:
                    col = clause.split(None, 1)[0]
                    if col not in _allowed_columns:
                        raise ValueError(f"Columna no permitida en WHERE: {col}")
                query = "SELECT * FROM tienda_pedidos"
                if where_clauses:
                    query += " WHERE " + " AND ".join(where_clauses)
                query += " ORDER BY creado_en DESC"
                cursor = conn.execute(query, params)
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch store orders: {e}")

    def obtener_pedido_por_id(self, pedido_id: int) -> dict | None:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM tienda_pedidos WHERE id = ?", (pedido_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                pedido = dict(row)
                cursor2 = conn.execute("""
                    SELECT tpi.*, p.codigo, p.nombre
                    FROM tienda_pedidos_items tpi
                    LEFT JOIN productos p ON tpi.producto_id = p.id
                    WHERE tpi.pedido_id = ?
                """, (pedido_id,))
                pedido["items"] = [dict(r) for r in cursor2.fetchall()]
                return pedido
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch store order: {e}")

    def actualizar_estado_pedido(self, pedido_id: int, estado: str) -> None:
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE tienda_pedidos SET estado = ?, actualizado_en = ? WHERE id = ?",
                    (estado, now, pedido_id),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to update order status: {e}")

    def obtener_estadisticas_tienda(self) -> dict:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT
                        COUNT(*) as total_pedidos,
                        COALESCE(SUM(CASE WHEN estado = 'pendiente' THEN 1 ELSE 0 END), 0) as pendientes,
                        COALESCE(SUM(CASE WHEN estado = 'entregado' THEN 1 ELSE 0 END), 0) as entregados,
                        COALESCE(SUM(total), 0) as ingresos_totales
                    FROM tienda_pedidos
                """)
                return dict(cursor.fetchone())
        except sqlite3.Error:
            return {"total_pedidos": 0, "pendientes": 0, "entregados": 0, "ingresos_totales": 0}
