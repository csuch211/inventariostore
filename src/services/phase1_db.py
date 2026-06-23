"""
Phase 1 feature data-access layer.

Each method operates on the shared inventario.db via the existing
DatabaseManager connection helpers. Each method is small and self-contained;
it is the responsibility of `phase1_service.py` (and the controller) to wrap
these calls with validation, business rules and audit logging.

Why a separate module? The legacy `services/database.py` is large and touches
many subsystems. Adding ~1500 lines of new schema-backed methods would create
a merge nightmare. Keeping Phase 1 isolated makes the change easy to revert
and to review.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from utils.exceptions import DatabaseException, StockInsufficientException
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _conn(db):
    return db._get_connection()


def _audit(db, conn, accion, tabla, registro_id, usuario, detalles):
    db._audit_log(conn, accion, tabla, registro_id, usuario, detalles)


# ======================================================================
# F1: Devoluciones
# ======================================================================


def crear_devolucion(
    db,
    venta_id: int,
    items: list[dict],
    motivo: str = "",
    usuario: str = "system",
) -> dict:
    """Register a return against a sale, restoring stock and emitting a
    negative payment (nota de crédito) for the returned amount.

    Each item must be a dict with keys: producto_id, cantidad, precio_unitario.
    The whole flow runs inside a single DB transaction so SQLite doesn't lock.
    """
    now = datetime.now().isoformat()
    if not items:
        raise DatabaseException("La devolución no contiene items")
    try:
        with _conn(db) as conn:
            venta_row = conn.execute(
                "SELECT id, estado FROM ventas WHERE id = ?", (venta_id,)
            ).fetchone()
            if not venta_row:
                raise DatabaseException(f"Venta {venta_id} no encontrada")
            if venta_row["estado"] == "cancelada":
                raise DatabaseException("No se puede devolver sobre una venta cancelada")
            subtotal_total = 0.0
            inserted_ids = []
            for item in items:
                pid = int(item["producto_id"])
                cantidad = int(item["cantidad"])
                precio = float(item["precio_unitario"])
                if cantidad <= 0:
                    raise DatabaseException("Cantidad a devolver debe ser mayor a cero")
                subtotal = round(cantidad * precio, 2)
                subtotal_total += subtotal
                cursor = conn.execute(
                    """INSERT INTO devoluciones
                       (venta_id, producto_id, cantidad, precio_unitario, subtotal,
                        motivo, estado, creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, 'completada', ?, ?)""",
                    (venta_id, pid, cantidad, precio, subtotal, motivo, now, usuario),
                )
                inserted_ids.append(cursor.lastrowid)

            # Restore stock in the SAME transaction so we never see
            # "database is locked" from nested connections.
            for item in items:
                pid = int(item["producto_id"])
                cantidad = int(item["cantidad"])
                producto = conn.execute(
                    "SELECT cantidad FROM productos WHERE id = ?", (pid,)
                ).fetchone()
                if not producto:
                    raise DatabaseException(f"Producto {pid} no existe")
                cantidad_anterior = int(producto["cantidad"])
                cantidad_nueva = cantidad_anterior + cantidad
                conn.execute(
                    """UPDATE productos SET cantidad = ?, actualizado_en = ?,
                       actualizado_por = ? WHERE id = ?""",
                    (cantidad_nueva, now, usuario, pid),
                )
                conn.execute(
                    """INSERT INTO historial_stock
                       (producto_id, cantidad_anterior, cantidad_nueva,
                        tipo_movimiento, razon, creado_en, usuario)
                       VALUES (?, ?, ?, 'entrada', ?, ?, ?)""",
                    (
                        pid,
                        cantidad_anterior,
                        cantidad_nueva,
                        f"Devolución venta #{venta_id}",
                        now,
                        usuario,
                    ),
                )

            # Emit a negative payment (nota de crédito) for traceability
            conn.execute(
                """INSERT INTO pagos (venta_id, metodo, monto, referencia, creado_en)
                   VALUES (?, 'nota_credito', ?, ?, ?)""",
                (venta_id, -round(subtotal_total, 2), f"Devolución venta #{venta_id}", now),
            )
            conn.commit()
            _audit(
                db,
                conn,
                "CREATE",
                "devoluciones",
                venta_id,
                usuario,
                f"Devolución registrada por ${subtotal_total:.2f}",
            )
            logger.info(f"Return registered for sale {venta_id}: ${subtotal_total:.2f}")
            return {
                "devolucion_ids": inserted_ids,
                "subtotal_total": round(subtotal_total, 2),
                "items": items,
            }
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to create return: {e}")


def obtener_devoluciones(db, venta_id: int | None = None) -> list[dict]:
    try:
        with _conn(db) as conn:
            if venta_id is not None:
                cursor = conn.execute(
                    """SELECT d.*, p.nombre as producto_nombre, p.codigo as producto_codigo
                       FROM devoluciones d
                       LEFT JOIN productos p ON d.producto_id = p.id
                       WHERE d.venta_id = ? ORDER BY d.creado_en DESC""",
                    (venta_id,),
                )
            else:
                cursor = conn.execute(
                    """SELECT d.*, p.nombre as producto_nombre, p.codigo as producto_codigo,
                              v.cliente_id, v.creado_en as venta_fecha
                       FROM devoluciones d
                       LEFT JOIN productos p ON d.producto_id = p.id
                       LEFT JOIN ventas v ON d.venta_id = v.id
                       ORDER BY d.creado_en DESC"""
                )
            return [dict(r) for r in cursor.fetchall()]
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch returns: {e}")


# ======================================================================
# F2: Transferencias entre almacenes
# ======================================================================


def crear_transferencia(
    db,
    almacen_origen_id: int,
    almacen_destino_id: int,
    producto_id: int,
    cantidad: int,
    nota: str = "",
    usuario: str = "system",
) -> dict:
    """Move `cantidad` units from origin to destination warehouse atomically.

    Validates: distinct warehouses, sufficient stock at origin, both
    warehouses active. Stock changes are recorded in `inventario_almacen`
    and in `historial_stock` with tipo_movimiento = 'transferencia'.
    """
    if almacen_origen_id == almacen_destino_id:
        raise DatabaseException("Origen y destino deben ser distintos")
    if cantidad <= 0:
        raise DatabaseException("Cantidad debe ser mayor a cero")
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            # Validate warehouses
            for wid in (almacen_origen_id, almacen_destino_id):
                row = conn.execute(
                    "SELECT id, activo FROM almacenes WHERE id = ?", (wid,)
                ).fetchone()
                if not row or not row["activo"]:
                    raise DatabaseException(f"Almacén {wid} no disponible")

            # Read current stock at origin (sum across rows in case of duplicates)
            stock_row = conn.execute(
                """SELECT COALESCE(SUM(cantidad), 0) AS total
                   FROM inventario_almacen WHERE producto_id = ? AND almacen_id = ?""",
                (producto_id, almacen_origen_id),
            ).fetchone()
            stock_origen = int(stock_row["total"] or 0)
            if stock_origen < cantidad:
                raise StockInsufficientException(
                    f"Stock insuficiente en origen: tiene {stock_origen}, necesita {cantidad}"
                )

            # Debit origin (use UPDATE ... WHERE cantidad >= ? for safety)
            cur = conn.execute(
                """UPDATE inventario_almacen SET cantidad = cantidad - ?
                   WHERE producto_id = ? AND almacen_id = ? AND cantidad >= ?""",
                (cantidad, producto_id, almacen_origen_id, cantidad),
            )
            if cur.rowcount == 0:
                raise StockInsufficientException("Stock insuficiente en origen")
            # Ensure destination row exists (upsert)
            conn.execute(
                """INSERT INTO inventario_almacen (producto_id, almacen_id, cantidad)
                   VALUES (?, ?, ?)
                   ON CONFLICT(producto_id, almacen_id)
                   DO UPDATE SET cantidad = cantidad + excluded.cantidad""",
                (producto_id, almacen_destino_id, cantidad),
            )

            cursor = conn.execute(
                """INSERT INTO transferencias_almacen
                   (almacen_origen_id, almacen_destino_id, producto_id, cantidad,
                    estado, nota, creado_en, creado_por)
                   VALUES (?, ?, ?, ?, 'completada', ?, ?, ?)""",
                (
                    almacen_origen_id,
                    almacen_destino_id,
                    producto_id,
                    cantidad,
                    nota,
                    now,
                    usuario,
                ),
            )
            transferencia_id = cursor.lastrowid

            # Audit movement in historial_stock (no change to global stock)
            conn.execute(
                """INSERT INTO historial_stock
                   (producto_id, cantidad_anterior, cantidad_nueva, tipo_movimiento,
                    razon, creado_en, usuario)
                   VALUES (?, ?, ?, 'transferencia', ?, ?, ?)""",
                (
                    producto_id,
                    stock_origen,
                    stock_origen,
                    f"Transferencia #{transferencia_id} entre almacenes",
                    now,
                    usuario,
                ),
            )
            conn.commit()
            _audit(
                db,
                conn,
                "CREATE",
                "transferencias_almacen",
                transferencia_id,
                usuario,
                f"Transferencia {cantidad} u. del producto {producto_id} ({almacen_origen_id} -> {almacen_destino_id})",
            )
            logger.info(
                f"Transfer #{transferencia_id}: product {producto_id} "
                f"{cantidad} u. {almacen_origen_id}->{almacen_destino_id}"
            )
            return {"id": transferencia_id, "cantidad": cantidad}
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to transfer stock: {e}")


def obtener_transferencias(db, almacen_id: int | None = None) -> list[dict]:
    try:
        with _conn(db) as conn:
            if almacen_id is not None:
                cursor = conn.execute(
                    """SELECT t.*,
                              ao.nombre as almacen_origen, ad.nombre as almacen_destino,
                              p.nombre as producto_nombre, p.codigo as producto_codigo
                       FROM transferencias_almacen t
                       LEFT JOIN almacenes ao ON t.almacen_origen_id = ao.id
                       LEFT JOIN almacenes ad ON t.almacen_destino_id = ad.id
                       LEFT JOIN productos p ON t.producto_id = p.id
                       WHERE t.almacen_origen_id = ? OR t.almacen_destino_id = ?
                       ORDER BY t.creado_en DESC""",
                    (almacen_id, almacen_id),
                )
            else:
                cursor = conn.execute(
                    """SELECT t.*,
                              ao.nombre as almacen_origen, ad.nombre as almacen_destino,
                              p.nombre as producto_nombre, p.codigo as producto_codigo
                       FROM transferencias_almacen t
                       LEFT JOIN almacenes ao ON t.almacen_origen_id = ao.id
                       LEFT JOIN almacenes ad ON t.almacen_destino_id = ad.id
                       LEFT JOIN productos p ON t.producto_id = p.id
                       ORDER BY t.creado_en DESC"""
                )
            return [dict(r) for r in cursor.fetchall()]
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch transfers: {e}")


# ======================================================================
# F3: Conteo físico / reconciliación
# ======================================================================


def crear_sesion_conteo(
    db,
    nombre: str,
    almacen_id: int | None = None,
    notas: str = "",
    usuario: str = "system",
    producto_ids: list[int] | None = None,
) -> int:
    """Create a counting session. If producto_ids is given, the session is
    pre-populated with one item per product carrying `cantidad_sistema`
    snapshot. Otherwise items are added later as counts come in.
    """
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            cursor = conn.execute(
                """INSERT INTO sesiones_conteo
                   (nombre, almacen_id, estado, notas, creado_en, creado_por)
                   VALUES (?, ?, 'en_progreso', ?, ?, ?)""",
                (nombre, almacen_id, notas, now, usuario),
            )
            sesion_id = cursor.lastrowid
            if producto_ids:
                for pid in producto_ids:
                    sistema_row = conn.execute(
                        "SELECT cantidad FROM productos WHERE id = ?", (pid,)
                    ).fetchone()
                    sistema = int(sistema_row["cantidad"]) if sistema_row else 0
                    conn.execute(
                        """INSERT INTO conteo_items
                           (sesion_id, producto_id, cantidad_sistema)
                           VALUES (?, ?, ?)""",
                        (sesion_id, pid, sistema),
                    )
            conn.commit()
            _audit(
                db,
                conn,
                "CREATE",
                "sesiones_conteo",
                sesion_id,
                usuario,
                f"Sesión de conteo creada: {nombre}",
            )
            return sesion_id
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to create counting session: {e}")


def registrar_conteo_item(
    db,
    sesion_id: int,
    producto_id: int,
    cantidad_contada: float,
    notas: str = "",
    usuario: str = "system",
) -> int:
    """Insert (or update) the counted quantity for a product in a session and
    compute `diferencia = contado - sistema`.
    """
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            sesion = conn.execute(
                "SELECT id, estado FROM sesiones_conteo WHERE id = ?", (sesion_id,)
            ).fetchone()
            if not sesion:
                raise DatabaseException("Sesión de conteo no encontrada")
            if sesion["estado"] != "en_progreso":
                raise DatabaseException("La sesión está cerrada")
            sistema_row = conn.execute(
                "SELECT cantidad FROM productos WHERE id = ?", (producto_id,)
            ).fetchone()
            if not sistema_row:
                raise DatabaseException("Producto no encontrado")
            sistema = float(sistema_row["cantidad"])
            diferencia = round(float(cantidad_contada) - sistema, 4)
            existing = conn.execute(
                """SELECT id FROM conteo_items
                   WHERE sesion_id = ? AND producto_id = ?""",
                (sesion_id, producto_id),
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE conteo_items SET cantidad_contada = ?, diferencia = ?,
                       notas = ?, contado_en = ?, contado_por = ? WHERE id = ?""",
                    (cantidad_contada, diferencia, notas, now, usuario, existing["id"]),
                )
                item_id = existing["id"]
            else:
                cur = conn.execute(
                    """INSERT INTO conteo_items
                       (sesion_id, producto_id, cantidad_sistema, cantidad_contada,
                        diferencia, notas, contado_en, contado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        sesion_id,
                        producto_id,
                        sistema,
                        cantidad_contada,
                        diferencia,
                        notas,
                        now,
                        usuario,
                    ),
                )
                item_id = cur.lastrowid
            conn.commit()
            return item_id
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to record count: {e}")


def cerrar_sesion_conteo(
    db, sesion_id: int, aplicar_ajustes: bool, usuario: str = "system"
) -> dict:
    """Close a counting session. When `aplicar_ajustes=True`, every item with
    `diferencia != 0` becomes a stock adjustment of type 'ajuste'. Otherwise
    the session closes without modifying product stock.
    """
    now = datetime.now().isoformat()
    ajustes = 0
    try:
        with _conn(db) as conn:
            sesion = conn.execute(
                "SELECT * FROM sesiones_conteo WHERE id = ?", (sesion_id,)
            ).fetchone()
            if not sesion:
                raise DatabaseException("Sesión no encontrada")
            if sesion["estado"] != "en_progreso":
                raise DatabaseException("La sesión ya está cerrada")
            conn.execute(
                """UPDATE sesiones_conteo SET estado = 'cerrada', cerrado_en = ?
                   WHERE id = ?""",
                (now, sesion_id),
            )
            items = conn.execute(
                """SELECT * FROM conteo_items WHERE sesion_id = ?""", (sesion_id,)
            ).fetchall()
            conn.commit()
            _audit(
                db,
                conn,
                "UPDATE",
                "sesiones_conteo",
                sesion_id,
                usuario,
                f"Sesión de conteo cerrada (ajustes={aplicar_ajustes})",
            )
        if aplicar_ajustes:
            for item in items:
                if item["diferencia"] is None:
                    continue
                delta = round(float(item["diferencia"]), 4)
                if delta == 0:
                    continue
                # Use actualizar_stock with the final target quantity so the
                # usual history entry is created. Compute target from
                # counted value.
                db.actualizar_stock(
                    producto_id=int(item["producto_id"]),
                    cantidad_nueva=round(float(item["cantidad_contada"])),
                    tipo_movimiento="ajuste",
                    razon=f"Conteo físico #{sesion_id}",
                    usuario=usuario,
                )
                ajustes += 1
        return {"sesion_id": sesion_id, "items": len(items), "ajustes": ajustes}
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to close counting session: {e}")


def obtener_sesion_conteo(db, sesion_id: int) -> dict:
    try:
        with _conn(db) as conn:
            sesion = conn.execute(
                """SELECT s.*, a.nombre as almacen_nombre
                   FROM sesiones_conteo s
                   LEFT JOIN almacenes a ON s.almacen_id = a.id
                   WHERE s.id = ?""",
                (sesion_id,),
            ).fetchone()
            if not sesion:
                raise DatabaseException("Sesión no encontrada")
            items = conn.execute(
                """SELECT ci.*, p.nombre as producto_nombre, p.codigo as producto_codigo
                   FROM conteo_items ci
                   LEFT JOIN productos p ON ci.producto_id = p.id
                   WHERE ci.sesion_id = ? ORDER BY p.nombre""",
                (sesion_id,),
            ).fetchall()
            data = dict(sesion)
            data["items"] = [dict(i) for i in items]
            return data
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch session: {e}")


def obtener_sesiones_conteo(db) -> list[dict]:
    try:
        with _conn(db) as conn:
            cursor = conn.execute(
                """SELECT s.*, a.nombre as almacen_nombre,
                          (SELECT COUNT(*) FROM conteo_items WHERE sesion_id = s.id) AS items_count
                   FROM sesiones_conteo s
                   LEFT JOIN almacenes a ON s.almacen_id = a.id
                   ORDER BY s.creado_en DESC"""
            )
            return [dict(r) for r in cursor.fetchall()]
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch sessions: {e}")


# ======================================================================
# F4: Lotes / Series / Vencimientos
# ======================================================================


def crear_lote(
    db,
    producto_id: int,
    codigo_lote: str,
    cantidad_inicial: int,
    fecha_fabricacion: str | None = None,
    fecha_vencimiento: str | None = None,
    serie: str | None = None,
    ubicacion: str | None = None,
    proveedor_id: int | None = None,
    usuario: str = "system",
) -> int:
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            cur = conn.execute(
                """INSERT INTO lotes
                   (producto_id, codigo_lote, serie, cantidad_inicial, cantidad_actual,
                    fecha_fabricacion, fecha_vencimiento, ubicacion, proveedor_id,
                    creado_en, actualizado_en)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    producto_id,
                    codigo_lote,
                    serie,
                    cantidad_inicial,
                    cantidad_inicial,
                    fecha_fabricacion,
                    fecha_vencimiento,
                    ubicacion,
                    proveedor_id,
                    now,
                    now,
                ),
            )
            lote_id = cur.lastrowid
            conn.commit()
            _audit(
                db,
                conn,
                "CREATE",
                "lotes",
                lote_id,
                usuario,
                f"Lote {codigo_lote} creado para producto {producto_id}",
            )
            return lote_id
    except sqlite3.IntegrityError:
        raise DatabaseException(f"Ya existe el lote {codigo_lote} para el producto {producto_id}")
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to create lot: {e}")


def obtener_lotes(
    db,
    producto_id: int | None = None,
    proximos_vencer_dias: int | None = None,
) -> list[dict]:
    """List lots, optionally filtered by product. If `proximos_vencer_dias`
    is provided, only lots whose `fecha_vencimiento` falls within that
    window (or is already past) are returned, ordered by expiry.
    """
    try:
        with _conn(db) as conn:
            base = (
                "SELECT l.*, p.nombre as producto_nombre, p.codigo as producto_codigo, "
                "pr.nombre as proveedor_nombre "
                "FROM lotes l "
                "LEFT JOIN productos p ON l.producto_id = p.id "
                "LEFT JOIN proveedores pr ON l.proveedor_id = pr.id "
            )
            if producto_id is not None:
                rows = conn.execute(
                    base
                    + "WHERE l.producto_id = ? ORDER BY l.fecha_vencimiento ASC, l.creado_en DESC",
                    (producto_id,),
                ).fetchall()
            elif proximos_vencer_dias is not None:
                rows = conn.execute(
                    base + "WHERE l.fecha_vencimiento IS NOT NULL "
                    "ORDER BY date(l.fecha_vencimiento) ASC"
                ).fetchall()
            else:
                rows = conn.execute(base + "ORDER BY l.creado_en DESC").fetchall()
            result = [dict(r) for r in rows]
            if proximos_vencer_dias is not None:
                today = datetime.now().date()
                from datetime import timedelta

                cutoff = today + timedelta(days=proximos_vencer_dias)
                filtered = []
                for r in result:
                    fv = r.get("fecha_vencimiento")
                    if not fv:
                        continue
                    try:
                        d = datetime.fromisoformat(fv).date()
                    except ValueError:
                        continue
                    if d <= cutoff:
                        r["dias_para_vencer"] = (d - today).days
                        filtered.append(r)
                return filtered
            return result
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch lots: {e}")


