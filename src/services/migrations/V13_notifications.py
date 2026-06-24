"""V13: Create notifications module tables.

Tables: notificaciones, plantillas_notificacion, canales_notificacion, preferencias_notificacion
"""


def run(db):
    """Create notifications module tables if they don't exist."""
    try:
        with db._get_connection() as conn:
            # Notification templates
            conn.execute("""
                CREATE TABLE IF NOT EXISTS plantillas_notificacion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL,
                    asunto TEXT NOT NULL,
                    cuerpo TEXT NOT NULL,
                    tipo TEXT DEFAULT 'email',
                    variables TEXT,
                    activo INTEGER DEFAULT 1,
                    creado_en TEXT NOT NULL,
                    creado_por TEXT
                )
            """)

            # Notification channels
            conn.execute("""
                CREATE TABLE IF NOT EXISTS canales_notificacion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL,
                    tipo TEXT NOT NULL,
                    configuracion TEXT,
                    activo INTEGER DEFAULT 1,
                    creado_en TEXT NOT NULL
                )
            """)

            # Notifications log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notificaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    mensaje TEXT NOT NULL,
                    tipo TEXT DEFAULT 'info',
                    canal TEXT DEFAULT 'sistema',
                    destinatario TEXT,
                    estado TEXT DEFAULT 'pendiente',
                    enviado_en TEXT,
                    leido_en TEXT,
                    referencia_tipo TEXT,
                    referencia_id INTEGER,
                    creado_en TEXT NOT NULL,
                    creado_por TEXT
                )
            """)

            # User notification preferences
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preferencias_notificacion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL UNIQUE,
                    email_enabled INTEGER DEFAULT 1,
                    push_enabled INTEGER DEFAULT 1,
                    stock_alertas INTEGER DEFAULT 1,
                    ventas_notif INTEGER DEFAULT 1,
                    sistema_notif INTEGER DEFAULT 1,
                    frecuencia TEXT DEFAULT 'inmediato',
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notificaciones_estado ON notificaciones(estado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notificaciones_destinatario ON notificaciones(destinatario)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notificaciones_tipo ON notificaciones(tipo)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notificaciones_creado ON notificaciones(creado_en)")

            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V13 failed: {e}")
