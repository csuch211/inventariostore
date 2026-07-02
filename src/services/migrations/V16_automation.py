"""V16: Automation, forecasting, ABC, pricing, and customer segmentation tables."""

from datetime import datetime


def run(db):
    try:
        with db._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS automation_config (
                    clave TEXT PRIMARY KEY,
                    valor TEXT NOT NULL,
                    descripcion TEXT,
                    actualizado_en TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS demand_forecasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id INTEGER NOT NULL,
                    periodo TEXT NOT NULL,
                    demanda_pronosticada REAL NOT NULL,
                    demanda_real REAL,
                    intervalo_inferior REAL,
                    intervalo_superior REAL,
                    modelo TEXT DEFAULT 'moving_average',
                    creado_en TEXT NOT NULL,
                    FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS abc_classification (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id INTEGER NOT NULL UNIQUE,
                    clasificacion TEXT NOT NULL CHECK(clasificacion IN ('A', 'B', 'C')),
                    porcentaje_acumulado REAL,
                    valor_anual REAL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS customer_segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id INTEGER NOT NULL UNIQUE,
                    segmento TEXT NOT NULL,
                    rfm_score INTEGER,
                    recencia_dias INTEGER,
                    frecuencia INTEGER,
                    monetario REAL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS pricing_suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id INTEGER NOT NULL,
                    precio_actual REAL NOT NULL,
                    precio_sugerido REAL NOT NULL,
                    motivo TEXT,
                    confianza REAL DEFAULT 0.5,
                    estado TEXT DEFAULT 'pendiente',
                    creado_en TEXT NOT NULL,
                    aplicado_en TEXT,
                    FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS auto_reorder_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id INTEGER NOT NULL,
                    orden_compra_id INTEGER,
                    cantidad INTEGER NOT NULL,
                    motivo TEXT,
                    estado TEXT DEFAULT 'pendiente',
                    creado_en TEXT NOT NULL,
                    procesado_en TEXT,
                    FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
            """)

            now = datetime.now().isoformat()
            defaults = [
                ("auto_reorder_enabled", "false", "Generar órdenes de compra automáticas desde alertas de stock"),
                ("auto_reorder_min_stock", "5", "Stock mínimo para activar reorden automático"),
                ("auto_store_sync", "true", "Sincronizar stock de tienda automáticamente (marcar sin stock)"),
                ("auto_notify_order_status", "true", "Notificar cambios de estado en pedidos de tienda"),
                ("auto_demand_forecast", "false", "Ejecutar pronóstico de demanda periódicamente"),
                ("auto_abc_classify", "false", "Ejecutar clasificación ABC periódicamente"),
                ("auto_dynamic_pricing", "false", "Generar sugerencias de precios dinámicos"),
                ("auto_customer_segments", "false", "Ejecutar segmentación de clientes periódicamente"),
                ("auto_run_interval", "3600", "Intervalo de ejecución automática en segundos"),
                ("auto_last_run", "", "Última ejecución del motor de automatización"),
            ]
            for clave, valor, desc in defaults:
                conn.execute(
                    "INSERT OR IGNORE INTO automation_config (clave, valor, descripcion, actualizado_en) VALUES (?, ?, ?, ?)",
                    (clave, valor, desc, now),
                )

            conn.execute("CREATE INDEX IF NOT EXISTS idx_demand_forecast_producto ON demand_forecasts(producto_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_demand_forecast_periodo ON demand_forecasts(periodo)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_abc_classificacion ON abc_classification(clasificacion)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_customer_segments_segmento ON customer_segments(segmento)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pricing_suggestions_estado ON pricing_suggestions(estado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_auto_reorder_log_estado ON auto_reorder_log(estado)")

            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V16 failed: {e}")
