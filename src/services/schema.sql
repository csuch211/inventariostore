-- Schema initialization for InventarioStore
-- Executed by DatabaseManager._init_database()

-- Core tables

CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    cantidad INTEGER DEFAULT 0,
    precio REAL DEFAULT 0.0,
    descripcion TEXT,
    categoria TEXT,
    activo INTEGER DEFAULT 1,
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL,
    creado_por TEXT,
    actualizado_por TEXT
);

CREATE TABLE IF NOT EXISTS historial_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    cantidad_anterior INTEGER,
    cantidad_nueva INTEGER,
    tipo_movimiento TEXT,
    razon TEXT,
    creado_en TEXT NOT NULL,
    usuario TEXT,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

-- Audit (conditional: only if ENABLE_AUDIT_LOG)
-- CREATE TABLE IF NOT EXISTS auditoria (...)

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nombre TEXT NOT NULL,
    rol TEXT NOT NULL DEFAULT 'operador',
    activo INTEGER DEFAULT 1,
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    permisos TEXT,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    descripcion TEXT,
    activo INTEGER DEFAULT 1,
    creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    contacto TEXT,
    telefono TEXT,
    email TEXT,
    direccion TEXT,
    activo INTEGER DEFAULT 1,
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ordenes_compra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_id INTEGER,
    producto_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    estado TEXT DEFAULT 'pendiente',
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL,
    creado_por TEXT,
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

CREATE TABLE IF NOT EXISTS imagenes_producto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    ruta TEXT NOT NULL,
    tipo TEXT DEFAULT 'imagen',
    creado_en TEXT NOT NULL,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

-- RBAC

CREATE TABLE IF NOT EXISTS permisos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clave TEXT UNIQUE NOT NULL,
    modulo TEXT NOT NULL,
    accion TEXT NOT NULL,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS rol_permisos (
    rol_id INTEGER NOT NULL,
    permiso_id INTEGER NOT NULL,
    PRIMARY KEY (rol_id, permiso_id),
    FOREIGN KEY (rol_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permiso_id) REFERENCES permisos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS usuario_permisos_extra (
    usuario_id INTEGER NOT NULL,
    permiso_id INTEGER NOT NULL,
    PRIMARY KEY (usuario_id, permiso_id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (permiso_id) REFERENCES permisos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS usuario_roles (
    usuario_id INTEGER NOT NULL,
    rol_id INTEGER NOT NULL,
    PRIMARY KEY (usuario_id, rol_id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (rol_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- Sales

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    telefono TEXT,
    email TEXT,
    direccion TEXT,
    activo INTEGER DEFAULT 1,
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER,
    total REAL NOT NULL DEFAULT 0,
    estado TEXT DEFAULT 'completada',
    creado_en TEXT NOT NULL,
    creado_por TEXT,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

CREATE TABLE IF NOT EXISTS ventas_detalle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario REAL NOT NULL,
    subtotal REAL NOT NULL,
    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

CREATE TABLE IF NOT EXISTS pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL,
    metodo TEXT NOT NULL DEFAULT 'efectivo',
    monto REAL NOT NULL,
    referencia TEXT,
    creado_en TEXT NOT NULL,
    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE
);

-- Config & backups

CREATE TABLE IF NOT EXISTS configuracion (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ruta TEXT NOT NULL,
    tamano INTEGER DEFAULT 0,
    tipo TEXT DEFAULT 'manual',
    creado_en TEXT NOT NULL,
    creado_por TEXT
);

-- Warehouses

CREATE TABLE IF NOT EXISTS almacenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    ubicacion TEXT,
    activo INTEGER DEFAULT 1,
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventario_almacen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    almacen_id INTEGER NOT NULL,
    cantidad INTEGER DEFAULT 0,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
    FOREIGN KEY (almacen_id) REFERENCES almacenes(id) ON DELETE CASCADE,
    UNIQUE(producto_id, almacen_id)
);

-- Fase 1: Devoluciones

CREATE TABLE IF NOT EXISTS devoluciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario REAL NOT NULL,
    subtotal REAL NOT NULL,
    motivo TEXT,
    estado TEXT DEFAULT 'completada',
    creado_en TEXT NOT NULL,
    creado_por TEXT,
    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

-- Fase 1: Transferencias

CREATE TABLE IF NOT EXISTS transferencias_almacen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    almacen_origen_id INTEGER NOT NULL,
    almacen_destino_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    estado TEXT DEFAULT 'completada',
    nota TEXT,
    creado_en TEXT NOT NULL,
    creado_por TEXT,
    FOREIGN KEY (almacen_origen_id) REFERENCES almacenes(id),
    FOREIGN KEY (almacen_destino_id) REFERENCES almacenes(id),
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

-- Fase 1: Conteo fisico

CREATE TABLE IF NOT EXISTS sesiones_conteo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    almacen_id INTEGER,
    estado TEXT DEFAULT 'en_progreso',
    notas TEXT,
    creado_en TEXT NOT NULL,
    cerrado_en TEXT,
    creado_por TEXT,
    FOREIGN KEY (almacen_id) REFERENCES almacenes(id)
);

CREATE TABLE IF NOT EXISTS conteo_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad_sistema REAL NOT NULL DEFAULT 0,
    cantidad_contada REAL,
    diferencia REAL,
    notas TEXT,
    contado_en TEXT,
    contado_por TEXT,
    FOREIGN KEY (sesion_id) REFERENCES sesiones_conteo(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

-- Fase 1: Lotes

CREATE TABLE IF NOT EXISTS lotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    codigo_lote TEXT NOT NULL,
    serie TEXT,
    cantidad_inicial INTEGER NOT NULL DEFAULT 0,
    cantidad_actual INTEGER NOT NULL DEFAULT 0,
    fecha_fabricacion TEXT,
    fecha_vencimiento TEXT,
    ubicacion TEXT,
    proveedor_id INTEGER,
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),
    UNIQUE(producto_id, codigo_lote)
);

-- Fase 1: Listas de precios

CREATE TABLE IF NOT EXISTS listas_precios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    descripcion TEXT,
    activo INTEGER DEFAULT 1,
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS precios_producto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    lista_id INTEGER NOT NULL,
    precio REAL NOT NULL,
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
    FOREIGN KEY (lista_id) REFERENCES listas_precios(id) ON DELETE CASCADE,
    UNIQUE(producto_id, lista_id)
);

-- Fase 1: Impuestos

CREATE TABLE IF NOT EXISTS impuestos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    porcentaje REAL NOT NULL,
    tipo TEXT DEFAULT 'iva',
    activo INTEGER DEFAULT 1,
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);

