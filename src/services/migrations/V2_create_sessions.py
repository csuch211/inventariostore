"""V2: Create sessions table for persistent session storage."""


def run(db):
    """Create the sessions table if it doesn't exist."""
    try:
        with db._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sesiones (
                    token TEXT PRIMARY KEY,
                    usuario_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    rol TEXT NOT NULL,
                    creado_en TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sesiones_expires
                ON sesiones(expires_at)
            """)
            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V2 failed: {e}")
