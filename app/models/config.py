"""Reglas operativas configurables y catálogos iniciales.

IMPORTANTE: los valores por defecto son SUPUESTOS de trabajo. Según el diccionario de la WBS
(1.2.1) las reglas del club deben definirse y validarse con la Gerencia; por eso todas se
pueden modificar desde Administración > Reglas del club sin tocar el código.
"""
from app.db import ahora_txt, execute, get_db, one, query

CONFIG_DEFAULTS = {
    "moneda": ("₡", "Símbolo de moneda mostrado en montos"),
    "max_intentos_login": ("5", "Intentos fallidos de inicio de sesión antes de bloquear"),
    "minutos_bloqueo": ("15", "Minutos de bloqueo tras superar los intentos fallidos"),
    "dias_plazo_pago": ("15", "Días de plazo de pago desde la generación del estado de cuenta"),
    "dias_aviso_vencimiento": ("3", "Días de anticipación para el recordatorio de pago próximo a vencer"),
    "reserva_autoconfirmar": ("1", "1: la reserva del socio queda confirmada de inmediato; 0: queda pendiente hasta que el personal la confirme"),
    "dias_anticipacion_max": ("60", "Máximo de días de anticipación para reservar"),
    "dias_renovacion": ("365", "Duración (días) de una membresía antes de su fecha de renovación"),
}

TIPOS_DEFAULT = [
    # tipo, cuota, límite invitados/mes, máx. beneficiarios, autoservicio
    ("individual", 38000.0, 3, 0, 1),
    ("familiar", 45000.0, 5, 4, 1),
    ("corporativa", 90000.0, 10, 0, 1),
    ("honoraria", 0.0, 6, 0, 0),
]

INSTALACIONES_DEFAULT = [
    # nombre, tipo, descripción, apertura, cierre, aforo, modo
    ("Cancha de golf", "golf", "Campo de golf de 9 hoyos.", "06:00", "17:00", 4, "exclusiva"),
    ("Cancha de tenis", "tenis", "Cancha de tenis de polvo de ladrillo.", "06:00", "21:00", 4, "exclusiva"),
    ("Piscina", "piscina", "Piscina semiolímpica con área de descanso.", "08:00", "19:00", 60, "compartida"),
    ("Salón de eventos", "salon", "Salón para eventos sociales con cocina de apoyo.", "09:00", "23:00", 120, "exclusiva"),
]

SERVICIOS_DEFAULT = {
    "Cancha de golf": [("Alquiler de palos", 15000.0), ("Alquiler de carrito", 20000.0)],
    "Cancha de tenis": [("Alquiler de raquetas", 5000.0), ("Bolas nuevas", 4000.0)],
    "Piscina": [("Alquiler de sombrilla", 3000.0)],
    "Salón de eventos": [("Montaje de mobiliario", 50000.0), ("Equipo de sonido", 40000.0)],
}

PLANTILLAS_DEFAULT = {
    "registro_socio": (
        "Nuevo socio",
        "Bienvenido al Club Valle Alto",
        "Hola {nombre},\n\nSu cuenta en la plataforma del Club Valle Alto fue creada correctamente. "
        "Ya puede iniciar sesión con su correo electrónico ({correo}) para consultar su información, "
        "reservar instalaciones y revisar su estado de cuenta.\n\nClub Valle Alto",
        "nombre, correo",
    ),
    "reserva_confirmada": (
        "Reserva confirmada",
        "Reserva confirmada: {instalacion} el {fecha}",
        "Hola {nombre},\n\nSu reserva de {instalacion} quedó confirmada para el {fecha}, de {hora_inicio} a {hora_fin} "
        "({personas} persona(s)).\n\nClub Valle Alto",
        "nombre, instalacion, fecha, hora_inicio, hora_fin, personas",
    ),
    "reserva_modificada": (
        "Reserva modificada",
        "Su reserva de {instalacion} fue modificada",
        "Hola {nombre},\n\nSu reserva de {instalacion} fue modificada. Nuevo horario: {fecha}, de {hora_inicio} a "
        "{hora_fin} ({personas} persona(s)).\n\nClub Valle Alto",
        "nombre, instalacion, fecha, hora_inicio, hora_fin, personas",
    ),
    "reserva_cancelada": (
        "Reserva cancelada",
        "Su reserva de {instalacion} fue cancelada",
        "Hola {nombre},\n\nSu reserva de {instalacion} del {fecha}, de {hora_inicio} a {hora_fin}, fue cancelada.\n\nClub Valle Alto",
        "nombre, instalacion, fecha, hora_inicio, hora_fin",
    ),
    "estado_cuenta": (
        "Nuevo estado de cuenta",
        "Estado de cuenta {periodo}",
        "Hola {nombre},\n\nSe generó su estado de cuenta del periodo {periodo}. Total: {total}; pendiente de pago: {pendiente}. "
        "Puede consultarlo y descargar el PDF en {enlace}.\n\nClub Valle Alto",
        "nombre, periodo, total, pendiente, enlace",
    ),
    "recordatorio_pago": (
        "Pago próximo a vencer",
        "Recordatorio: pago por vencer el {fecha_limite}",
        "Hola {nombre},\n\nLe recordamos que el cargo «{concepto}» por {monto} vence el {fecha_limite}.\n\nClub Valle Alto",
        "nombre, concepto, monto, fecha_limite",
    ),
    "pago_vencido": (
        "Pago vencido",
        "Pago vencido: {concepto}",
        "Hola {nombre},\n\nEl cargo «{concepto}» por {monto} venció el {fecha_limite} y continúa pendiente. "
        "Por favor comuníquese con la administración del club.\n\nClub Valle Alto",
        "nombre, concepto, monto, fecha_limite",
    ),
    "recuperar_password": (
        "Recuperación de contraseña",
        "Recupere su contraseña",
        "Hola {nombre},\n\nRecibimos una solicitud para restablecer su contraseña. Use este enlace (válido por 60 minutos): "
        "{enlace}\n\nSi usted no la solicitó, ignore este mensaje.\n\nClub Valle Alto",
        "nombre, enlace",
    ),
}


