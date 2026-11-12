"""Configuración de la aplicación. Todo se puede sobrescribir con variables de entorno."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _bool(v, default=False):
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "si", "sí", "on")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-solo-para-desarrollo-cambiar-en-produccion")
    DATABASE = os.environ.get("DATABASE", os.path.join(BASE_DIR, "instance", "club.db"))
    BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")

    # Correo saliente (opcional)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_USE_TLS = _bool(os.environ.get("MAIL_USE_TLS"), True)
    MAIL_FROM = os.environ.get("MAIL_FROM", "Club Valle Alto <no-responder@example.com>")

    # Sesión
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool(os.environ.get("SESSION_COOKIE_SECURE"), False)
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8 horas

    TESTING = False
