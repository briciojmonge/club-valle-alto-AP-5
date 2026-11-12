"""Controlador del portal del socio: perfil, membresía, invitados, reservas y estado de cuenta."""
from datetime import date, timedelta

from flask import Blueprint, Response, abort, flash, g, redirect, render_template, request, url_for

from app.db import ReglaError, hoy
from app.models import config, cuenta, instalacion, invitado, membresia, reserva, socio
from app.services import pdf
from app.services.security import socio_requerido

bp = Blueprint("portal", __name__, url_prefix="/socio")


@bp.get("")
@socio_requerido
def inicio():
    sid = g.socio["id"]
    membresia.refrescar_vencimientos()
    m = membresia.vigente(sid)
    proximas = [r for r in reserva.listar_socio(sid) if r["estado"] in ("pendiente", "confirmada")
                and r["fecha"] >= hoy().isoformat()][::-1][:5]
    res = cuenta.resumen(sid, cuenta.periodo_actual())
    return render_template("socio/inicio.html", m=m, proximas=proximas, res=res, periodo=cuenta.periodo_actual(),
                           cupo=invitado.cupo(sid, hoy().strftime("%Y-%m")))


# ---------------------------------------------------------------- perfil
@bp.route("/perfil", methods=["GET", "POST"])
@socio_requerido
def perfil():
    if request.method == "POST":
        try:
            socio.actualizar_perfil(g.socio["id"], request.form)
            flash("Sus datos se actualizaron correctamente.", "ok")
            return redirect(url_for("portal.perfil"))
        except ReglaError as e:
            flash(str(e), "error")
            return render_template("socio/perfil.html", f=request.form)
    return render_template("socio/perfil.html", f=g.socio)


@bp.route("/password", methods=["GET", "POST"])
@socio_requerido
def password():
    if request.method == "POST":
        try:
            socio.cambiar_password(g.socio["id"], request.form.get("actual"), request.form.get("nueva"), request.form.get("nueva2"))
            flash("Contraseña actualizada.", "ok")
            return redirect(url_for("portal.inicio"))
        except ReglaError as e:
            flash(str(e), "error")
    return render_template("socio/password.html")


# ---------------------------------------------------------------- membresía y beneficiarios
@bp.route("/membresia", methods=["GET", "POST"], endpoint="membresia")
@socio_requerido
def membresia_pagina():
    sid = g.socio["id"]
    if request.method == "POST":
        try:
            membresia.crear(sid, request.form.get("tipo"), f"socio:{sid}")
            flash("Membresía registrada correctamente.", "ok")
            return redirect(url_for("portal.membresia"))
        except ReglaError as e:
            flash(str(e), "error")
    membresia.refrescar_vencimientos()
    m = membresia.vigente(sid)
    t = config.tipo(m["tipo"]) if m else None
    return render_template("socio/membresia.html", m=m, t=t, tipos=config.tipos(),
                           beneficiarios=membresia.beneficiarios(m["id"]) if m else [],
                           historial=membresia.historial(m["id"]) if m else [], f=request.form)


