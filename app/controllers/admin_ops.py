"""Controlador de administración (operación): instalaciones, reservas, calendario, ocupación, reportes e invitados."""
from datetime import date, timedelta

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app.db import ReglaError, hoy
from app.models import instalacion, invitado, reserva
from app.services import validators as v
from app.services.security import admin_requerido

bp = Blueprint("admin_ops", __name__, url_prefix="/admin")


# ---------------------------------------------------------------- instalaciones
@bp.route("/instalaciones", methods=["GET", "POST"])
@admin_requerido("instalaciones")
def instalaciones():
    if request.method == "POST":
        try:
            iid = instalacion.crear(request.form)
            flash("Instalación creada.", "ok")
            return redirect(url_for("admin_ops.instalacion_editar", iid=iid))
        except ReglaError as e:
            flash(str(e), "error")
    lista = instalacion.listar()
    return render_template("admin/instalaciones.html", lista=lista, f=request.form, tipos=instalacion.TIPOS, modos=instalacion.MODOS,
                           servicios={i["id"]: instalacion.servicios(i["id"]) for i in lista}, hoy_iso=hoy().isoformat(),
                           abrir_nueva=request.method == "POST")


@bp.route("/instalaciones/<int:iid>", methods=["GET", "POST"])
@admin_requerido("instalaciones")
def instalacion_editar(iid):
    inst = instalacion.por_id(iid)
    if inst is None:
        abort(404)
    if request.method == "POST":
        try:
            instalacion.actualizar(iid, request.form)
            flash("Instalación actualizada.", "ok")
            return redirect(url_for("admin_ops.instalacion_editar", iid=iid))
        except ReglaError as e:
            flash(str(e), "error")
    return render_template("admin/instalacion_form.html", inst=inst, f=request.form if request.method == "POST" else inst,
                           servicios=instalacion.servicios(iid, solo_activos=False),
                           bloqueos=instalacion.bloqueos(iid, hoy().isoformat()), tipos=instalacion.TIPOS, modos=instalacion.MODOS)


