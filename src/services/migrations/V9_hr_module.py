"""V9: Create HR tables for human resources module.

Tables: empleados, nomina, asistencia, vacaciones, evaluaciones
"""


def run(db):
    """Create HR tables if they don't exist."""
    try:
        with db._get_connection() as conn:
            # Employees table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS empleados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_empleado TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL,
                    apellido TEXT NOT NULL,
                    email TEXT,
                    telefono TEXT,
                    fecha_nacimiento TEXT,
                    fecha_ingreso TEXT NOT NULL,
                    puesto TEXT NOT NULL,
                    departamento TEXT NOT NULL,
                    salario_base REAL NOT NULL DEFAULT 0,
                    estado TEXT DEFAULT 'activo',
                    foto_url TEXT,
                    notas TEXT,
                    creado_en TEXT NOT NULL,
                    creado_por TEXT
                )
            """)

            # Payroll table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nomina (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    empleado_id INTEGER NOT NULL,
                    periodo_inicio TEXT NOT NULL,
                    periodo_fin TEXT NOT NULL,
                    salario_bruto REAL NOT NULL DEFAULT 0,
                    deducciones REAL DEFAULT 0,
                    bonificaciones REAL DEFAULT 0,
                    salario_neto REAL NOT NULL DEFAULT 0,
                    estado TEXT DEFAULT 'pendiente',
                    metodo_pago TEXT DEFAULT 'transferencia',
                    notas TEXT,
                    creado_en TEXT NOT NULL,
                    creado_por TEXT,
                    FOREIGN KEY (empleado_id) REFERENCES empleados(id)
                )
            """)

            # Attendance table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS asistencia (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    empleado_id INTEGER NOT NULL,
                    fecha TEXT NOT NULL,
                    hora_entrada TEXT,
                    hora_salida TEXT,
                    horas_trabajadas REAL DEFAULT 0,
                    horas_extras REAL DEFAULT 0,
                    estado TEXT DEFAULT 'presente',
                    notas TEXT,
                    FOREIGN KEY (empleado_id) REFERENCES empleados(id)
                )
            """)

            # Vacation table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vacaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    empleado_id INTEGER NOT NULL,
                    fecha_inicio TEXT NOT NULL,
                    fecha_fin TEXT NOT NULL,
                    dias INTEGER NOT NULL,
                    motivo TEXT,
                    estado TEXT DEFAULT 'pendiente',
                    aprobado_por TEXT,
                    notas TEXT,
                    FOREIGN KEY (empleado_id) REFERENCES empleados(id)
                )
            """)

            # Evaluations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evaluaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    empleado_id INTEGER NOT NULL,
                    evaluador TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    periodo TEXT,
                    puntuacion REAL DEFAULT 0,
                    fortalezas TEXT,
                    areas_mejora TEXT,
                    objetivos TEXT,
                    notas TEXT,
                    FOREIGN KEY (empleado_id) REFERENCES empleados(id)
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_empleados_numero ON empleados(numero_empleado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_empleados_departamento ON empleados(departamento)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_empleados_estado ON empleados(estado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nomina_empleado ON nomina(empleado_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nomina_periodo ON nomina(periodo_inicio, periodo_fin)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_asistencia_empleado ON asistencia(empleado_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_asistencia_fecha ON asistencia(fecha)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vacaciones_empleado ON vacaciones(empleado_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vacaciones_estado ON vacaciones(estado)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evaluaciones_empleado ON evaluaciones(empleado_id)")

            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Migration V9 failed: {e}")
