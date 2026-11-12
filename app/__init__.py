"""Fábrica de la aplicación Flask del Sistema de Gestión para Club Valle Alto (arquitectura MVC)."""
import os
from datetime import date, datetime

import click
from flask import Flask, g, render_template, request

from config import Config


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    app.config.setdefault("CSRF_ENABLED", True)
    if test_config:
        app.config.update(test_config)

    from app import db
    from app.models import admin as admin_model
    from app.models import config as config_model
    from app.services import security

    app.teardown_appcontext(db.close_db)

    # Esquema y catálogos iniciales (idempotente): la app arranca lista en un hosting nuevo.
    with app.app_context():
        db.init_db()
        config_model.cargar_catalogos_iniciales()

    app.before_request(security.cargar_usuario)
    app.before_request(security.verificar_csrf)
    app.after_request(security.cabeceras_seguridad)

    # ---- Controladores (C de MVC) ----
    from app.controllers import admin_cobros, admin_core, admin_ops, auth, portal
    for bp in (auth.bp, portal.bp, admin_core.bp, admin_ops.bp, admin_cobros.bp):
        app.register_blueprint(bp)

    # ---- Utilidades para las vistas (V de MVC) ----
    app.jinja_env.globals.update(
        csrf_token=security.csrf_token,
        puede=admin_model.puede,
        ROLES=admin_model.ROLES,
        moneda=config_model.moneda,
        hoy=lambda: db.hoy(),
    )

    app.jinja_env.filters["zip"] = lambda a, *otros: zip(a, *otros)

    @app.template_filter("fecha")
    def f_fecha(v):
        if not v:
            return ""
        try:
            return datetime.strptime(str(v)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return str(v)

    @app.template_filter("fechahora")
    def f_fechahora(v):
        if not v:
            return ""
        try:
            return datetime.strptime(str(v)[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return str(v)

    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    dias = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]

    @app.template_filter("periodo_nombre")
    def f_periodo(v, corto=False):
        """'2026-10' → 'Octubre 2026' (o 'Oct 2026')."""
        try:
            anio, mes = str(v)[:7].split("-")
            nombre = meses[int(mes) - 1]
            return (nombre[:3].capitalize() if corto else nombre.capitalize()) + f" {anio}"
        except (ValueError, IndexError):
            return str(v)

    @app.template_filter("dia_corto")
    def f_dia_corto(v, anio=False):
        """'2026-10-17' → 'Sáb 17 oct' (con anio=True: 'Sáb 17 oct 2026')."""
        try:
            d = datetime.strptime(str(v)[:10], "%Y-%m-%d")
            return f"{dias[d.weekday()].capitalize()} {d.day} {meses[d.month - 1][:3]}" + (f" {d.year}" if anio else "")
        except ValueError:
            return str(v)

    @app.template_filter("dinero")
    def f_dinero(v):
        return config_model.moneda(float(v or 0))

    @app.errorhandler(403)
    def e403(e):
        return render_template("error.html", codigo=403, titulo="Acceso restringido",
                               mensaje="Su rol no tiene permiso para ver esta sección."), 403

    @app.errorhandler(404)
    def e404(e):
        return render_template("error.html", codigo=404, titulo="Página no encontrada",
                               mensaje="La dirección que busca no existe o fue movida."), 404

    @app.errorhandler(400)
    def e400(e):
        return render_template("error.html", codigo=400, titulo="Solicitud no válida",
                               mensaje=getattr(e, "description", "La solicitud no es válida.")), 400

    @app.errorhandler(500)
    def e500(e):
        return render_template("error.html", codigo=500, titulo="Error del servidor",
                               mensaje="Ocurrió un problema inesperado. Intente de nuevo en unos minutos."), 500

    @app.get("/salud")
    def salud():
        return {"estado": "ok"}

    # ---- Comandos de línea de comandos ----
    @app.cli.command("init-db")
    def cli_init_db():
        """Crea las tablas y carga los catálogos iniciales (idempotente)."""
        db.init_db()
        config_model.cargar_catalogos_iniciales()
        click.echo("Base de datos lista.")

    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Borra todos los datos antes de cargar los de prueba.")
    def cli_seed(reset):
        """Carga datos ficticios de prueba (socios, reservas, cargos)."""
        from app import seed
        seed.cargar(reset=reset)
        click.echo("Datos de prueba cargados. Vea docs/INSTALACION.md para las credenciales.")

    @app.cli.command("tareas-diarias")
    def cli_tareas():
        """Vencimiento de membresías, reservas finalizadas y recordatorios de pago."""
        from app.models import cuenta
        click.echo(cuenta.tareas_diarias())

    @app.cli.command("crear-admin")
    @click.option("--nombre", prompt=True)
    @click.option("--cedula", prompt=True)
    @click.option("--correo", prompt=True)
    @click.option("--rol", type=click.Choice(["general", "instalaciones", "cobros"]), default="general")
    @click.password_option()
    def cli_crear_admin(nombre, cedula, correo, rol, password):
        """Crea un usuario administrador."""
        from werkzeug.datastructures import MultiDict
        admin_model.crear(MultiDict({"nombre": nombre, "cedula": cedula, "correo": correo, "rol": rol, "password": password}))
        click.echo("Administrador creado.")

    return app