def eliminar_lote(db, lote_id: int, usuario: str = "system") -> bool:
    try:
        with _conn(db) as conn:
            conn.execute("DELETE FROM lotes WHERE id = ?", (lote_id,))
            conn.commit()
            _audit(db, conn, "DELETE", "lotes", lote_id, usuario, "Lote eliminado")
            return True
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to delete lot: {e}")


# ======================================================================
# F5: Listas de precios multi-nivel
# ======================================================================


def crear_lista_precio(db, nombre: str, descripcion: str = "", usuario: str = "system") -> int:
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            cur = conn.execute(
                """INSERT INTO listas_precios
                   (nombre, descripcion, activo, creado_en, actualizado_en)
                   VALUES (?, ?, 1, ?, ?)""",
                (nombre, descripcion, now, now),
            )
            lista_id = cur.lastrowid
            conn.commit()
            _audit(
                db,
                conn,
                "CREATE",
                "listas_precios",
                lista_id,
                usuario,
                f"Lista de precios creada: {nombre}",
            )
            return lista_id
    except sqlite3.IntegrityError:
        raise DatabaseException(f"Lista '{nombre}' ya existe")
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to create price list: {e}")


def obtener_listas_precios(db, solo_activas: bool = True) -> list[dict]:
    try:
        with _conn(db) as conn:
            if solo_activas:
                cur = conn.execute("SELECT * FROM listas_precios WHERE activo = 1 ORDER BY nombre")
            else:
                cur = conn.execute("SELECT * FROM listas_precios ORDER BY nombre")
            return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch price lists: {e}")


