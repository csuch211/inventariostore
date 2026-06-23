"""V12: Create document management tables.

Tables: documentos, categorias_documentos, versiones_documento, permisos_documento, tags_documento
"""


def run(db):
    """Create document management tables if they don't exist."""
    try:
        with db._get_connection() as conn:
            # Document categories
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categorias_documentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL,
                    descripcion TEXT,
                    icono TEXT DEFAULT 'folder',
                    color TEXT DEFAULT '#2563EB',
                    padre_id INTEGER,
                    activo INTEGER DEFAULT 1,
                    creado_en TEXT NOT NULL,
                    FOREIGN KEY (padre_id) REFERENCES categorias_documentos(id)
                )
            """)

            # Documents table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    descripcion TEXT,
                    categoria_id INTEGER,
                    tipo TEXT NOT NULL DEFAULT 'documento',
                    archivo_nombre TEXT,
                    archivo_ruta TEXT,
                    archivo_tamaño INTEGER DEFAULT 0,
                    mime_type TEXT,
                    tags TEXT,
                    estado TEXT DEFAULT 'borrador',
                    visibilidad TEXT DEFAULT 'privado',
                    autor TEXT NOT NULL,
                    version_actual INTEGER DEFAULT 1,
                    creado_en TEXT NOT NULL,
                    actualizado_en TEXT NOT NULL,
                    FOREIGN KEY (categoria_id) REFERENCES categorias_documentos(id)
                )
            """)

            # Document versions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS versiones_documento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    documento_id INTEGER NOT NULL,
                    numero_version INTEGER NOT NULL,
                    archivo_nombre TEXT,
                    archivo_ruta TEXT,
                    archivo_tamaño INTEGER DEFAULT 0,
                    cambios TEXT,
                    autor TEXT NOT NULL,
                    creado_en TEXT NOT NULL,
                    FOREIGN KEY (documento_id) REFERENCES documentos(id) ON DELETE CASCADE
                )
            """)

            # Document permissions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS permisos_documento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    documento_id INTEGER NOT NULL,
                    usuario_id INTEGER,
                    rol TEXT,
                    puede_ver INTEGER DEFAULT 1,
                    puede_editar INTEGER DEFAULT 0,
                    puede_eliminar INTEGER DEFAULT 0,
                    FOREIGN KEY (documento_id) REFERENCES documentos(id) ON DELETE CASCADE,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
                )
            """)

            # Document tags
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tags_documento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    documento_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    FOREIGN KEY (documento_id) REFERENCES documentos(id) ON DELETE CASCADE
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documentos_categoria ON documentos(categoria_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documentos_tipo ON documentos(tipo)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documentos_estado ON documentos(estado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documentos_autor ON documentos(autor)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_versiones_documento ON versiones_documento(documento_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_permisos_documento ON permisos_documento(documento_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_documento ON tags_documento(documento_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags_documento(tag)")

            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V12 failed: {e}")
