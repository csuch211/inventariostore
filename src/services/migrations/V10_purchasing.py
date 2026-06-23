"""V10: Create purchasing module tables.

Tables: cotizaciones, cotizacion_detalle, evaluaciones_proveedor, recepciones
"""


def run(db):
    """Create purchasing module tables if they don't exist."""
    try:
        with db._get_connection() as conn:
            # Quotations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cotizaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero TEXT UNIQUE NOT NULL,
                    proveedor_id INTEGER NOT NULL,
                    fecha_solicitud TEXT NOT NULL,
                    fecha_validez TEXT,
                    estado TEXT DEFAULT 'solicitada',
                    notas TEXT,
                    subtotal REAL DEFAULT 0,
                    impuestos REAL DEFAULT 0,
                    total REAL DEFAULT 0,
                    creado_en TEXT NOT NULL,
                    creado_por TEXT,
                    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
                )
            """)

            # Quotation detail lines
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cotizacion_detalle (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cotizacion_id INTEGER NOT NULL,
                    producto_id INTEGER,
                    descripcion TEXT NOT NULL,
                    cantidad REAL NOT NULL DEFAULT 1,
                    precio_unitario REAL NOT NULL,
                    subtotal REAL NOT NULL,
                    notas TEXT,
                    FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id) ON DELETE CASCADE,
                    FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
            """)

            # Supplier evaluations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evaluaciones_proveedor (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proveedor_id INTEGER NOT NULL,
                    evaluador TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    calidad REAL DEFAULT 0,
                    puntualidad REAL DEFAULT 0,
                    precio REAL DEFAULT 0,
                    servicio REAL DEFAULT 0,
                    puntuacion_global REAL DEFAULT 0,
                    comentarios TEXT,
                    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
                )
            """)

            # Goods received notes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recepciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    orden_compra_id INTEGER,
                    proveedor_id INTEGER NOT NULL,
                    numero TEXT UNIQUE NOT NULL,
                    fecha_recepcion TEXT NOT NULL,
                    estado TEXT DEFAULT 'recibida',
                    calidad TEXT DEFAULT 'aceptada',
                    notas TEXT,
                    creado_en TEXT NOT NULL,
                    creado_por TEXT,
                    FOREIGN KEY (orden_compra_id) REFERENCES ordenes_compra(id),
                    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
                )
            """)

            # Reception detail lines
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recepcion_detalle (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recepcion_id INTEGER NOT NULL,
                    producto_id INTEGER NOT NULL,
                    cantidad_solicitada REAL NOT NULL,
                    cantidad_recibida REAL NOT NULL,
                    estado_calidad TEXT DEFAULT 'aceptado',
                    notas TEXT,
                    FOREIGN KEY (recepcion_id) REFERENCES recepciones(id) ON DELETE CASCADE,
                    FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cotizaciones_proveedor ON cotizaciones(proveedor_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cotizaciones_estado ON cotizaciones(estado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cotizacion_detalle_cotizacion ON cotizacion_detalle(cotizacion_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evaluaciones_proveedor ON evaluaciones_proveedor(proveedor_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_recepciones_orden ON recepciones(orden_compra_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_recepciones_proveedor ON recepciones(proveedor_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_recepcion_detalle_recepcion ON recepcion_detalle(recepcion_id)")

            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V10 failed: {e}")
