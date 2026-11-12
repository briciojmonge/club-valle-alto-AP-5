"""Controlador de administración (cobros): membresías, estados de cuenta, pagos y morosidad."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app.db import ReglaError, hoy
from app.models import config, cuenta, membresia, socio
from app.services import validators as v
from app.services.security import admin_requerido

bp = Blueprint("admin_cobros", __name__, url_prefix="/admin")


# ---------------------------------------------------------------- membresías (módulo 2, lado administrativo)
@bp.get("/membresias")
@admin_requerido("membresias")
def membresias():
    membresia.refrescar_vencimientos()
    a = request.args
    return render_template("admin/membresias.html", lista=membresia.listar(a.get("estado", ""), a.get("tipo", ""), a.get("q", "")),
                           tipos=config.tipos(), a=a)


@bp.route("/membresias/nueva", methods=["GET", "POST"])
@admin_requerido("membresias")
def membresia_nueva():
    if request.method == "POST":
        try:
            sid = v.entero(request.form.get("socio_id"), "El socio", 1)
            if socio.por_id(sid) is None:
                raise ReglaError("El socio seleccionado no existe.")
            tipo = request.form.get("tipo")
            cuota_txt = (request.form.get("cuota") or "").strip()
            cuota = v.monto(cuota_txt, "La cuota") if cuota_txt else None
            mid = membresia.crear(sid, tipo, f"admin:{g.admin['id']}", por_personal=True, cuota=cuota)
            flash("Membresía creada.", "ok")
            return redirect(url_for("admin_cobros.membresia_detalle", mid=mid))
        except ReglaError as e:
            flash(str(e), "error")
    sin = [s for s in socio.listar() if not s["membresia_tipo"]]
    return render_template("admin/membresia_nueva.html", socios=sin, tipos=config.tipos(), f=request.form)


@bp.get("/membresias/<int:mid>")
@admin_requerido("membresias")
def membresia_detalle(mid):
    m = membresia.por_id(mid)
    if m is None:
        abort(404)
    return render_template("admin/membresia_detalle.html", m=m, t=config.tipo(m["tipo"]), tipos=config.tipos(),
                           historial=membresia.historial(mid), beneficiarios=membresia.beneficiarios(mid))


@bp.post("/membresias/<int:mid>/modificar")
@admin_requerido("membresias")
def membresia_modificar(mid):
    try:
        membresia.modificar(mid, request.form.get("tipo"), v.monto(request.form.get("cuota"), "La cuota"),
                            v.fecha(request.form.get("fecha_renovacion"), "La fecha de renovación").isoformat(), f"admin:{g.admin['id']}")
        flash("Membresía modificada.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("admin_cobros.membresia_detalle", mid=mid))


@bp.post("/membresias/<int:mid>/estado")
@admin_requerido("membresias")
def membresia_estado(mid):
    try:
        membresia.cambiar_estado(mid, request.form.get("estado"), request.form.get("motivo"), f"admin:{g.admin['id']}")
        flash("Estado de la membresía actualizado.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("admin_cobros.membresia_detalle", mid=mid))


@bp.post("/membresias/<int:mid>/renovar")
@admin_requerido("membresias")
def membresia_renovar(mid):
    try:
        membresia.renovar(mid, f"admin:{g.admin['id']}")
        flash("Membresía renovada y activada.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("admin_cobros.membresia_detalle", mid=mid))


@bp.post("/membresias/<int:mid>/beneficiarios")
@admin_requerido("membresias")
def membresia_beneficiario(mid):
    try:
        membresia.agregar_beneficiario(mid, request.form)
        flash("Beneficiario agregado.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("admin_cobros.membresia_detalle", mid=mid))


@bp.post("/membresias/<int:mid>/beneficiarios/<int:bid>/eliminar")
@admin_requerido("membresias")
def membresia_beneficiario_eliminar(mid, bid):
    membresia.eliminar_beneficiario(mid, bid)
    flash("Beneficiario eliminado.", "ok")
    return redirect(url_for("admin_cobros.membresia_detalle", mid=mid))


# ---------------------------------------------------------------- estado de cuenta (módulo 7, lado administrativo)
@bp.route("/cuentas", methods=["GET", "POST"])
@admin_requerido("cuentas")
def cuentas():
    if request.method == "POST":
        try:
            r = cuenta.generar_periodo((request.form.get("periodo") or "").strip())
            flash(f"Periodo generado: {r['cuotas']} cuota(s), {r['servicios']} cargo(s) de servicios y "
                  f"{r['estados_cuenta']} estado(s) de cuenta nuevo(s) notificado(s).", "ok")
            return redirect(url_for("admin_cobros.cuentas", periodo=request.form.get("periodo")))
        except ReglaError as e:
            flash(str(e), "error")
    periodo = request.args.get("periodo", cuenta.periodo_actual())
    estado = request.args.get("estado", "")
    q = request.args.get("q", "")
    return render_template("admin/cuentas.html", lista=cuenta.resumen_por_socio(periodo, estado, q), periodo=periodo, estado=estado, q=q,
                           periodos=cuenta.periodos_disponibles())


@bp.post("/cuentas/<int:cid>/pago")
@admin_requerido("cuentas")
def cuenta_pago(cid):
    try:
        cuenta.registrar_pago(cid, g.admin["id"], (request.form.get("fecha_pago") or "").strip() or None)
        flash("Pago registrado.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(request.form.get("volver") if (request.form.get("volver") or "").startswith("/admin/") else url_for("admin_cobros.cuentas"))


@bp.get("/morosos")
@admin_requerido("cuentas")
def morosos():
    min_dias = request.args.get("min_dias", 0, type=int) or 0
    return render_template("admin/morosos.html", lista=cuenta.morosos(min_dias), min_dias=min_dias)


@bp.post("/tareas")
@admin_requerido("cuentas")
def ejecutar_tareas():
    r = cuenta.tareas_diarias()
    flash(f"Tareas ejecutadas: {r['membresias_vencidas']} membresía(s) vencida(s), {r['recordatorios']} recordatorio(s) de pago "
          f"y {r['avisos_vencido']} aviso(s) de pago vencido.", "ok")
    return redirect(url_for("admin_cobros.cuentas"))
