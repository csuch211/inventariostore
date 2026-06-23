"""V7: Create invoicing tables for billing module.

Tables: facturas, factura_detalle
Supports: invoice generation, tax integration, discounts, credit notes.
"""


def run(db):
    """Create invoicing tables if they don't exist."""
    try:
        with db._get_connection() as conn:
            # Invoices table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS facturas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero TEXT UNIQUE NOT NULL,
                    venta_id INTEGER,
                    cliente_id INTEGER NOT NULL,
                    subtotal REAL NOT NULL DEFAULT 0,
                    impuestos_total REAL NOT NULL DEFAULT 0,
                    descuentos_total REAL NOT NULL DEFAULT 0,
                    total REAL NOT NULL DEFAULT 0,
                    estado TEXT DEFAULT 'borrador',
                    tipo TEXT DEFAULT 'factura',
                    fecha_emision TEXT,
                    fecha_vencimiento TEXT,
                    notas TEXT,
                    creado_en TEXT NOT NULL,
                    creado_por TEXT,
                    FOREIGN KEY (venta_id) REFERENCES ventas(id),
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
                )
            """)

            # Invoice detail lines
            conn.execute("""
                CREATE TABLE IF NOT EXISTS factura_detalle (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    factura_id INTEGER NOT NULL,
                    producto_id INTEGER,
                    descripcion TEXT NOT NULL,
                    cantidad REAL NOT NULL DEFAULT 1,
                    precio_unitario REAL NOT NULL,
                    descuento_pct REAL DEFAULT 0,
                    descuento_monto REAL DEFAULT 0,
                    impuesto_pct REAL DEFAULT 0,
                    impuesto_monto REAL DEFAULT 0,
                    subtotal REAL NOT NULL,
                    FOREIGN KEY (factura_id) REFERENCES facturas(id) ON DELETE CASCADE,
                    FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
            """)

            # Accounts receivable
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cuentas_cobrar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id INTEGER NOT NULL,
                    factura_id INTEGER,
                    monto_original REAL NOT NULL,
                    monto_pagado REAL DEFAULT 0,
                    monto_pendiente REAL NOT NULL,
                    fecha_emision TEXT NOT NULL,
                    fecha_vencimiento TEXT NOT NULL,
                    estado TEXT DEFAULT 'pendiente',
                    notas TEXT,
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                    FOREIGN KEY (factura_id) REFERENCES facturas(id)
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facturas_numero ON facturas(numero)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facturas_cliente ON facturas(cliente_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facturas_estado ON facturas(estado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facturas_fecha ON facturas(fecha_emision)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_factura_detalle_factura ON factura_detalle(factura_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cuentas_cobrar_cliente ON cuentas_cobrar(cliente_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cuentas_cobrar_estado ON cuentas_cobrar(estado)")

            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V7 failed: {e}")
