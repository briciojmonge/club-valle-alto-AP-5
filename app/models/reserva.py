"""Módulos 4 y 6: Reserva de instalaciones y gestión operativa (calendario, ocupación, reportes)."""
from datetime import date, datetime, timedelta

from app.db import ReglaError, ahora, ahora_txt, execute, hoy, one, query
from app.models import config, instalacion, membresia, notificacion, socio
from app.services import validators as v

ESTADOS_ACTIVOS = ("pendiente", "confirmada")        # bloquean disponibilidad
ESTADOS_OCUPACION = ("pendiente", "confirmada", "finalizada")


# ---------------------------------------------------------------- utilidades de disponibilidad
def _traslapan(a_ini, a_fin, b_ini, b_fin):
    return a_ini < b_fin and b_ini < a_fin


def ocupacion_maxima(reservas, ini, fin):
    """Máximo de personas simultáneas dentro de [ini, fin) (minutos) para una lista de reservas."""
    puntos = [ini] + [v.minutos(r["hora_inicio"]) for r in reservas if ini <= v.minutos(r["hora_inicio"]) < fin]
    mejor = 0
    for p in puntos:
        total = sum(r["personas"] for r in reservas if v.minutos(r["hora_inicio"]) <= p < v.minutos(r["hora_fin"]))
        mejor = max(mejor, total)
    return mejor


def validar_disponibilidad(inst, fecha_iso, hora_ini, hora_fin, personas, excluir_id=None):
    ini, fin = v.minutos(hora_ini), v.minutos(hora_fin)
    if ini >= fin:
        raise ReglaError("La hora de finalización debe ser posterior a la de inicio.")
    if ini < v.minutos(inst["hora_apertura"]) or fin > v.minutos(inst["hora_cierre"]):
        raise ReglaError(f"{inst['nombre']} atiende de {inst['hora_apertura']} a {inst['hora_cierre']}. "
                         "Ajuste el horario de la reserva.")
    if personas > inst["aforo_max"]:
        raise ReglaError(f"El aforo máximo de {inst['nombre']} es de {inst['aforo_max']} persona(s).")
    for b in query("SELECT * FROM bloqueos WHERE instalacion_id=? AND fecha=?", (inst["id"], fecha_iso)):
        if _traslapan(ini, fin, v.minutos(b["hora_inicio"]), v.minutos(b["hora_fin"])):
            raise ReglaError(f"La instalación no está disponible en ese horario: {b['motivo']} "
                             f"({b['hora_inicio']}–{b['hora_fin']}).")
    otras = [r for r in query(
        "SELECT * FROM reservas WHERE instalacion_id=? AND fecha=? AND estado IN ('pendiente','confirmada') AND id<>?",
        (inst["id"], fecha_iso, excluir_id or 0))
        if _traslapan(ini, fin, v.minutos(r["hora_inicio"]), v.minutos(r["hora_fin"]))]
    if inst["modo"] == "exclusiva":
        if otras:
            raise ReglaError("La instalación ya está reservada en ese horario (traslape con otra reserva). Elija otra franja.")
    else:
        pico = ocupacion_maxima(otras, ini, fin)
        if pico + personas > inst["aforo_max"]:
            libres = max(inst["aforo_max"] - pico, 0)
            raise ReglaError(f"No hay cupo suficiente en ese horario: quedan {libres} lugar(es) de {inst['aforo_max']}.")


def _inicio_dt(r):
    return datetime.strptime(f"{r['fecha']} {r['hora_inicio']}", "%Y-%m-%d %H:%M")


def _fin_dt(r):
    return datetime.strptime(f"{r['fecha']} {r['hora_fin']}", "%Y-%m-%d %H:%M")


# ---------------------------------------------------------------- consultas
def por_id(rid):
    return one("SELECT r.*, i.nombre AS instalacion, i.modo, s.nombre AS socio_nombre, s.correo AS socio_correo, s.cedula AS socio_cedula "
               "FROM reservas r JOIN instalaciones i ON i.id=r.instalacion_id JOIN socios s ON s.id=r.socio_id WHERE r.id=?", (rid,))


