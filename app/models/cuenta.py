"""Módulo 7: Estado de cuenta, cargos, pagos manuales y morosidad. Incluye las tareas programadas."""
import re
from datetime import date, timedelta

from flask import current_app

from app.db import ReglaError, ahora_txt, execute, get_db, hoy, one, query
from app.models import config, membresia, notificacion, reserva, socio

_PERIODO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# Estado "efectivo": un cargo pendiente con la fecha límite vencida se muestra como vencido.
_ESTADO_EFECTIVO = "CASE WHEN c.estado='pendiente' AND c.fecha_limite < ? THEN 'vencido' ELSE c.estado END"


def periodo_valido(p):
    if not _PERIODO.match(p or ""):
        raise ReglaError("El periodo debe tener el formato AAAA-MM (por ejemplo 2026-11).")
    return p


def periodo_actual():
    return hoy().strftime("%Y-%m")


# ---------------------------------------------------------------- generación
def generar_periodo(periodo):
    """Genera (de forma idempotente) las cuotas y cargos de servicios del periodo y los estados de cuenta."""
    periodo_valido(periodo)
    db = get_db()
    limite = (hoy() + timedelta(days=config.obtener_int("dias_plazo_pago", 15))).isoformat()
    n_cuotas = n_serv = 0

    for m in db.execute("SELECT m.* FROM membresias m JOIN socios s ON s.id=m.socio_id "
                        "WHERE m.estado='activa' AND s.estado='activo' AND m.cuota > 0").fetchall():
        cur = db.execute(
            "INSERT OR IGNORE INTO cargos(socio_id, periodo, tipo, concepto, monto, fecha_limite, membresia_id) "
            "VALUES (?,?, 'cuota', ?, ?, ?, ?)",
            (m["socio_id"], periodo, f"Cuota de membresía {m['tipo']} {periodo}", m["cuota"], limite, m["id"]))
        n_cuotas += cur.rowcount

    filas = db.execute(
        "SELECT r.id AS rid, r.socio_id, r.fecha, i.nombre AS instalacion, rs.servicio_id, rs.costo, sa.nombre AS servicio "
        "FROM reservas r JOIN reserva_servicios rs ON rs.reserva_id=r.id JOIN servicios_adicionales sa ON sa.id=rs.servicio_id "
        "JOIN instalaciones i ON i.id=r.instalacion_id "
        "WHERE r.estado IN ('confirmada','finalizada') AND substr(r.fecha,1,7)=? AND rs.costo > 0", (periodo,)).fetchall()
    for f in filas:
        cur = db.execute(
            "INSERT OR IGNORE INTO cargos(socio_id, periodo, tipo, concepto, monto, fecha_limite, reserva_id, servicio_id) "
            "VALUES (?,?, 'servicio', ?, ?, ?, ?, ?)",
            (f["socio_id"], periodo, f"{f['servicio']} – {f['instalacion']} ({f['fecha']})", f["costo"], limite, f["rid"], f["servicio_id"]))
        n_serv += cur.rowcount
    db.commit()

    nuevos = 0
    socios_ids = [r["socio_id"] for r in db.execute(
        "SELECT DISTINCT socio_id FROM cargos WHERE periodo=? AND estado<>'anulado'", (periodo,)).fetchall()]
    for sid in socios_ids:
        if one("SELECT 1 FROM estados_cuenta WHERE socio_id=? AND periodo=?", (sid, periodo)):
            continue
        execute("INSERT INTO estados_cuenta(socio_id, periodo, generado_en) VALUES (?,?,?)", (sid, periodo, ahora_txt()))
        nuevos += 1
        s = socio.por_id(sid)
        res = resumen(sid, periodo)
        notificacion.notificar(s, "estado_cuenta", {
            "periodo": periodo, "total": config.moneda(res["total"]), "pendiente": config.moneda(res["pendiente"]),
            "enlace": current_app.config["BASE_URL"].rstrip("/") + f"/socio/cuenta/{periodo}"})
    return {"cuotas": n_cuotas, "servicios": n_serv, "estados_cuenta": nuevos}


