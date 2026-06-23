"""V3: Drop legacy 'estado' column from productos, use 'activo' exclusively.

All other tables (categorias, proveedores, clientes, almacenes,
variantes_producto) already use activo=1/0. This migration makes
productos consistent by removing the old TEXT estado column.
"""


def run(db):
    """Drop the estado column from productos if it exists."""
    try:
        with db._get_connection() as conn:
            # Check if column exists
            cursor = conn.execute("PRAGMA table_info(productos)")
            columns = {row[1] for row in cursor.fetchall()}

            if "estado" in columns:
                # SQLite doesn't support DROP COLUMN directly in older versions.
                # We recreate the table without the column.
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS productos_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo TEXT UNIQUE NOT NULL,
                        nombre TEXT NOT NULL,
                        cantidad INTEGER DEFAULT 0,
                        precio REAL DEFAULT 0.0,
                        descripcion TEXT,
                        categoria TEXT,
                        activo INTEGER DEFAULT 1,
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL,
                        creado_por TEXT,
                        actualizado_por TEXT,
                        stock_min INTEGER DEFAULT 0,
                        proveedor_id INTEGER,
                        unidad_medida TEXT DEFAULT 'unidad',
                        precio_costo REAL,
                        margen REAL,
                        impuesto_id INTEGER,
                        sku TEXT
                    );

                    INSERT INTO productos_new (
                        id, codigo, nombre, cantidad, precio, descripcion,
                        categoria, activo, creado_en, actualizado_en,
                        creado_por, actualizado_por, stock_min, proveedor_id,
                        unidad_medida, precio_costo, margen, impuesto_id, sku
                    )
                    SELECT
                        id, codigo, nombre, cantidad, precio, descripcion,
                        categoria, activo, creado_en, actualizado_en,
                        creado_por, actualizado_por,
                        COALESCE(stock_min, 0),
                        proveedor_id,
                        COALESCE(unidad_medida, 'unidad'),
                        precio_costo, margen, impuesto_id, sku
                    FROM productos;

                    DROP TABLE productos;
                    ALTER TABLE productos_new RENAME TO productos;
                """)

            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V3 failed: {e}")
