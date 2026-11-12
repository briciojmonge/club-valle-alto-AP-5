"""Sesiones, CSRF, cabeceras de seguridad y control de acceso por rol."""
import hmac
import secrets
from functools import wraps

from flask import abort, current_app, flash, g, redirect, request, session, url_for

from app.models import admin as admin_model
from app.models import socio as socio_model


# ---------------------------------------------------------------- CSRF
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def verificar_csrf():
    if not current_app.config.get("CSRF_ENABLED", True):
        return
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        enviado = request.form.get("_csrf", "")
        esperado = session.get("_csrf", "")
        if not esperado or not hmac.compare_digest(enviado, esperado):
            abort(400, description="La sesión del formulario venció o no es válida. Recargue la página e intente de nuevo.")


# ---------------------------------------------------------------- usuario actual
def cargar_usuario():
    g.socio = None
    g.admin = None
    sid = session.get("socio_id")
    if sid:
        s = socio_model.por_id(sid)
        if s and s["estado"] == "activo":
            g.socio = s
        else:
            session.pop("socio_id", None)
    aid = session.get("admin_id")
    if aid:
        a = admin_model.por_id(aid)
        if a and a["activo"]:
            g.admin = a
        else:
            session.pop("admin_id", None)


def iniciar_sesion_socio(socio_id):
    session.clear()           # evita la fijación de sesión
    session["socio_id"] = socio_id
    session.permanent = True


def iniciar_sesion_admin(admin_id):
    session.clear()
    session["admin_id"] = admin_id
    session.permanent = True


def cerrar_sesion():
    session.clear()


# ---------------------------------------------------------------- decoradores
def socio_requerido(vista):
    @wraps(vista)
    def envoltura(*a, **kw):
        if g.socio is None:
            flash("Inicie sesión para continuar.", "error")
            return redirect(url_for("auth.login"))
        if g.socio["debe_cambiar_password"] and request.endpoint not in ("portal.password", "auth.logout"):
            flash("Por seguridad, debe cambiar su contraseña temporal antes de continuar.", "error")
            return redirect(url_for("portal.password"))
        return vista(*a, **kw)
    return envoltura


def admin_requerido(modulo=None):
    """Exige sesión de administrador y, si se indica, que su rol tenga permiso sobre el módulo."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(*a, **kw):
            if g.admin is None:
                flash("Inicie sesión como administrador para continuar.", "error")
                return redirect(url_for("auth.admin_login"))
            if modulo and not admin_model.puede(g.admin["rol"], modulo):
                abort(403)
            return vista(*a, **kw)
        return envoltura
    return decorador


def cabeceras_seguridad(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; form-action 'self'; frame-ancestors 'none'")
    if request.endpoint and ("login" in request.endpoint or request.path.startswith(("/socio", "/admin"))):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp
