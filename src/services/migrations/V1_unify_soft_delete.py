"""V1: Add activo column to productos table for consistent soft-delete."""


def run(db):
    """Add activo column to productos table."""
    try:
        with db._get_connection() as conn:
            # Check if estado column exists
            cursor = conn.execute("PRAGMA table_info(productos)")
            columns = {row[1] for row in cursor.fetchall()}

            if "activo" not in columns:
                conn.execute("ALTER TABLE productos ADD COLUMN activo INTEGER DEFAULT 1")

            if "estado" in columns:
                # Sync activo from existing estado values
                conn.execute(
                    "UPDATE productos SET activo = 1 WHERE estado = 'activo' OR estado IS NULL"
                )
                conn.execute("UPDATE productos SET activo = 0 WHERE estado = 'inactivo'")

            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V1 failed: {e}")
