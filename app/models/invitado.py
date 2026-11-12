"""Módulo 3: Registro de invitados con límite mensual por tipo de membresía."""
from datetime import timedelta

from app.db import ReglaError, ahora_txt, execute, hoy, one, query
from app.models import config, membresia
from app.services import validators as v

RELACIONES = ("familiar", "amigo", "otro")


def cupo(socio_id, mes):
    """(usados, limite) de invitados del socio para el mes 'YYYY-MM'."""
    m = membresia.vigente(socio_id)
    limite = config.tipo(m["tipo"])["limite_invitados_mes"] if m else 0
    usados = one("SELECT COUNT(*) AS n FROM invitados WHERE socio_id=? AND strftime('%Y-%m', fecha_visita)=?",
                 (socio_id, mes))["n"]
    return usados, limite


def registrar(socio_id, form):
    m = membresia.vigente(socio_id)
    if m is None or m["estado"] != "activa":
        raise ReglaError("Necesita una membresía activa para registrar invitados.")
    nombre = v.texto(form.get("nombre"), "El nombre del invitado", 3, 120)
    ced = v.cedula(form.get("cedula"), "La cédula del invitado")
    visita = v.fecha(form.get("fecha_visita"), "La fecha de visita")
    if visita < hoy():
        raise ReglaError("La fecha de visita no puede estar en el pasado.")
    if visita > hoy() + timedelta(days=config.obtener_int("dias_anticipacion_max", 60)):
        raise ReglaError("La fecha de visita excede la anticipación máxima permitida.")
    inst = one("SELECT * FROM instalaciones WHERE id=? AND activa=1", (form.get("instalacion_id"),))
    if inst is None:
        raise ReglaError("Seleccione una instalación válida.")
    relacion = form.get("relacion")
    if relacion not in RELACIONES:
        raise ReglaError("Seleccione la relación del invitado con el socio.")
    if ced == one("SELECT cedula FROM socios WHERE id=?", (socio_id,))["cedula"]:
        raise ReglaError("No puede registrarse a sí mismo como invitado.")
    if one("SELECT 1 FROM invitados WHERE socio_id=? AND cedula=? AND fecha_visita=?", (socio_id, ced, visita.isoformat())):
        raise ReglaError("Ese invitado ya está registrado para esa fecha.")
    usados, limite = cupo(socio_id, visita.strftime("%Y-%m"))
    if usados >= limite:
        raise ReglaError(f"Alcanzó el límite de {limite} invitado(s) por mes de su membresía {m['tipo']} "
                         f"para {visita.strftime('%m/%Y')}. No es posible agregar más.")
    return execute(
        "INSERT INTO invitados(socio_id, nombre, cedula, fecha_visita, instalacion_id, relacion, creado_en) VALUES (?,?,?,?,?,?,?)",
        (socio_id, nombre, ced, visita.isoformat(), inst["id"], relacion, ahora_txt()))


def eliminar(socio_id, invitado_id):
    fila = one("SELECT * FROM invitados WHERE id=? AND socio_id=?", (invitado_id, socio_id))
    if fila is None:
        raise ReglaError("Invitado no encontrado.")
    if fila["fecha_visita"] < hoy().isoformat():
        raise ReglaError("No se puede eliminar un invitado de una visita ya pasada.")
    execute("DELETE FROM invitados WHERE id=?", (invitado_id,))


def listar_socio(socio_id):
    return query("SELECT i.*, ins.nombre AS instalacion FROM invitados i JOIN instalaciones ins ON ins.id=i.instalacion_id "
                 "WHERE i.socio_id=? ORDER BY i.fecha_visita DESC, i.id DESC", (socio_id,))


def esperados(fecha, instalacion_id=None):
    """Listado de invitados esperados un día (para recepción)."""
    sql = ("SELECT i.*, ins.nombre AS instalacion, s.nombre AS socio_nombre, s.cedula AS socio_cedula "
           "FROM invitados i JOIN instalaciones ins ON ins.id=i.instalacion_id JOIN socios s ON s.id=i.socio_id "
           "WHERE i.fecha_visita=?")
    args = [fecha]
    if instalacion_id:
        sql += " AND i.instalacion_id=?"
        args.append(instalacion_id)
    sql += " ORDER BY ins.nombre, i.nombre"
    return query(sql, args)
