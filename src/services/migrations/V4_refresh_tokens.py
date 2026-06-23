"""V4: Create refresh_tokens table for JWT refresh token storage."""


def run(db):
    """Create the refresh_tokens table if it doesn't exist."""
    try:
        with db._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jti TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user
                ON refresh_tokens(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires
                ON refresh_tokens(expires_at)
            """)
            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V4 failed: {e}")
