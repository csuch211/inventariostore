"""Repository for automation features: forecasting, ABC, pricing, segmentation."""

from datetime import datetime

from services.repository.base import BaseRepository
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AutomationRepository(BaseRepository):
    """CRUD for automation config, forecasts, ABC, customer segments, pricing suggestions."""

    # ── Automation config ──────────────────────────────────────────────

    def obtener_config(self) -> dict[str, str]:
        try:
            with self._get_connection() as conn:
                rows = conn.execute("SELECT clave, valor FROM automation_config").fetchall()
                return {r["clave"]: r["valor"] for r in rows}
        except Exception as e:
            raise DatabaseException(f"Error loading automation config: {e}")

    def guardar_config(self, clave: str, valor: str) -> bool:
        try:
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO automation_config (clave, valor, descripcion, actualizado_en) "
                    "VALUES (?, ?, '', ?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor, actualizado_en=excluded.actualizado_en",
                    (clave, valor, now),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving automation config {clave}: {e}")
            return False

    # ── Demand Forecast ────────────────────────────────────────────────

    def guardar_pronostico(self, producto_id: int, periodo: str, demanda: float,
                           intervalo_inf: float = 0, intervalo_sup: float = 0,
                           modelo: str = "moving_average") -> int:
        try:
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                cur = conn.execute(
                    "INSERT INTO demand_forecasts (producto_id, periodo, demanda_pronosticada, "
                    "intervalo_inferior, intervalo_superior, modelo, creado_en) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (producto_id, periodo, demanda, intervalo_inf, intervalo_sup, modelo, now),
                )
                conn.commit()
                return cur.lastrowid or 0
        except Exception as e:
            raise DatabaseException(f"Error saving forecast for product {producto_id}: {e}")

    def obtener_pronosticos(self, producto_id: int | None = None,
                            periodo: str | None = None) -> list[dict]:
        try:
            with self._get_connection() as conn:
                sql = "SELECT * FROM demand_forecasts WHERE 1=1"
                params = []
                if producto_id is not None:
                    sql += " AND producto_id = ?"
                    params.append(producto_id)
                if periodo:
                    sql += " AND periodo = ?"
                    params.append(periodo)
                sql += " ORDER BY periodo DESC, id DESC LIMIT 500"
                return [dict(r) for r in conn.execute(sql, params).fetchall()]
        except Exception as e:
            raise DatabaseException(f"Error loading forecasts: {e}")

    def limpiar_pronosticos(self, producto_id: int | None = None) -> int:
        try:
            with self._get_connection() as conn:
                if producto_id:
                    cur = conn.execute("DELETE FROM demand_forecasts WHERE producto_id = ?", (producto_id,))
                else:
                    cur = conn.execute("DELETE FROM demand_forecasts")
                conn.commit()
                return cur.rowcount
        except Exception as e:
            raise DatabaseException(f"Error clearing forecasts: {e}")

    # ── ABC Classification ─────────────────────────────────────────────

    def guardar_clasificacion_abc(self, producto_id: int, clasificacion: str,
                                   porcentaje_acumulado: float, valor_anual: float) -> bool:
        try:
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO abc_classification (producto_id, clasificacion, porcentaje_acumulado, "
                    "valor_anual, updated_at) VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(producto_id) DO UPDATE SET "
                    "clasificacion=excluded.clasificacion, porcentaje_acumulado=excluded.porcentaje_acumulado, "
                    "valor_anual=excluded.valor_anual, updated_at=excluded.updated_at",
                    (producto_id, clasificacion, porcentaje_acumulado, valor_anual, now),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving ABC for product {producto_id}: {e}")
            return False

    def obtener_clasificaciones_abc(self, clasificacion: str | None = None) -> list[dict]:
        try:
            with self._get_connection() as conn:
                sql = """SELECT a.*, p.codigo, p.nombre, p.cantidad as stock, p.precio
                         FROM abc_classification a
                         JOIN productos p ON p.id = a.producto_id
                         WHERE 1=1"""
                params = []
                if clasificacion:
                    sql += " AND a.clasificacion = ?"
                    params.append(clasificacion)
                sql += " ORDER BY a.valor_anual DESC"
                return [dict(r) for r in conn.execute(sql, params).fetchall()]
        except Exception as e:
            raise DatabaseException(f"Error loading ABC classifications: {e}")

    def limpiar_abc(self) -> int:
        try:
            with self._get_connection() as conn:
                cur = conn.execute("DELETE FROM abc_classification")
                conn.commit()
                return cur.rowcount
        except Exception as e:
            raise DatabaseException(f"Error clearing ABC: {e}")

    # ── Customer Segments ──────────────────────────────────────────────

    def guardar_segmento_cliente(self, cliente_id: int, segmento: str, rfm_score: int,
                                  recencia_dias: int, frecuencia: int, monetario: float) -> bool:
        try:
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO customer_segments (cliente_id, segmento, rfm_score, recencia_dias, "
                    "frecuencia, monetario, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(cliente_id) DO UPDATE SET "
                    "segmento=excluded.segmento, rfm_score=excluded.rfm_score, "
                    "recencia_dias=excluded.recencia_dias, frecuencia=excluded.frecuencia, "
                    "monetario=excluded.monetario, updated_at=excluded.updated_at",
                    (cliente_id, segmento, rfm_score, recencia_dias, frecuencia, monetario, now),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving segment for client {cliente_id}: {e}")
            return False

    def obtener_segmentos_clientes(self, segmento: str | None = None) -> list[dict]:
        try:
            with self._get_connection() as conn:
                sql = """SELECT s.*, c.nombre as cliente_nombre, c.telefono, c.email
                         FROM customer_segments s
                         JOIN clientes c ON c.id = s.cliente_id
                         WHERE 1=1"""
                params = []
                if segmento:
                    sql += " AND s.segmento = ?"
                    params.append(segmento)
                sql += " ORDER BY s.monetario DESC"
                return [dict(r) for r in conn.execute(sql, params).fetchall()]
        except Exception as e:
            raise DatabaseException(f"Error loading customer segments: {e}")

    # ── Pricing Suggestions ────────────────────────────────────────────

    def guardar_sugerencia_precio(self, producto_id: int, precio_actual: float,
                                   precio_sugerido: float, motivo: str = "",
                                   confianza: float = 0.5) -> int:
        try:
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                cur = conn.execute(
                    "INSERT INTO pricing_suggestions (producto_id, precio_actual, precio_sugerido, "
                    "motivo, confianza, estado, creado_en) VALUES (?, ?, ?, ?, ?, 'pendiente', ?)",
                    (producto_id, precio_actual, precio_sugerido, motivo, confianza, now),
                )
                conn.commit()
                return cur.lastrowid or 0
        except Exception as e:
            raise DatabaseException(f"Error saving pricing suggestion: {e}")

    def obtener_sugerencias_precio(self, estado: str | None = None) -> list[dict]:
        try:
            with self._get_connection() as conn:
                sql = """SELECT s.*, p.codigo, p.nombre, p.cantidad as stock
                         FROM pricing_suggestions s
                         JOIN productos p ON p.id = s.producto_id
                         WHERE 1=1"""
                params = []
                if estado:
                    sql += " AND s.estado = ?"
                    params.append(estado)
                sql += " ORDER BY s.confianza DESC, s.creado_en DESC"
                return [dict(r) for r in conn.execute(sql, params).fetchall()]
        except Exception as e:
            raise DatabaseException(f"Error loading pricing suggestions: {e}")

    def aplicar_sugerencia_precio(self, sugerencia_id: int) -> bool:
        try:
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                row = conn.execute("SELECT * FROM pricing_suggestions WHERE id = ?", (sugerencia_id,)).fetchone()
                if not row:
                    return False
                conn.execute("UPDATE productos SET precio = ? WHERE id = ?",
                             (row["precio_sugerido"], row["producto_id"]))
                conn.execute("UPDATE pricing_suggestions SET estado = 'aplicado', aplicado_en = ? WHERE id = ?",
                             (now, sugerencia_id))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error applying pricing suggestion {sugerencia_id}: {e}")
            return False

    def rechazar_sugerencia_precio(self, sugerencia_id: int) -> bool:
        try:
            with self._get_connection() as conn:
                conn.execute("UPDATE pricing_suggestions SET estado = 'rechazado' WHERE id = ?",
                             (sugerencia_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error rejecting pricing suggestion {sugerencia_id}: {e}")
            return False

    # ── Auto Reorder Log ───────────────────────────────────────────────

    def registrar_reorden(self, producto_id: int, cantidad: int, motivo: str,
                           orden_compra_id: int | None = None) -> int:
        try:
            now = datetime.now().isoformat()
            with self._get_connection() as conn:
                cur = conn.execute(
                    "INSERT INTO auto_reorder_log (producto_id, orden_compra_id, cantidad, motivo, estado, creado_en) "
                    "VALUES (?, ?, ?, ?, 'pendiente', ?)",
                    (producto_id, orden_compra_id, cantidad, motivo, now),
                )
                conn.commit()
                return cur.lastrowid or 0
        except Exception as e:
            raise DatabaseException(f"Error logging auto-reorder: {e}")

    def obtener_reordenes(self, estado: str | None = None) -> list[dict]:
        try:
            with self._get_connection() as conn:
                sql = """SELECT r.*, p.codigo, p.nombre
                         FROM auto_reorder_log r
                         JOIN productos p ON p.id = r.producto_id
                         WHERE 1=1"""
                params = []
                if estado:
                    sql += " AND r.estado = ?"
                    params.append(estado)
                sql += " ORDER BY r.creado_en DESC LIMIT 200"
                return [dict(r) for r in conn.execute(sql, params).fetchall()]
        except Exception as e:
            raise DatabaseException(f"Error loading reorder log: {e}")
