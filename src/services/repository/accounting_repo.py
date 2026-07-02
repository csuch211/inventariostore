"""Accounting repository for double-entry bookkeeping."""

import sqlite3
from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AccountingRepository(BaseRepository):
    """Repository for accounting operations."""

    def _next_asiento_number(self, fecha: str | None = None) -> str:
        """Generate the next sequential journal entry number."""
        year = str(datetime.now().year)
        if fecha and len(fecha) >= 4:
            year = fecha[:4]
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM asientos_contables WHERE strftime('%Y', fecha) = ?",
                (year,),
            ).fetchone()
            seq = (row["cnt"] or 0) + 1
        return f"ASI-{year}-{seq:05d}"

    def crear_asiento(
        self,
        fecha: str,
        descripcion: str,
        tipo: str,
        movimientos: list[dict],
        usuario: str = "system",
        referencia_id: int | None = None,
        referencia_tipo: str | None = None,
    ) -> dict:
        """Create a journal entry with debit/credit movements.

        Args:
            fecha: Entry date (YYYY-MM-DD)
            descripcion: Entry description
            tipo: Entry type (venta, compra, pago, ajuste, devolucion)
            movimientos: List of {cuenta_codigo, cuenta_nombre, debito, credito}
            usuario: Created by user
            referencia_id: Optional reference transaction ID
            referencia_tipo: Optional reference type
        """
        numero = self._next_asiento_number(fecha)
        now = datetime.now().isoformat()

        # Validate: total debits must equal total credits
        total_debito = sum(m.get("debito", 0) for m in movimientos)
        total_credito = sum(m.get("credito", 0) for m in movimientos)
        if abs(total_debito - total_credito) > 0.01:
            raise DatabaseException(
                f"Debits ({total_debito:.2f}) must equal credits ({total_credito:.2f})"
            )

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO asientos_contables
                       (numero, fecha, descripcion, tipo, referencia_id, referencia_tipo,
                        estado, creado_en, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, 'confirmado', ?, ?)""",
                    (numero, fecha, descripcion, tipo, referencia_id, referencia_tipo, now, usuario),
                )
                asiento_id = cursor.lastrowid

                for mov in movimientos:
                    conn.execute(
                        """INSERT INTO movimientos_contables
                           (asiento_id, cuenta_codigo, cuenta_nombre, debito, credito, descripcion)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (asiento_id, mov["cuenta_codigo"], mov["cuenta_nombre"],
                         mov.get("debito", 0), mov.get("credito", 0), mov.get("descripcion", "")),
                    )

                self._audit_log(conn, "CREATE", "asientos_contables", asiento_id, usuario,
                               f"Asiento {numero}: {descripcion}")
                conn.commit()

            return {"id": asiento_id, "numero": numero}
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to create journal entry: {e}")

    def obtener_asiento(self, asiento_id: int) -> dict | None:
        """Get journal entry with movements."""
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM asientos_contables WHERE id = ?",
                    (asiento_id,),
                ).fetchone()
                if not row:
                    return None

                asiento = dict(row)
                movimientos = conn.execute(
                    "SELECT * FROM movimientos_contables WHERE asiento_id = ?",
                    (asiento_id,),
                ).fetchall()
                asiento["movimientos"] = [dict(m) for m in movimientos]
                return asiento
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch journal entry: {e}")

    def obtener_asientos(self, fecha_inicio: str | None = None, fecha_fin: str | None = None) -> list[dict]:
        """List journal entries with optional date range."""
        try:
            with self._get_connection() as conn:
                where = []
                params = []
                if fecha_inicio:
                    where.append("fecha >= ?")
                    params.append(fecha_inicio)
                if fecha_fin:
                    where.append("fecha <= ?")
                    params.append(fecha_fin)

                _allowed_columns = {"fecha"}
                for clause in where:
                    col = clause.split(None, 1)[0]
                    if col not in _allowed_columns:
                        raise ValueError(f"Columna no permitida en WHERE: {col}")
                where_clause = " AND ".join(where) if where else "1=1"
                cursor = conn.execute(
                    f"SELECT * FROM asientos_contables WHERE {where_clause} ORDER BY fecha DESC, id DESC",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch journal entries: {e}")

    def obtener_plan_cuentas(self, tipo: str | None = None) -> list[dict]:
        """Get chart of accounts."""
        try:
            with self._get_connection() as conn:
                if tipo:
                    cursor = conn.execute(
                        "SELECT * FROM plan_cuentas WHERE tipo = ? AND activa = 1 ORDER BY codigo",
                        (tipo,),
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM plan_cuentas WHERE activa = 1 ORDER BY codigo"
                    )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch chart of accounts: {e}")

    def obtener_balance_comprobacion(self, fecha_inicio: str | None = None, fecha_fin: str | None = None) -> list[dict]:
        """Get trial balance: sum of debits and credits per account."""
        try:
            with self._get_connection() as conn:
                where = ["a.estado = 'confirmado'"]
                params = []
                if fecha_inicio:
                    where.append("a.fecha >= ?")
                    params.append(fecha_inicio)
                if fecha_fin:
                    where.append("a.fecha <= ?")
                    params.append(fecha_fin)

                _allowed_columns = {"a.estado", "a.fecha"}
                for clause in where:
                    col = clause.split(None, 1)[0]
                    if col not in _allowed_columns:
                        raise ValueError(f"Columna no permitida en WHERE: {col}")
                where_clause = " AND ".join(where)
                cursor = conn.execute(
                    f"""SELECT
                            m.cuenta_codigo,
                            m.cuenta_nombre,
                            COALESCE(SUM(m.debito), 0) as total_debito,
                            COALESCE(SUM(m.credito), 0) as total_credito
                        FROM movimientos_contables m
                        JOIN asientos_contables a ON m.asiento_id = a.id
                        WHERE {where_clause}
                        GROUP BY m.cuenta_codigo, m.cuenta_nombre
                        ORDER BY m.cuenta_codigo""",
                    params,
                )
                return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to fetch trial balance: {e}")
