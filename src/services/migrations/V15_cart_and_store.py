"""V15: Cart, sales config, and online store tables.

Tables: configuracion_ventas, carritos, carritos_items,
        tienda_config, tienda_productos, tienda_pedidos, tienda_pedidos_items
"""


def run(db):
    try:
        with db._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS configuracion_ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clave TEXT UNIQUE NOT NULL,
                    valor TEXT NOT NULL,
                    descripcion TEXT,
                    actualizado_en TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS carritos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL,
                    cliente_id INTEGER,
                    estado TEXT DEFAULT 'activo',
                    notas TEXT,
                    creado_en TEXT NOT NULL,
                    actualizado_en TEXT NOT NULL,
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS carritos_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    carrito_id INTEGER NOT NULL,
                    producto_id INTEGER NOT NULL,
                    cantidad INTEGER NOT NULL,
                    precio_unitario REAL NOT NULL,
                    FOREIGN KEY (carrito_id) REFERENCES carritos(id) ON DELETE CASCADE,
                    FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS tienda_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clave TEXT UNIQUE NOT NULL,
                    valor TEXT NOT NULL,
                    descripcion TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS tienda_productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id INTEGER NOT NULL UNIQUE,
                    visible INTEGER DEFAULT 1,
                    descripcion_larga TEXT,
                    imagen_url TEXT,
                    destacado INTEGER DEFAULT 0,
                    orden INTEGER DEFAULT 0,
                    FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS tienda_pedidos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_nombre TEXT NOT NULL,
                    cliente_email TEXT NOT NULL,
                    cliente_telefono TEXT,
                    direccion_envio TEXT,
                    notas TEXT,
                    total REAL NOT NULL,
                    estado TEXT DEFAULT 'pendiente',
                    metodo_pago TEXT DEFAULT 'pendiente',
                    creado_en TEXT NOT NULL,
                    actualizado_en TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS tienda_pedidos_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pedido_id INTEGER NOT NULL,
                    producto_id INTEGER NOT NULL,
                    cantidad INTEGER NOT NULL,
                    precio_unitario REAL NOT NULL,
                    subtotal REAL NOT NULL,
                    FOREIGN KEY (pedido_id) REFERENCES tienda_pedidos(id) ON DELETE CASCADE,
                    FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
            """)

            # Default sales config
            conn.execute(
                "INSERT OR IGNORE INTO configuracion_ventas (clave, valor, descripcion, actualizado_en) VALUES (?, ?, ?, ?)",
                ("iva_rate", "0.0", "Tasa de IVA predeterminada (ej: 0.16)", "2026-01-01T00:00:00"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO configuracion_ventas (clave, valor, descripcion, actualizado_en) VALUES (?, ?, ?, ?)",
                ("default_payment_method", "efectivo", "Método de pago predeterminado", "2026-01-01T00:00:00"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO configuracion_ventas (clave, valor, descripcion, actualizado_en) VALUES (?, ?, ?, ?)",
                ("default_discount", "0", "Descuento predeterminado (%)", "2026-01-01T00:00:00"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO configuracion_ventas (clave, valor, descripcion, actualizado_en) VALUES (?, ?, ?, ?)",
                ("auto_clear_cart", "true", "Limpiar carrito automáticamente al completar venta", "2026-01-01T00:00:00"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO configuracion_ventas (clave, valor, descripcion, actualizado_en) VALUES (?, ?, ?, ?)",
                ("enable_discounts", "true", "Habilitar descuentos en ventas", "2026-01-01T00:00:00"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO configuracion_ventas (clave, valor, descripcion, actualizado_en) VALUES (?, ?, ?, ?)",
                ("credit_limit", "0", "Límite de crédito predeterminado para clientes (0=sin límite)", "2026-01-01T00:00:00"),
            )

            # Default store config
            conn.execute(
                "INSERT OR IGNORE INTO tienda_config (clave, valor, descripcion) VALUES (?, ?, ?)",
                ("store_enabled", "false", "Activar tienda online"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO tienda_config (clave, valor, descripcion) VALUES (?, ?, ?)",
                ("store_name", "Mi Tienda", "Nombre de la tienda online"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO tienda_config (clave, valor, descripcion) VALUES (?, ?, ?)",
                ("store_email", "", "Email de contacto de la tienda"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO tienda_config (clave, valor, descripcion) VALUES (?, ?, ?)",
                ("store_currency", "ARS", "Moneda de la tienda"),
            )

            conn.execute("CREATE INDEX IF NOT EXISTS idx_carritos_usuario ON carritos(usuario)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_carritos_estado ON carritos(estado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_carritos_items_carrito ON carritos_items(carrito_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tienda_productos_visible ON tienda_productos(visible)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tienda_productos_destacado ON tienda_productos(destacado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tienda_pedidos_estado ON tienda_pedidos(estado)")

            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V15 failed: {e}")