def cargar_catalogos_iniciales():
    """Inserta (sin pisar lo existente) configuración, tipos, instalaciones y plantillas."""
    db = get_db()
    for clave, (valor, desc) in CONFIG_DEFAULTS.items():
        db.execute("INSERT OR IGNORE INTO config_club(clave, valor, descripcion) VALUES (?,?,?)", (clave, valor, desc))
    for t in TIPOS_DEFAULT:
        db.execute(
            "INSERT OR IGNORE INTO tipos_membresia(tipo, cuota_mensual, limite_invitados_mes, max_beneficiarios, autoservicio) "
            "VALUES (?,?,?,?,?)", t)
    for nombre, tipo, desc, ap, ci, aforo, modo in INSTALACIONES_DEFAULT:
        db.execute(
            "INSERT OR IGNORE INTO instalaciones(nombre, tipo, descripcion, hora_apertura, hora_cierre, aforo_max, modo) "
            "VALUES (?,?,?,?,?,?,?)", (nombre, tipo, desc, ap, ci, aforo, modo))
        inst_id = db.execute("SELECT id FROM instalaciones WHERE nombre=?", (nombre,)).fetchone()[0]
        for sn, costo in SERVICIOS_DEFAULT.get(nombre, []):
            existe = db.execute("SELECT 1 FROM servicios_adicionales WHERE instalacion_id=? AND nombre=?", (inst_id, sn)).fetchone()
            if not existe:
                db.execute("INSERT INTO servicios_adicionales(instalacion_id, nombre, costo) VALUES (?,?,?)", (inst_id, sn, costo))
    for codigo, (nombre, asunto, cuerpo, variables) in PLANTILLAS_DEFAULT.items():
        db.execute(
            "INSERT OR IGNORE INTO plantillas_notificacion(codigo, nombre, asunto, cuerpo, variables, actualizado_en) "
            "VALUES (?,?,?,?,?,?)", (codigo, nombre, asunto, cuerpo, variables, ahora_txt()))
    db.commit()


# ---- acceso a la configuración -------------------------------------------------
def obtener(clave, default=None):
    fila = one("SELECT valor FROM config_club WHERE clave=?", (clave,))
    if fila is not None:
        return fila["valor"]
    if clave in CONFIG_DEFAULTS:
        return CONFIG_DEFAULTS[clave][0]
    return default


def obtener_int(clave, default=0):
    try:
        return int(obtener(clave, default))
    except (TypeError, ValueError):
        return default


def guardar(clave, valor):
    execute(
        "INSERT INTO config_club(clave, valor) VALUES (?,?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
        (clave, str(valor)))


def todas():
    return query("SELECT clave, valor, descripcion FROM config_club ORDER BY clave")


def tipos():
    return query("SELECT * FROM tipos_membresia ORDER BY CASE tipo WHEN 'individual' THEN 1 WHEN 'familiar' THEN 2 "
                 "WHEN 'corporativa' THEN 3 ELSE 4 END")


def tipo(nombre):
    return one("SELECT * FROM tipos_membresia WHERE tipo=?", (nombre,))


def actualizar_tipo(nombre, cuota, limite_invitados, max_beneficiarios):
    execute("UPDATE tipos_membresia SET cuota_mensual=?, limite_invitados_mes=?, max_beneficiarios=? WHERE tipo=?",
            (cuota, limite_invitados, max_beneficiarios, nombre))


def moneda(valor):
    # Formato del prototipo: ₡45 000 (espacio de no separación como separador de miles, sin decimales)
    return f"{obtener('moneda', '₡')}{valor:,.0f}".replace(",", "\u00a0")
