"""Módulo 2: Registro de membresías, beneficiarios e historial de estados."""
from datetime import timedelta

from app.db import ReglaError, ahora_txt, execute, hoy, one, query
from app.models import config
from app.services import validators as v

ESTADOS = ("activa", "suspendida", "vencida", "baja")


def por_id(mid):
    return one("SELECT m.*, s.nombre AS socio_nombre, s.cedula AS socio_cedula, s.correo AS socio_correo "
               "FROM membresias m JOIN socios s ON s.id = m.socio_id WHERE m.id=?", (mid,))


def vigente(socio_id):
    """Membresía del socio que no está dada de baja (como máximo una)."""
    return one("SELECT * FROM membresias WHERE socio_id=? AND estado<>'baja'", (socio_id,))


def listar(estado="", tipo="", busqueda=""):
    sql = ("SELECT m.*, s.nombre AS socio_nombre, s.cedula AS socio_cedula FROM membresias m "
           "JOIN socios s ON s.id = m.socio_id WHERE m.estado<>'baja' ")
    args = []
    if estado in ESTADOS:
        sql = sql.replace("m.estado<>'baja'", "m.estado = ?")
        args.append(estado)
    if tipo:
        sql += " AND m.tipo = ?"
        args.append(tipo)
    if busqueda:
        sql += " AND (s.nombre LIKE ? OR s.cedula LIKE ?)"
        like = f"%{busqueda.strip()}%"
        args += [like, like]
    sql += " ORDER BY s.nombre"
    return query(sql, args)


def _registrar_historial(mid, anterior, nuevo, motivo, actor):
    execute("INSERT INTO membresia_historial(membresia_id, estado_anterior, estado_nuevo, motivo, actor, fecha) "
            "VALUES (?,?,?,?,?,?)", (mid, anterior, nuevo, motivo, actor, ahora_txt()))


def crear(socio_id, tipo, actor, por_personal=False, cuota=None, fecha_inscripcion=None):
    t = config.tipo(tipo)
    if t is None:
        raise ReglaError("Seleccione un tipo de membresía válido.")
    if not por_personal and not t["autoservicio"]:
        raise ReglaError(f"La membresía {tipo} solo puede ser asignada por el personal administrativo.")
    if vigente(socio_id):
        raise ReglaError("El socio ya tiene una membresía vigente. Debe darla de baja antes de registrar otra.")
    inscripcion = fecha_inscripcion or hoy()
    renovacion = inscripcion + timedelta(days=config.obtener_int("dias_renovacion", 365))
    monto = t["cuota_mensual"] if cuota is None else cuota
    mid = execute(
        "INSERT INTO membresias(socio_id, tipo, fecha_inscripcion, fecha_renovacion, cuota, estado) VALUES (?,?,?,?,?, 'activa')",
        (socio_id, tipo, inscripcion.isoformat(), renovacion.isoformat(), monto))
    _registrar_historial(mid, None, "activa", "Alta de membresía", actor)
    return mid


def modificar(mid, tipo, cuota, fecha_renovacion, actor):
    m = por_id(mid)
    if m["estado"] == "baja":
        raise ReglaError("No se puede modificar una membresía dada de baja.")
    t = config.tipo(tipo)
    if t is None:
        raise ReglaError("Tipo de membresía no válido.")
    n_benef = one("SELECT COUNT(*) AS n FROM beneficiarios WHERE membresia_id=?", (mid,))["n"]
    if n_benef > t["max_beneficiarios"]:
        raise ReglaError(f"La membresía {tipo} permite máximo {t['max_beneficiarios']} beneficiario(s) y esta tiene {n_benef}. "
                         "Elimine beneficiarios antes de cambiar el tipo.")
    execute("UPDATE membresias SET tipo=?, cuota=?, fecha_renovacion=? WHERE id=?", (tipo, cuota, fecha_renovacion, mid))


def cambiar_estado(mid, nuevo, motivo, actor):
    if nuevo not in ESTADOS:
        raise ReglaError("Estado no válido.")
    m = por_id(mid)
    if m["estado"] == "baja":
        raise ReglaError("La membresía ya fue dada de baja y no puede cambiar de estado.")
    if m["estado"] == nuevo:
        raise ReglaError("La membresía ya se encuentra en ese estado.")
    if nuevo == "activa" and m["fecha_renovacion"] < hoy().isoformat():
        raise ReglaError("La fecha de renovación ya pasó: use «Renovar» para reactivar la membresía.")
    execute("UPDATE membresias SET estado=? WHERE id=?", (nuevo, mid))
    _registrar_historial(mid, m["estado"], nuevo, (motivo or "").strip()[:250] or None, actor)


def renovar(mid, actor):
    m = por_id(mid)
    if m["estado"] == "baja":
        raise ReglaError("No se puede renovar una membresía dada de baja.")
    base = max(hoy(), __import__("datetime").date.fromisoformat(m["fecha_renovacion"]))
    nueva = base + timedelta(days=config.obtener_int("dias_renovacion", 365))
    execute("UPDATE membresias SET fecha_renovacion=?, estado='activa' WHERE id=?", (nueva.isoformat(), mid))
    _registrar_historial(mid, m["estado"], "activa", "Renovación", actor)