# ---------------------------------------------------------------- consultas
def cargos_socio(socio_id, periodo):
    return query(f"SELECT c.*, {_ESTADO_EFECTIVO} AS estado_efectivo FROM cargos c "
                 "WHERE c.socio_id=? AND c.periodo=? AND c.estado<>'anulado' ORDER BY c.tipo DESC, c.id",
                 (hoy().isoformat(), socio_id, periodo))


def resumen(socio_id, periodo):
    cargos = cargos_socio(socio_id, periodo)
    total = sum(c["monto"] for c in cargos)
    pagado = sum(c["monto"] for c in cargos if c["estado_efectivo"] == "pagado")
    vencido = sum(c["monto"] for c in cargos if c["estado_efectivo"] == "vencido")
    pendiente = sum(c["monto"] for c in cargos if c["estado_efectivo"] in ("pendiente", "vencido"))
    return {"cargos": cargos, "total": total, "pagado": pagado, "vencido": vencido, "pendiente": pendiente}


def periodos_socio(socio_id):
    filas = query("SELECT * FROM estados_cuenta WHERE socio_id=? ORDER BY periodo DESC", (socio_id,))
    return [{"periodo": f["periodo"], "generado_en": f["generado_en"], **{k: v for k, v in resumen(socio_id, f["periodo"]).items() if k != "cargos"}}
            for f in filas]


def estado_existe(socio_id, periodo):
    return one("SELECT 1 FROM estados_cuenta WHERE socio_id=? AND periodo=?", (socio_id, periodo)) is not None


def listar_cargos(periodo="", estado="", busqueda=""):
    sql = (f"SELECT c.*, s.nombre AS socio_nombre, s.cedula AS socio_cedula, {_ESTADO_EFECTIVO} AS estado_efectivo "
           "FROM cargos c JOIN socios s ON s.id=c.socio_id WHERE c.estado<>'anulado'")
    args = [hoy().isoformat()]
    if periodo:
        sql += " AND c.periodo=?"; args.append(periodo)
    if busqueda:
        sql += " AND (s.nombre LIKE ? OR s.cedula LIKE ?)"; like = f"%{busqueda.strip()}%"; args += [like, like]
    filas = query(sql + " ORDER BY s.nombre, c.id", args)
    if estado in ("pagado", "pendiente", "vencido"):
        filas = [f for f in filas if f["estado_efectivo"] == estado]
    return filas


def resumen_por_socio(periodo, estado="", busqueda=""):
    """Una fila por socio con total, pagado, pendiente y sus cargos pendientes (pantalla de Cobros)."""
    por_socio = {}
    for c in listar_cargos(periodo, "", busqueda):
        f = por_socio.setdefault(c["socio_id"], {"socio_id": c["socio_id"], "nombre": c["socio_nombre"], "total": 0.0, "pagado": 0.0,
                                                 "pendiente": 0.0, "vencido": False, "cargos_pendientes": []})
        f["total"] += c["monto"]
        if c["estado_efectivo"] == "pagado":
            f["pagado"] += c["monto"]
        else:
            f["pendiente"] += c["monto"]
            f["cargos_pendientes"].append(c)
            f["vencido"] = f["vencido"] or c["estado_efectivo"] == "vencido"
    for f in por_socio.values():
        f["estado"] = "pagado" if not f["cargos_pendientes"] else ("vencido" if f["vencido"] else "pendiente")
    filas = sorted(por_socio.values(), key=lambda f: f["nombre"])
    return [f for f in filas if not estado or f["estado"] == estado]


def periodos_disponibles():
    """Periodos con cargos (más recientes primero) más el actual."""
    filas = [r["periodo"] for r in query("SELECT DISTINCT periodo FROM cargos ORDER BY periodo DESC")]
    actual = periodo_actual()
    return filas if actual in filas else [actual] + filas


def registrar_pago(cargo_id, admin_id, fecha_pago=None):
    c = one("SELECT * FROM cargos WHERE id=?", (cargo_id,))
    if c is None:
        raise ReglaError("Cargo no encontrado.")
    if c["estado"] != "pendiente":
        raise ReglaError("Solo se puede registrar el pago de un cargo pendiente o vencido.")
    fecha = ahora_txt()
    if fecha_pago:
        try:
            fecha = date.fromisoformat(fecha_pago).isoformat() + " 12:00:00"
        except ValueError:
            raise ReglaError("La fecha de pago no es válida.")
        if fecha[:10] > hoy().isoformat():
            raise ReglaError("La fecha de pago no puede ser futura.")
    execute("UPDATE cargos SET estado='pagado', fecha_pago=?, registrado_por=? WHERE id=?", (fecha, admin_id, cargo_id))


