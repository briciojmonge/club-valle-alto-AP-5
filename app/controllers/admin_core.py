"""Controlador de administración (núcleo): panel, socios, usuarios administradores, reglas y notificaciones."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app.db import ReglaError, hoy, one
from app.models import admin as admin_model
from app.models import config, cuenta, membresia, notificacion, reserva, socio
from app.services import validators as v
from app.services.security import admin_requerido

bp = Blueprint("admin_core", __name__, url_prefix="/admin")


@bp.get("")
@admin_requerido()
def panel():
    membresia.refrescar_vencimientos()
    reserva.finalizar_pasadas()
    h = hoy().isoformat()
    datos = {
        "socios_activos": one("SELECT COUNT(*) AS n FROM socios WHERE estado='activo'")["n"],
        "membresias_activas": one("SELECT COUNT(*) AS n FROM membresias WHERE estado='activa'")["n"],
        "reservas_hoy": one("SELECT COUNT(*) AS n FROM reservas WHERE fecha=? AND estado IN ('pendiente','confirmada','finalizada')", (h,))["n"],
        "reservas_pendientes": one("SELECT COUNT(*) AS n FROM reservas WHERE estado='pendiente'")["n"],
        "invitados_hoy": one("SELECT COUNT(*) AS n FROM invitados WHERE fecha_visita=?", (h,))["n"],
        "morosos": len(cuenta.morosos()),
    }
    return render_template("admin/panel.html", d=datos, hoy_reservas=reserva.listar(fecha_desde=h, fecha_hasta=h))


# ---------------------------------------------------------------- socios (módulo 5: gestión de cuentas)
@bp.get("/socios")
@admin_requerido("socios")
def socios():
    return render_template("admin/socios.html", lista=socio.listar(request.args.get("q", ""), request.args.get("estado", "")),
                           q=request.args.get("q", ""), estado=request.args.get("estado", ""))


@bp.get("/socios/<int:sid>")
@admin_requerido("socios")
def socio_detalle(sid):
    s = socio.por_id(sid)
    if s is None:
        abort(404)
    m = membresia.vigente(sid)
    return render_template("admin/socio_detalle.html", s=s, m=m, historial=membresia.historial(m["id"]) if m else [],
                           puede_membresias=admin_model.puede(g.admin["rol"], "membresias"))


@bp.post("/socios/<int:sid>/estado")
@admin_requerido("socios")
def socio_estado(sid):
    if socio.por_id(sid) is None:
        abort(404)
    try:
        socio.cambiar_estado(sid, request.form.get("estado"))
        flash("Estado de la cuenta actualizado.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("admin_core.socio_detalle", sid=sid))


@bp.post("/socios/<int:sid>/password")
@admin_requerido("socios")
def socio_password(sid):
    s = socio.por_id(sid)
    if s is None:
        abort(404)
    temporal = socio.restablecer_temporal(sid)
    # La contraseña temporal se muestra una sola vez; el socio deberá cambiarla al ingresar.
    return render_template("admin/socio_temporal.html", s=s, temporal=temporal)


# ---------------------------------------------------------------- usuarios administradores
@bp.route("/usuarios", methods=["GET", "POST"])
@admin_requerido("usuarios_admin")
def usuarios():
    if request.method == "POST":
        try:
            admin_model.crear(request.form)
            flash("Administrador registrado.", "ok")
            return redirect(url_for("admin_core.usuarios"))
        except ReglaError as e:
            flash(str(e), "error")
    return render_template("admin/usuarios.html", lista=admin_model.listar(), f=request.form)


@bp.post("/usuarios/<int:aid>/activo")
@admin_requerido("usuarios_admin")
def usuario_activo(aid):
    if admin_model.por_id(aid) is None:
        abort(404)
    try:
        admin_model.cambiar_activo(aid, request.form.get("activo") == "1", g.admin["id"])
        flash("Usuario actualizado.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("admin_core.usuarios"))


@bp.post("/usuarios/<int:aid>/rol")
@admin_requerido("usuarios_admin")
def usuario_rol(aid):
    if admin_model.por_id(aid) is None:
        abort(404)
    try:
        admin_model.cambiar_rol(aid, request.form.get("rol"), g.admin["id"])
        flash("Rol actualizado.", "ok")
    except ReglaError as e:
        flash(str(e), "error")
    return redirect(url_for("admin_core.usuarios"))


# ---------------------------------------------------------------- reglas operativas del club
@bp.route("/reglas", methods=["GET", "POST"])
@admin_requerido("reglas")
def reglas():
    if request.method == "POST":
        try:
            for t in config.tipos():
                n = t["tipo"]
                config.actualizar_tipo(
                    n, v.monto(request.form.get(f"cuota_{n}"), f"La cuota {n}"),
                    v.entero(request.form.get(f"invitados_{n}"), f"El límite de invitados {n}", 0, 500),
                    v.entero(request.form.get(f"benef_{n}"), f"El máximo de beneficiarios {n}", 0, 50))
            for clave in ("moneda", "max_intentos_login", "minutos_bloqueo", "dias_plazo_pago", "dias_aviso_vencimiento",
                          "reserva_autoconfirmar", "dias_anticipacion_max", "dias_renovacion"):
                valor = (request.form.get(clave) or "").strip()
                if not valor:
                    raise ReglaError(f"El parámetro «{clave}» no puede quedar vacío.")
                if clave != "moneda":
                    v.entero(valor, clave, 0, 3650)
                config.guardar(clave, valor)
            flash("Reglas del club actualizadas. Los cambios aplican a nuevas operaciones.", "ok")
            return redirect(url_for("admin_core.reglas"))
        except ReglaError as e:
            flash(str(e), "error")
    return render_template("admin/reglas.html", tipos=config.tipos(), params={c["clave"]: c for c in config.todas()})


# ---------------------------------------------------------------- notificaciones (módulo 8)
@bp.get("/notificaciones")
@admin_requerido("notificaciones")
def notificaciones():
    socio_id = request.args.get("socio_id", type=int)
    codigo = request.args.get("codigo", "")
    fecha = request.args.get("fecha", "")
    return render_template("admin/notificaciones.html", lista=notificacion.historial(socio_id, codigo or None, fecha=fecha or None),
                           plantillas=notificacion.plantillas(), socios=socio.listar(), codigo=codigo, socio_id=socio_id, fecha=fecha)


@bp.get("/notificaciones/<int:nid>")
@admin_requerido("notificaciones")
def notificacion_detalle(nid):
    n = one("SELECT n.*, s.nombre AS socio_nombre FROM notificaciones n LEFT JOIN socios s ON s.id=n.socio_id WHERE n.id=?", (nid,))
    if n is None:
        abort(404)
    return render_template("admin/notificacion_detalle.html", n=n)


@bp.get("/plantillas")
@admin_requerido("plantillas")
def plantillas():
    lista = notificacion.plantillas()
    return redirect(url_for("admin_core.plantilla_editar", codigo=lista[0]["codigo"]))


@bp.route("/plantillas/<codigo>", methods=["GET", "POST"])
@admin_requerido("plantillas")
def plantilla_editar(codigo):
    p = notificacion.plantilla(codigo)
    if p is None:
        abort(404)
    lista = notificacion.plantillas()
    previa = None
    f = p
    if request.method == "POST":
        f = request.form
        if request.form.get("accion") == "previsualizar":
            previa = notificacion.vista_previa(request.form.get("asunto", ""), request.form.get("cuerpo", ""))
        else:
            try:
                notificacion.actualizar_plantilla(codigo, request.form.get("asunto", ""), request.form.get("cuerpo", ""),
                                                  request.form.get("activa") == "1")
                flash("Plantilla guardada.", "ok")
                return redirect(url_for("admin_core.plantilla_editar", codigo=codigo))
            except ReglaError as e:
                flash(str(e), "error")
    else:
        previa = notificacion.vista_previa(p["asunto"], p["cuerpo"])
    return render_template("admin/plantilla_form.html", p=p, f=f, lista=lista, previa=previa)