def servicios_de(rid):
    return query("SELECT rs.*, sa.nombre FROM reserva_servicios rs JOIN servicios_adicionales sa ON sa.id=rs.servicio_id "
                 "WHERE rs.reserva_id=? ORDER BY sa.nombre", (rid,))


def listar_socio(socio_id):
    finalizar_pasadas()
    return query("SELECT r.*, i.nombre AS instalacion FROM reservas r JOIN instalaciones i ON i.id=r.instalacion_id "
                 "WHERE r.socio_id=? ORDER BY r.fecha DESC, r.hora_inicio DESC", (socio_id,))


def listar(fecha_desde="", fecha_hasta="", instalacion_id="", estado="", busqueda=""):
    finalizar_pasadas()
    sql = ("SELECT r.*, i.nombre AS instalacion, s.nombre AS socio_nombre FROM reservas r "
           "JOIN instalaciones i ON i.id=r.instalacion_id JOIN socios s ON s.id=r.socio_id WHERE 1=1")
    args = []
    if fecha_desde:
        sql += " AND r.fecha>=?"; args.append(fecha_desde)
    if fecha_hasta:
        sql += " AND r.fecha<=?"; args.append(fecha_hasta)
    if instalacion_id:
        sql += " AND r.instalacion_id=?"; args.append(instalacion_id)
    if estado:
        sql += " AND r.estado=?"; args.append(estado)
    if busqueda:
        sql += " AND (s.nombre LIKE ? OR s.cedula LIKE ?)"; like = f"%{busqueda.strip()}%"; args += [like, like]
    return query(sql + " ORDER BY r.fecha DESC, r.hora_inicio DESC LIMIT 500", args)


def finalizar_pasadas():
    """Pasa a 'finalizada' las reservas confirmadas cuyo horario ya terminó."""
    ahora_dt = ahora()
    for r in query("SELECT id, fecha, hora_fin FROM reservas WHERE estado='confirmada' AND fecha<=?", (ahora_dt.date().isoformat(),)):
        if _fin_dt(r) <= ahora_dt:
            execute("UPDATE reservas SET estado='finalizada', actualizado_en=? WHERE id=?", (ahora_txt(), r["id"]))


# ---------------------------------------------------------------- operaciones del socio
def _leer_form(form, inst):
    fecha = v.fecha(form.get("fecha"), "La fecha de la reserva")
    ini = v.hora(form.get("hora_inicio"), "La hora de inicio")
    fin = v.hora(form.get("hora_fin"), "La hora de fin")
    personas = v.entero(form.get("personas"), "El número de personas", 1)
    if fecha < hoy():
        raise ReglaError("No se pueden crear reservas en fechas pasadas.")
    if fecha > hoy() + timedelta(days=config.obtener_int("dias_anticipacion_max", 60)):
        raise ReglaError(f"Solo se puede reservar con hasta {config.obtener_int('dias_anticipacion_max', 60)} días de anticipación.")
    if fecha == hoy() and v.minutos(ini) <= ahora().hour * 60 + ahora().minute:
        raise ReglaError("La hora de inicio ya pasó.")
    ids = form.getlist("servicios") if hasattr(form, "getlist") else (form.get("servicios") or [])
    validos = {str(s["id"]): s for s in instalacion.servicios(inst["id"])}
    elegidos = []
    for sid in ids:
        if sid not in validos:
            raise ReglaError("Uno de los servicios adicionales no pertenece a la instalación seleccionada.")
        elegidos.append(validos[sid])
    return fecha.isoformat(), ini, fin, personas, elegidos


def _exigir_socio_habilitado(socio_id):
    s = socio.por_id(socio_id)
    if s["estado"] != "activo":
        raise ReglaError("Su cuenta no está activa; no puede reservar.")
    m = membresia.vigente(socio_id)
    if m is None or m["estado"] != "activa":
        raise ReglaError("Necesita una membresía activa para reservar instalaciones.")


