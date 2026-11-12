"""Controlador de autenticación: registro, inicio/cierre de sesión y recuperación de contraseña."""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.db import ReglaError
from app.models import admin as admin_model
from app.models import instalacion, socio
from app.services import security

bp = Blueprint("auth", __name__)


@bp.get("/")
def inicio():
    return render_template("inicio.html", instalaciones=instalacion.listar(solo_activas=True))


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        try:
            sid = socio.registrar(request.form)
            security.iniciar_sesion_socio(sid)
            flash("¡Registro exitoso! Ya puede asociar su membresía.", "ok")
            return redirect(url_for("portal.membresia"))
        except ReglaError as e:
            flash(str(e), "error")
    return render_template("auth/registro.html", f=request.form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            fila = socio.autenticar(request.form.get("correo"), request.form.get("password"))
            security.iniciar_sesion_socio(fila["id"])
            return redirect(url_for("portal.inicio"))
        except ReglaError as e:
            flash(str(e), "error")
    return render_template("auth/login.html", f=request.form, admin=False)


@bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        try:
            fila = admin_model.autenticar(request.form.get("correo"), request.form.get("password"))
            security.iniciar_sesion_admin(fila["id"])
            return redirect(url_for("admin_core.panel"))
        except ReglaError as e:
            flash(str(e), "error")
    return render_template("auth/login.html", f=request.form, admin=True)


@bp.post("/logout")
def logout():
    security.cerrar_sesion()
    flash("Sesión cerrada.", "ok")
    return redirect(url_for("auth.inicio"))


@bp.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if request.method == "POST":
        socio.solicitar_recuperacion(request.form.get("correo"))
        # Mensaje idéntico exista o no el correo (evita enumerar socios).
        flash("Si el correo está registrado, recibirá un enlace para restablecer su contraseña (válido por 60 minutos).", "ok")
        return redirect(url_for("auth.login"))
    return render_template("auth/recuperar.html")


@bp.route("/recuperar/<token>", methods=["GET", "POST"])
def restablecer(token):
    if socio.token_valido(token) is None:
        flash("El enlace no es válido o ya venció. Solicite uno nuevo.", "error")
        return redirect(url_for("auth.recuperar"))
    if request.method == "POST":
        try:
            socio.restablecer_con_token(token, request.form.get("password"), request.form.get("password2"))
            flash("Contraseña actualizada. Ya puede iniciar sesión.", "ok")
            return redirect(url_for("auth.login"))
        except ReglaError as e:
            flash(str(e), "error")
    return render_template("auth/restablecer.html", token=token)
