"""Módulo 5: Usuarios administradores y permisos por rol."""
from werkzeug.security import generate_password_hash

from app.db import ReglaError, ahora_txt, execute, one, query
from app.models import acceso
from app.services import validators as v

ROLES = {
    "general": "Administrador general",
    "instalaciones": "Encargado de instalaciones",
    "cobros": "Encargado de cobros",
}

# Matriz de permisos (ver docs/ROLES_Y_PERMISOS.md). Cada módulo lista los roles autorizados.
PERMISOS = {
    "socios": {"general", "cobros"},
    "membresias": {"general", "cobros"},
    "usuarios_admin": {"general"},
    "instalaciones": {"general", "instalaciones"},
    "reservas": {"general", "instalaciones"},
    "reportes_uso": {"general", "instalaciones"},
    "invitados": {"general", "instalaciones", "cobros"},  # listado para recepción: todos los roles
    "cuentas": {"general", "cobros"},
    "notificaciones": {"general", "cobros"},
    "plantillas": {"general"},
    "reglas": {"general"},
}


def puede(rol, modulo):
    return rol in PERMISOS.get(modulo, set())


def por_id(admin_id):
    return one("SELECT * FROM admins WHERE id=?", (admin_id,))


def por_correo(correo):
    return one("SELECT * FROM admins WHERE correo=?", ((correo or "").strip().lower(),))


def listar():
    return query("SELECT * FROM admins ORDER BY nombre")


def crear(form):
    rol = form.get("rol")
    if rol not in ROLES:
        raise ReglaError("Seleccione un rol válido.")
    nombre = v.texto(form.get("nombre"), "El nombre completo", 3, 120)
    ced = v.cedula(form.get("cedula"))
    correo = v.correo(form.get("correo"))
    pwd = v.password(form.get("password"))
    if one("SELECT 1 FROM admins WHERE cedula=? OR correo=?", (ced, correo)):
        raise ReglaError("Ya existe un administrador con esa cédula o correo.")
    return execute(
        "INSERT INTO admins(nombre, cedula, correo, rol, password_hash, creado_en) VALUES (?,?,?,?,?,?)",
        (nombre, ced, correo, rol, generate_password_hash(pwd), ahora_txt()))


def cambiar_activo(admin_id, activo, actor_id):
    if admin_id == actor_id and not activo:
        raise ReglaError("No puede desactivar su propio usuario.")
    fila = por_id(admin_id)
    if fila["rol"] == "general" and not activo:
        otros = one("SELECT COUNT(*) AS n FROM admins WHERE rol='general' AND activo=1 AND id<>?", (admin_id,))["n"]
        if otros == 0:
            raise ReglaError("Debe existir al menos un administrador general activo.")
    execute("UPDATE admins SET activo=? WHERE id=?", (1 if activo else 0, admin_id))


def cambiar_rol(admin_id, rol, actor_id):
    if rol not in ROLES:
        raise ReglaError("Rol no válido.")
    fila = por_id(admin_id)
    if fila["rol"] == "general" and rol != "general":
        otros = one("SELECT COUNT(*) AS n FROM admins WHERE rol='general' AND activo=1 AND id<>?", (admin_id,))["n"]
        if otros == 0:
            raise ReglaError("Debe existir al menos un administrador general activo.")
    execute("UPDATE admins SET rol=? WHERE id=?", (rol, admin_id))


def autenticar(correo, password):
    fila = por_correo(correo)
    acceso.verificar("admins", fila, password)
    if not fila["activo"]:
        raise ReglaError("Este usuario administrador está desactivado.")
    return fila
