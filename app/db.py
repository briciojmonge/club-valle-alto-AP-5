"""Acceso a datos (SQLite). Capa mínima compartida por todos los modelos."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from flask import current_app, g

# Costa Rica no usa horario de verano: UTC-6 fijo.
TZ_CR = timezone(timedelta(hours=-6))


def ahora():
    """Fecha y hora actual de Costa Rica (naive, para comparar con los textos guardados)."""
    return datetime.now(TZ_CR).replace(tzinfo=None, microsecond=0)


def ahora_txt():
    return ahora().strftime("%Y-%m-%d %H:%M:%S")


def hoy():
    return ahora().date()


def get_db():
    if "db" not in g:
        path = current_app.config["DATABASE"]
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        g.db = sqlite3.connect(path, detect_types=0)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    schema = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema, encoding="utf-8") as f:
        db.executescript(f.read())
    db.execute("UPDATE tipos_membresia SET autoservicio=1 WHERE tipo='honoraria' AND autoservicio=0")
    db.execute("UPDATE notificaciones SET asunto='Recuperación de contraseña', "
               "cuerpo='[enlace reservado para el destinatario]', detalle=NULL "
               "WHERE codigo='recuperar_password' AND instr(cuerpo, '[enlace reservado para el destinatario]')=0")
    db.commit()


def query(sql, args=()):
    return get_db().execute(sql, args).fetchall()


def one(sql, args=()):
    return get_db().execute(sql, args).fetchone()


def execute(sql, args=()):
    """Ejecuta y confirma. Devuelve el id insertado."""
    db = get_db()
    cur = db.execute(sql, args)
    if not g.get("transaccion_escritura"):
        db.commit()
    return cur.lastrowid


@contextmanager
def transaccion_escritura():
    """Reserva el turno de escritura antes de consultar disponibilidad."""
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    g.transaccion_escritura = True
    try:
        with db:
            yield
    finally:
        g.pop("transaccion_escritura", None)


class ReglaError(Exception):
    """Violación de una regla de negocio; el mensaje se muestra al usuario."""
