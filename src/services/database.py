"""
Database manager: factory for repositories + schema initialization.

All repository proxies have been removed — access repos directly via
``db.product_repo``, ``db.sale_repo``, etc.
"""

import contextlib
import sqlite3
from datetime import datetime
from pathlib import Path

from config.settings import (
    DATABASE_FILE,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USER,
    DEFAULT_OPERATOR_PASSWORD,
    DEFAULT_OPERATOR_USER,
    ENABLE_AUDIT_LOG,
)
from services.auth import _LEGACY_SALT, _hash_with_salt
from services.migrator import upgrade as run_migrations
from services.permissions import (
    PERMISSIONS_BY_MODULE,
    ROLE_DEFAULT_PERMISSIONS,
    ROLE_DESCRIPTIONS,
)
from services.repository import (
    AccountingRepository,
    AutomationRepository,
    BaseRepository,
    CartRepository,
    ConfigRepository,
    CRMRepository,
    DocumentRepository,
    EmployeeRepository,
    HRRepository,
    InventoryRepository,
    InvoiceRepository,
    NotificationRepository,
    ProductRepository,
    PurchasingRepository,
    SaleRepository,
    SalesEnhancedRepository,
    StoreRepository,
    UserRepository,
)
from utils.exceptions import DatabaseException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class DatabaseManager:
    """Factory for repositories + schema initialization."""

    _local = BaseRepository._local

    def __init__(self, db_path: Path = DATABASE_FILE) -> None:
        self.db_path = db_path
        self.product_repo = ProductRepository(db_path)
        self.user_repo = UserRepository(db_path)
        self.sale_repo = SaleRepository(db_path)
        self.inventory_repo = InventoryRepository(db_path)
        self.config_repo = ConfigRepository(db_path)
        self.invoice_repo = InvoiceRepository(db_path)
        self.accounting_repo = AccountingRepository(db_path)
        self.employee_repo = EmployeeRepository(db_path)
        self.hr_repo = HRRepository(db_path)
        self.purchasing_repo = PurchasingRepository(db_path)
        self.crm_repo = CRMRepository(db_path)
        self.document_repo = DocumentRepository(db_path)
        self.notification_repo = NotificationRepository(db_path)
        self.sales_enhanced_repo = SalesEnhancedRepository(db_path)
        self.cart_repo = CartRepository(db_path)
        self.store_repo = StoreRepository(db_path)
        self.automation_repo = AutomationRepository(db_path)
        self._init_database()
        logger.info(f"Database initialized at {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection (reuses per-thread)."""
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
            logger.exception(f"Database connection error: {e}")
            raise DatabaseException(f"Connection failed: {e}")

    def _init_database(self):
        """Initialize database schema from schema.sql + conditional tables."""
        try:
            with self._get_connection() as conn:
                # Execute the main schema SQL
                schema_path = Path(__file__).parent / "schema.sql"
                conn.executescript(schema_path.read_text(encoding="utf-8"))

                # Conditional: audit table (only if enabled)
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
                    conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_auditoria_creado_en"
                        " ON auditoria(creado_en)"
                    )

                # Fix legacy roles schema if needed
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

                conn.commit()
                self.seed_rbac()
                self.migrar_schema()

                applied = run_migrations(self)
                if applied:
                    logger.info(f"Applied {applied} pending migration(s)")

                logger.info("Database schema initialized successfully")
        except sqlite3.Error as e:
            logger.exception(f"Error initializing database: {e}")
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

                # Assign default role to existing users
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
        """Add missing columns to existing tables (safe migration)."""
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
                with contextlib.suppress(sqlite3.OperationalError):
                    conn.execute("ALTER TABLE productos ADD COLUMN precio_costo REAL DEFAULT 0")
                with contextlib.suppress(sqlite3.OperationalError):
                    conn.execute("ALTER TABLE productos ADD COLUMN margen REAL DEFAULT 0")
                with contextlib.suppress(sqlite3.OperationalError):
                    conn.execute(
                        "ALTER TABLE productos ADD COLUMN impuesto_id INTEGER REFERENCES impuestos(id)"
                    )
                with contextlib.suppress(sqlite3.OperationalError):
                    conn.execute("ALTER TABLE productos ADD COLUMN sku TEXT")
                self._seed_default_users(conn)
                conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Schema migration error: {e}")

    def _seed_default_users(self, conn):
        """Ensure the default users exist in the usuarios table. Idempotent."""
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
            cursor2 = conn.execute("SELECT id FROM roles WHERE nombre = ?", (rol,))
            rrow = cursor2.fetchone()
            if rrow:
                conn.execute(
                    "INSERT OR IGNORE INTO usuario_roles (usuario_id, rol_id) VALUES (?, ?)",
                    (user_id, rrow["id"]),
                )
            logger.info(f"Seeded default user: {username} as {rol}")

    # ============ Audit ============

    def _audit_log(
        self,
        conn: sqlite3.Connection,
        accion: str,
        tabla: str,
        registro_id: int,
        usuario: str,
        detalles: str,
    ):
        """Internal audit logging — used by advanced_inventory_db.py and extended_features_db.py."""
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

    def obtener_auditoria(self, limit=100) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM auditoria ORDER BY creado_en DESC LIMIT ?", (limit,)
            )
            return [dict(r) for r in cursor.fetchall()]

    # ---- Backward compatibility: delegate unknown attrs to repos ----

    _repos: list  # type: ignore[assignment]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def _get_repos(self) -> list:
        return [
            self.product_repo, self.user_repo, self.sale_repo,
            self.inventory_repo, self.config_repo, self.invoice_repo,
            self.accounting_repo, self.employee_repo, self.hr_repo,
            self.purchasing_repo, self.crm_repo, self.document_repo,
            self.notification_repo, self.sales_enhanced_repo,
            self.cart_repo, self.store_repo, self.automation_repo,
        ]

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(f"'DatabaseManager' has no attribute '{name}'")
        for repo in self._get_repos():
            if hasattr(repo, name):
                return getattr(repo, name)
        raise AttributeError(f"'DatabaseManager' has no attribute '{name}'")