-- Fase 1: Caja / Turnos POS

CREATE TABLE IF NOT EXISTS turnos_caja (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT NOT NULL,
    monto_inicial REAL NOT NULL DEFAULT 0,
    monto_final REAL,
    monto_esperado REAL,
    diferencia REAL,
    estado TEXT DEFAULT 'abierto',
    notas_apertura TEXT,
    notas_cierre TEXT,
    abierto_en TEXT NOT NULL,
    cerrado_en TEXT
);

CREATE TABLE IF NOT EXISTS movimientos_caja (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turno_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    monto REAL NOT NULL,
    concepto TEXT,
    referencia TEXT,
    creado_en TEXT NOT NULL,
    FOREIGN KEY (turno_id) REFERENCES turnos_caja(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ventas_turno (
    turno_id INTEGER NOT NULL,
    venta_id INTEGER NOT NULL,
    PRIMARY KEY (turno_id, venta_id),
    FOREIGN KEY (turno_id) REFERENCES turnos_caja(id) ON DELETE CASCADE,
    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE
);

-- Fase 3: Variantes

CREATE TABLE IF NOT EXISTS variantes_producto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    sku TEXT UNIQUE NOT NULL,
    atributos TEXT NOT NULL,
    cantidad INTEGER DEFAULT 0,
    precio_override REAL,
    activo INTEGER DEFAULT 1,
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_variantes_producto ON variantes_producto(producto_id);

-- Fase 3: Plantillas de reporte

CREATE TABLE IF NOT EXISTS plantillas_reporte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    modulo TEXT NOT NULL DEFAULT 'productos',
    columnas TEXT NOT NULL,
    filtros TEXT,
    agrupacion TEXT,
    ordenado_por TEXT,
    creado_por TEXT,
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);

-- Fase 3: Jobs push

CREATE TABLE IF NOT EXISTS jobs_push (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    destinatario TEXT NOT NULL,
    asunto TEXT NOT NULL,
    cuerpo TEXT NOT NULL,
    estado TEXT DEFAULT 'pendiente',
    intentos INTEGER DEFAULT 0,
    ultimo_error TEXT,
    creado_en TEXT NOT NULL,
    enviado_en TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_estado ON jobs_push(estado, creado_en);

-- Fase 3: Preferencias de usuario

CREATE TABLE IF NOT EXISTS usuario_prefs (
    usuario TEXT PRIMARY KEY,
    idioma TEXT NOT NULL DEFAULT 'es',
    tema TEXT DEFAULT 'light',
    actualizado_en TEXT NOT NULL
);

-- Performance indexes

CREATE INDEX IF NOT EXISTS idx_productos_codigo ON productos(codigo);
CREATE INDEX IF NOT EXISTS idx_productos_categoria ON productos(categoria);
CREATE INDEX IF NOT EXISTS idx_productos_activo ON productos(activo);
CREATE INDEX IF NOT EXISTS idx_historial_stock_producto ON historial_stock(producto_id);
CREATE INDEX IF NOT EXISTS idx_historial_stock_fecha ON historial_stock(producto_id, creado_en);
CREATE INDEX IF NOT EXISTS idx_ventas_creado_en ON ventas(creado_en);
CREATE INDEX IF NOT EXISTS idx_ventas_estado ON ventas(estado);
CREATE INDEX IF NOT EXISTS idx_ventas_detalle_venta ON ventas_detalle(venta_id);
CREATE INDEX IF NOT EXISTS idx_clientes_activo ON clientes(activo);
CREATE INDEX IF NOT EXISTS idx_ordenes_estado ON ordenes_compra(estado);
-- Note: idx_auditoria_creado_en is created conditionally in database.py
-- Note: HR indexes (empleados, nomina, asistencia, vacaciones) are created by migration V9
-- Note: Document indexes (tags_documento) are created by migration V12