def morosos(min_dias=0):
    """Socios con cargos vencidos, con el atraso máximo y monto adeudado."""
    hoy_d = hoy()
    filas = query("SELECT c.*, s.nombre AS socio_nombre, s.cedula AS socio_cedula, s.correo AS socio_correo, s.telefono AS socio_telefono "
                  "FROM cargos c JOIN socios s ON s.id=c.socio_id WHERE c.estado='pendiente' AND c.fecha_limite < ? "
                  "ORDER BY s.nombre", (hoy_d.isoformat(),))
    por_socio = {}
    for f in filas:
        dias = (hoy_d - date.fromisoformat(f["fecha_limite"])).days
        m = por_socio.setdefault(f["socio_id"], {
            "socio_id": f["socio_id"], "nombre": f["socio_nombre"], "cedula": f["socio_cedula"], "correo": f["socio_correo"],
            "telefono": f["socio_telefono"], "cargos": 0, "monto": 0.0, "dias_atraso": 0, "tipos": set(), "periodo": f["periodo"]})
        m["cargos"] += 1
        m["tipos"].add(f["tipo"])
        m["periodo"] = min(m["periodo"], f["periodo"])
        m["monto"] += f["monto"]
        m["dias_atraso"] = max(m["dias_atraso"], dias)
    lista = [m for m in por_socio.values() if m["dias_atraso"] >= min_dias]
    for m in lista:
        d = m["dias_atraso"]
        m["rubro"] = "Cuota de membresía" if m["tipos"] == {"cuota"} else ("Servicios adicionales" if m["tipos"] == {"servicio"} else "Cuota y servicios")
        m["tramo"] = "1–30 días" if d <= 30 else ("31–60 días" if d <= 60 else "Más de 60 días")
    return sorted(lista, key=lambda m: m["dias_atraso"], reverse=True)


# ---------------------------------------------------------------- tareas programadas
def tareas_diarias():
    """Mantenimiento diario: membresías vencidas, reservas finalizadas y recordatorios de pago."""
    resultado = {"membresias_vencidas": membresia.refrescar_vencimientos()}
    reserva.finalizar_pasadas()
    hoy_d = hoy()
    aviso = (hoy_d + timedelta(days=config.obtener_int("dias_aviso_vencimiento", 3))).isoformat()
    recordatorios = vencidos = 0
    for c in query("SELECT c.*, s.nombre, s.correo FROM cargos c JOIN socios s ON s.id=c.socio_id "
                   "WHERE c.estado='pendiente' AND c.recordatorio_enviado=0 AND c.fecha_limite BETWEEN ? AND ?",
                   (hoy_d.isoformat(), aviso)):
        notificacion.notificar({"id": c["socio_id"], "nombre": c["nombre"], "correo": c["correo"]}, "recordatorio_pago",
                               {"concepto": c["concepto"], "monto": config.moneda(c["monto"]), "fecha_limite": c["fecha_limite"]})
        execute("UPDATE cargos SET recordatorio_enviado=1 WHERE id=?", (c["id"],))
        recordatorios += 1
    for c in query("SELECT c.*, s.nombre, s.correo FROM cargos c JOIN socios s ON s.id=c.socio_id "
                   "WHERE c.estado='pendiente' AND c.vencido_notificado=0 AND c.fecha_limite < ?", (hoy_d.isoformat(),)):
        notificacion.notificar({"id": c["socio_id"], "nombre": c["nombre"], "correo": c["correo"]}, "pago_vencido",
                               {"concepto": c["concepto"], "monto": config.moneda(c["monto"]), "fecha_limite": c["fecha_limite"]})
        execute("UPDATE cargos SET vencido_notificado=1 WHERE id=?", (c["id"],))
        vencidos += 1
    resultado.update(recordatorios=recordatorios, avisos_vencido=vencidos)
    return resultado
