"""Módulo 1: Registro y autenticación de socios."""
import hashlib
import secrets
from datetime import timedelta

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import ReglaError, ahora, ahora_txt, execute, one, query
from app.models import acceso, notificacion
from app.services import validators as v


def _hash(p):
    return generate_password_hash(p)


def por_id(socio_id):
    return one("SELECT * FROM socios WHERE id=?", (socio_id,))


def por_correo(correo):
    return one("SELECT * FROM socios WHERE correo=?", ((correo or "").strip().lower(),))


def _validar_datos(f):
    return {
        "nombre": v.texto(f.get("nombre"), "El nombre completo", 3, 120),
        "cedula": v.cedula(f.get("cedula")),
        "correo": v.correo(f.get("correo")),
        "telefono": v.telefono(f.get("telefono")),
        "direccion": v.texto(f.get("direccion"), "La dirección", 5, 250),
        "fecha_nacimiento": v.fecha_nacimiento(f.get("fecha_nacimiento")).isoformat(),
    }


def _verificar_unicos(d, excluir_id=None):
    otro = one("SELECT id FROM socios WHERE cedula=? AND id<>?", (d["cedula"], excluir_id or 0))
    if otro:
        raise ReglaError("Ya existe un socio registrado con esa cédula.")
    otro = one("SELECT id FROM socios WHERE correo=? AND id<>?", (d["correo"], excluir_id or 0))
    if otro:
        raise ReglaError("Ya existe un socio registrado con ese correo electrónico.")


def registrar(form):
    d = _validar_datos(form)
    pwd = v.password(form.get("password"))
    if pwd != form.get("password2"):
        raise ReglaError("Las contraseñas no coinciden.")
    _verificar_unicos(d)
    socio_id = execute(
        "INSERT INTO socios(nombre, cedula, correo, telefono, direccion, fecha_nacimiento, password_hash, creado_en) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (d["nombre"], d["cedula"], d["correo"], d["telefono"], d["direccion"], d["fecha_nacimiento"], _hash(pwd), ahora_txt()))
    notificacion.notificar(por_id(socio_id), "registro_socio", {})
    return socio_id


def autenticar(correo, password):
    fila = por_correo(correo)
    acceso.verificar("socios", fila, password)
    if fila["estado"] == "suspendido":
        raise ReglaError("Su cuenta está suspendida. Contacte a la administración del club.")
    if fila["estado"] == "desactivado":
        raise ReglaError("Su cuenta está desactivada. Contacte a la administración del club.")
    return fila


def actualizar_perfil(socio_id, form):
    d = _validar_datos(form)
    _verificar_unicos(d, socio_id)
    execute("UPDATE socios SET nombre=?, cedula=?, correo=?, telefono=?, direccion=?, fecha_nacimiento=? WHERE id=?",
            (d["nombre"], d["cedula"], d["correo"], d["telefono"], d["direccion"], d["fecha_nacimiento"], socio_id))


def cambiar_password(socio_id, actual, nueva, confirmacion):
    fila = por_id(socio_id)
    if not check_password_hash(fila["password_hash"], actual or ""):
        raise ReglaError("La contraseña actual no es correcta.")
    nueva = v.password(nueva)
    if nueva != confirmacion:
        raise ReglaError("Las contraseñas nuevas no coinciden.")
    execute("UPDATE socios SET password_hash=?, debe_cambiar_password=0 WHERE id=?", (_hash(nueva), socio_id))


# ---- recuperación de contraseña ----------------------------------------------------
def _hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def solicitar_recuperacion(correo):
    """Envía el enlace si el correo existe. No revela si existe o no."""
    fila = por_correo(correo)
    if fila is None or fila["estado"] == "desactivado":
        return
    token = secrets.token_urlsafe(32)
    expira = (ahora() + timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M:%S")
    execute("INSERT INTO reset_tokens(socio_id, token_hash, expira_en, creado_en) VALUES (?,?,?,?)",
            (fila["id"], _hash_token(token), expira, ahora_txt()))
    enlace = current_app.config["BASE_URL"].rstrip("/") + "/recuperar/" + token
    notificacion.notificar(fila, "recuperar_password", {"enlace": enlace})


def token_valido(token):
    fila = one("SELECT * FROM reset_tokens WHERE token_hash=? AND usado=0", (_hash_token(token or ""),))
    if fila is None or fila["expira_en"] < ahora_txt():
        return None
    return fila


def restablecer_con_token(token, nueva, confirmacion):
    fila = token_valido(token)
    if fila is None:
        raise ReglaError("El enlace no es válido o ya venció. Solicite uno nuevo.")
    nueva = v.password(nueva)
    if nueva != confirmacion:
        raise ReglaError("Las contraseñas no coinciden.")
    execute("UPDATE socios SET password_hash=?, intentos_fallidos=0, bloqueado_hasta=NULL, debe_cambiar_password=0 WHERE id=?",
            (_hash(nueva), fila["socio_id"]))
    execute("UPDATE reset_tokens SET usado=1 WHERE socio_id=?", (fila["socio_id"],))


# ---- gestión por administradores ------------------------------------------------------
def listar(busqueda="", estado=""):
    sql = ("SELECT s.*, (SELECT tipo FROM membresias m WHERE m.socio_id=s.id AND m.estado<>'baja') AS membresia_tipo, "
           "(SELECT estado FROM membresias m WHERE m.socio_id=s.id AND m.estado<>'baja') AS membresia_estado "
           "FROM socios s WHERE 1=1")
    args = []
    if busqueda:
        sql += " AND (s.nombre LIKE ? OR s.cedula LIKE ? OR s.correo LIKE ?)"
        like = f"%{busqueda.strip()}%"
        args += [like, like, like]
    if estado in ("activo", "suspendido", "desactivado"):
        sql += " AND s.estado = ?"
        args.append(estado)
    sql += " ORDER BY s.nombre"
    return query(sql, args)


def cambiar_estado(socio_id, estado):
    if estado not in ("activo", "suspendido", "desactivado"):
        raise ReglaError("Estado no válido.")
    execute("UPDATE socios SET estado=? WHERE id=?", (estado, socio_id))


def restablecer_temporal(socio_id):
    """Asigna una contraseña temporal (se muestra una sola vez al administrador)."""
    temporal = secrets.token_urlsafe(9) + "7a"
    execute("UPDATE socios SET password_hash=?, debe_cambiar_password=1, intentos_fallidos=0, bloqueado_hasta=NULL WHERE id=?",
            (_hash(temporal), socio_id))
    return temporal