def asignar_precio(
    db, producto_id: int, lista_id: int, precio: float, usuario: str = "system"
) -> int:
    if precio < 0:
        raise DatabaseException("El precio no puede ser negativo")
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            cur = conn.execute(
                """INSERT INTO precios_producto
                   (producto_id, lista_id, precio, creado_en, actualizado_en)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(producto_id, lista_id)
                   DO UPDATE SET precio = excluded.precio, actualizado_en = excluded.actualizado_en""",
                (producto_id, lista_id, precio, now, now),
            )
            pid = cur.lastrowid
            conn.commit()
            _audit(
                db,
                conn,
                "UPSERT",
                "precios_producto",
                pid,
                usuario,
                f"Precio {precio} asignado (prod={producto_id}, lista={lista_id})",
            )
            return pid
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to assign price: {e}")


def obtener_precio_producto(db, producto_id: int, lista_id: int | None = None) -> dict:
    """Return price info: base `precio`, optional cost & margin, and the
    per-list price if `lista_id` is given.
    """
    try:
        with _conn(db) as conn:
            row = conn.execute(
                "SELECT id, precio, precio_costo, margen FROM productos WHERE id = ?",
                (producto_id,),
            ).fetchone()
            if not row:
                raise DatabaseException("Producto no encontrado")
            out = dict(row)
            if lista_id is not None:
                pr = conn.execute(
                    """SELECT precio FROM precios_producto
                       WHERE producto_id = ? AND lista_id = ?""",
                    (producto_id, lista_id),
                ).fetchone()
                out["precio_lista"] = float(pr["precio"]) if pr else None
            return out
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch price: {e}")


