"""
Enhanced database management with connection pooling and error handling
"""

import contextlib
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

from config.settings import (
    DATABASE_FILE,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USER,
    DEFAULT_OPERATOR_PASSWORD,
    DEFAULT_OPERATOR_USER,
    ENABLE_AUDIT_LOG,
    STOCK_LOW_DEFAULT,
)
from services.auth import _LEGACY_SALT, _hash_with_salt
from services.migrator import upgrade as run_migrations
from services.permissions import (
    PERMISSIONS_BY_MODULE,
    ROLE_DEFAULT_PERMISSIONS,
    ROLE_DESCRIPTIONS,
)
from services.repository import (
    ConfigRepository,
    InventoryRepository,
    ProductRepository,
    SaleRepository,
    UserRepository,
)
from utils.exceptions import DatabaseException, DuplicateProductException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class DatabaseManager:
    """Professional database manager with audit logging"""

    _local = threading.local()

    def __init__(self, db_path: Path = DATABASE_FILE) -> None:
        self.db_path = db_path
        self.product_repo = ProductRepository(db_path)
        self.user_repo = UserRepository(db_path)
        self.sale_repo = SaleRepository(db_path)
        self.inventory_repo = InventoryRepository(db_path)
        self.config_repo = ConfigRepository(db_path)
        self._init_database()
        logger.info(f"Database initialized at {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection (reuses per-thread)"""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.execute("SELECT 1")
                return self._local.conn
            except sqlite3.Error:
                with contextlib.suppress(Exception):
                    self._local.conn.close()
                self._local.conn = None
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
            return conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise DatabaseException(f"Connection failed: {e}")

    def close_connections(self) -> None:
        """Close thread-local connection for cleanup"""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            with contextlib.suppress(Exception):
                self._local.conn.close()
            self._local.conn = None

    def _init_database(self):
        """Initialize database schema"""
        try:
            with self._get_connection() as conn:
                # Main products table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS productos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo TEXT UNIQUE NOT NULL,
                        nombre TEXT NOT NULL,
                        cantidad INTEGER DEFAULT 0,
                        precio REAL DEFAULT 0.0,
                        descripcion TEXT,
                        categoria TEXT,
                        estado TEXT DEFAULT 'activo',
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL,
                        creado_por TEXT,
                        actualizado_por TEXT
                    )
                """)

                # Stock history table for audit trail
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS historial_stock (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        producto_id INTEGER NOT NULL,
                        cantidad_anterior INTEGER,
                        cantidad_nueva INTEGER,
                        tipo_movimiento TEXT,
                        razon TEXT,
                        creado_en TEXT NOT NULL,
                        usuario TEXT,
                        FOREIGN KEY (producto_id) REFERENCES productos(id)
                    )
                """)

                # Audit log table
                if ENABLE_AUDIT_LOG:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS auditoria (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            accion TEXT NOT NULL,
                            tabla TEXT NOT NULL,
                            registro_id INTEGER,
                            usuario TEXT,
                            detalles TEXT,
                            creado_en TEXT NOT NULL
                        )
                    """)

                # Users table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        nombre TEXT NOT NULL,
                        rol TEXT NOT NULL DEFAULT 'operador',
                        activo INTEGER DEFAULT 1,
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL
                    )
                """)

                # Roles/permissions table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS roles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT UNIQUE NOT NULL,
                        permisos TEXT,  -- legacy column, no longer the source of truth
                        descripcion TEXT
                    )
                """)

                # If the roles table was created with the legacy schema
                # (permisos TEXT NOT NULL), drop and recreate it. No legacy
                # data is preserved — roles are re-seeded by seed_rbac().
                cursor_info = conn.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name='roles'"
                ).fetchone()
                if cursor_info and "permisos TEXT NOT NULL" in (cursor_info[0] or ""):
                    conn.execute("DROP TABLE roles")
                    conn.execute("""
                        CREATE TABLE roles (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            nombre TEXT UNIQUE NOT NULL,
                            permisos TEXT,
                            descripcion TEXT
                        )
                    """)

                # Categories table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS categorias (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT UNIQUE NOT NULL,
                        descripcion TEXT,
                        activo INTEGER DEFAULT 1,
                        creado_en TEXT NOT NULL
                    )
                """)

                # Suppliers table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS proveedores (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT NOT NULL,
                        contacto TEXT,
                        telefono TEXT,
                        email TEXT,
                        direccion TEXT,
                        activo INTEGER DEFAULT 1,
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL
                    )
                """)

                # Purchase orders table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ordenes_compra (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        proveedor_id INTEGER,
                        producto_id INTEGER NOT NULL,
                        cantidad INTEGER NOT NULL,
                        estado TEXT DEFAULT 'pendiente',
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL,
                        creado_por TEXT,
                        FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),
                        FOREIGN KEY (producto_id) REFERENCES productos(id)
                    )
                """)

                # Product images table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS imagenes_producto (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        producto_id INTEGER NOT NULL,
                        ruta TEXT NOT NULL,
                        tipo TEXT DEFAULT 'imagen',
                        creado_en TEXT NOT NULL,
                        FOREIGN KEY (producto_id) REFERENCES productos(id)
                    )
                """)

                # ============ RBAC: permissions catalog ============
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS permisos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        clave TEXT UNIQUE NOT NULL,
                        modulo TEXT NOT NULL,
                        accion TEXT NOT NULL,
                        descripcion TEXT
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS rol_permisos (
                        rol_id INTEGER NOT NULL,
                        permiso_id INTEGER NOT NULL,
                        PRIMARY KEY (rol_id, permiso_id),
                        FOREIGN KEY (rol_id) REFERENCES roles(id) ON DELETE CASCADE,
                        FOREIGN KEY (permiso_id) REFERENCES permisos(id) ON DELETE CASCADE
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS usuario_permisos_extra (
                        usuario_id INTEGER NOT NULL,
                        permiso_id INTEGER NOT NULL,
                        PRIMARY KEY (usuario_id, permiso_id),
                        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                        FOREIGN KEY (permiso_id) REFERENCES permisos(id) ON DELETE CASCADE
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS usuario_roles (
                        usuario_id INTEGER NOT NULL,
                        rol_id INTEGER NOT NULL,
                        PRIMARY KEY (usuario_id, rol_id),
                        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                        FOREIGN KEY (rol_id) REFERENCES roles(id) ON DELETE CASCADE
                    )
                """)

                # ============ New feature tables ============

                # Customers table (for POS/Sales module)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS clientes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT NOT NULL,
                        telefono TEXT,
                        email TEXT,
                        direccion TEXT,
                        activo INTEGER DEFAULT 1,
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL
                    )
                """)

                # Sales table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ventas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cliente_id INTEGER,
                        total REAL NOT NULL DEFAULT 0,
                        estado TEXT DEFAULT 'completada',
                        creado_en TEXT NOT NULL,
                        creado_por TEXT,
                        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
                    )
                """)

                # Sale details table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ventas_detalle (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        venta_id INTEGER NOT NULL,
                        producto_id INTEGER NOT NULL,
                        cantidad INTEGER NOT NULL,
                        precio_unitario REAL NOT NULL,
                        subtotal REAL NOT NULL,
                        FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
                        FOREIGN KEY (producto_id) REFERENCES productos(id)
                    )
                """)

                # Payments table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS pagos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        venta_id INTEGER NOT NULL,
                        metodo TEXT NOT NULL DEFAULT 'efectivo',
                        monto REAL NOT NULL,
                        referencia TEXT,
                        creado_en TEXT NOT NULL,
                        FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE
                    )
                """)

                # Application configuration table (theme, SMTP, backup schedule, etc.)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS configuracion (
                        clave TEXT PRIMARY KEY,
                        valor TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL
                    )
                """)

                # Backup history table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS backups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ruta TEXT NOT NULL,
                        tamano INTEGER DEFAULT 0,
                        tipo TEXT DEFAULT 'manual',
                        creado_en TEXT NOT NULL,
                        creado_por TEXT
                    )
                """)

                # ============ Warehouses (F2.1) ============
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS almacenes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT NOT NULL,
                        ubicacion TEXT,
                        activo INTEGER DEFAULT 1,
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS inventario_almacen (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        producto_id INTEGER NOT NULL,
                        almacen_id INTEGER NOT NULL,
                        cantidad INTEGER DEFAULT 0,
                        FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
                        FOREIGN KEY (almacen_id) REFERENCES almacenes(id) ON DELETE CASCADE,
                        UNIQUE(producto_id, almacen_id)
                    )
                """)

                # ============ Fase 1: Devoluciones / Notas de crédito ============
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS devoluciones (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        venta_id INTEGER NOT NULL,
                        producto_id INTEGER NOT NULL,
                        cantidad INTEGER NOT NULL,
                        precio_unitario REAL NOT NULL,
                        subtotal REAL NOT NULL,
                        motivo TEXT,
                        estado TEXT DEFAULT 'completada',
                        creado_en TEXT NOT NULL,
                        creado_por TEXT,
                        FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
                        FOREIGN KEY (producto_id) REFERENCES productos(id)
                    )
                """)

                # ============ Fase 1: Transferencias entre almacenes ============
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS transferencias_almacen (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        almacen_origen_id INTEGER NOT NULL,
                        almacen_destino_id INTEGER NOT NULL,
                        producto_id INTEGER NOT NULL,
                        cantidad INTEGER NOT NULL,
                        estado TEXT DEFAULT 'completada',
                        nota TEXT,
                        creado_en TEXT NOT NULL,
                        creado_por TEXT,
                        FOREIGN KEY (almacen_origen_id) REFERENCES almacenes(id),
                        FOREIGN KEY (almacen_destino_id) REFERENCES almacenes(id),
                        FOREIGN KEY (producto_id) REFERENCES productos(id)
                    )
                """)

                # ============ Fase 1: Conteo físico / reconciliación ============
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sesiones_conteo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT NOT NULL,
                        almacen_id INTEGER,
                        estado TEXT DEFAULT 'en_progreso',
                        notas TEXT,
                        creado_en TEXT NOT NULL,
                        cerrado_en TEXT,
                        creado_por TEXT,
                        FOREIGN KEY (almacen_id) REFERENCES almacenes(id)
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conteo_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sesion_id INTEGER NOT NULL,
                        producto_id INTEGER NOT NULL,
                        cantidad_sistema REAL NOT NULL DEFAULT 0,
                        cantidad_contada REAL,
                        diferencia REAL,
                        notas TEXT,
                        contado_en TEXT,
                        contado_por TEXT,
                        FOREIGN KEY (sesion_id) REFERENCES sesiones_conteo(id) ON DELETE CASCADE,
                        FOREIGN KEY (producto_id) REFERENCES productos(id)
                    )
                """)

                # ============ Fase 1: Lotes / Series / Vencimientos ============
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS lotes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        producto_id INTEGER NOT NULL,
                        codigo_lote TEXT NOT NULL,
                        serie TEXT,
                        cantidad_inicial INTEGER NOT NULL DEFAULT 0,
                        cantidad_actual INTEGER NOT NULL DEFAULT 0,
                        fecha_fabricacion TEXT,
                        fecha_vencimiento TEXT,
                        ubicacion TEXT,
                        proveedor_id INTEGER,
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL,
                        FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
                        FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),
                        UNIQUE(producto_id, codigo_lote)
                    )
                """)

                # ============ Fase 1: Listas de precios multi-nivel ============
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS listas_precios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT UNIQUE NOT NULL,
                        descripcion TEXT,
                        activo INTEGER DEFAULT 1,
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS precios_producto (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        producto_id INTEGER NOT NULL,
                        lista_id INTEGER NOT NULL,
                        precio REAL NOT NULL,
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL,
                        FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
                        FOREIGN KEY (lista_id) REFERENCES listas_precios(id) ON DELETE CASCADE,
                        UNIQUE(producto_id, lista_id)
                    )
                """)

                # ============ Fase 1: Impuestos ============
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS impuestos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT UNIQUE NOT NULL,
                        porcentaje REAL NOT NULL,
                        tipo TEXT DEFAULT 'iva',
                        activo INTEGER DEFAULT 1,
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL
                    )
                """)

                # ============ Fase 1: Caja / Turnos POS ============
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS turnos_caja (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario TEXT NOT NULL,
                        monto_inicial REAL NOT NULL DEFAULT 0,
                        monto_final REAL,
                        monto_esperado REAL,
                        diferencia REAL,
                        estado TEXT DEFAULT 'abierto',
                        notas_apertura TEXT,
                        notas_cierre TEXT,
                        abierto_en TEXT NOT NULL,
                        cerrado_en TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS movimientos_caja (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        turno_id INTEGER NOT NULL,
                        tipo TEXT NOT NULL,
                        monto REAL NOT NULL,
                        concepto TEXT,
                        referencia TEXT,
                        creado_en TEXT NOT NULL,
                        FOREIGN KEY (turno_id) REFERENCES turnos_caja(id) ON DELETE CASCADE
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ventas_turno (
                        turno_id INTEGER NOT NULL,
                        venta_id INTEGER NOT NULL,
                        PRIMARY KEY (turno_id, venta_id),
                        FOREIGN KEY (turno_id) REFERENCES turnos_caja(id) ON DELETE CASCADE,
                        FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE
                    )
                """)

                # ============ Fase 3: Variantes de producto ============
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS variantes_producto (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        producto_id INTEGER NOT NULL,
                        sku TEXT UNIQUE NOT NULL,
                        atributos TEXT NOT NULL,  -- JSON: {"talla":"M","color":"rojo"}
                        cantidad INTEGER DEFAULT 0,
                        precio_override REAL,
                        activo INTEGER DEFAULT 1,
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL,
                        FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_variantes_producto
                    ON variantes_producto(producto_id)
                """)

                # ============ Fase 3: Plantillas de reporte personalizable ============
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS plantillas_reporte (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT NOT NULL,
                        modulo TEXT NOT NULL DEFAULT 'productos',
                        columnas TEXT NOT NULL,  -- JSON: ["codigo","nombre","precio"]
                        filtros TEXT,            -- JSON: dict de filtros
                        agrupacion TEXT,         -- columna por la que agrupar
                        ordenado_por TEXT,
                        creado_por TEXT,
                        creado_en TEXT NOT NULL,
                        actualizado_en TEXT NOT NULL
                    )
                """)

                # ============ Fase 3: Cola de jobs (push/email) ============
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS jobs_push (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tipo TEXT NOT NULL,        -- 'low_stock' | 'sale' | 'order_received' | 'custom'
                        destinatario TEXT NOT NULL,
                        asunto TEXT NOT NULL,
                        cuerpo TEXT NOT NULL,
                        estado TEXT DEFAULT 'pendiente',  -- pendiente|enviado|fallido
                        intentos INTEGER DEFAULT 0,
                        ultimo_error TEXT,
                        creado_en TEXT NOT NULL,
                        enviado_en TEXT
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_jobs_estado
                    ON jobs_push(estado, creado_en)
                """)

                # ============ Fase 3: Preferencia de idioma por usuario ============
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS usuario_prefs (
                        usuario TEXT PRIMARY KEY,
                        idioma TEXT NOT NULL DEFAULT 'es',
                        tema TEXT DEFAULT 'light',
                        actualizado_en TEXT NOT NULL
                    )
                """)

                conn.commit()
                self.seed_rbac()
                self.migrar_schema()

                # Run pending database migrations
                applied = run_migrations(self)
                if applied:
                    logger.info(f"Applied {applied} pending migration(s)")

                logger.info("Database schema initialized successfully")
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {e}")
            raise DatabaseException(f"Schema initialization failed: {e}")

    def seed_rbac(self) -> None:
        """Seed the permission catalog, default roles, and role->permission
        mappings. Idempotent. Called from _init_database.
        """
        try:
            with self._get_connection() as conn:
                # Seed permisos
                for module_key, perms in PERMISSIONS_BY_MODULE.items():
                    for p in perms:
                        clave = p["clave"]
                        accion = clave.split(".", 1)[1] if "." in clave else clave
                        conn.execute(
                            """INSERT OR IGNORE INTO permisos (clave, modulo, accion, descripcion)
                               VALUES (?, ?, ?, ?)""",
                            (clave, module_key, accion, p["descripcion"]),
                        )

                # Seed roles
                for rol_name, desc in ROLE_DESCRIPTIONS.items():
                    conn.execute(
                        "INSERT OR IGNORE INTO roles (nombre, descripcion) VALUES (?, ?)",
                        (rol_name, desc),
                    )

                # Seed rol_permisos from defaults
                for rol_name, perms in ROLE_DEFAULT_PERMISSIONS.items():
                    cursor = conn.execute("SELECT id FROM roles WHERE nombre = ?", (rol_name,))
                    row = cursor.fetchone()
                    if not row:
                        continue
                    rol_id = row["id"]
                    for perm_key in perms:
                        cursor2 = conn.execute(
                            "SELECT id FROM permisos WHERE clave = ?", (perm_key,)
                        )
                        prow = cursor2.fetchone()
                        if not prow:
                            continue
                        conn.execute(
                            "INSERT OR IGNORE INTO rol_permisos (rol_id, permiso_id) VALUES (?, ?)",
                            (rol_id, prow["id"]),
                        )

                # Assign default role to existing users with rol="admin"/"operador"
                cursor = conn.execute("SELECT id, username, rol FROM usuarios")
                for u in cursor.fetchall():
                    legacy_rol = (u["rol"] or "operador").lower()
                    if legacy_rol not in ROLE_DEFAULT_PERMISSIONS:
                        legacy_rol = "operador"
                    cursor2 = conn.execute("SELECT id FROM roles WHERE nombre = ?", (legacy_rol,))
                    rrow = cursor2.fetchone()
                    if rrow:
                        conn.execute(
                            "INSERT OR IGNORE INTO usuario_roles (usuario_id, rol_id) VALUES (?, ?)",
                            (u["id"], rrow["id"]),
                        )

                conn.commit()
                logger.info("RBAC catalog seeded")
        except sqlite3.Error as e:
            logger.warning(f"RBAC seed error: {e}")

    def migrar_schema(self) -> None:
        """Add missing columns to existing tables (safe migration)"""
        try:
            with self._get_connection() as conn:
                with contextlib.suppress(sqlite3.OperationalError):
                    conn.execute("ALTER TABLE productos ADD COLUMN stock_min INTEGER DEFAULT 0")
                with contextlib.suppress(sqlite3.OperationalError):
                    conn.execute(
                        "ALTER TABLE productos ADD COLUMN proveedor_id INTEGER REFERENCES proveedores(id)"
                    )
                with contextlib.suppress(sqlite3.OperationalError):
                    conn.execute("ALTER TABLE usuarios ADD COLUMN theme_mode TEXT DEFAULT 'light'")
                with contextlib.suppress(sqlite3.OperationalError):
                    conn.execute(
                        "ALTER TABLE productos ADD COLUMN unidad_medida TEXT DEFAULT 'unidad'"
                    )
                # Fase 1: precios multi-nivel e impuestos en producto
                with contextlib.suppress(sqlite3.OperationalError):
                    conn.execute("ALTER TABLE productos ADD COLUMN precio_costo REAL DEFAULT 0")
                with contextlib.suppress(sqlite3.OperationalError):
                    conn.execute("ALTER TABLE productos ADD COLUMN margen REAL DEFAULT 0")
                with contextlib.suppress(sqlite3.OperationalError):
                    conn.execute(
                        "ALTER TABLE productos ADD COLUMN impuesto_id INTEGER REFERENCES impuestos(id)"
                    )
                # Fase 1: SKU secundario opcional
                with contextlib.suppress(sqlite3.OperationalError):
                    conn.execute("ALTER TABLE productos ADD COLUMN sku TEXT")
                # Seed default users in `usuarios` table if missing (so RBAC
                # resolution can find them). This runs after _init_database
                # and after seed_rbac.
                self._seed_default_users(conn)
                conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Schema migration error: {e}")

    def _seed_default_users(self, conn):
        """Ensure the legacy in-memory users (admin/usuario) also exist in
        the `usuarios` table so RBAC resolution finds them. Idempotent.
        """
        defaults = [
            (DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASSWORD, "Administrador", "admin"),
            (DEFAULT_OPERATOR_USER, DEFAULT_OPERATOR_PASSWORD, "Operador", "operador"),
        ]
        now = datetime.now().isoformat()
        for username, password, full_name, rol in defaults:
            cursor = conn.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
            if cursor.fetchone() is not None:
                continue
            ph = _hash_with_salt(password, _LEGACY_SALT)
            cursor = conn.execute(
                """INSERT INTO usuarios
                   (username, password_hash, nombre, rol, activo,
                    creado_en, actualizado_en)
                   VALUES (?, ?, ?, ?, 1, ?, ?)""",
                (username, ph, full_name, rol, now, now),
            )
            user_id = cursor.lastrowid
            # Assign role
            cursor2 = conn.execute("SELECT id FROM roles WHERE nombre = ?", (rol,))
            rrow = cursor2.fetchone()
            if rrow:
                conn.execute(
                    "INSERT OR IGNORE INTO usuario_roles (usuario_id, rol_id) VALUES (?, ?)",
                    (user_id, rrow["id"]),
                )
            logger.info(f"Seeded default user: {username} as {rol}")

    def _audit_log(
        self,
        conn: sqlite3.Connection,
        accion: str,
        tabla: str,
        registro_id: int,
        usuario: str,
        detalles: str,
    ):
        """Internal audit logging"""
        if ENABLE_AUDIT_LOG:
            try:
                now = datetime.now().isoformat()
                conn.execute(
                    """
                    INSERT INTO auditoria (accion, tabla, registro_id, usuario, detalles, creado_en)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (accion, tabla, registro_id, usuario, detalles, now),
                )
            except sqlite3.Error as e:
                logger.warning(f"Failed to record audit log: {e}")

    # ============ Product methods → self.product_repo ============

    def crear_producto(
        self,
        codigo: str,
        nombre: str,
        cantidad: int = 0,
        precio: float = 0.0,
        descripcion: str = "",
        categoria: str = "",
        stock_min: int = 0,
        proveedor_id: int | None = None,
        usuario: str = "system",
    ) -> dict:
        return self.product_repo.crear_producto(
            codigo,
            nombre,
            cantidad,
            precio,
            descripcion,
            categoria,
            stock_min,
            proveedor_id,
            usuario,
        )

    def obtener_todos_productos(self, estado: str = "activo") -> list[dict]:
        return self.product_repo.obtener_todos_productos(estado)

    def obtener_producto_por_id(self, producto_id: int) -> dict | None:
        return self.product_repo.obtener_producto_por_id(producto_id)

    def obtener_producto_por_codigo(self, codigo: str) -> dict | None:
        return self.product_repo.obtener_producto_por_codigo(codigo)

    def actualizar_producto(
        self,
        producto_id: int,
        nombre: str | None = None,
        cantidad: int | None = None,
        precio: float | None = None,
        descripcion: str | None = None,
        categoria: str | None = None,
        stock_min: int | None = None,
        proveedor_id: int | None = None,
        usuario: str = "system",
    ) -> dict:
        return self.product_repo.actualizar_producto(
            producto_id,
            nombre,
            cantidad,
            precio,
            descripcion,
            categoria,
            stock_min,
            proveedor_id,
            usuario,
        )

    def actualizar_stock(
        self,
        producto_id: int,
        cantidad_nueva: int,
        tipo_movimiento: str = "ajuste",
        razon: str = "",
        usuario: str = "system",
    ) -> dict:
        return self.product_repo.actualizar_stock(
            producto_id,
            cantidad_nueva,
            tipo_movimiento,
            razon,
            usuario,
        )

    def eliminar_producto(self, producto_id: int, usuario: str = "system") -> None:
        self.product_repo.eliminar_producto(producto_id, usuario)

    def buscar_productos(self, query: str) -> list[dict]:
        return self.product_repo.buscar_productos(query)

    def obtener_historial_stock(self, producto_id: int) -> list[dict]:
        return self.product_repo.obtener_historial_stock(producto_id)

    def _query_stock_bajo(
        self, low_threshold: int | None = None, include_proveedor: bool = False
    ) -> list[dict]:
        return self.product_repo._query_stock_bajo(low_threshold, include_proveedor)

    def obtener_productos_con_stock_bajo(self, low_threshold: int | None = None) -> list[dict]:
        return self.product_repo.obtener_productos_con_stock_bajo(low_threshold)

    def obtener_historial_stock_completo(self, limit=100) -> list[dict]:
        return self.product_repo.obtener_historial_stock_completo(limit)

    def obtener_estadisticas(self) -> dict:
        return self.product_repo.obtener_estadisticas()

    def crear_categoria(self, nombre, descripcion="", usuario="system") -> int:
        return self.product_repo.crear_categoria(nombre, descripcion, usuario)

    def obtener_categorias(self) -> list[dict]:
        return self.product_repo.obtener_categorias()

    def crear_proveedor(
        self, nombre, contacto="", telefono="", email="", direccion="", usuario="system"
    ) -> int:
        return self.product_repo.crear_proveedor(
            nombre, contacto, telefono, email, direccion, usuario
        )

    def obtener_proveedores(self) -> list[dict]:
        return self.product_repo.obtener_proveedores()

    def crear_orden_compra(self, proveedor_id, producto_id, cantidad, usuario="system") -> int:
        return self.product_repo.crear_orden_compra(proveedor_id, producto_id, cantidad, usuario)

    def obtener_ordenes_compra(self, estado=None) -> list[dict]:
        return self.product_repo.obtener_ordenes_compra(estado)

    def actualizar_categoria(
        self, categoria_id: int, nombre: str, descripcion: str = "", usuario: str = "system"
    ) -> int:
        return self.product_repo.actualizar_categoria(categoria_id, nombre, descripcion, usuario)

    def eliminar_categoria(self, categoria_id: int, usuario: str = "system") -> bool:
        return self.product_repo.eliminar_categoria(categoria_id, usuario)

    def obtener_categoria_por_id(self, categoria_id: int) -> dict | None:
        return self.product_repo.obtener_categoria_por_id(categoria_id)

    def seed_categorias(self, nombres: list[str], usuario: str = "system") -> int:
        return self.product_repo.seed_categorias(nombres, usuario)

    def actualizar_proveedor(
        self,
        proveedor_id: int,
        nombre: str,
        contacto: str = "",
        telefono: str = "",
        email: str = "",
        direccion: str = "",
        usuario: str = "system",
    ) -> int:
        return self.product_repo.actualizar_proveedor(
            proveedor_id,
            nombre,
            contacto,
            telefono,
            email,
            direccion,
            usuario,
        )

    def eliminar_proveedor(self, proveedor_id: int, usuario: str = "system") -> bool:
        return self.product_repo.eliminar_proveedor(proveedor_id, usuario)

    def obtener_proveedor_por_id(self, proveedor_id: int) -> dict | None:
        return self.product_repo.obtener_proveedor_por_id(proveedor_id)

    def cambiar_estado_orden(
        self,
        orden_id: int,
        nuevo_estado: str,
        usuario: str = "system",
    ) -> bool:
        return self.product_repo.cambiar_estado_orden(orden_id, nuevo_estado, usuario)

    def eliminar_orden_compra(self, orden_id: int, usuario: str = "system") -> bool:
        return self.product_repo.eliminar_orden_compra(orden_id, usuario)

    def obtener_orden_compra_por_id(self, orden_id: int) -> dict | None:
        return self.product_repo.obtener_orden_compra_por_id(orden_id)

    def obtener_distribucion_categorias(self) -> list[dict]:
        return self.product_repo.obtener_distribucion_categorias()

    def obtener_top_productos_por_stock(self, limit: int = 10) -> list[dict]:
        return self.product_repo.obtener_top_productos_por_stock(limit)

    def obtener_serie_inventario(self, dias: int = 30) -> list[dict]:
        return self.product_repo.obtener_serie_inventario(dias)

    def bulk_eliminar_productos(self, ids: list[int], usuario: str = "system") -> int:
        return self.product_repo.bulk_eliminar_productos(ids, usuario)

    def bulk_actualizar_categoria(
        self, ids: list[int], categoria: str, usuario: str = "system"
    ) -> int:
        return self.product_repo.bulk_actualizar_categoria(ids, categoria, usuario)

    def bulk_exportar_productos(self, ids: list[int]) -> list[dict]:
        return self.product_repo.bulk_exportar_productos(ids)

    def obtener_productos_stock_bajo(self) -> list[dict]:
        return self.product_repo.obtener_productos_stock_bajo()

    # ============ User/RBAC methods → self.user_repo ============

    def crear_usuario(self, username, password_hash, nombre, rol, usuario="system") -> int:
        return self.user_repo.crear_usuario(username, password_hash, nombre, rol, usuario)

    def obtener_usuarios(self) -> list[dict]:
        return self.user_repo.obtener_usuarios()

    def obtener_usuario_por_username(self, username) -> dict | None:
        return self.user_repo.obtener_usuario_por_username(username)

    def obtener_permisos_catalogo(self) -> list[dict]:
        return self.user_repo.obtener_permisos_catalogo()

    def obtener_roles(self) -> list[dict]:
        return self.user_repo.obtener_roles()

    def obtener_rol_por_nombre(self, nombre: str) -> dict | None:
        return self.user_repo.obtener_rol_por_nombre(nombre)

    def obtener_permisos_de_rol(self, rol_id: int) -> list[str]:
        return self.user_repo.obtener_permisos_de_rol(rol_id)

    def obtener_roles_de_usuario(self, usuario_id: int) -> list[dict]:
        return self.user_repo.obtener_roles_de_usuario(usuario_id)

    def obtener_permisos_de_usuario(self, usuario_id: int) -> list[str]:
        return self.user_repo.obtener_permisos_de_usuario(usuario_id)

    def asignar_rol_a_usuario(
        self, usuario_id: int, rol_id: int, usuario_actor: str = "system"
    ) -> bool:
        return self.user_repo.asignar_rol_a_usuario(usuario_id, rol_id, usuario_actor)

    def actualizar_tema_usuario(self, usuario_id: int, tema: str) -> None:
        return self.user_repo.actualizar_tema_usuario(usuario_id, tema)

    def obtener_permisos_extra(self, usuario_id: int) -> list[str]:
        return self.user_repo.obtener_permisos_extra(usuario_id)

    def agregar_permiso_extra(
        self, usuario_id: int, permiso_clave: str, usuario_actor: str = "system"
    ) -> bool:
        return self.user_repo.agregar_permiso_extra(usuario_id, permiso_clave, usuario_actor)

    def quitar_permiso_extra(
        self, usuario_id: int, permiso_clave: str, usuario_actor: str = "system"
    ) -> bool:
        return self.user_repo.quitar_permiso_extra(usuario_id, permiso_clave, usuario_actor)

    def obtener_usuario_por_username_full(self, username: str) -> dict | None:
        return self.user_repo.obtener_usuario_por_username_full(username)

    # ============ Client/Sales methods → self.sale_repo ============

    def crear_cliente(self, nombre, telefono="", email="", direccion="", usuario="system") -> int:
        return self.sale_repo.crear_cliente(nombre, telefono, email, direccion, usuario)

    def obtener_clientes(self) -> list[dict]:
        return self.sale_repo.obtener_clientes()

    def obtener_cliente_por_id(self, cliente_id: int) -> dict | None:
        return self.sale_repo.obtener_cliente_por_id(cliente_id)

    def actualizar_cliente(
        self, cliente_id, nombre, telefono="", email="", direccion="", usuario="system"
    ) -> int:
        return self.sale_repo.actualizar_cliente(
            cliente_id, nombre, telefono, email, direccion, usuario
        )

    def eliminar_cliente(self, cliente_id: int, usuario="system") -> None:
        return self.sale_repo.eliminar_cliente(cliente_id, usuario)

    def crear_venta(
        self,
        cliente_id,
        total,
        items: list[dict],
        metodo_pago="efectivo",
        referencia="",
        usuario="system",
    ) -> int:
        return self.sale_repo.crear_venta(
            cliente_id, total, items, metodo_pago, referencia, usuario
        )

    def obtener_ventas(self, limit=100) -> list[dict]:
        return self.sale_repo.obtener_ventas(limit)

    def obtener_venta_por_id(self, venta_id: int) -> dict | None:
        return self.sale_repo.obtener_venta_por_id(venta_id)

    def cancelar_venta(self, venta_id: int, usuario="system") -> None:
        return self.sale_repo.cancelar_venta(venta_id, usuario)

    def obtener_ventas_estadisticas(self) -> dict:
        return self.sale_repo.obtener_ventas_estadisticas()

    # ============ Config/Backup methods → self.config_repo ============

    def obtener_config(self, clave: str, default: str = "") -> str:
        return self.config_repo.obtener_config(clave, default)

    def guardar_config(self, clave: str, valor: str) -> None:
        return self.config_repo.guardar_config(clave, valor)

    def registrar_backup(
        self, ruta: str, tamano: int, tipo: str = "manual", usuario: str = "system"
    ) -> None:
        return self.config_repo.registrar_backup(ruta, tamano, tipo, usuario)

    def obtener_backups(self, limit=50) -> list[dict]:
        return self.config_repo.obtener_backups(limit)

    def eliminar_backup(self, backup_id: int) -> None:
        return self.config_repo.eliminar_backup(backup_id)

    # ============ Warehouse/Inventory methods → self.inventory_repo ============

    def crear_almacen(self, nombre: str, ubicacion: str = "", usuario: str = "system") -> int:
        return self.inventory_repo.crear_almacen(nombre, ubicacion, usuario)

    def obtener_almacenes(self) -> list[dict]:
        return self.inventory_repo.obtener_almacenes()

    def obtener_almacen_por_id(self, almacen_id: int) -> dict | None:
        return self.inventory_repo.obtener_almacen_por_id(almacen_id)

    def actualizar_almacen(
        self,
        almacen_id: int,
        nombre: str | None = None,
        ubicacion: str | None = None,
        usuario: str = "system",
    ) -> None:
        return self.inventory_repo.actualizar_almacen(almacen_id, nombre, ubicacion, usuario)

    def eliminar_almacen(self, almacen_id: int, usuario: str = "system") -> None:
        return self.inventory_repo.eliminar_almacen(almacen_id, usuario)

    def obtener_inventario_almacen(self, almacen_id: int) -> list[dict]:
        return self.inventory_repo.obtener_inventario_almacen(almacen_id)

    def ajustar_stock_almacen(
        self, producto_id: int, almacen_id: int, cantidad: int, usuario: str = "system"
    ) -> int:
        return self.inventory_repo.ajustar_stock_almacen(producto_id, almacen_id, cantidad, usuario)

    def obtener_todo_stock_almacenes(self) -> list[dict]:
        return self.inventory_repo.obtener_todo_stock_almacenes()

    # ============ Audit (stays on DatabaseManager, reads audit table) ============

    def obtener_auditoria(self, limit=100) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM auditoria ORDER BY creado_en DESC LIMIT ?", (limit,)
            )
            return [dict(r) for r in cursor.fetchall()]
