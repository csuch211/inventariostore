"""V8: Create accounting tables for double-entry bookkeeping.

Tables: plan_cuentas, asientos_contables, movimientos_contables
Supports: journal entries, chart of accounts, trial balance.
"""


def run(db):
    """Create accounting tables if they don't exist."""
    try:
        with db._get_connection() as conn:
            # Chart of accounts
            conn.execute("""
                CREATE TABLE IF NOT EXISTS plan_cuentas (
                    codigo TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    padre_codigo TEXT,
                    nivel INTEGER DEFAULT 1,
                    activa INTEGER DEFAULT 1
                )
            """)

            # Journal entries
            conn.execute("""
                CREATE TABLE IF NOT EXISTS asientos_contables (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero TEXT UNIQUE NOT NULL,
                    fecha TEXT NOT NULL,
                    descripcion TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    referencia_id INTEGER,
                    referencia_tipo TEXT,
                    estado TEXT DEFAULT 'borrador',
                    creado_en TEXT NOT NULL,
                    creado_por TEXT
                )
            """)

            # Accounting movements (debit/credit)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS movimientos_contables (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asiento_id INTEGER NOT NULL,
                    cuenta_codigo TEXT NOT NULL,
                    cuenta_nombre TEXT NOT NULL,
                    debito REAL DEFAULT 0,
                    credito REAL DEFAULT 0,
                    descripcion TEXT,
                    FOREIGN KEY (asiento_id) REFERENCES asientos_contables(id) ON DELETE CASCADE
                )
            """)

            # Bank reconciliation
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conciliacion_bancaria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha DATE NOT NULL,
                    descripcion TEXT NOT NULL,
                    monto REAL NOT NULL,
                    tipo TEXT NOT NULL,
                    conciliado INTEGER DEFAULT 0,
                    asiento_id INTEGER,
                    notas TEXT,
                    FOREIGN KEY (asiento_id) REFERENCES asientos_contables(id)
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_asientos_fecha ON asientos_contables(fecha)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_asientos_tipo ON asientos_contables(tipo)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_asientos_estado ON asientos_contables(estado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_asiento ON movimientos_contables(asiento_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_cuenta ON movimientos_contables(cuenta_codigo)")

            # Seed default chart of accounts
            _seed_plan_cuentas(conn)

            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V8 failed: {e}")


def _seed_plan_cuentas(conn):
    """Seed the default chart of accounts for a small business."""
    cuentas = [
        # Assets
        ("1.1", "Caja y Bancos", "activo", None, 1),
        ("1.1.01", "Caja", "activo", "1.1", 2),
        ("1.1.02", "Banco", "activo", "1.1", 2),
        ("1.2", "Cuentas por Cobrar", "activo", None, 1),
        ("1.2.01", "Clientes", "activo", "1.2", 2),
        ("1.3", "Inventario", "activo", None, 1),
        ("1.3.01", "Mercancía", "activo", "1.3", 2),
        ("1.4", "Activos Fijos", "activo", None, 1),
        ("1.4.01", "Equipo", "activo", "1.4", 2),

        # Liabilities
        ("2.1", "Cuentas por Pagar", "pasivo", None, 1),
        ("2.1.01", "Proveedores", "pasivo", "2.1", 2),
        ("2.2", "Impuestos por Pagar", "pasivo", None, 1),
        ("2.2.01", "IVA por Pagar", "pasivo", "2.2", 2),

        # Equity
        ("3.1", "Capital Social", "patrimonio", None, 1),
        ("3.2", "Resultados Acumulados", "patrimonio", None, 1),

        # Revenue
        ("4.1", "Ventas", "ingreso", None, 1),
        ("4.1.01", "Ventas de Mercancía", "ingreso", "4.1", 2),
        ("4.2", "Otros Ingresos", "ingreso", None, 1),

        # Expenses
        ("5.1", "Costo de Ventas", "gasto", None, 1),
        ("5.1.01", "Costo de Mercancía", "gasto", "5.1", 2),
        ("5.2", "Gastos Operativos", "gasto", None, 1),
        ("5.2.01", "Sueldos", "gasto", "5.2", 2),
        ("5.2.02", "Arrendamiento", "gasto", "5.2", 2),
        ("5.2.03", "Servicios", "gasto", "5.2", 2),
        ("5.3", "Impuestos", "gasto", None, 1),
        ("5.3.01", "IVA Descontable", "gasto", "5.3", 2),
    ]

    for codigo, nombre, tipo, padre, nivel in cuentas:
        conn.execute(
            """INSERT OR IGNORE INTO plan_cuentas (codigo, nombre, tipo, padre_codigo, nivel)
               VALUES (?, ?, ?, ?, ?)""",
            (codigo, nombre, tipo, padre, nivel),
        )
