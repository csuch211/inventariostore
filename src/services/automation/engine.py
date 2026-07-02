"""
Automation engine — rules engine + lightweight ML-lite models.

Modules:
- Auto reorder: generate purchase orders from low-stock alerts.
- Store sync: auto-mark store products as out-of-stock when inventory = 0.
- Order notifications: send in-app notifications on store order status changes.
- Demand forecast: simple moving average / exponential smoothing.
- ABC classification: Pareto-based product ranking.
- Dynamic pricing: suggest price adjustments based on velocity and ABC class.
- Customer segmentation: RFM-based client clustering.
- Scheduler: runs all enabled tasks on a configurable interval.
"""

import asyncio
from collections import defaultdict
from datetime import datetime
from statistics import mean, stdev

from services.repository.automation_repo import AutomationRepository
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AutomationEngine:
    """Central automation engine — all rules and models live here."""

    def __init__(self, db):
        self.db = db
        self.repo = AutomationRepository(db.db_path)
        self._task: asyncio.Task | None = None
        self._running = False

    # ── Scheduler ──────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("AutomationEngine started")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("AutomationEngine stopped")

    async def _run_loop(self):
        while self._running:
            try:
                config = self.repo.obtener_config()
                interval = int(config.get("auto_run_interval", "3600"))
                await self.run_all(config)
                self.repo.guardar_config("auto_last_run", datetime.now().isoformat())
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"AutomationEngine loop error: {e}")
                await asyncio.sleep(300)

    async def run_all(self, config: dict | None = None):
        """Execute all enabled automation tasks."""
        if config is None:
            config = self.repo.obtener_config()

        results = {}

        if config.get("auto_reorder_enabled", "false") == "true":
            try:
                count = self.auto_reorder(int(config.get("auto_reorder_min_stock", "5")))
                results["auto_reorder"] = count
                logger.info(f"Auto-reorder: {count} orders generated")
            except Exception as e:
                logger.error(f"Auto-reorder failed: {e}")

        if config.get("auto_store_sync", "true") == "true":
            try:
                count = self.sync_store_stock()
                results["store_sync"] = count
                logger.info(f"Store sync: {count} products updated")
            except Exception as e:
                logger.error(f"Store sync failed: {e}")

        if config.get("auto_demand_forecast", "false") == "true":
            try:
                count = self.generate_forecasts()
                results["demand_forecast"] = count
                logger.info(f"Demand forecast: {count} products forecasted")
            except Exception as e:
                logger.error(f"Demand forecast failed: {e}")

        if config.get("auto_abc_classify", "false") == "true":
            try:
                count = self.classify_abc()
                results["abc_classify"] = count
                logger.info(f"ABC classify: {count} products classified")
            except Exception as e:
                logger.error(f"ABC classify failed: {e}")

        if config.get("auto_dynamic_pricing", "false") == "true":
            try:
                count = self.suggest_prices()
                results["dynamic_pricing"] = count
                logger.info(f"Dynamic pricing: {count} suggestions generated")
            except Exception as e:
                logger.error(f"Dynamic pricing failed: {e}")

        if config.get("auto_customer_segments", "false") == "true":
            try:
                count = self.segment_customers()
                results["customer_segments"] = count
                logger.info(f"Customer segments: {count} clients segmented")
            except Exception as e:
                logger.error(f"Customer segments failed: {e}")

        return results

    # ── 1. Auto Reorder ────────────────────────────────────────────────

    def auto_reorder(self, min_stock: int = 5) -> int:
        """Generate purchase orders for products below minimum stock."""
        productos = self._get_low_stock_products(min_stock)
        count = 0
        for p in productos:
            proveedor_id = p.get("proveedor_id")
            if not proveedor_id:
                continue
            reorder_qty = max(p.get("stock_min", min_stock) * 2 - p.get("cantidad", 0), 1)
            try:
                with self.db._get_connection() as conn:
                    now = datetime.now().isoformat()
                    cur = conn.execute(
                        "INSERT INTO ordenes_compra (proveedor_id, producto_id, cantidad, estado, creado_en) "
                        "VALUES (?, ?, ?, 'pendiente', ?)",
                        (proveedor_id, p["id"], reorder_qty, now),
                    )
                    orden_id = cur.lastrowid
                    conn.commit()
                self.repo.registrar_reorden(
                    producto_id=p["id"], cantidad=reorder_qty,
                    motivo=f"Stock bajo ({p.get('cantidad', 0)} < {min_stock})",
                    orden_compra_id=orden_id,
                )
                count += 1
            except Exception as e:
                logger.error(f"Auto-reorder failed for product {p['id']}: {e}")
        return count

    def _get_low_stock_products(self, threshold: int = 5) -> list[dict]:
        try:
            with self.db._get_connection() as conn:
                rows = conn.execute("""
                    SELECT p.id, p.codigo, p.nombre, p.cantidad, p.stock_min, p.precio, p.proveedor_id
                    FROM productos p
                    WHERE p.activo = 1
                    AND (p.cantidad <= ? OR (p.stock_min > 0 AND p.cantidad <= p.stock_min))
                    ORDER BY p.cantidad ASC
                """, (threshold,)).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error querying low stock products: {e}")
            return []

    # ── 2. Store Stock Sync ────────────────────────────────────────────

    def sync_store_stock(self) -> int:
        """Auto-mark store products as invisible when stock = 0."""
        count = 0
        try:
            with self.db._get_connection() as conn:
                cur = conn.execute("""
                    UPDATE tienda_productos SET visible = 0
                    WHERE visible = 1 AND producto_id IN (
                        SELECT id FROM productos WHERE cantidad <= 0
                    )
                """)
                count = cur.rowcount
                conn.commit()

                cur2 = conn.execute("""
                    UPDATE tienda_productos SET visible = 1
                    WHERE visible = 0 AND producto_id IN (
                        SELECT id FROM productos WHERE cantidad > 0
                    )
                """)
                count += cur2.rowcount
                conn.commit()
        except Exception as e:
            logger.error(f"Error syncing store stock: {e}")
        return count

    # ── 3. Order Status Notifications ──────────────────────────────────

    def check_pending_order_notifications(self) -> int:
        """Create in-app notifications for recently changed store orders."""
        from services.repository.notification_repo import NotificationRepository

        notif_repo = NotificationRepository(self.db.db_path)
        count = 0
        try:
            with self.db._get_connection() as conn:
                rows = conn.execute("""
                    SELECT id, cliente_nombre, cliente_email, estado, total
                    FROM tienda_pedidos
                    WHERE actualizado_en > datetime('now', '-1 hour')
                    ORDER BY actualizado_en DESC
                """).fetchall()
            for r in rows:
                pedido = dict(r)
                estados_label = {
                    "pendiente": "pendiente",
                    "confirmado": "confirmado",
                    "enviado": "enviado",
                    "entregado": "entregado",
                    "cancelado": "cancelado",
                }
                label = estados_label.get(pedido["estado"], pedido["estado"])
                notif_repo.crear_notificacion(
                    titulo=f"Pedido #{pedido['id']} {label}",
                    mensaje=f"El pedido de {pedido['cliente_nombre']} por ${pedido['total']:.2f} está {label}",
                    tipo="pedido_tienda",
                    destinatario="admin",
                    referencia_tipo="tienda_pedido",
                    referencia_id=pedido["id"],
                    usuario="system",
                )
                count += 1
        except Exception as e:
            logger.error(f"Error creating order notifications: {e}")
        return count

    # ── 4. Demand Forecast (Moving Average + Exponential Smoothing) ────

    def generate_forecasts(self, periods: int = 4) -> int:
        """Generate demand forecasts using simple moving average and Holt-Winters style smoothing."""
        ventas = self._get_sales_history(months=6)
        if not ventas:
            return 0

        product_sales = defaultdict(list)
        for v in ventas:
            product_sales[v["producto_id"]].append(v)

        count = 0
        for pid, sales in product_sales.items():
            sales.sort(key=lambda x: x["mes"])
            values = [s["total_qty"] for s in sales]

            if len(values) < 2:
                continue

            # Simple moving average (last 3 periods)
            window = min(3, len(values))
            ma = mean(values[-window:])

            # Exponential smoothing
            alpha = 0.3
            smoothed = values[0]
            for v in values[1:]:
                smoothed = alpha * v + (1 - alpha) * smoothed

            # Use average of both methods
            forecast = (ma + smoothed) / 2

            # Simple confidence interval
            if len(values) >= 3:
                std = stdev(values[-window:]) if len(values[-window:]) > 1 else forecast * 0.2
            else:
                std = forecast * 0.3

            next_month = self._next_period(sales[-1]["mes"])

            self.repo.guardar_pronostico(
                producto_id=pid,
                periodo=next_month,
                demanda=round(forecast, 1),
                intervalo_inf=round(max(0, forecast - 1.96 * std), 1),
                intervalo_sup=round(forecast + 1.96 * std, 1),
                modelo="ensemble",
            )

            # Also record the forecast against the last known period
            self.repo.guardar_pronostico(
                producto_id=pid,
                periodo=sales[-1]["mes"],
                demanda=round(forecast, 1),
                modelo="ensemble",
            )
            count += 1

        return count

    def _get_sales_history(self, months: int = 6) -> list[dict]:
        try:
            with self.db._get_connection() as conn:
                rows = conn.execute("""
                    SELECT vd.producto_id,
                           strftime('%Y-%m', v.creado_en) as mes,
                           SUM(vd.cantidad) as total_qty,
                           SUM(vd.subtotal) as total_amount
                    FROM ventas_detalle vd
                    JOIN ventas v ON v.id = vd.venta_id
                    WHERE v.estado = 'completada'
                      AND v.creado_en >= date('now', '-{} months')
                    GROUP BY vd.producto_id, mes
                    ORDER BY mes ASC
                """, (months,)).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error querying sales history: {e}")
            return []

    @staticmethod
    def _next_period(current: str) -> str:
        parts = current.split("-")
        year, month = int(parts[0]), int(parts[1])
        month += 1
        if month > 12:
            month = 1
            year += 1
        return f"{year}-{month:02d}"

    # ── 5. ABC Classification ──────────────────────────────────────────

    def classify_abc(self) -> int:
        """Pareto-based ABC classification by sales value (last 12 months)."""
        try:
            with self.db._get_connection() as conn:
                rows = conn.execute("""
                    SELECT vd.producto_id,
                           SUM(vd.subtotal) as valor_anual
                    FROM ventas_detalle vd
                    JOIN ventas v ON v.id = vd.venta_id
                    WHERE v.estado = 'completada'
                      AND v.creado_en >= date('now', '-12 months')
                    GROUP BY vd.producto_id
                    ORDER BY valor_anual DESC
                """).fetchall()
        except Exception as e:
            logger.error(f"Error querying ABC data: {e}")
            return 0

        if not rows:
            return 0

        total_valor = sum(r["valor_anual"] for r in rows)
        if total_valor <= 0:
            return 0

        acumulado = 0
        count = 0
        for r in rows:
            acumulado += r["valor_anual"]
            pct = acumulado / total_valor * 100
            if pct <= 80:
                clasif = "A"
            elif pct <= 95:
                clasif = "B"
            else:
                clasif = "C"

            if self.repo.guardar_clasificacion_abc(
                producto_id=r["producto_id"],
                clasificacion=clasif,
                porcentaje_acumulado=round(pct, 1),
                valor_anual=round(r["valor_anual"], 2),
            ):
                count += 1

        return count

    # ── 6. Dynamic Pricing Suggestions ─────────────────────────────────

    def suggest_prices(self) -> int:
        """Generate pricing suggestions based on demand velocity, stock, and ABC class."""
        try:
            with self.db._get_connection() as conn:
                products = conn.execute("""
                    SELECT p.id, p.nombre, p.codigo, p.precio, p.cantidad as stock,
                           p.stock_min, COALESCE(a.clasificacion, 'C') as clasificacion
                    FROM productos p
                    LEFT JOIN abc_classification a ON a.producto_id = p.id
                    WHERE p.activo = 1 AND p.precio > 0
                    ORDER BY p.id
                """).fetchall()
        except Exception as e:
            logger.error(f"Error querying products for pricing: {e}")
            return 0

        count = 0
        for p in products:
            prod = dict(p)
            price = prod["precio"]
            stock = prod["stock"]
            clasif = prod["clasificacion"]

            # Sales velocity (from demand forecasts)
            forecasts = self.repo.obtener_pronosticos(producto_id=prod["id"], periodo=datetime.now().strftime("%Y-%m"))
            velocity = forecasts[0]["demanda_pronosticada"] if forecasts else 0

            reasons = []
            suggested = price

            if clasif == "A" and velocity > stock > 0:
                # High demand, low stock -> suggest price increase
                increase = min(0.15, (velocity - stock) / velocity * 0.1)
                suggested = price * (1 + increase)
                reasons.append(f"Alta demanda (ABC A, vel={velocity:.1f}/mes, stock={stock})")
            elif clasif == "C" and stock > velocity * 3 and velocity > 0:
                # Slow mover, excess stock -> suggest price decrease
                decrease = min(0.25, (stock - velocity * 2) / stock * 0.15)
                suggested = price * (1 - decrease)
                reasons.append(f"Baja rotación (ABC C, stock={stock}, vel={velocity:.1f}/mes)")
            elif stock == 0 and price > 0:
                # Out of stock premium products -> no suggestion needed
                continue
            else:
                continue

            # Only suggest if change is > 5%
            change_pct = abs(suggested - price) / price
            if change_pct < 0.05:
                continue

            suggested = round(suggested, 2)
            confidence = min(0.9, change_pct * 2)

            self.repo.guardar_sugerencia_precio(
                producto_id=prod["id"],
                precio_actual=price,
                precio_sugerido=suggested,
                motivo="; ".join(reasons),
                confianza=confidence,
            )
            count += 1

        return count

    # ── 7. Customer Segmentation (RFM) ─────────────────────────────────

    def segment_customers(self) -> int:
        """RFM-based customer segmentation."""
        try:
            with self.db._get_connection() as conn:
                rows = conn.execute("""
                    SELECT v.cliente_id,
                           c.nombre,
                           julianday('now') - julianday(MAX(v.creado_en)) as recencia_dias,
                           COUNT(DISTINCT v.id) as frecuencia,
                           SUM(v.total) as monetario
                    FROM ventas v
                    JOIN clientes c ON c.id = v.cliente_id
                    WHERE v.estado = 'completada'
                    GROUP BY v.cliente_id
                    ORDER BY monetario DESC
                """).fetchall()
        except Exception as e:
            logger.error(f"Error querying RFM data: {e}")
            return 0

        if not rows:
            return 0

        # Score each dimension 1-5
        recencias = sorted([r["recencia_dias"] for r in rows])
        frecuencias = sorted([r["frecuencia"] for r in rows])
        monetarios = sorted([r["monetario"] for r in rows])

        def percentile_score(value, sorted_list, reverse=False):
            if not sorted_list or len(sorted_list) < 2:
                return 3
            if reverse:
                rank = sum(1 for v in sorted_list if v >= value)
            else:
                rank = sum(1 for v in sorted_list if v <= value)
            pct = (rank - 1) / (len(sorted_list) - 1) * 100
            if pct >= 80:
                return 5
            elif pct >= 60:
                return 4
            elif pct >= 40:
                return 3
            elif pct >= 20:
                return 2
            return 1

        count = 0
        for r in rows:
            cliente = dict(r)
            r_score = percentile_score(cliente["recencia_dias"], recencias, reverse=True)
            f_score = percentile_score(cliente["frecuencia"], frecuencias)
            m_score = percentile_score(cliente["monetario"], monetarios)
            rfm_total = r_score + f_score + m_score

            if rfm_total >= 13:
                segmento = "VIP"
            elif rfm_total >= 10:
                segmento = "Frecuente"
            elif rfm_total >= 7:
                segmento = "Regular"
            elif rfm_total >= 4:
                segmento = "Ocasional"
            else:
                segmento = "Perdido"

            if self.repo.guardar_segmento_cliente(
                cliente_id=cliente["cliente_id"],
                segmento=segmento,
                rfm_score=rfm_total,
                recencia_dias=int(cliente["recencia_dias"]),
                frecuencia=cliente["frecuencia"],
                monetario=cliente["monetario"],
            ):
                count += 1

        return count