def nombre_actor(actor):
    """Nombre legible de quien hizo un cambio ('socio:3', 'admin:1' o 'sistema')."""
    tipo, _, ident = (actor or "").partition(":")
    tabla = {"socio": "socios", "admin": "admins"}.get(tipo)
    if tabla and ident.isdigit():
        fila = one(f"SELECT nombre FROM {tabla} WHERE id=?", (int(ident),))
        if fila:
            return fila["nombre"]
    return "Sistema" if tipo in ("sistema", "") else actor


def historial(mid):
    filas = query("SELECT * FROM membresia_historial WHERE membresia_id=? ORDER BY id DESC", (mid,))
    return [dict(f, actor_nombre=nombre_actor(f["actor"])) for f in filas]


def cambiar_tipo(mid, tipo, actor):
    """El socio (o el personal) cambia el tipo de membresía; la cuota pasa a la del nuevo tipo."""
    m = por_id(mid)
    t = config.tipo(tipo)
    if t is None:
        raise ReglaError("Seleccione un tipo de membresía válido.")
    if m["tipo"] == tipo:
        raise ReglaError("Esa ya es su membresía actual.")
    if not t["autoservicio"] and not actor.startswith("admin:"):
        raise ReglaError(f"La membresía {tipo} solo puede ser asignada por el personal administrativo.")
    modificar(mid, tipo, t["cuota_mensual"], m["fecha_renovacion"], actor)
    _registrar_historial(mid, m["estado"], m["estado"], f"Cambio de tipo: {m['tipo']} → {tipo}", actor)


def refrescar_vencimientos():
    """Marca como vencidas las membresías activas cuya fecha de renovación ya pasó."""
    filas = query("SELECT id FROM membresias WHERE estado='activa' AND fecha_renovacion < ?", (hoy().isoformat(),))
    for f in filas:
        execute("UPDATE membresias SET estado='vencida' WHERE id=?", (f["id"],))
        _registrar_historial(f["id"], "activa", "vencida", "Fecha de renovación vencida", "sistema")
    return len(filas)


# ---- beneficiarios -------------------------------------------------------------------
def beneficiarios(mid):
    return query("SELECT * FROM beneficiarios WHERE membresia_id=? ORDER BY nombre", (mid,))


def agregar_beneficiario(mid, form):
    m = por_id(mid)
    if m is None or m["estado"] == "baja":
        raise ReglaError("Membresía no disponible.")
    t = config.tipo(m["tipo"])
    if t["max_beneficiarios"] == 0:
        raise ReglaError("Este tipo de membresía no admite beneficiarios (solo la familiar).")
    n = one("SELECT COUNT(*) AS n FROM beneficiarios WHERE membresia_id=?", (mid,))["n"]
    if n >= t["max_beneficiarios"]:
        raise ReglaError(f"Se alcanzó el máximo de {t['max_beneficiarios']} beneficiarios permitido por el reglamento del club.")
    nombre = v.texto(form.get("nombre"), "El nombre del beneficiario", 3, 120)
    ced = v.cedula(form.get("cedula"), "La cédula del beneficiario")
    parentesco = v.texto(form.get("parentesco"), "El parentesco", 2, 60)
    nac = v.fecha_nacimiento(form.get("fecha_nacimiento")).isoformat()
    if ced == m["socio_cedula"]:
        raise ReglaError("El titular no puede registrarse como su propio beneficiario.")
    if one("SELECT 1 FROM beneficiarios WHERE membresia_id=? AND cedula=?", (mid, ced)):
        raise ReglaError("Ese beneficiario ya está registrado en la membresía.")
    return execute("INSERT INTO beneficiarios(membresia_id, nombre, cedula, parentesco, fecha_nacimiento) VALUES (?,?,?,?,?)",
                   (mid, nombre, ced, parentesco, nac))


def editar_beneficiario(mid, bid, form):
    b = one("SELECT * FROM beneficiarios WHERE id=? AND membresia_id=?", (bid, mid))
    if b is None:
        raise ReglaError("El beneficiario no existe.")
    m = por_id(mid)
    nombre = v.texto(form.get("nombre"), "El nombre del beneficiario", 3, 120)
    ced = v.cedula(form.get("cedula"), "La cédula del beneficiario")
    parentesco = v.texto(form.get("parentesco"), "El parentesco", 2, 60)
    nac = v.fecha_nacimiento(form.get("fecha_nacimiento")).isoformat()
    if ced == m["socio_cedula"]:
        raise ReglaError("El titular no puede registrarse como su propio beneficiario.")
    if one("SELECT 1 FROM beneficiarios WHERE membresia_id=? AND cedula=? AND id<>?", (mid, ced, bid)):
        raise ReglaError("Ese beneficiario ya está registrado en la membresía.")
    execute("UPDATE beneficiarios SET nombre=?, cedula=?, parentesco=?, fecha_nacimiento=? WHERE id=?", (nombre, ced, parentesco, nac, bid))


def eliminar_beneficiario(mid, bid):
    execute("DELETE FROM beneficiarios WHERE id=? AND membresia_id=?", (bid, mid))