def crear(socio_id, form):
    _exigir_socio_habilitado(socio_id)
    inst = instalacion.por_id(form.get("instalacion_id") or 0)
    if inst is None or not inst["activa"]:
        raise ReglaError("Seleccione una instalación válida.")
    fecha, ini, fin, personas, servicios = _leer_form(form, inst)
    validar_disponibilidad(inst, fecha, ini, fin, personas)
    estado = "confirmada" if config.obtener("reserva_autoconfirmar", "1") == "1" else "pendiente"
    rid = execute(
        "INSERT INTO reservas(socio_id, instalacion_id, fecha, hora_inicio, hora_fin, personas, estado, creado_en, actualizado_en) "
        "VALUES (?,?,?,?,?,?,?,?,?)", (socio_id, inst["id"], fecha, ini, fin, personas, estado, ahora_txt(), ahora_txt()))
    for s in servicios:
        execute("INSERT INTO reserva_servicios(reserva_id, servicio_id, costo) VALUES (?,?,?)", (rid, s["id"], s["costo"]))
    if estado == "confirmada":
        _notificar(rid, "reserva_confirmada")
    return rid


def _puede_cambiar(r):
    if r["estado"] not in ESTADOS_ACTIVOS:
        raise ReglaError("Solo se pueden modificar o cancelar reservas pendientes o confirmadas.")


def modificar(rid, form, socio_id=None):
    r = por_id(rid)
    if r is None or (socio_id is not None and r["socio_id"] != socio_id):
        raise ReglaError("Reserva no encontrada.")
    _puede_cambiar(r)
    if socio_id is not None and _inicio_dt(r) <= ahora():
        raise ReglaError("La reserva ya inició; no se puede modificar.")
    inst = instalacion.por_id(r["instalacion_id"])
    fecha, ini, fin, personas, servicios = _leer_form(form, inst)
    validar_disponibilidad(inst, fecha, ini, fin, personas, excluir_id=rid)
    execute("UPDATE reservas SET fecha=?, hora_inicio=?, hora_fin=?, personas=?, actualizado_en=? WHERE id=?",
            (fecha, ini, fin, personas, ahora_txt(), rid))
    nuevos = {s["id"] for s in servicios}
    for s in servicios_de(rid):
        if s["servicio_id"] not in nuevos:
            execute("DELETE FROM reserva_servicios WHERE reserva_id=? AND servicio_id=?", (rid, s["servicio_id"]))
            execute("UPDATE cargos SET estado='anulado' WHERE reserva_id=? AND servicio_id=? AND estado='pendiente'", (rid, s["servicio_id"]))
    for s in servicios:
        execute("INSERT OR IGNORE INTO reserva_servicios(reserva_id, servicio_id, costo) VALUES (?,?,?)", (rid, s["id"], s["costo"]))
    _notificar(rid, "reserva_modificada")


def cancelar(rid, socio_id=None):
    r = por_id(rid)
    if r is None or (socio_id is not None and r["socio_id"] != socio_id):
        raise ReglaError("Reserva no encontrada.")
    _puede_cambiar(r)
    if socio_id is not None and _inicio_dt(r) <= ahora():
        raise ReglaError("La reserva ya inició; no se puede cancelar.")
    execute("UPDATE reservas SET estado='cancelada', actualizado_en=? WHERE id=?", (ahora_txt(), rid))
    execute("UPDATE cargos SET estado='anulado' WHERE reserva_id=? AND estado='pendiente'", (rid,))
    _notificar(rid, "reserva_cancelada")


def confirmar(rid):
    r = por_id(rid)
    if r is None or r["estado"] != "pendiente":
        raise ReglaError("Solo se pueden confirmar reservas pendientes.")
    inst = instalacion.por_id(r["instalacion_id"])
    validar_disponibilidad(inst, r["fecha"], r["hora_inicio"], r["hora_fin"], r["personas"], excluir_id=rid)
    execute("UPDATE reservas SET estado='confirmada', actualizado_en=? WHERE id=?", (ahora_txt(), rid))
    _notificar(rid, "reserva_confirmada")


def _notificar(rid, codigo):
    r = por_id(rid)
    notificacion.notificar(
        {"id": r["socio_id"], "nombre": r["socio_nombre"], "correo": r["socio_correo"]}, codigo,
        {"instalacion": r["instalacion"], "fecha": r["fecha"], "hora_inicio": r["hora_inicio"],
         "hora_fin": r["hora_fin"], "personas": r["personas"]})


def total_servicios(rid):
    return sum(s["costo"] for s in servicios_de(rid))


