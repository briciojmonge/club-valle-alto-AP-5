"""Validaciones de entrada reutilizables."""
import re
from datetime import date, datetime

from app.db import ReglaError

_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def texto(valor, campo, minimo=1, maximo=120):
    v = (valor or "").strip()
    if len(v) < minimo:
        raise ReglaError(f"{campo} es obligatorio.")
    if len(v) > maximo:
        raise ReglaError(f"{campo} no puede superar {maximo} caracteres.")
    return v


def cedula(valor, campo="La cédula"):
    v = re.sub(r"[\s\-]", "", (valor or ""))
    if not v.isdigit() or not (9 <= len(v) <= 12):
        raise ReglaError(f"{campo} debe tener entre 9 y 12 dígitos (puede escribirla con o sin guiones).")
    return v


def correo(valor):
    v = (valor or "").strip().lower()
    if not _EMAIL.match(v) or len(v) > 160:
        raise ReglaError("Ingrese un correo electrónico válido.")
    return v


def telefono(valor):
    v = re.sub(r"[\s\-()]", "", (valor or ""))
    if v.startswith("+"):
        digitos = v[1:]
    else:
        digitos = v
    if not digitos.isdigit() or not (8 <= len(digitos) <= 15):
        raise ReglaError("Ingrese un teléfono válido (8 a 15 dígitos).")
    return v


def fecha(valor, campo="La fecha"):
    try:
        return datetime.strptime((valor or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ReglaError(f"{campo} no es válida (use el formato AAAA-MM-DD).")


def fecha_nacimiento(valor):
    d = fecha(valor, "La fecha de nacimiento")
    if d >= date.today() or d.year < 1900:
        raise ReglaError("La fecha de nacimiento no es válida.")
    return d


def hora(valor, campo="La hora"):
    v = (valor or "").strip()
    if not _HORA.match(v):
        raise ReglaError(f"{campo} no es válida (use el formato HH:MM).")
    return v


def entero(valor, campo, minimo=None, maximo=None):
    try:
        n = int(str(valor).strip())
    except (TypeError, ValueError):
        raise ReglaError(f"{campo} debe ser un número entero.")
    if minimo is not None and n < minimo:
        raise ReglaError(f"{campo} debe ser como mínimo {minimo}.")
    if maximo is not None and n > maximo:
        raise ReglaError(f"{campo} debe ser como máximo {maximo}.")
    return n


def monto(valor, campo="El monto"):
    try:
        n = float(str(valor).replace(",", ".").strip())
    except (TypeError, ValueError):
        raise ReglaError(f"{campo} debe ser un número.")
    if n < 0 or n > 10_000_000:
        raise ReglaError(f"{campo} no es válido.")
    return round(n, 2)


def password(valor):
    v = valor or ""
    if len(v) < 8:
        raise ReglaError("La contraseña debe tener al menos 8 caracteres.")
    if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
        raise ReglaError("La contraseña debe incluir al menos una letra y un número.")
    if len(v) > 128:
        raise ReglaError("La contraseña es demasiado larga.")
    return v


def minutos(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)