def actualizar_precios_producto(
    db,
    producto_id: int,
    precio: float | None = None,
    precio_costo: float | None = None,
    margen: float | None = None,
    usuario: str = "system",
) -> dict:
    """Update the base price and/or cost/margin on the product."""
    now = datetime.now().isoformat()
    fields = []
    values = []
    if precio is not None:
        fields.append("precio = ?")
        values.append(float(precio))
    if precio_costo is not None:
        fields.append("precio_costo = ?")
        values.append(float(precio_costo))
    if margen is not None:
        fields.append("margen = ?")
        values.append(float(margen))
    if not fields:
        return db.obtener_producto_por_id(producto_id)
    try:
        with _conn(db) as conn:
            values.extend([now, usuario, producto_id])
            conn.execute(
                f"UPDATE productos SET {', '.join(fields)}, actualizado_en = ?, actualizado_por = ? WHERE id = ?",
                values,
            )
            conn.commit()
            _audit(
                db,
                conn,
                "UPDATE",
                "productos",
                producto_id,
                usuario,
                f"Precios actualizados: {', '.join(fields)}",
            )
            return db.obtener_producto_por_id(producto_id)
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to update prices: {e}")


# ======================================================================
# F6: Impuestos
# ======================================================================


def crear_impuesto(
    db,
    nombre: str,
    porcentaje: float,
    tipo: str = "iva",
    usuario: str = "system",
) -> int:
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            cur = conn.execute(
                """INSERT INTO impuestos
                   (nombre, porcentaje, tipo, activo, creado_en, actualizado_en)
                   VALUES (?, ?, ?, 1, ?, ?)""",
                (nombre, float(porcentaje), tipo, now, now),
            )
            tax_id = cur.lastrowid
            conn.commit()
            _audit(
                db,
                conn,
                "CREATE",
                "impuestos",
                tax_id,
                usuario,
                f"Impuesto {nombre} ({porcentaje}%) creado",
            )
            return tax_id
    except sqlite3.IntegrityError:
        raise DatabaseException(f"Impuesto '{nombre}' ya existe")
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to create tax: {e}")


def obtener_impuestos(db, solo_activos: bool = True) -> list[dict]:
    try:
        with _conn(db) as conn:
            if solo_activos:
                cur = conn.execute("SELECT * FROM impuestos WHERE activo = 1 ORDER BY nombre")
            else:
                cur = conn.execute("SELECT * FROM impuestos ORDER BY nombre")
            return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch taxes: {e}")


