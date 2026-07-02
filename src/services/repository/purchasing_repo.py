"""Purchasing repository for quotations, supplier evaluations, and receiving."""

import sqlite3
from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PurchasingRepository(BaseRepository):
    """Repository for purchasing operations."""

    def _next_quotation_number(self) -> str:
        """Generate the next sequential quotation number."""
        year = datetime.now().year
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM cotizaciones WHERE strftime('%Y', creado_en) = ?",
                (str(year),),
            ).fetchone()
            seq = (row["cnt"] or 0) + 1
        return f"COT-{year}-{seq:05d}"

    def _next_reception_number(self) -> str:
        """Generate the next sequential reception number."""
        year = datetime.now().year
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM recepciones WHERE strftime('%Y', creado_en) = ?",
                (str(year),),
            ).fetchone()
            seq = (row["cnt"] or 0) + 1
        return f"REC-{year}-{seq:05d}"

    # ============ Cotizaciones ============

    def crear_cotizacion(
        self,
        proveedor_id: int,
        items: list[dict],
        fecha_validez: str = "",
        notas: str = "",
        usuario: str = "system",
    ) -> dict:
        """Create a quotation from a supplier."""
        numero = self._next_quotation_number()
        now = datetime.now().isoformat()
        if not fecha_validez:
            from datetime import timedelta
            fecha_validez = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        subtotal = sum(item.get("cantidad", 1) * item.get("precio_unitario", 0) for item in items)

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO cotizaciones
                       (numero, proveedor_id, fecha_solicitud, fecha_validez, notas,
                        subtotal, creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (numero, proveedor_id, now, fecha_validez, notas, subtotal, now, usuario),
                )
                cotizacion_id = cursor.lastrowid

                for item in items:
                    cantidad = item.get("cantidad", 1)
                    precio = item.get("precio_unitario", 0)
                    conn.execute(
                        """INSERT INTO cotizacion_detalle
                           (cotizacion_id, producto_id, descripcion, cantidad,
                            precio_unitario, subtotal, notas)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (cotizacion_id, item.get("producto_id"), item.get("descripcion", ""),
                         cantidad, precio, cantidad * precio, item.get("notas", "")),
                    )

                self._audit_log(conn, "CREATE", "cotizaciones", cotizacion_id, usuario,
                               f"Cotización {numero} creada")
                conn.commit()
            return {"id": cotizacion_id, "numero": numero, "subtotal": subtotal}
        except sqlite3.IntegrityError:
            raise DatabaseException(f"Quotation number {numero} already exists")
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create quotation: {e}")

    def obtener_cotizacion(self, cotizacion_id: int) -> dict | None:
        """Get quotation with detail lines."""
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    """SELECT c.*, p.nombre as proveedor_nombre
                       FROM cotizaciones c
                       LEFT JOIN proveedores p ON c.proveedor_id = p.id
                       WHERE c.id = ?""",
                    (cotizacion_id,),
                ).fetchone()
                if not row:
                    return None

                cotizacion = dict(row)
                detalle = conn.execute(
                    "SELECT * FROM cotizacion_detalle WHERE cotizacion_id = ?",
                    (cotizacion_id,),
                ).fetchall()
                cotizacion["detalle"] = [dict(d) for d in detalle]
                return cotizacion
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch quotation: {e}")

    def obtener_cotizaciones(self, proveedor_id: int | None = None, estado: str | None = None) -> list[dict]:
        """List quotations."""
        try:
            with self._get_connection() as conn:
                where = []
                params = []
                if proveedor_id:
                    where.append("c.proveedor_id = ?")
                    params.append(proveedor_id)
                if estado:
                    where.append("c.estado = ?")
                    params.append(estado)

                _allowed_columns = {"c.proveedor_id", "c.estado"}
                for clause in where:
                    col = clause.split(None, 1)[0]
                    if col not in _allowed_columns:
                        raise ValueError(f"Columna no permitida en WHERE: {col}")
                where_clause = " AND ".join(where) if where else "1=1"
                cursor = conn.execute(
                    f"""SELECT c.*, p.nombre as proveedor_nombre
                        FROM cotizaciones c
                        LEFT JOIN proveedores p ON c.proveedor_id = p.id
                        WHERE {where_clause}
                        ORDER BY c.creado_en DESC""",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch quotations: {e}")

    def aprobar_cotizacion(self, cotizacion_id: int, usuario: str = "system") -> bool:
        """Approve a quotation."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE cotizaciones SET estado = 'aprobada' WHERE id = ?",
                    (cotizacion_id,),
                )
                self._audit_log(conn, "UPDATE", "cotizaciones", cotizacion_id, usuario, "Cotización aprobada")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to approve quotation: {e}")

    def rechazar_cotizacion(self, cotizacion_id: int, usuario: str = "system") -> bool:
        """Reject a quotation."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE cotizaciones SET estado = 'rechazada' WHERE id = ?",
                    (cotizacion_id,),
                )
                self._audit_log(conn, "UPDATE", "cotizaciones", cotizacion_id, usuario, "Cotización rechazada")
                conn.commit()
            return True
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to reject quotation: {e}")

    def convertir_a_orden(self, cotizacion_id: int, usuario: str = "system") -> dict:
        """Convert approved quotation to purchase order."""
        try:
            cotizacion = self.obtener_cotizacion(cotizacion_id)
            if not cotizacion:
                raise DatabaseException("Quotation not found")
            if cotizacion["estado"] != "aprobada":
                raise DatabaseException("Quotation must be approved first")

            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                # Create purchase order
                cursor = conn.execute(
                    """INSERT INTO ordenes_compra
                       (proveedor_id, producto_id, cantidad, creado_en, actualizado_en, creado_por)
                       SELECT ?, producto_id, cantidad, ?, ?, ?
                       FROM cotizacion_detalle WHERE cotizacion_id = ?""",
                    (cotizacion["proveedor_id"], now, now, usuario, cotizacion_id),
                )
                orden_id = cursor.lastrowid

                # Update quotation status
                conn.execute(
                    "UPDATE cotizaciones SET estado = 'convertida' WHERE id = ?",
                    (cotizacion_id,),
                )

                self._audit_log(conn, "CREATE", "ordenes_compra", orden_id, usuario,
                               f"Orden creada desde cotización {cotizacion['numero']}")
                conn.commit()

            return {"id": orden_id, "proveedor_id": cotizacion["proveedor_id"]}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to convert quotation: {e}")

    # ============ Evaluaciones de Proveedor ============

    def crear_evaluacion_proveedor(
        self,
        proveedor_id: int,
        evaluador: str,
        fecha: str,
        calidad: float = 0,
        puntualidad: float = 0,
        precio: float = 0,
        servicio: float = 0,
        comentarios: str = "",
        usuario: str = "system",
    ) -> dict:
        """Create a supplier evaluation."""
        puntuacion_global = (calidad + puntualidad + precio + servicio) / 4

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO evaluaciones_proveedor
                       (proveedor_id, evaluador, fecha, calidad, puntualidad,
                        precio, servicio, puntuacion_global, comentarios)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (proveedor_id, evaluador, fecha, calidad, puntualidad,
                     precio, servicio, puntuacion_global, comentarios),
                )
                evaluacion_id = cursor.lastrowid
                self._audit_log(conn, "CREATE", "evaluaciones_proveedor", evaluacion_id, usuario,
                               f"Evaluación creada para proveedor {proveedor_id}")
                conn.commit()
            return {"id": evaluacion_id, "puntuacion_global": puntuacion_global}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create supplier evaluation: {e}")

    def obtener_evaluaciones_proveedor(self, proveedor_id: int | None = None) -> list[dict]:
        """List supplier evaluations."""
        try:
            with self._get_connection() as conn:
                if proveedor_id:
                    cursor = conn.execute(
                        """SELECT ev.*, p.nombre as proveedor_nombre
                           FROM evaluaciones_proveedor ev
                           JOIN proveedores p ON ev.proveedor_id = p.id
                           WHERE ev.proveedor_id = ?
                           ORDER BY ev.fecha DESC""",
                        (proveedor_id,),
                    )
                else:
                    cursor = conn.execute(
                        """SELECT ev.*, p.nombre as proveedor_nombre
                           FROM evaluaciones_proveedor ev
                           JOIN proveedores p ON ev.proveedor_id = p.id
                           ORDER BY ev.fecha DESC"""
                    )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch evaluations: {e}")

    def promedio_evaluacion_proveedor(self, proveedor_id: int) -> dict:
        """Get average evaluation scores for a supplier."""
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    """SELECT
                       COALESCE(AVG(calidad), 0) as avg_calidad,
                       COALESCE(AVG(puntualidad), 0) as avg_puntualidad,
                       COALESCE(AVG(precio), 0) as avg_precio,
                       COALESCE(AVG(servicio), 0) as avg_servicio,
                       COALESCE(AVG(puntuacion_global), 0) as avg_global,
                       COUNT(*) as total_evaluaciones
                       FROM evaluaciones_proveedor
                       WHERE proveedor_id = ?""",
                    (proveedor_id,),
                ).fetchone()
                return dict(row) if row else {}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to calculate average scores: {e}")

    # ============ Recepciones ============

    def crear_recepcion(
        self,
        proveedor_id: int,
        items: list[dict],
        orden_compra_id: int | None = None,
        calidad: str = "aceptada",
        notas: str = "",
        usuario: str = "system",
    ) -> dict:
        """Create a goods received note."""
        numero = self._next_reception_number()
        now = datetime.now().isoformat()

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO recepciones
                       (orden_compra_id, proveedor_id, numero, fecha_recepcion,
                        calidad, notas, creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (orden_compra_id, proveedor_id, numero, now, calidad, notas, now, usuario),
                )
                recepcion_id = cursor.lastrowid

                for item in items:
                    conn.execute(
                        """INSERT INTO recepcion_detalle
                           (recepcion_id, producto_id, cantidad_solicitada,
                            cantidad_recibida, estado_calidad, notas)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (recepcion_id, item.get("producto_id"),
                         item.get("cantidad_solicitada", 0),
                         item.get("cantidad_recibida", 0),
                         item.get("estado_calidad", "aceptado"),
                         item.get("notas", "")),
                    )

                self._audit_log(conn, "CREATE", "recepciones", recepcion_id, usuario,
                               f"Recepción {numero} registrada")
                conn.commit()
            return {"id": recepcion_id, "numero": numero}
        except sqlite3.IntegrityError:
            raise DatabaseException(f"Reception number {numero} already exists")
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create reception: {e}")

    def obtener_recepciones(self, proveedor_id: int | None = None) -> list[dict]:
        """List receptions."""
        try:
            with self._get_connection() as conn:
                where = []
                params = []
                if proveedor_id:
                    where.append("r.proveedor_id = ?")
                    params.append(proveedor_id)

                _allowed_columns = {"r.proveedor_id"}
                for clause in where:
                    col = clause.split(None, 1)[0]
                    if col not in _allowed_columns:
                        raise ValueError(f"Columna no permitida en WHERE: {col}")
                where_clause = " AND ".join(where) if where else "1=1"
                cursor = conn.execute(
                    f"""SELECT r.*, p.nombre as proveedor_nombre
                        FROM recepciones r
                        LEFT JOIN proveedores p ON r.proveedor_id = p.id
                        WHERE {where_clause}
                        ORDER BY r.fecha_recepcion DESC""",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch receptions: {e}")
