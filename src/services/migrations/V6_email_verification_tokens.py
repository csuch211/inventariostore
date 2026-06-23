"""V6: Create email verification tokens table for new user registration."""


def run(db):
    """Create the email_verification_tokens table if it doesn't exist."""
    try:
        with db._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS email_verification_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_hash TEXT UNIQUE NOT NULL,
                    expires_at TEXT NOT NULL,
                    used INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_email_verification_user
                ON email_verification_tokens(user_id)
            """)
            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V6 failed: {e}")