def invitados_de_reserva(r):
    """Invitados del socio registrados para la misma fecha e instalación de la reserva."""
    return query("SELECT * FROM invitados WHERE socio_id=? AND fecha_visita=? AND instalacion_id=? ORDER BY nombre",
                 (r["socio_id"], r["fecha"], r["instalacion_id"]))


# ---------------------------------------------------------------- gestión operativa
def ocupacion_por_franja(inst, fecha_iso):
    """Ocupación por franja horaria de una instalación en una fecha."""
    ap, ci = v.minutos(inst["hora_apertura"]), v.minutos(inst["hora_cierre"])
    reservas = query(
        "SELECT * FROM reservas WHERE instalacion_id=? AND fecha=? AND estado IN ('pendiente','confirmada','finalizada')",
        (inst["id"], fecha_iso))
    bloqueos = query("SELECT * FROM bloqueos WHERE instalacion_id=? AND fecha=?", (inst["id"], fecha_iso))
    franjas = []
    t = ap
    while t < ci:
        t_fin = min(t + 60, ci)
        bloqueo = next((b for b in bloqueos if _traslapan(t, t_fin, v.minutos(b["hora_inicio"]), v.minutos(b["hora_fin"]))), None)
        en_franja = [r for r in reservas if _traslapan(t, t_fin, v.minutos(r["hora_inicio"]), v.minutos(r["hora_fin"]))]
        personas = ocupacion_maxima(en_franja, t, t_fin)
        if bloqueo:
            estado = "bloqueada"
        elif personas >= inst["aforo_max"] or (inst["modo"] == "exclusiva" and en_franja):
            estado = "completa"
        elif personas > 0:
            estado = "parcial"
        else:
            estado = "libre"
        franjas.append({
            "inicio": f"{t // 60:02d}:{t % 60:02d}", "fin": f"{t_fin // 60:02d}:{t_fin % 60:02d}",
            "personas": personas, "aforo": inst["aforo_max"], "estado": estado, "reservas": len(en_franja),
            "pct": min(100, round(100 * personas / inst["aforo_max"])) if inst["aforo_max"] else 0,
            "motivo": bloqueo["motivo"] if bloqueo else "",
        })
        t = t_fin
    return franjas


def calendario_semana(inst, lunes):
    """Reservas y bloqueos de una instalación para los 7 días desde `lunes` (date)."""
    dias = []
    for i in range(7):
        d = lunes + timedelta(days=i)
        dias.append({
            "fecha": d,
            "reservas": query("SELECT r.*, s.nombre AS socio_nombre FROM reservas r JOIN socios s ON s.id=r.socio_id "
                              "WHERE r.instalacion_id=? AND r.fecha=? AND r.estado<>'cancelada' ORDER BY r.hora_inicio",
                              (inst["id"], d.isoformat())),
            "bloqueos": query("SELECT * FROM bloqueos WHERE instalacion_id=? AND fecha=? ORDER BY hora_inicio",
                              (inst["id"], d.isoformat())),
        })
    return dias


def reporte_uso(desde, hasta):
    """Uso de instalaciones por periodo: reservas, horas y personas. Ordenado de mayor a menor demanda."""
    finalizar_pasadas()
    filas = []
    for inst in instalacion.listar():
        rs = query("SELECT * FROM reservas WHERE instalacion_id=? AND fecha BETWEEN ? AND ? AND estado IN ('confirmada','finalizada')",
                   (inst["id"], desde, hasta))
        horas = sum((v.minutos(r["hora_fin"]) - v.minutos(r["hora_inicio"])) for r in rs) / 60
        canceladas = one("SELECT COUNT(*) AS n FROM reservas WHERE instalacion_id=? AND fecha BETWEEN ? AND ? AND estado='cancelada'",
                         (inst["id"], desde, hasta))["n"]
        filas.append({"instalacion": inst["nombre"], "reservas": len(rs), "horas": round(horas, 1),
                      "personas": sum(r["personas"] for r in rs), "canceladas": canceladas})
    filas.sort(key=lambda f: (f["reservas"], f["horas"]), reverse=True)
    for i, f in enumerate(filas):
        f["ranking"] = i + 1
    return filas