@bp.post("/membresia/cambiar")
@socio_requerido
def membresia_cambiar():
    m = membresia.vigente(g.socio["id"])
    if m is None:
        abort(404)
    try:
        membresia.cambiar_tipo(m["id"], request.form.get("tipo"), f"socio:{g.socio['id']}")
        flash("Tipo de membresía actualizado.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("portal.membresia"))


@bp.post("/membresia/beneficiarios/<int:bid>/editar")
@socio_requerido
def beneficiario_editar(bid):
    m = membresia.vigente(g.socio["id"])
    if m is None:
        abort(404)
    try:
        membresia.editar_beneficiario(m["id"], bid, request.form)
        flash("Beneficiario actualizado.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("portal.membresia"))


@bp.post("/membresia/beneficiarios")
@socio_requerido
def beneficiario_nuevo():
    m = membresia.vigente(g.socio["id"])
    if m is None:
        abort(404)
    try:
        membresia.agregar_beneficiario(m["id"], request.form)
        flash("Beneficiario agregado.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("portal.membresia"))


@bp.post("/membresia/beneficiarios/<int:bid>/eliminar")
@socio_requerido
def beneficiario_eliminar(bid):
    m = membresia.vigente(g.socio["id"])
    if m is None:
        abort(404)
    membresia.eliminar_beneficiario(m["id"], bid)
    flash("Beneficiario eliminado.", "ok")
    return redirect(url_for("portal.membresia"))


# ---------------------------------------------------------------- invitados
@bp.route("/invitados", methods=["GET", "POST"])
@socio_requerido
def invitados():
    sid = g.socio["id"]
    if request.method == "POST":
        try:
            invitado.registrar(sid, request.form)
            flash("Invitado registrado.", "ok")
            return redirect(url_for("portal.invitados"))
        except ReglaError as e:
            flash(str(e), "error")
    mes = hoy().strftime("%Y-%m")
    usados, limite = invitado.cupo(sid, mes)
    return render_template("socio/invitados.html", lista=invitado.listar_socio(sid), usados=usados, limite=limite,
                           opciones=[(i["id"], i["nombre"]) for i in instalacion.listar(solo_activas=True)],
                           m=membresia.vigente(sid), f=request.form)


@bp.post("/invitados/<int:iid>/eliminar")
@socio_requerido
def invitado_eliminar(iid):
    try:
        invitado.eliminar(g.socio["id"], iid)
        flash("Invitado eliminado.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("portal.invitados"))


# ---------------------------------------------------------------- reservas
@bp.get("/reservas")
@socio_requerido
def reservas():
    pestana = request.args.get("estado", "activas")
    if pestana not in ("activas", "finalizadas", "canceladas"):
        pestana = "activas"
    grupos = {"activas": [], "finalizadas": [], "canceladas": []}
    for r in reserva.listar_socio(g.socio["id"]):
        if r["estado"] in ("pendiente", "confirmada"):
            grupos["activas"].append(r)
        elif r["estado"] == "finalizada":
            grupos["finalizadas"].append(r)
        else:
            grupos["canceladas"].append(r)
    return render_template("socio/reservas.html", lista=grupos[pestana], pestana=pestana, cuentas={k: len(v) for k, v in grupos.items()})


def _horas(inst, extra=()):
    """Horas en punto disponibles para elegir en los formularios de reserva."""
    ap, ci = int(inst["hora_apertura"][:2]), int(inst["hora_cierre"][:2])
    horas = {f"{h:02d}:00" for h in range(ap, ci + 1)} | {e for e in extra if e}
    return sorted(horas)


def _datos_form_reserva(inst_id):
    insts = instalacion.listar(solo_activas=True)
    inst = instalacion.por_id(inst_id) if inst_id else (insts[0] if insts else None)
    return insts, inst


@bp.route("/reservas/nueva", methods=["GET", "POST"])
@socio_requerido
def reserva_nueva():
    if request.method == "POST":
        try:
            reserva.crear(g.socio["id"], request.form)
            flash("Reserva registrada. Recibirá la notificación por correo.", "ok")
            return redirect(url_for("portal.reservas"))
        except ReglaError as e:
            flash(str(e), "error")
    inst_id = request.values.get("instalacion_id", type=int)
    insts, inst = _datos_form_reserva(inst_id)
    fecha = request.values.get("fecha") or hoy().isoformat()
    franjas = reserva.ocupacion_por_franja(inst, fecha) if inst else []
    return render_template("socio/reserva_form.html", insts=insts, inst=inst, servicios=instalacion.servicios(inst["id"]) if inst else [],
                           f=request.form if request.method == "POST" else request.args, reserva=None, franjas=franjas,
                           fecha=fecha, elegidos=request.form.getlist("servicios"), m=membresia.vigente(g.socio["id"]),
                           horas=_horas(inst, (request.values.get("hora_inicio"), request.values.get("hora_fin"))) if inst else [])


@bp.route("/reservas/<int:rid>", methods=["GET", "POST"])
@socio_requerido
def reserva_editar(rid):
    r = reserva.por_id(rid)
    if r is None or r["socio_id"] != g.socio["id"]:
        abort(404)
    if request.method == "POST":
        try:
            reserva.modificar(rid, request.form, socio_id=g.socio["id"])
            flash("Reserva modificada.", "ok")
            return redirect(url_for("portal.reservas"))
        except ReglaError as e:
            flash(str(e), "error")
    inst = instalacion.por_id(r["instalacion_id"])
    fecha = (request.form.get("fecha") if request.method == "POST" else None) or r["fecha"]
    elegidos = request.form.getlist("servicios") if request.method == "POST" else [str(s["servicio_id"]) for s in reserva.servicios_de(rid)]
    return render_template("socio/reserva_form.html", insts=[inst], inst=inst, servicios=instalacion.servicios(inst["id"]),
                           f=request.form if request.method == "POST" else r, reserva=r,
                           franjas=reserva.ocupacion_por_franja(inst, fecha), fecha=fecha, elegidos=elegidos, m=None,
                           horas=_horas(inst, (r["hora_inicio"], r["hora_fin"], request.form.get("hora_inicio"), request.form.get("hora_fin"))))


@bp.post("/reservas/<int:rid>/cancelar")
@socio_requerido
def reserva_cancelar(rid):
    try:
        reserva.cancelar(rid, socio_id=g.socio["id"])
        flash("Reserva cancelada.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("portal.reservas"))


# ---------------------------------------------------------------- estado de cuenta
def _vista_cuenta(periodo):
    sid = g.socio["id"]
    periodos = cuenta.periodos_socio(sid)
    if periodo is None:
        periodo = periodos[0]["periodo"] if periodos else cuenta.periodo_actual()
    existe = cuenta.estado_existe(sid, periodo)
    res = cuenta.resumen(sid, periodo) if existe else None
    return render_template("socio/cuenta.html", periodo=periodo, res=res, periodos=periodos)


@bp.get("/cuenta")
@socio_requerido
def cuenta_historial():
    return _vista_cuenta(None)


@bp.get("/cuenta/<periodo>")
@socio_requerido
def cuenta_detalle(periodo):
    try:
        cuenta.periodo_valido(periodo)
    except ReglaError:
        abort(404)
    if not cuenta.estado_existe(g.socio["id"], periodo):
        abort(404)
    return _vista_cuenta(periodo)


@bp.get("/cuenta/<periodo>/pdf")
@socio_requerido
def cuenta_pdf(periodo):
    try:
        cuenta.periodo_valido(periodo)
    except ReglaError:
        abort(404)
    sid = g.socio["id"]
    fila = cuenta.estado_existe(sid, periodo)
    if not fila:
        abort(404)
    m = membresia.vigente(sid)
    from app.db import one
    gen = one("SELECT generado_en FROM estados_cuenta WHERE socio_id=? AND periodo=?", (sid, periodo))["generado_en"]
    data = pdf.estado_cuenta_pdf(g.socio, periodo, cuenta.resumen(sid, periodo), m["tipo"] if m else None, gen)
    return Response(data, mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=estado-de-cuenta-{periodo}.pdf"})
