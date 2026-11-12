-- Esquema de base de datos del Sistema de Gestión para Club Valle Alto (SQLite)
-- Fechas: texto ISO (YYYY-MM-DD). Horas: 'HH:MM'. Fecha-hora: 'YYYY-MM-DD HH:MM:SS'.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS config_club (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS tipos_membresia (
    tipo TEXT PRIMARY KEY CHECK (tipo IN ('individual','familiar','corporativa','honoraria')),
    cuota_mensual REAL NOT NULL DEFAULT 0 CHECK (cuota_mensual >= 0),
    limite_invitados_mes INTEGER NOT NULL DEFAULT 0 CHECK (limite_invitados_mes >= 0),
    max_beneficiarios INTEGER NOT NULL DEFAULT 0 CHECK (max_beneficiarios >= 0),
    autoservicio INTEGER NOT NULL DEFAULT 1   -- 1: el socio puede solicitarla; 0: solo la crea el personal
);

CREATE TABLE IF NOT EXISTS socios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    cedula TEXT NOT NULL UNIQUE,
    correo TEXT NOT NULL UNIQUE,
    telefono TEXT NOT NULL,
    direccion TEXT NOT NULL,
    fecha_nacimiento TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo','suspendido','desactivado')),
    intentos_fallidos INTEGER NOT NULL DEFAULT 0,
    bloqueado_hasta TEXT,
    debe_cambiar_password INTEGER NOT NULL DEFAULT 0,
    creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    socio_id INTEGER NOT NULL REFERENCES socios(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expira_en TEXT NOT NULL,
    usado INTEGER NOT NULL DEFAULT 0,
    creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    cedula TEXT NOT NULL UNIQUE,
    correo TEXT NOT NULL UNIQUE,
    rol TEXT NOT NULL CHECK (rol IN ('general','instalaciones','cobros')),
    password_hash TEXT NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1,
    intentos_fallidos INTEGER NOT NULL DEFAULT 0,
    bloqueado_hasta TEXT,
    creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS membresias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    socio_id INTEGER NOT NULL REFERENCES socios(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL REFERENCES tipos_membresia(tipo),
    fecha_inscripcion TEXT NOT NULL,
    fecha_renovacion TEXT NOT NULL,
    cuota REAL NOT NULL CHECK (cuota >= 0),
    estado TEXT NOT NULL DEFAULT 'activa' CHECK (estado IN ('activa','suspendida','vencida','baja'))
);
-- Un socio solo puede tener una membresía vigente (no dada de baja) a la vez.
CREATE UNIQUE INDEX IF NOT EXISTS ux_membresia_vigente
    ON membresias(socio_id) WHERE estado <> 'baja';

CREATE TABLE IF NOT EXISTS membresia_historial (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    membresia_id INTEGER NOT NULL REFERENCES membresias(id) ON DELETE CASCADE,
    estado_anterior TEXT,
    estado_nuevo TEXT NOT NULL,
    motivo TEXT,
    actor TEXT NOT NULL,           -- 'socio:<id>', 'admin:<id>' o 'sistema'
    fecha TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS beneficiarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    membresia_id INTEGER NOT NULL REFERENCES membresias(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    cedula TEXT NOT NULL,
    parentesco TEXT NOT NULL,
    fecha_nacimiento TEXT NOT NULL,
    UNIQUE (membresia_id, cedula)
);

CREATE TABLE IF NOT EXISTS instalaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL CHECK (tipo IN ('golf','tenis','piscina','salon')),
    descripcion TEXT NOT NULL DEFAULT '',
    hora_apertura TEXT NOT NULL,
    hora_cierre TEXT NOT NULL,
    aforo_max INTEGER NOT NULL CHECK (aforo_max > 0),
    -- exclusiva: una reserva por franja. compartida: se suman personas hasta el aforo.
    modo TEXT NOT NULL DEFAULT 'exclusiva' CHECK (modo IN ('exclusiva','compartida')),
    activa INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS servicios_adicionales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instalacion_id INTEGER NOT NULL REFERENCES instalaciones(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    costo REAL NOT NULL DEFAULT 0 CHECK (costo >= 0),
    activo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS bloqueos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instalacion_id INTEGER NOT NULL REFERENCES instalaciones(id) ON DELETE CASCADE,
    fecha TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    hora_fin TEXT NOT NULL,
    motivo TEXT NOT NULL,
    admin_id INTEGER REFERENCES admins(id)
);

CREATE TABLE IF NOT EXISTS reservas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    socio_id INTEGER NOT NULL REFERENCES socios(id) ON DELETE CASCADE,
    instalacion_id INTEGER NOT NULL REFERENCES instalaciones(id),
    fecha TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    hora_fin TEXT NOT NULL,
    personas INTEGER NOT NULL CHECK (personas > 0),
    estado TEXT NOT NULL DEFAULT 'confirmada' CHECK (estado IN ('pendiente','confirmada','cancelada','finalizada')),
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_reservas_inst_fecha ON reservas(instalacion_id, fecha);
CREATE INDEX IF NOT EXISTS ix_reservas_socio ON reservas(socio_id);

CREATE TABLE IF NOT EXISTS reserva_servicios (
    reserva_id INTEGER NOT NULL REFERENCES reservas(id) ON DELETE CASCADE,
    servicio_id INTEGER NOT NULL REFERENCES servicios_adicionales(id),
    costo REAL NOT NULL,
    PRIMARY KEY (reserva_id, servicio_id)
);

CREATE TABLE IF NOT EXISTS invitados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    socio_id INTEGER NOT NULL REFERENCES socios(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    cedula TEXT NOT NULL,
    fecha_visita TEXT NOT NULL,
    instalacion_id INTEGER NOT NULL REFERENCES instalaciones(id),
    relacion TEXT NOT NULL CHECK (relacion IN ('familiar','amigo','otro')),
    creado_en TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_invitados_fecha ON invitados(fecha_visita);

CREATE TABLE IF NOT EXISTS cargos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    socio_id INTEGER NOT NULL REFERENCES socios(id) ON DELETE CASCADE,
    periodo TEXT NOT NULL,                       -- 'YYYY-MM'
    tipo TEXT NOT NULL CHECK (tipo IN ('cuota','servicio')),
    concepto TEXT NOT NULL,
    monto REAL NOT NULL CHECK (monto >= 0),
    fecha_limite TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','pagado','anulado')),
    membresia_id INTEGER REFERENCES membresias(id),
    reserva_id INTEGER REFERENCES reservas(id),
    servicio_id INTEGER REFERENCES servicios_adicionales(id),
    fecha_pago TEXT,
    registrado_por INTEGER REFERENCES admins(id),
    recordatorio_enviado INTEGER NOT NULL DEFAULT 0,
    vencido_notificado INTEGER NOT NULL DEFAULT 0
);
-- Evita duplicar la cuota de un periodo y el cargo de un servicio por reserva.
CREATE UNIQUE INDEX IF NOT EXISTS ux_cargo_cuota ON cargos(membresia_id, periodo) WHERE tipo = 'cuota';
CREATE UNIQUE INDEX IF NOT EXISTS ux_cargo_servicio ON cargos(reserva_id, servicio_id) WHERE tipo = 'servicio';
CREATE INDEX IF NOT EXISTS ix_cargos_socio_periodo ON cargos(socio_id, periodo);

CREATE TABLE IF NOT EXISTS estados_cuenta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    socio_id INTEGER NOT NULL REFERENCES socios(id) ON DELETE CASCADE,
    periodo TEXT NOT NULL,
    generado_en TEXT NOT NULL,
    UNIQUE (socio_id, periodo)
);

CREATE TABLE IF NOT EXISTS plantillas_notificacion (
    codigo TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    asunto TEXT NOT NULL,
    cuerpo TEXT NOT NULL,
    activa INTEGER NOT NULL DEFAULT 1,
    variables TEXT NOT NULL DEFAULT '',
    actualizado_en TEXT
);

CREATE TABLE IF NOT EXISTS notificaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    socio_id INTEGER REFERENCES socios(id) ON DELETE SET NULL,
    codigo TEXT NOT NULL,
    destinatario TEXT NOT NULL,
    asunto TEXT NOT NULL,
    cuerpo TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('enviado','simulado','error','omitido')),
    detalle TEXT,
    creado_en TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_notif_socio ON notificaciones(socio_id, creado_en);
