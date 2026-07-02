"""Invoice repository for billing operations."""

import sqlite3
from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class InvoiceRepository(BaseRepository):
    """Repository for invoice CRUD operations."""

    def _next_invoice_number(self, tipo: str = "factura") -> str:
        """Generate the next sequential invoice number."""
        prefix = {"factura": "FACT", "boleta": "BOL", "nota_credito": "NC"}.get(tipo, "DOC")
        year = datetime.now().year
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM facturas WHERE tipo = ? AND strftime('%Y', creado_en) = ?",
                (tipo, str(year)),
            ).fetchone()
            seq = (row["cnt"] or 0) + 1
        return f"{prefix}-{year}-{seq:05d}"

    def crear_factura(
        self,
        cliente_id: int,
        items: list[dict],
        tipo: str = "factura",
        descuento_total: float = 0,
        notas: str = "",
        usuario: str = "system",
        venta_id: int | None = None,
    ) -> dict:
        """Create an invoice with line items and compute taxes."""
        numero = self._next_invoice_number(tipo)
        now = datetime.now().isoformat()

        subtotal = 0
        impuestos_total = 0
        detalle_rows = []

        for item in items:
            cantidad = item.get("cantidad", 1)
            precio = item.get("precio_unitario", 0)
            descuento_pct = item.get("descuento_pct", 0)
            impuesto_pct = item.get("impuesto_pct", 0)

            line_subtotal = cantidad * precio
            desc_monto = line_subtotal * (descuento_pct / 100)
            after_desc = line_subtotal - desc_monto
            imp_monto = after_desc * (impuesto_pct / 100)
            line_total = after_desc + imp_monto

            subtotal += line_subtotal
            impuestos_total += imp_monto

            detalle_rows.append((
                item.get("producto_id"),
                item.get("descripcion", ""),
                cantidad,
                precio,
                descuento_pct,
                desc_monto,
                impuesto_pct,
                imp_monto,
                line_total,
            ))

        total = subtotal - descuento_total + impuestos_total

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO facturas
                       (numero, venta_id, cliente_id, subtotal, impuestos_total,
                        descuentos_total, total, estado, tipo, fecha_emision,
                        notas, creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'emitida', ?, ?, ?, ?, ?)""",
                    (numero, venta_id, cliente_id, subtotal, impuestos_total,
                     descuento_total, total, tipo, now, notas, now, usuario),
                )
                factura_id = cursor.lastrowid

                for row in detalle_rows:
                    conn.execute(
                        """INSERT INTO factura_detalle
                           (factura_id, producto_id, descripcion, cantidad,
                            precio_unitario, descuento_pct, descuento_monto,
                            impuesto_pct, impuesto_monto, subtotal)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (factura_id, *row),
                    )

                # Create accounts receivable if credit sale
                if tipo == "factura":
                    conn.execute(
                        """INSERT INTO cuentas_cobrar
                           (cliente_id, factura_id, monto_original, monto_pendiente,
                            fecha_emision, fecha_vencimiento)
                           VALUES (?, ?, ?, ?, ?, date(?, '+30 days'))""",
                        (cliente_id, factura_id, total, total, now, now),
                    )

                self._audit_log(conn, "CREATE", "facturas", factura_id, usuario,
                               f"Factura {numero} por ${total:.2f}")
                conn.commit()

            return {"id": factura_id, "numero": numero, "total": total}
        except sqlite3.IntegrityError:
            raise DatabaseException(f"Invoice number {numero} already exists")
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create invoice: {e}")

    def obtener_factura(self, factura_id: int) -> dict | None:
        """Get invoice with line items."""
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    """SELECT f.*, c.nombre as cliente_nombre
                       FROM facturas f
                       LEFT JOIN clientes c ON f.cliente_id = c.id
                       WHERE f.id = ?""",
                    (factura_id,),
                ).fetchone()
                if not row:
                    return None

                factura = dict(row)
                detalle = conn.execute(
                    "SELECT * FROM factura_detalle WHERE factura_id = ?",
                    (factura_id,),
                ).fetchall()
                factura["detalle"] = [dict(d) for d in detalle]
                return factura
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch invoice: {e}")

    def obtener_facturas(self, estado: str | None = None, cliente_id: int | None = None) -> list[dict]:
        """List invoices with optional filters."""
        try:
            with self._get_connection() as conn:
                where = []
                params = []
                if estado:
                    where.append("f.estado = ?")
                    params.append(estado)
                if cliente_id:
                    where.append("f.cliente_id = ?")
                    params.append(cliente_id)

                _allowed_columns = {"f.estado", "f.cliente_id"}
                for clause in where:
                    col = clause.split(None, 1)[0]
                    if col not in _allowed_columns:
                        raise ValueError(f"Columna no permitida en WHERE: {col}")
                where_clause = " AND ".join(where) if where else "1=1"
                cursor = conn.execute(
                    f"""SELECT f.*, c.nombre as cliente_nombre
                        FROM facturas f
                        LEFT JOIN clientes c ON f.cliente_id = c.id
                        WHERE {where_clause}
                        ORDER BY f.creado_en DESC""",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch invoices: {e}")

    def actualizar_estado(self, factura_id: int, nuevo_estado: str, usuario: str = "system") -> bool:
        """Update invoice status."""
        valid_states = {"borrador", "emitida", "pagada", "cancelada"}
        if nuevo_estado not in valid_states:
            raise DatabaseException(f"Invalid invoice state: {nuevo_estado}")

        try:
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE facturas SET estado = ?, fecha_emision = COALESCE(fecha_emision, ?) WHERE id = ?",
                    (nuevo_estado, now, factura_id),
                )
                self._audit_log(conn, "UPDATE", "facturas", factura_id, usuario,
                               f"Estado cambiado a {nuevo_estado}")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to update invoice state: {e}")

    def eliminar_factura(self, factura_id: int, usuario: str = "system") -> bool:
        """Cancel an invoice (soft cancel)."""
        return self.actualizar_estado(factura_id, "cancelada", usuario)
