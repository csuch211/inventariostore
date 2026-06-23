"""V11: Create CRM tables for customer relationship management.

Tables: contactos, oportunidades, actividades_seguimiento, campanas, notas
"""


def run(db):
    """Create CRM tables if they don't exist."""
    try:
        with db._get_connection() as conn:
            # Contacts (extends clientes with CRM data)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS contactos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id INTEGER,
                    nombre TEXT NOT NULL,
                    apellido TEXT NOT NULL,
                    email TEXT,
                    telefono TEXT,
                    cargo TEXT,
                    empresa TEXT,
                    fuente TEXT DEFAULT 'directo',
                    estado TEXT DEFAULT 'activo',
                    notas TEXT,
                    creado_en TEXT NOT NULL,
                    creado_por TEXT,
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
                )
            """)

            # Opportunities/deals
            conn.execute("""
                CREATE TABLE IF NOT EXISTS oportunidades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contacto_id INTEGER NOT NULL,
                    titulo TEXT NOT NULL,
                    monto REAL DEFAULT 0,
                    estado TEXT DEFAULT 'abierta',
                    prioridad TEXT DEFAULT 'media',
                    fecha_cierre_estimada TEXT,
                    fecha_cierre_real TEXT,
                    notas TEXT,
                    creado_en TEXT NOT NULL,
                    creado_por TEXT,
                    FOREIGN KEY (contacto_id) REFERENCES contactos(id)
                )
            """)

            # Follow-up activities
            conn.execute("""
                CREATE TABLE IF NOT EXISTS actividades_seguimiento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contacto_id INTEGER NOT NULL,
                    oportunidad_id INTEGER,
                    tipo TEXT NOT NULL,
                    titulo TEXT NOT NULL,
                    descripcion TEXT,
                    fecha_programada TEXT,
                    fecha_completada TEXT,
                    estado TEXT DEFAULT 'pendiente',
                    resultado TEXT,
                    creado_en TEXT NOT NULL,
                    creado_por TEXT,
                    FOREIGN KEY (contacto_id) REFERENCES contactos(id),
                    FOREIGN KEY (oportunidad_id) REFERENCES oportunidades(id)
                )
            """)

            # Campaigns
            conn.execute("""
                CREATE TABLE IF NOT EXISTS campanas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    tipo TEXT DEFAULT 'email',
                    descripcion TEXT,
                    fecha_inicio TEXT,
                    fecha_fin TEXT,
                    estado TEXT DEFAULT 'borrador',
                    presupuesto REAL DEFAULT 0,
                    gasto REAL DEFAULT 0,
                    creado_en TEXT NOT NULL,
                    creado_por TEXT
                )
            """)

            # Campaign members
            conn.execute("""
                CREATE TABLE IF NOT EXISTS campana_contactos (
                    campana_id INTEGER NOT NULL,
                    contacto_id INTEGER NOT NULL,
                    estado TEXT DEFAULT 'pendiente',
                    PRIMARY KEY (campana_id, contacto_id),
                    FOREIGN KEY (campana_id) REFERENCES campanas(id) ON DELETE CASCADE,
                    FOREIGN KEY (contacto_id) REFERENCES contactos(id) ON DELETE CASCADE
                )
            """)

            # Notes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notas_crm (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contacto_id INTEGER,
                    oportunidad_id INTEGER,
                    campana_id INTEGER,
                    titulo TEXT NOT NULL,
                    contenido TEXT NOT NULL,
                    tipo TEXT DEFAULT 'general',
                    creado_en TEXT NOT NULL,
                    creado_por TEXT,
                    FOREIGN KEY (contacto_id) REFERENCES contactos(id),
                    FOREIGN KEY (oportunidad_id) REFERENCES oportunidades(id),
                    FOREIGN KEY (campana_id) REFERENCES campanas(id)
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_contactos_cliente ON contactos(cliente_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_contactos_empresa ON contactos(empresa)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_contactos_estado ON contactos(estado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_oportunidades_contacto ON oportunidades(contacto_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_oportunidades_estado ON oportunidades(estado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_oportunidades_cierre ON oportunidades(fecha_cierre_estimada)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actividades_contacto ON actividades_seguimiento(contacto_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actividades_estado ON actividades_seguimiento(estado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_campanas_estado ON campanas(estado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notas_contacto ON notas_crm(contacto_id)")

            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V11 failed: {e}")