@bp.post("/instalaciones/<int:iid>/servicios")
@admin_requerido("instalaciones")
def servicio_nuevo(iid):
    if instalacion.por_id(iid) is None:
        abort(404)
    try:
        instalacion.crear_servicio(iid, request.form)
        flash("Servicio adicional agregado.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("admin_ops.instalacion_editar", iid=iid))


@bp.post("/instalaciones/<int:iid>/servicios/<int:sid>")
@admin_requerido("instalaciones")
def servicio_estado(iid, sid):
    instalacion.cambiar_servicio(iid, sid, request.form.get("activo") == "1")
    flash("Servicio actualizado.", "ok")
    return redirect(url_for("admin_ops.instalacion_editar", iid=iid))


@bp.post("/instalaciones/<int:iid>/bloqueos")
@admin_requerido("instalaciones")
def bloqueo_nuevo(iid):
    if instalacion.por_id(iid) is None:
        abort(404)
    try:
        instalacion.crear_bloqueo(iid, request.form, g.admin["id"])
        flash("Instalación bloqueada en el horario indicado.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    if request.form.get("volver") == "lista":
        return redirect(url_for("admin_ops.instalaciones"))
    return redirect(url_for("admin_ops.instalacion_editar", iid=iid))


@bp.post("/instalaciones/<int:iid>/bloqueos/<int:bid>/eliminar")
@admin_requerido("instalaciones")
def bloqueo_eliminar(iid, bid):
    instalacion.eliminar_bloqueo(bid)
    flash("Bloqueo eliminado.", "ok")
    return redirect(url_for("admin_ops.instalacion_editar", iid=iid))


# ---------------------------------------------------------------- reservas
@bp.get("/reservas")
@admin_requerido("reservas")
def reservas():
    a = request.args
    lista = reserva.listar(a.get("desde", ""), a.get("hasta", ""), a.get("instalacion_id", ""), a.get("estado", ""), a.get("q", ""))
    return render_template("admin/reservas.html", lista=lista, instalaciones=instalacion.listar(), a=a)


@bp.get("/reservas/<int:rid>")
@admin_requerido("reservas")
def reserva_detalle(rid):
    r = reserva.por_id(rid)
    if r is None:
        abort(404)
    srv = reserva.servicios_de(rid)
    return render_template("admin/reserva_detalle.html", r=r, servicios=srv, total=sum(s["costo"] for s in srv),
                           invitados=reserva.invitados_de_reserva(r))


@bp.post("/reservas/<int:rid>/confirmar")
@admin_requerido("reservas")
def reserva_confirmar(rid):
    try:
        reserva.confirmar(rid)
        flash("Reserva confirmada y notificada al socio.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("admin_ops.reserva_detalle", rid=rid))


@bp.post("/reservas/<int:rid>/cancelar")
@admin_requerido("reservas")
def reserva_cancelar(rid):
    try:
        reserva.cancelar(rid)
        flash("Reserva cancelada y notificada al socio.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("admin_ops.reserva_detalle", rid=rid))


@bp.route("/reservas/<int:rid>/editar", methods=["GET", "POST"])
@admin_requerido("reservas")
def reserva_editar(rid):
    r = reserva.por_id(rid)
    if r is None:
        abort(404)
    if request.method == "POST":
        try:
            reserva.modificar(rid, request.form)
            flash("Reserva modificada y notificada al socio.", "ok")
            return redirect(url_for("admin_ops.reserva_detalle", rid=rid))
        except ReglaError as e:
            flash(str(e), "error")
    inst = instalacion.por_id(r["instalacion_id"])
    elegidos = request.form.getlist("servicios") if request.method == "POST" else [str(s["servicio_id"]) for s in reserva.servicios_de(rid)]
    return render_template("admin/reserva_form.html", r=r, inst=inst, servicios=instalacion.servicios(inst["id"]),
                           f=request.form if request.method == "POST" else r, elegidos=elegidos)


# ---------------------------------------------------------------- calendario, ocupación y reportes
def _instalacion_seleccionada():
    insts = instalacion.listar()
    iid = request.args.get("instalacion_id", type=int)
    inst = next((i for i in insts if i["id"] == iid), insts[0] if insts else None)
    return insts, inst


def _iniciales(nombre):
    partes = nombre.split()
    apellido = partes[-2] if len(partes) >= 3 else (partes[1] if len(partes) == 2 else "")
    return f"{partes[0][0]}. {apellido}".strip()


@bp.get("/calendario")
@admin_requerido("reservas")
def calendario():
    insts, inst = _instalacion_seleccionada()
    try:
        base = v.fecha(request.args.get("fecha") or hoy().isoformat())
    except ReglaError:
        base = hoy()
    lunes = base - timedelta(days=base.weekday())
    dias = reserva.calendario_semana(inst, lunes) if inst else []
    horas, eventos, detalle = [], [], None
    if inst:
        ap, ci = int(inst["hora_apertura"][:2]), -(-v.minutos(inst["hora_cierre"]) // 60)
        horas = [(f"{h:02d}:00", h - ap + 2) for h in range(ap, ci)]
        elegido = request.args.get("reserva", type=int)
        for col, d in enumerate(dias, start=2):
            for r in d["reservas"]:
                ini, fin = v.minutos(r["hora_inicio"]), v.minutos(r["hora_fin"])
                fila, largo = ini // 60 - ap + 2, max(1, -(-fin // 60) - ini // 60)
                eventos.append({"clase": f"r{fila} c{col} h{largo}" + (" pendiente" if r["estado"] == "pendiente" else ""), "texto": _iniciales(r["socio_nombre"]),
                                "id": r["id"], "elegido": r["id"] == elegido, "bloqueo": False, "fecha": d["fecha"].isoformat(),
                                "titulo": f"{r['socio_nombre']} · {r['hora_inicio']}–{r['hora_fin']}"})
            for b in d["bloqueos"]:
                ini, fin = v.minutos(b["hora_inicio"]), v.minutos(b["hora_fin"])
                fila, largo = ini // 60 - ap + 2, max(1, -(-fin // 60) - ini // 60)
                eventos.append({"clase": f"r{fila} c{col} h{largo} bloqueo", "texto": "Bloqueo", "id": None, "elegido": False, "bloqueo": True,
                                "fecha": d["fecha"].isoformat(), "titulo": f"Bloqueo: {b['motivo']} ({b['hora_inicio']}–{b['hora_fin']})"})
        if elegido:
            det = reserva.por_id(elegido)
            if det and det["instalacion_id"] == inst["id"]:
                from app.db import query
                detalle = {"r": det, "socio": query("SELECT nombre FROM socios WHERE id=?", (det["socio_id"],))[0]["nombre"],
                           "servicios": query("SELECT s.nombre FROM reserva_servicios rs JOIN servicios_adicionales s ON s.id=rs.servicio_id WHERE rs.reserva_id=?", (elegido,)),
                           "invitados": query("SELECT nombre FROM invitados WHERE socio_id=? AND fecha_visita=? AND instalacion_id=?",
                                              (det["socio_id"], det["fecha"], det["instalacion_id"]))}
    return render_template("admin/calendario.html", insts=insts, inst=inst, dias=dias, lunes=lunes, horas=horas, eventos=eventos, detalle=detalle,
                           hoy_iso=hoy().isoformat(), anterior=(lunes - timedelta(days=7)).isoformat(), siguiente=(lunes + timedelta(days=7)).isoformat(),
                           fin_semana=lunes + timedelta(days=6))


def _bandas(inst, fecha):
    """Ocupación por bandas de 2 horas (promedio de las franjas horarias) para la pantalla de ocupación."""
    franjas = reserva.ocupacion_por_franja(inst, fecha)
    bandas = []
    for k in range(0, len(franjas), 2):
        grupo = franjas[k:k + 2]
        pcts = [(100 if f["reservas"] else 0) if inst["modo"] == "exclusiva" else f["pct"] for f in grupo]
        bandas.append({"inicio": grupo[0]["inicio"], "fin": grupo[-1]["fin"], "pct": round(sum(pcts) / len(pcts))})
    return bandas


@bp.get("/ocupacion")
@admin_requerido("reservas")
def ocupacion():
    insts, inst = _instalacion_seleccionada()
    hoy_d = hoy()
    periodo = request.args.get("periodo") or hoy_d.strftime("%Y-%m")
    try:
        anio, mes = (int(x) for x in periodo.split("-"))
        primero = date(anio, mes, 1)
    except (ValueError, TypeError):
        periodo, primero = hoy_d.strftime("%Y-%m"), hoy_d.replace(day=1)
    ultimo = (primero.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    reserva.finalizar_pasadas()
    filas = reserva.reporte_uso(primero.isoformat(), ultimo.isoformat())
    maximo = max((f["reservas"] for f in filas), default=0)
    periodos = []
    for k in range(-6, 3):
        y, m = divmod(hoy_d.year * 12 + hoy_d.month - 1 + k, 12)
        periodos.append(f"{y}-{m + 1:02d}")
    return render_template("admin/ocupacion.html", insts=insts, inst=inst, bandas=_bandas(inst, hoy_d.isoformat()) if inst else [],
                           filas=filas, maximo=maximo, periodo=periodo, periodos=periodos,
                           mayor=filas[0] if filas and filas[0]["reservas"] else None, menor=filas[-1] if filas else None)


@bp.get("/reportes/uso")
@admin_requerido("reportes_uso")
def reporte_uso():
    hoy_d = hoy()
    try:
        desde = v.fecha(request.args.get("desde") or hoy_d.replace(day=1).isoformat(), "La fecha inicial")
        hasta = v.fecha(request.args.get("hasta") or hoy_d.isoformat(), "La fecha final")
        if desde > hasta:
            raise ReglaError("La fecha inicial no puede ser posterior a la final.")
    except ReglaError as e:
        flash(str(e), "error")
        desde, hasta = hoy_d.replace(day=1), hoy_d
    filas = reserva.reporte_uso(desde.isoformat(), hasta.isoformat())
    return render_template("admin/reporte_uso.html", filas=filas, desde=desde.isoformat(), hasta=hasta.isoformat(),
                           mayor=filas[0] if filas and filas[0]["reservas"] else None,
                           menor=filas[-1] if filas else None)


# ---------------------------------------------------------------- invitados esperados (recepción)
@bp.get("/invitados")
@admin_requerido("invitados")
def invitados_esperados():
    try:
        fecha = v.fecha(request.args.get("fecha") or hoy().isoformat()).isoformat()
    except ReglaError as e:
        flash(str(e), "error")
        fecha = hoy().isoformat()
    iid = request.args.get("instalacion_id", type=int)
    return render_template("admin/invitados.html", lista=invitado.esperados(fecha, iid), fecha=fecha,
                           instalaciones=instalacion.listar(), iid=iid)