def calcular_precio_con_impuesto(precio_base: float, porcentaje: float) -> dict:
    """Return breakdown for tax-inclusive pricing. `precio_base` is treated
    as the pre-tax price. `porcentaje` is a value such as 19 for 19%.
    """
    if precio_base < 0:
        raise DatabaseException("Precio base no puede ser negativo")
    pct = float(porcentaje or 0)
    base = round(float(precio_base), 2)
    impuesto = round(base * pct / 100.0, 2)
    total = round(base + impuesto, 2)
    return {
        "base": base,
        "porcentaje": pct,
        "impuesto": impuesto,
        "total": total,
    }


def asignar_impuesto_producto(
    db, producto_id: int, impuesto_id: int | None, usuario: str = "system"
) -> bool:
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            conn.execute(
                "UPDATE productos SET impuesto_id = ?, actualizado_en = ?, actualizado_por = ? WHERE id = ?",
                (impuesto_id, now, usuario, producto_id),
            )
            conn.commit()
            _audit(
                db,
                conn,
                "UPDATE",
                "productos",
                producto_id,
                usuario,
                f"Impuesto {impuesto_id} asignado",
            )
            return True
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to assign tax: {e}")


# ======================================================================
# F7: Caja / Turnos POS
# ======================================================================


def abrir_turno(db, usuario: str, monto_inicial: float = 0, notas: str = "") -> int:
    """Open a new POS shift for `usuario`. Refuses if there's already an
    open shift for the same user.
    """
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            open_shift = conn.execute(
                """SELECT id FROM turnos_caja
                   WHERE usuario = ? AND estado = 'abierto'""",
                (usuario,),
            ).fetchone()
            if open_shift:
                raise DatabaseException(
                    f"Ya existe un turno abierto para {usuario} (#{open_shift['id']})"
                )
            cur = conn.execute(
                """INSERT INTO turnos_caja
                   (usuario, monto_inicial, estado, notas_apertura, abierto_en)
                   VALUES (?, ?, 'abierto', ?, ?)""",
                (usuario, float(monto_inicial), notas, now),
            )
            turno_id = cur.lastrowid
            conn.commit()
            _audit(
                db,
                conn,
                "CREATE",
                "turnos_caja",
                turno_id,
                usuario,
                f"Turno abierto con ${monto_inicial:.2f}",
            )
            return turno_id
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to open shift: {e}")


def registrar_movimiento_caja(
    db,
    turno_id: int,
    tipo: str,
    monto: float,
    concepto: str = "",
    referencia: str = "",
) -> int:
    """Tipo: 'ingreso' | 'egreso' | 'venta'."""
    if tipo not in ("ingreso", "egreso", "venta"):
        raise DatabaseException("Tipo de movimiento inválido")
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            turno = conn.execute(
                "SELECT estado FROM turnos_caja WHERE id = ?", (turno_id,)
            ).fetchone()
            if not turno:
                raise DatabaseException("Turno no encontrado")
            if turno["estado"] != "abierto":
                raise DatabaseException("El turno está cerrado")
            cur = conn.execute(
                """INSERT INTO movimientos_caja
                   (turno_id, tipo, monto, concepto, referencia, creado_en)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (turno_id, tipo, float(monto), concepto, referencia, now),
            )
            conn.commit()
            return cur.lastrowid
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to register cash movement: {e}")


def asociar_venta_a_turno(db, turno_id: int, venta_id: int) -> bool:
    try:
        with _conn(db) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO ventas_turno (turno_id, venta_id) VALUES (?, ?)",
                (turno_id, venta_id),
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to link sale to shift: {e}")


def cerrar_turno(
    db, turno_id: int, monto_final: float, notas: str = "", usuario: str = "system"
) -> dict:
    """Close a shift. `monto_final` is the cash counted at close.
    `monto_esperado` = initial + sum(ingresos/ventas) - sum(egresos).
    `diferencia` = monto_final - monto_esperado.
    """
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            turno = conn.execute("SELECT * FROM turnos_caja WHERE id = ?", (turno_id,)).fetchone()
            if not turno:
                raise DatabaseException("Turno no encontrado")
            if turno["estado"] != "abierto":
                raise DatabaseException("El turno ya está cerrado")
            totals = conn.execute(
                """SELECT
                       COALESCE(SUM(CASE WHEN tipo = 'ingreso' OR tipo = 'venta' THEN monto ELSE 0 END), 0) AS total_ingresos,
                       COALESCE(SUM(CASE WHEN tipo = 'egreso' THEN monto ELSE 0 END), 0) AS total_egresos,
                       COALESCE(SUM(CASE WHEN tipo = 'venta' THEN monto ELSE 0 END), 0) AS total_ventas
                   FROM movimientos_caja WHERE turno_id = ?""",
                (turno_id,),
            ).fetchone()
            ventas_total = float(totals["total_ventas"] or 0)
            ingresos_total = float(totals["total_ingresos"] or 0)
            egresos_total = float(totals["total_egresos"] or 0)
            monto_esperado = round(
                float(turno["monto_inicial"]) + ingresos_total - egresos_total, 2
            )
            diferencia = round(float(monto_final) - monto_esperado, 2)
            conn.execute(
                """UPDATE turnos_caja SET estado = 'cerrado', monto_final = ?,
                   monto_esperado = ?, diferencia = ?, notas_cierre = ?, cerrado_en = ?
                   WHERE id = ?""",
                (float(monto_final), monto_esperado, diferencia, notas, now, turno_id),
            )
            conn.commit()
            _audit(
                db,
                conn,
                "UPDATE",
                "turnos_caja",
                turno_id,
                usuario,
                f"Turno cerrado: esperado ${monto_esperado:.2f}, real ${monto_final:.2f}, dif ${diferencia:.2f}",
            )
            return {
                "id": turno_id,
                "monto_inicial": float(turno["monto_inicial"]),
                "total_ventas": ventas_total,
                "total_ingresos": ingresos_total,
                "total_egresos": egresos_total,
                "monto_esperado": monto_esperado,
                "monto_final": float(monto_final),
                "diferencia": diferencia,
            }
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to close shift: {e}")


def obtener_turno(db, turno_id: int) -> dict:
    try:
        with _conn(db) as conn:
            turno = conn.execute("SELECT * FROM turnos_caja WHERE id = ?", (turno_id,)).fetchone()
            if not turno:
                raise DatabaseException("Turno no encontrado")
            movimientos = conn.execute(
                "SELECT * FROM movimientos_caja WHERE turno_id = ? ORDER BY creado_en ASC",
                (turno_id,),
            ).fetchall()
            ventas = conn.execute(
                """SELECT v.id, v.total, v.creado_en, c.nombre as cliente_nombre
                   FROM ventas_turno vt
                   JOIN ventas v ON vt.venta_id = v.id
                   LEFT JOIN clientes c ON v.cliente_id = c.id
                   WHERE vt.turno_id = ?
                   ORDER BY v.creado_en ASC""",
                (turno_id,),
            ).fetchall()
            data = dict(turno)
            data["movimientos"] = [dict(m) for m in movimientos]
            data["ventas"] = [dict(v) for v in ventas]
            return data
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch shift: {e}")


def obtener_turnos(db, usuario: str | None = None) -> list[dict]:
    try:
        with _conn(db) as conn:
            if usuario:
                cur = conn.execute(
                    "SELECT * FROM turnos_caja WHERE usuario = ? ORDER BY abierto_en DESC",
                    (usuario,),
                )
            else:
                cur = conn.execute("SELECT * FROM turnos_caja ORDER BY abierto_en DESC")
            return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch shifts: {e}")


def obtener_turno_abierto(db, usuario: str) -> dict | None:
    try:
        with _conn(db) as conn:
            row = conn.execute(
                """SELECT * FROM turnos_caja
                   WHERE usuario = ? AND estado = 'abierto'
                   ORDER BY abierto_en DESC LIMIT 1""",
                (usuario,),
            ).fetchone()
            return dict(row) if row else None
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to fetch open shift: {e}")


# ======================================================================
# F8: Búsqueda avanzada con filtros
# ======================================================================


def buscar_productos_avanzado(
    db,
    texto: str | None = None,
    categoria: str | None = None,
    proveedor_id: int | None = None,
    estado: str = "activo",
    precio_min: float | None = None,
    precio_max: float | None = None,
    stock_min: int | None = None,
    stock_max: int | None = None,
    solo_bajo_stock: bool = False,
    orden: str = "nombre",
    limite: int = 200,
) -> list[dict]:
    """Combined filter search on the product catalog. All filters are AND'd.
    `orden` accepts: nombre, precio, cantidad, creado_en, actualizado_en.
    """
    where = ["p.estado = ?"]
    params: list = [estado]
    if texto:
        like = f"%{texto}%"
        where.append("(p.codigo LIKE ? OR p.nombre LIKE ? OR p.descripcion LIKE ? OR p.sku LIKE ?)")
        params.extend([like, like, like, like])
    if categoria:
        where.append("p.categoria = ?")
        params.append(categoria)
    if proveedor_id is not None:
        where.append("p.proveedor_id = ?")
        params.append(int(proveedor_id))
    if precio_min is not None:
        where.append("p.precio >= ?")
        params.append(float(precio_min))
    if precio_max is not None:
        where.append("p.precio <= ?")
        params.append(float(precio_max))
    if stock_min is not None:
        where.append("p.cantidad >= ?")
        params.append(int(stock_min))
    if stock_max is not None:
        where.append("p.cantidad <= ?")
        params.append(int(stock_max))
    if solo_bajo_stock:
        where.append("(p.cantidad = 0 OR (p.stock_min > 0 AND p.cantidad <= p.stock_min))")
    ordenes = {
        "nombre": "p.nombre ASC",
        "precio": "p.precio DESC",
        "cantidad": "p.cantidad ASC",
        "creado_en": "p.creado_en DESC",
        "actualizado_en": "p.actualizado_en DESC",
    }
    order_by = ordenes.get(orden, "p.nombre ASC")
    sql = (
        "SELECT p.*, pr.nombre as proveedor_nombre "
        "FROM productos p LEFT JOIN proveedores pr ON p.proveedor_id = pr.id "
        f"WHERE {' AND '.join(where)} ORDER BY {order_by} LIMIT ?"
    )
    params.append(int(limite))
    try:
        with _conn(db) as conn:
            cur = conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to search products: {e}")


# ======================================================================
# F9: Auto-reaprovisionamiento
# ======================================================================


def sugerir_reabastecimiento(db, supplier_id: int | None = None) -> list[dict]:
    """Build a purchase-order draft from low-stock products. Strategy:
    - Take all products where cantidad <= stock_min (or 0 if stock_min=0
      and they appear in `obtener_productos_con_stock_bajo`).
    - For each, compute `cantidad_sugerida = max(stock_min * 2 - cantidad, stock_min)`.
    - If `proveedor_id` is None, use the product's primary supplier.
      Products without a supplier are returned with `proveedor_id = None`.
    - If `supplier_id` is given, only that supplier's products are returned.
    """
    low = db.obtener_productos_con_stock_bajo()
    if supplier_id is not None:
        low = [p for p in low if p.get("proveedor_id") == int(supplier_id)]
    suggestions = []
    for p in low:
        stock_min = int(p.get("stock_min") or 0)
        cantidad = int(p.get("cantidad") or 0)
        if stock_min <= 0:
            cantidad_sugerida = max(10, cantidad)
        else:
            cantidad_sugerida = max(stock_min * 2 - cantidad, stock_min)
        suggestions.append(
            {
                "producto_id": p["id"],
                "codigo": p["codigo"],
                "nombre": p["nombre"],
                "cantidad_actual": cantidad,
                "stock_min": stock_min,
                "cantidad_sugerida": int(cantidad_sugerida),
                "proveedor_id": p.get("proveedor_id"),
                "proveedor_nombre": p.get("proveedor_nombre"),
            }
        )
    return suggestions


def crear_ordenes_desde_sugerencias(
    db,
    supplier_id: int,
    suggestions: list[dict],
    usuario: str = "system",
) -> list[int]:
    """Persist one purchase order per suggestion. Returns the new order ids."""
    created = []
    now = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            for s in suggestions:
                cantidad = int(s.get("cantidad_sugerida", 0))
                pid = int(s["producto_id"])
                if cantidad <= 0:
                    continue
                cur = conn.execute(
                    """INSERT INTO ordenes_compra
                       (proveedor_id, producto_id, cantidad, estado,
                        creado_en, actualizado_en, creado_por)
                       VALUES (?, ?, ?, 'pendiente', ?, ?, ?)""",
                    (supplier_id, pid, cantidad, now, now, usuario),
                )
                created.append(cur.lastrowid)
                _audit(
                    db,
                    conn,
                    "CREATE",
                    "ordenes_compra",
                    cur.lastrowid,
                    usuario,
                    f"Auto-orden generada desde sugerencia para producto {pid} x{cantidad}",
                )
            conn.commit()
            return created
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to create orders from suggestions: {e}")


# ======================================================================
# F10: Dashboard ejecutivo / KPIs
# ======================================================================


def obtener_kpis_dashboard(db) -> dict:
    """Aggregate KPIs for the dashboard view in a single round-trip.
    Returns a dict with the keys the UI expects.
    """
    today = datetime.now().date()
    month_start = today.replace(day=1).isoformat()
    today_iso = today.isoformat()
    now_iso = datetime.now().isoformat()
    try:
        with _conn(db) as conn:
            stats = conn.execute(
                """SELECT
                       COUNT(*) AS total_productos,
                       COALESCE(SUM(cantidad), 0) AS unidades_totales,
                       COALESCE(SUM(cantidad * precio), 0) AS valor_inventario_venta,
                       COALESCE(SUM(cantidad * COALESCE(precio_costo, 0)), 0) AS valor_inventario_costo
                   FROM productos WHERE estado = 'activo'"""
            ).fetchone()
            criticos = conn.execute(
                """SELECT COUNT(*) AS c FROM productos
                   WHERE estado = 'activo' AND cantidad <= COALESCE(stock_min, 0)"""
            ).fetchone()["c"]
            agotados = conn.execute(
                "SELECT COUNT(*) AS c FROM productos WHERE estado = 'activo' AND cantidad = 0"
            ).fetchone()["c"]
            ventas_hoy = conn.execute(
                """SELECT COUNT(*) AS c, COALESCE(SUM(total), 0) AS total
                   FROM ventas WHERE date(creado_en) = ?""",
                (today_iso,),
            ).fetchone()
            ventas_mes = conn.execute(
                """SELECT COUNT(*) AS c, COALESCE(SUM(total), 0) AS total
                   FROM ventas WHERE date(creado_en) >= ?""",
                (month_start,),
            ).fetchone()
            top_productos = conn.execute(
                """SELECT p.id, p.nombre, p.codigo, SUM(vd.cantidad) AS unidades,
                          SUM(vd.subtotal) AS ingresos
                   FROM ventas_detalle vd
                   JOIN productos p ON vd.producto_id = p.id
                   JOIN ventas v ON vd.venta_id = v.id
                   WHERE date(v.creado_en) >= ?
                   GROUP BY p.id ORDER BY unidades DESC LIMIT 5""",
                (month_start,),
            ).fetchall()
            valor_inventario_venta = float(stats["valor_inventario_venta"] or 0)
            valor_inventario_costo = float(stats["valor_inventario_costo"] or 0)
            margen_estimado = round(valor_inventario_venta - valor_inventario_costo, 2)
            return {
                "total_productos": int(stats["total_productos"] or 0),
                "unidades_totales": int(stats["unidades_totales"] or 0),
                "valor_inventario_venta": round(valor_inventario_venta, 2),
                "valor_inventario_costo": round(valor_inventario_costo, 2),
                "margen_estimado": margen_estimado,
                "productos_criticos": int(criticos or 0),
                "productos_agotados": int(agotados or 0),
                "ventas_hoy_count": int(ventas_hoy["c"] or 0),
                "ventas_hoy_total": round(float(ventas_hoy["total"] or 0), 2),
                "ventas_mes_count": int(ventas_mes["c"] or 0),
                "ventas_mes_total": round(float(ventas_mes["total"] or 0), 2),
                "top_productos_mes": [dict(r) for r in top_productos],
                "generado_en": now_iso,
            }
    except sqlite3.Error as e:
        raise DatabaseException(f"Failed to compute KPIs: {e}")
