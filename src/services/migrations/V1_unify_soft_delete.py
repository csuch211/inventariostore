"""V1: Add activo column to productos table for consistent soft-delete."""


def run(db):
    """Add activo column to productos table."""
    try:
        with db._get_connection() as conn:
            # Add activo column if it doesn't exist
            try:
                conn.execute("ALTER TABLE productos ADD COLUMN activo INTEGER DEFAULT 1")
            except Exception:
                pass  # Column already exists

            # Sync activo from existing estado values
            conn.execute(
                "UPDATE productos SET activo = 1 WHERE estado = 'activo' OR estado IS NULL"
            )
            conn.execute("UPDATE productos SET activo = 0 WHERE estado = 'inactivo'")
            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V1 failed: {e}")
