"""Lógica común de autenticación con bloqueo por intentos fallidos (socios y administradores)."""
from datetime import timedelta

from werkzeug.security import check_password_hash

from app.db import ReglaError, ahora, execute
from app.models import config

_TABLAS = {"socios", "admins"}
# Hash ficticio para igualar el tiempo de respuesta cuando el correo no existe.
_HASH_FALSO = "scrypt:32768:8:1$x$" + "0" * 128
MSG_CREDENCIALES = "Correo o contraseña incorrectos."


def verificar(tabla, fila, password):
    """Valida credenciales. Lanza ReglaError con un mensaje seguro si no procede el acceso."""
    assert tabla in _TABLAS
    if fila is None:
        try:
            check_password_hash(_HASH_FALSO, password or "")
        except Exception:
            pass
        raise ReglaError(MSG_CREDENCIALES)

    ahora_dt = ahora()
    if fila["bloqueado_hasta"]:
        hasta = ahora_dt.strptime(fila["bloqueado_hasta"], "%Y-%m-%d %H:%M:%S")
        if hasta > ahora_dt:
            faltan = int((hasta - ahora_dt).total_seconds() // 60) + 1
            raise ReglaError(
                f"Cuenta bloqueada por intentos fallidos. Intente de nuevo en {faltan} minuto(s) o recupere su contraseña.")

    if not check_password_hash(fila["password_hash"], password or ""):
        intentos = fila["intentos_fallidos"] + 1
        maximo = config.obtener_int("max_intentos_login", 5)
        if intentos >= maximo:
            hasta = (ahora_dt + timedelta(minutes=config.obtener_int("minutos_bloqueo", 15))).strftime("%Y-%m-%d %H:%M:%S")
            execute(f"UPDATE {tabla} SET intentos_fallidos=0, bloqueado_hasta=? WHERE id=?", (hasta, fila["id"]))
            raise ReglaError("Cuenta bloqueada por intentos fallidos. Intente de nuevo más tarde o recupere su contraseña.")
        execute(f"UPDATE {tabla} SET intentos_fallidos=? WHERE id=?", (intentos, fila["id"]))
        restantes = maximo - intentos
        raise ReglaError(f"{MSG_CREDENCIALES} Le quedan {restantes} intento(s) antes del bloqueo temporal.")

    execute(f"UPDATE {tabla} SET intentos_fallidos=0, bloqueado_hasta=NULL WHERE id=?", (fila["id"],))
