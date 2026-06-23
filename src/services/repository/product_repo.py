"""
Product, category, supplier, order, chart, and bulk operations repository.
"""

import sqlite3
from datetime import datetime, timedelta

from config.settings import STOCK_LOW_DEFAULT
from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException, DuplicateProductException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ProductRepository(BaseRepository):
    def crear_producto(
        self,
        codigo: str,
        nombre: str,
        cantidad: int = 0,
        precio: float = 0.0,
        descripcion: str = "",
        categoria: str = "",
        stock_min: int = 0,
        proveedor_id: int | None = None,
        usuario: str = "system",
    ) -> dict:
        """Create a new product"""
        try:
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO productos
                    (codigo, nombre, cantidad, precio, descripcion, categoria,
                     stock_min, proveedor_id, creado_en, actualizado_en, creado_por, actualizado_por)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        codigo,
                        nombre,
                        cantidad,
                        precio,
                        descripcion,
                        categoria,
                        stock_min,
                        proveedor_id,
                        now,
                        now,
                        usuario,
                        usuario,
                    ),
                )
                producto_id = cursor.lastrowid
                conn.commit()

                self._audit_log(
                    conn,
                    "CREATE",
                    "productos",
                    producto_id,
                    usuario,
                    f"Created product {codigo}",
                )

                logger.debug(f"Product created: {codigo} by {usuario}")
                return self.obtener_producto_por_id(producto_id)
        except sqlite3.IntegrityError:
            logger.error(f"Duplicate product code: {codigo}")
            raise DuplicateProductException(f"Product code {codigo} already exists")
        except sqlite3.Error as e:
            logger.error(f"Error creating product: {e}")
            raise DatabaseException(f"Failed to create product: {e}")

    def obtener_todos_productos(self, estado: str = "activo") -> list[dict]:
        """Get all products with supplier name"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT p.*, pr.nombre as proveedor_nombre
                       FROM productos p
                       LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
                       WHERE p.estado = ? ORDER BY p.creado_en DESC""",
                    (estado,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching products: {e}")
            raise DatabaseException(f"Failed to fetch products: {e}")

    def obtener_producto_por_id(self, producto_id: int) -> dict | None:
        """Get product by ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT p.*, pr.nombre as proveedor_nombre
                       FROM productos p
                       LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
                       WHERE p.id = ?""",
                    (producto_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error fetching product: {e}")
            raise DatabaseException(f"Failed to fetch product: {e}")

    def obtener_producto_por_codigo(self, codigo: str) -> dict | None:
        """Get product by code"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT p.*, pr.nombre as proveedor_nombre
                       FROM productos p
                       LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
                       WHERE p.codigo = ?""",
                    (codigo,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error fetching product by code: {e}")
            raise DatabaseException(f"Failed to fetch product: {e}")

    def actualizar_producto(
        self,
        producto_id: int,
        nombre: str | None = None,
        cantidad: int | None = None,
        precio: float | None = None,
        descripcion: str | None = None,
        categoria: str | None = None,
        stock_min: int | None = None,
        proveedor_id: int | None = None,
        usuario: str = "system",
    ) -> dict:
        """Update product"""
        try:
            now = datetime.now().isoformat()
            updates = []
            values = []

            if nombre is not None:
                updates.append("nombre = ?")
                values.append(nombre)
            if cantidad is not None:
                updates.append("cantidad = ?")
                values.append(cantidad)
            if precio is not None:
                updates.append("precio = ?")
                values.append(precio)
            if descripcion is not None:
                updates.append("descripcion = ?")
                values.append(descripcion)
            if categoria is not None:
                updates.append("categoria = ?")
                values.append(categoria)
            if stock_min is not None:
                updates.append("stock_min = ?")
                values.append(stock_min)
            if proveedor_id is not None:
                updates.append("proveedor_id = ?")
                values.append(proveedor_id)

            if not updates:
                return self.obtener_producto_por_id(producto_id)

            updates.append("actualizado_en = ?")
            values.append(now)
            updates.append("actualizado_por = ?")
            values.append(usuario)
            values.append(producto_id)

            with self._get_connection() as conn:
                conn.execute(f"UPDATE productos SET {', '.join(updates)} WHERE id = ?", values)
                conn.commit()
                self._audit_log(
                    conn, "UPDATE", "productos", producto_id, usuario, "Product updated"
                )
                logger.debug(f"Product {producto_id} updated by {usuario}")

            return self.obtener_producto_por_id(producto_id)
        except sqlite3.Error as e:
            logger.error(f"Error updating product: {e}")
            raise DatabaseException(f"Failed to update product: {e}")

    def actualizar_stock(
        self,
        producto_id: int,
        cantidad_nueva: int,
        tipo_movimiento: str = "ajuste",
        razon: str = "",
        usuario: str = "system",
    ) -> dict:
        """Update product stock with history"""
        try:
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                producto = self.obtener_producto_por_id(producto_id)
                if not producto:
                    raise DatabaseException(f"Product {producto_id} not found")

                cantidad_anterior = producto["cantidad"]

                tipo = tipo_movimiento.lower()
                if tipo in ("entrada", "compra"):
                    cantidad_final = cantidad_anterior + cantidad_nueva
                    if not razon:
                        razon = "Entrada de mercancía"
                elif tipo in ("salida", "venta"):
                    cantidad_final = max(0, cantidad_anterior - cantidad_nueva)
                    if not razon:
                        razon = "Salida de mercancía"
                elif tipo == "transferencia":
                    if cantidad_nueva >= 0:
                        cantidad_final = cantidad_anterior + cantidad_nueva
                    else:
                        cantidad_final = max(0, cantidad_anterior + cantidad_nueva)
                    if not razon:
                        razon = "Transferencia de inventario"
                else:
                    cantidad_final = max(0, cantidad_nueva)
                    if not razon:
                        razon = "Ajuste de inventario"

                conn.execute(
                    "UPDATE productos SET cantidad = ?, actualizado_en = ?, actualizado_por = ? WHERE id = ?",
                    (cantidad_final, now, usuario, producto_id),
                )

                conn.execute(
                    """
                    INSERT INTO historial_stock
                    (producto_id, cantidad_anterior, cantidad_nueva, tipo_movimiento, razon, creado_en, usuario)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        producto_id,
                        cantidad_anterior,
                        cantidad_final,
                        tipo_movimiento,
                        razon,
                        now,
                        usuario,
                    ),
                )

                conn.commit()
                self._audit_log(
                    conn,
                    "UPDATE_STOCK",
                    "productos",
                    producto_id,
                    usuario,
                    f"Stock changed from {cantidad_anterior} to {cantidad_final} ({tipo_movimiento})",
                )
                logger.debug(
                    f"Stock updated for product {producto_id}: {cantidad_anterior} -> {cantidad_final} ({tipo_movimiento})"
                )

            return self.obtener_producto_por_id(producto_id)
        except sqlite3.Error as e:
            logger.error(f"Error updating stock: {e}")
            raise DatabaseException(f"Failed to update stock: {e}")

    def eliminar_producto(self, producto_id: int, usuario: str = "system") -> None:
        """Soft delete product (mark as inactive)."""
        try:
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE productos SET estado = 'inactivo', actualizado_en = ?, actualizado_por = ? WHERE id = ?",
                    (now, usuario, producto_id),
                )
                conn.commit()
                self._audit_log(
                    conn, "DELETE", "productos", producto_id, usuario, "Product deleted"
                )
                logger.debug(f"Product {producto_id} deleted by {usuario}")
        except sqlite3.Error as e:
            logger.error(f"Error deleting product: {e}")
            raise DatabaseException(f"Failed to delete product: {e}")

    def buscar_productos(self, query: str) -> list[dict]:
        """Search products by code or name"""
        try:
            search_term = f"%{query}%"
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT p.*, pr.nombre as proveedor_nombre
                    FROM productos p
                    LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
                    WHERE p.estado = 'activo' AND (p.codigo LIKE ? OR p.nombre LIKE ?)
                    ORDER BY p.creado_en DESC
                    """,
                    (search_term, search_term),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error searching products: {e}")
            raise DatabaseException(f"Failed to search products: {e}")

    def obtener_historial_stock(self, producto_id: int) -> list[dict]:
        """Get stock history for a product"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM historial_stock
                    WHERE producto_id = ?
                    ORDER BY creado_en DESC
                    """,
                    (producto_id,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching stock history: {e}")
            raise DatabaseException(f"Failed to fetch stock history: {e}")

    def crear_categoria(self, nombre, descripcion="", usuario="system") -> int:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO categorias (nombre, descripcion, creado_en) VALUES (?, ?, ?)",
                (nombre, descripcion, now),
            )
            conn.commit()
            self._audit_log(
                conn,
                "CREATE",
                "categorias",
                cursor.lastrowid,
                usuario,
                f"Categoria creada: {nombre}",
            )
            return cursor.lastrowid

    def obtener_categorias(self) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM categorias WHERE activo = 1 ORDER BY nombre")
            return [dict(r) for r in cursor.fetchall()]

    def crear_proveedor(
        self, nombre, contacto="", telefono="", email="", direccion="", usuario="system"
    ) -> int:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO proveedores (nombre, contacto, telefono, email, direccion, creado_en, actualizado_en) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (nombre, contacto, telefono, email, direccion, now, now),
            )
            conn.commit()
            self._audit_log(
                conn,
                "CREATE",
                "proveedores",
                cursor.lastrowid,
                usuario,
                f"Proveedor creado: {nombre}",
            )
            return cursor.lastrowid

    def obtener_proveedores(self) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM proveedores WHERE activo = 1 ORDER BY nombre")
            return [dict(r) for r in cursor.fetchall()]

    def crear_orden_compra(self, proveedor_id, producto_id, cantidad, usuario="system") -> int:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO ordenes_compra (proveedor_id, producto_id, cantidad, creado_en, actualizado_en, creado_por) VALUES (?, ?, ?, ?, ?, ?)",
                (proveedor_id, producto_id, cantidad, now, now, usuario),
            )
            conn.commit()
            return cursor.lastrowid

    def obtener_ordenes_compra(self, estado=None) -> list[dict]:
        with self._get_connection() as conn:
            if estado:
                cursor = conn.execute(
                    """
                    SELECT oc.*, p.nombre as producto_nombre, p.codigo as producto_codigo, pr.nombre as proveedor_nombre
                    FROM ordenes_compra oc
                    LEFT JOIN productos p ON oc.producto_id = p.id
                    LEFT JOIN proveedores pr ON oc.proveedor_id = pr.id
                    WHERE oc.estado = ? ORDER BY oc.creado_en DESC
                """,
                    (estado,),
                )
            else:
                cursor = conn.execute("""
                    SELECT oc.*, p.nombre as producto_nombre, p.codigo as producto_codigo, pr.nombre as proveedor_nombre
                    FROM ordenes_compra oc
                    LEFT JOIN productos p ON oc.producto_id = p.id
                    LEFT JOIN proveedores pr ON oc.proveedor_id = pr.id
                    ORDER BY oc.creado_en DESC
                """)
            return [dict(r) for r in cursor.fetchall()]

    def _query_stock_bajo(
        self, low_threshold: int | None = None, include_proveedor: bool = False
    ) -> list[dict]:
        """Shared low-stock query used by both public methods."""
        if low_threshold is None:
            low_threshold = STOCK_LOW_DEFAULT
        if include_proveedor:
            select_cols = "p.*, pr.nombre as proveedor_nombre"
            table = "productos p LEFT JOIN proveedores pr ON p.proveedor_id = pr.id"
            prefix = "p."
        else:
            select_cols = "*"
            table = "productos"
            prefix = ""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    f"""SELECT {select_cols}
                        FROM {table}
                        WHERE {prefix}estado = 'activo' AND (
                            {prefix}cantidad = 0
                            OR ({prefix}stock_min > 0 AND {prefix}cantidad <= {prefix}stock_min)
                            OR ({prefix}stock_min = 0 AND {prefix}cantidad <= ?)
                        )
                        ORDER BY ({prefix}cantidad = 0) DESC,
                                 CASE WHEN {prefix}stock_min > 0
                                      THEN {prefix}cantidad * 1.0 / {prefix}stock_min
                                      ELSE {prefix}cantidad * 1.0 / ? END ASC""",
                    (low_threshold, low_threshold),
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch low stock products: {e}")

    def obtener_productos_con_stock_bajo(self, low_threshold: int | None = None) -> list[dict]:
        """Get low-stock products with alert_level column."""
        if low_threshold is None:
            low_threshold = STOCK_LOW_DEFAULT
        rows = self._query_stock_bajo(low_threshold, include_proveedor=False)
        for row in rows:
            if row["cantidad"] == 0:
                row["alert_level"] = "critical"
            elif (
                row["stock_min"] is not None
                and row["stock_min"] > 0
                and row["cantidad"] <= row["stock_min"]
            ) or (
                (row["stock_min"] is None or row["stock_min"] == 0)
                and row["cantidad"] <= low_threshold
            ):
                row["alert_level"] = "low"
            else:
                row["alert_level"] = "ok"
        return rows

    def obtener_historial_stock_completo(self, limit=100) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT hs.*, p.nombre as producto_nombre, p.codigo as producto_codigo
                FROM historial_stock hs
                LEFT JOIN productos p ON hs.producto_id = p.id
                ORDER BY hs.creado_en DESC LIMIT ?
            """,
                (limit,),
            )
            return [dict(r) for r in cursor.fetchall()]

    def obtener_estadisticas(self) -> dict:
        """Get inventory statistics"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT
                        COUNT(*) as total_productos,
                        SUM(cantidad) as cantidad_total,
                        SUM(cantidad * precio) as valor_total
                    FROM productos
                    WHERE estado = 'activo'
                """)
                row = cursor.fetchone()
                return dict(row) if row else {}
        except sqlite3.Error as e:
            logger.error(f"Error fetching statistics: {e}")
            raise DatabaseException(f"Failed to fetch statistics: {e}")

    def actualizar_categoria(
        self, categoria_id: int, nombre: str, descripcion: str = "", usuario: str = "system"
    ) -> int:
        """Update a category. Returns the row id."""
        datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE categorias SET nombre = ?, descripcion = ? WHERE id = ?",
                    (nombre, descripcion, categoria_id),
                )
                conn.commit()
                self._audit_log(
                    conn,
                    "UPDATE",
                    "categorias",
                    categoria_id,
                    usuario,
                    f"Categoria actualizada: {nombre}",
                )
                logger.debug(f"Category {categoria_id} updated by {usuario}")
                return categoria_id
        except sqlite3.IntegrityError:
            raise DuplicateProductException(f"Category name '{nombre}' already exists")
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to update category: {e}")

    def eliminar_categoria(self, categoria_id: int, usuario: str = "system") -> bool:
        """Soft-delete a category (mark inactive)."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE categorias SET activo = 0 WHERE id = ?",
                    (categoria_id,),
                )
                conn.commit()
                self._audit_log(
                    conn,
                    "DELETE",
                    "categorias",
                    categoria_id,
                    usuario,
                    "Categoria eliminada",
                )
                logger.debug(f"Category {categoria_id} deleted by {usuario}")
                return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete category: {e}")

    def obtener_categoria_por_id(self, categoria_id: int) -> dict | None:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM categorias WHERE id = ?", (categoria_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch category: {e}")

    def seed_categorias(self, nombres: list[str], usuario: str = "system") -> int:
        """Insert a list of category names, skipping duplicates. Returns count inserted."""
        inserted = 0
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                for nombre in nombres:
                    cursor = conn.execute("SELECT 1 FROM categorias WHERE nombre = ?", (nombre,))
                    if cursor.fetchone() is not None:
                        continue
                    new_id = conn.execute(
                        "INSERT INTO categorias (nombre, descripcion, creado_en) VALUES (?, ?, ?)",
                        (nombre, "", now),
                    ).lastrowid
                    self._audit_log(
                        conn,
                        "CREATE",
                        "categorias",
                        new_id,
                        usuario,
                        f"Categoria (seed): {nombre}",
                    )
                    inserted += 1
                conn.commit()
                if inserted:
                    logger.info(f"Seeded {inserted} categories")
                return inserted
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to seed categories: {e}")

    def actualizar_proveedor(
        self,
        proveedor_id: int,
        nombre: str,
        contacto: str = "",
        telefono: str = "",
        email: str = "",
        direccion: str = "",
        usuario: str = "system",
    ) -> int:
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """UPDATE proveedores SET nombre = ?, contacto = ?, telefono = ?,
                       email = ?, direccion = ?, actualizado_en = ? WHERE id = ?""",
                    (nombre, contacto, telefono, email, direccion, now, proveedor_id),
                )
                conn.commit()
                self._audit_log(
                    conn,
                    "UPDATE",
                    "proveedores",
                    proveedor_id,
                    usuario,
                    f"Proveedor actualizado: {nombre}",
                )
                logger.debug(f"Supplier {proveedor_id} updated by {usuario}")
                return proveedor_id
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to update supplier: {e}")

    def eliminar_proveedor(self, proveedor_id: int, usuario: str = "system") -> bool:
        """Soft-delete a supplier (mark inactive)."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE proveedores SET activo = 0 WHERE id = ?",
                    (proveedor_id,),
                )
                conn.commit()
                self._audit_log(
                    conn,
                    "DELETE",
                    "proveedores",
                    proveedor_id,
                    usuario,
                    "Proveedor eliminado",
                )
                logger.debug(f"Supplier {proveedor_id} deleted by {usuario}")
                return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete supplier: {e}")

    def obtener_proveedor_por_id(self, proveedor_id: int) -> dict | None:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM proveedores WHERE id = ?", (proveedor_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch supplier: {e}")

    def cambiar_estado_orden(
        self,
        orden_id: int,
        nuevo_estado: str,
        usuario: str = "system",
    ) -> bool:
        """Change order status. Allowed: pendiente, recibida, cancelada."""
        if nuevo_estado not in ("pendiente", "recibida", "cancelada"):
            raise DatabaseException(f"Invalid order status: {nuevo_estado}")
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE ordenes_compra SET estado = ?, actualizado_en = ? WHERE id = ?",
                    (nuevo_estado, now, orden_id),
                )
                conn.commit()
                self._audit_log(
                    conn,
                    "UPDATE",
                    "ordenes_compra",
                    orden_id,
                    usuario,
                    f"Estado de orden cambiado a: {nuevo_estado}",
                )
                logger.debug(f"Order {orden_id} status -> {nuevo_estado}")
                return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to update order status: {e}")

    def eliminar_orden_compra(self, orden_id: int, usuario: str = "system") -> bool:
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM ordenes_compra WHERE id = ?", (orden_id,))
                conn.commit()
                self._audit_log(
                    conn,
                    "DELETE",
                    "ordenes_compra",
                    orden_id,
                    usuario,
                    "Orden eliminada",
                )
                return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to delete order: {e}")

    def obtener_orden_compra_por_id(self, orden_id: int) -> dict | None:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT oc.*, p.nombre as producto_nombre, p.codigo as producto_codigo,
                              pr.nombre as proveedor_nombre
                       FROM ordenes_compra oc
                       LEFT JOIN productos p ON oc.producto_id = p.id
                       LEFT JOIN proveedores pr ON oc.proveedor_id = pr.id
                       WHERE oc.id = ?""",
                    (orden_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch order: {e}")

    def obtener_distribucion_categorias(self) -> list[dict]:
        """Return [{nombre, total}] with product count per category."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT COALESCE(c.nombre, 'Sin categoría') as nombre,
                              COUNT(p.id) as total
                       FROM categorias c
                       LEFT JOIN productos p ON p.categoria = c.nombre AND p.estado = 'activo'
                       WHERE c.activo = 1 OR c.id IS NULL
                       GROUP BY c.nombre
                       ORDER BY total DESC"""
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch category distribution: {e}")

    def obtener_top_productos_por_stock(self, limit: int = 10) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT nombre, cantidad FROM productos
                       WHERE estado = 'activo'
                       ORDER BY cantidad DESC LIMIT ?""",
                    (limit,),
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch top products: {e}")

    def obtener_serie_inventario(self, dias: int = 30) -> list[dict]:
        """Return a daily series of total inventory value over the last N days."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """SELECT substr(hs.creado_en, 1, 10) as fecha,
                              SUM(hs.cantidad_nueva * p.precio) as valor_dia
                       FROM historial_stock hs
                       JOIN productos p ON hs.producto_id = p.id
                       WHERE p.estado = 'activo'
                       GROUP BY fecha ORDER BY fecha"""
                )
                per_day = {row["fecha"]: float(row["valor_dia"]) for row in cursor.fetchall()}

                series = []
                running = 0.0
                today = datetime.now().date()
                for i in range(dias - 1, -1, -1):
                    day = today - timedelta(days=i)
                    day_iso = day.isoformat()
                    running += per_day.get(day_iso, 0.0)
                    series.append({"fecha": day_iso, "valor": running})
                return series
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch inventory series: {e}")

    def bulk_eliminar_productos(self, ids: list[int], usuario: str = "system") -> int:
        """Bulk soft-delete products."""
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                placeholders = ",".join("?" for _ in ids)
                conn.execute(
                    f"UPDATE productos SET estado = 'inactivo', actualizado_en = ?, actualizado_por = ? WHERE id IN ({placeholders})",
                    [now, usuario, *ids],
                )
                for pid in ids:
                    self._audit_log(conn, "DELETE", "productos", pid, usuario, "Bulk delete")
                conn.commit()
                return len(ids)
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to bulk delete products: {e}")

    def bulk_actualizar_categoria(
        self, ids: list[int], categoria: str, usuario: str = "system"
    ) -> int:
        now = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                placeholders = ",".join("?" for _ in ids)
                conn.execute(
                    f"UPDATE productos SET categoria = ?, actualizado_en = ?, actualizado_por = ? WHERE id IN ({placeholders})",
                    [categoria, now, usuario, *ids],
                )
                conn.commit()
                return len(ids)
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to bulk update category: {e}")

    def bulk_exportar_productos(self, ids: list[int]) -> list[dict]:
        """Export selected products as list of dicts."""
        try:
            with self._get_connection() as conn:
                placeholders = ",".join("?" for _ in ids)
                cursor = conn.execute(
                    f"SELECT p.*, pr.nombre as proveedor_nombre FROM productos p LEFT JOIN proveedores pr ON p.proveedor_id = pr.id WHERE p.id IN ({placeholders})",
                    ids,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to bulk export products: {e}")

    def obtener_productos_stock_bajo(self) -> list[dict]:
        """Get low-stock products for email alerts."""
        return self._query_stock_bajo(include_proveedor=True)
