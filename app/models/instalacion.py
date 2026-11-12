"""Instalaciones, servicios adicionales y bloqueos (mantenimiento / eventos privados)."""
from app.db import ReglaError, execute, hoy, one, query
from app.services import validators as v

TIPOS = {"golf": "Cancha de golf", "tenis": "Cancha de tenis", "piscina": "Piscina", "salon": "Salón de eventos"}
MODOS = {"exclusiva": "Exclusiva (una reserva por franja)", "compartida": "Compartida (se suman personas hasta el aforo)"}


def listar(solo_activas=False):
    sql = "SELECT * FROM instalaciones"
    if solo_activas:
        sql += " WHERE activa=1"
    return query(sql + " ORDER BY nombre")


def por_id(iid):
    return one("SELECT * FROM instalaciones WHERE id=?", (iid,))


def _validar(form):
    nombre = v.texto(form.get("nombre"), "El nombre", 3, 80)
    tipo = form.get("tipo")
    if tipo not in TIPOS:
        raise ReglaError("Seleccione un tipo de instalación válido.")
    modo = form.get("modo")
    if modo not in MODOS:
        raise ReglaError("Seleccione el modo de reserva.")
    ap = v.hora(form.get("hora_apertura"), "La hora de apertura")
    ci = v.hora(form.get("hora_cierre"), "La hora de cierre")
    if v.minutos(ap) >= v.minutos(ci):
        raise ReglaError("La hora de cierre debe ser posterior a la de apertura.")
    aforo = v.entero(form.get("aforo_max"), "El aforo máximo", 1, 5000)
    return nombre, tipo, (form.get("descripcion") or "").strip()[:300], ap, ci, aforo, modo


def crear(form):
    nombre, tipo, desc, ap, ci, aforo, modo = _validar(form)
    if one("SELECT 1 FROM instalaciones WHERE nombre=?", (nombre,)):
        raise ReglaError("Ya existe una instalación con ese nombre.")
    return execute("INSERT INTO instalaciones(nombre, tipo, descripcion, hora_apertura, hora_cierre, aforo_max, modo) "
                   "VALUES (?,?,?,?,?,?,?)", (nombre, tipo, desc, ap, ci, aforo, modo))


def actualizar(iid, form):
    nombre, tipo, desc, ap, ci, aforo, modo = _validar(form)
    if one("SELECT 1 FROM instalaciones WHERE nombre=? AND id<>?", (nombre, iid)):
        raise ReglaError("Ya existe una instalación con ese nombre.")
    execute("UPDATE instalaciones SET nombre=?, tipo=?, descripcion=?, hora_apertura=?, hora_cierre=?, aforo_max=?, modo=?, activa=? "
            "WHERE id=?", (nombre, tipo, desc, ap, ci, aforo, modo, 1 if form.get("activa") else 0, iid))


# ---- servicios adicionales -----------------------------------------------------
def servicios(iid, solo_activos=True):
    sql = "SELECT * FROM servicios_adicionales WHERE instalacion_id=?"
    if solo_activos:
        sql += " AND activo=1"
    return query(sql + " ORDER BY nombre", (iid,))


def crear_servicio(iid, form):
    nombre = v.texto(form.get("nombre"), "El nombre del servicio", 3, 80)
    costo = v.monto(form.get("costo"), "El costo")
    return execute("INSERT INTO servicios_adicionales(instalacion_id, nombre, costo) VALUES (?,?,?)", (iid, nombre, costo))


def cambiar_servicio(iid, sid, activo):
    execute("UPDATE servicios_adicionales SET activo=? WHERE id=? AND instalacion_id=?", (1 if activo else 0, sid, iid))


# ---- bloqueos ------------------------------------------------------------------------
def bloqueos(iid=None, desde=None):
    sql = ("SELECT b.*, i.nombre AS instalacion FROM bloqueos b JOIN instalaciones i ON i.id=b.instalacion_id WHERE 1=1")
    args = []
    if iid:
        sql += " AND b.instalacion_id=?"
        args.append(iid)
    if desde:
        sql += " AND b.fecha>=?"
        args.append(desde)
    return query(sql + " ORDER BY b.fecha, b.hora_inicio", args)


def crear_bloqueo(iid, form, admin_id):
    inst = por_id(iid)
    fecha = v.fecha(form.get("fecha"), "La fecha del bloqueo")
    if fecha < hoy():
        raise ReglaError("No se puede bloquear una fecha pasada.")
    ini = v.hora(form.get("hora_inicio"), "La hora de inicio")
    fin = v.hora(form.get("hora_fin"), "La hora de fin")
    if v.minutos(ini) >= v.minutos(fin):
        raise ReglaError("La hora de fin debe ser posterior a la de inicio.")
    if v.minutos(ini) < v.minutos(inst["hora_apertura"]) or v.minutos(fin) > v.minutos(inst["hora_cierre"]):
        raise ReglaError(f"El bloqueo debe estar dentro del horario de la instalación ({inst['hora_apertura']}–{inst['hora_cierre']}).")
    motivo = v.texto(form.get("motivo"), "El motivo", 3, 200)
    choques = query("SELECT id, hora_inicio, hora_fin FROM reservas WHERE instalacion_id=? AND fecha=? "
                    "AND estado IN ('pendiente','confirmada')", (iid, fecha.isoformat()))
    conflictivas = [c for c in choques if v.minutos(c["hora_inicio"]) < v.minutos(fin) and v.minutos(ini) < v.minutos(c["hora_fin"])]
    if conflictivas:
        ids = ", ".join(f"#{c['id']}" for c in conflictivas)
        raise ReglaError(f"Existen reservas en ese horario ({ids}). Cancélelas o modifíquelas antes de bloquear la instalación.")
    return execute("INSERT INTO bloqueos(instalacion_id, fecha, hora_inicio, hora_fin, motivo, admin_id) VALUES (?,?,?,?,?,?)",
                   (iid, fecha.isoformat(), ini, fin, motivo, admin_id))


def eliminar_bloqueo(bid):
    execute("DELETE FROM bloqueos WHERE id=?", (bid,))
