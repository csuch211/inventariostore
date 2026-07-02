"""V14: Create sales module tables for enhanced POS.

Tables: descuentos, promociones, ventas_detalle_descuento
"""


def run(db):
    """Create sales module tables if they don't exist."""
    try:
        with db._get_connection() as conn:
            # Discounts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS descuentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL,
                    tipo TEXT NOT NULL DEFAULT 'porcentaje',
                    valor REAL NOT NULL DEFAULT 0,
                    fecha_inicio TEXT,
                    fecha_fin TEXT,
                    uso_maximo INTEGER DEFAULT 0,
                    uso_actual INTEGER DEFAULT 0,
                    activo INTEGER DEFAULT 1,
                    creado_en TEXT NOT NULL,
                    creado_por TEXT
                )
            """)

            # Promotions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS promociones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    tipo TEXT NOT NULL DEFAULT 'descuento',
                    descripcion TEXT,
                    valor REAL DEFAULT 0,
                    fecha_inicio TEXT NOT NULL,
                    fecha_fin TEXT NOT NULL,
                    activo INTEGER DEFAULT 1,
                    creado_en TEXT NOT NULL,
                    creado_por TEXT
                )
            """)

            # Sale line item discounts
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ventas_detalle_descuento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    venta_detalle_id INTEGER NOT NULL,
                    descuento_id INTEGER,
                    tipo TEXT NOT NULL,
                    valor REAL NOT NULL,
                    monto REAL NOT NULL,
                    FOREIGN KEY (venta_detalle_id) REFERENCES ventas_detalle(id) ON DELETE CASCADE,
                    FOREIGN KEY (descuento_id) REFERENCES descuentos(id)
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_descuentos_codigo ON descuentos(codigo)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_descuentos_activo ON descuentos(activo)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_promociones_activo ON promociones(activo)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ventas_detalle_descuento_venta ON ventas_detalle_descuento(venta_detalle_id)")

            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V14 failed: {e}")
