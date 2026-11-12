"""Centro de notificaciones: plantillas editables, envío por correo e historial."""
import re

from app.db import ReglaError, ahora_txt, execute, one, query
from app.services.mailer import enviar_correo

_VAR = re.compile(r"\{(\w+)\}")


def render(texto, datos):
    """Sustituye {variable}. Variables desconocidas quedan vacías (sin ejecutar código)."""
    return _VAR.sub(lambda m: str(datos.get(m.group(1), "")), texto)


def plantillas():
    orden = ("registro_socio", "reserva_confirmada", "reserva_modificada", "reserva_cancelada", "estado_cuenta", "recordatorio_pago",
             "pago_vencido")
    filas = query("SELECT * FROM plantillas_notificacion")
    return sorted(filas, key=lambda f: (orden.index(f["codigo"]) if f["codigo"] in orden else len(orden), f["nombre"]))


def plantilla(codigo):
    return one("SELECT * FROM plantillas_notificacion WHERE codigo=?", (codigo,))


def actualizar_plantilla(codigo, asunto, cuerpo, activa):
    if not asunto.strip() or not cuerpo.strip():
        raise ReglaError("El asunto y el cuerpo de la plantilla son obligatorios.")
    if len(asunto) > 200 or len(cuerpo) > 5000:
        raise ReglaError("La plantilla es demasiado larga.")
    execute("UPDATE plantillas_notificacion SET asunto=?, cuerpo=?, activa=?, actualizado_en=? WHERE codigo=?",
            (asunto.strip(), cuerpo.strip(), 1 if activa else 0, ahora_txt(), codigo))


def notificar(socio, codigo, datos):
    """Genera y envía la notificación al socio, y la registra en el historial.

    `socio` es una fila con id, nombre y correo. Nunca lanza excepción por fallos de correo.
    """
    p = plantilla(codigo)
    if p is None:
        return None
    datos = dict(datos)
    datos.setdefault("nombre", socio["nombre"])
    datos.setdefault("correo", socio["correo"])
    asunto = render(p["asunto"], datos)
    cuerpo = render(p["cuerpo"], datos)
    if not p["activa"]:
        estado, detalle = "omitido", "Plantilla desactivada por un administrador."
    else:
        estado, detalle = enviar_correo(socio["correo"], asunto, cuerpo)
    return execute(
        "INSERT INTO notificaciones(socio_id, codigo, destinatario, asunto, cuerpo, estado, detalle, creado_en) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (socio["id"], codigo, socio["correo"], asunto, cuerpo, estado, detalle, ahora_txt()))


def historial(socio_id=None, codigo=None, limite=200, fecha=None):
    sql = ("SELECT n.*, s.nombre AS socio_nombre FROM notificaciones n LEFT JOIN socios s ON s.id = n.socio_id WHERE 1=1")
    args = []
    if socio_id:
        sql += " AND n.socio_id = ?"
        args.append(socio_id)
    if codigo:
        sql += " AND n.codigo = ?"
        args.append(codigo)
    if fecha:
        sql += " AND substr(n.creado_en, 1, 10) = ?"
        args.append(fecha)
    sql += " ORDER BY n.id DESC LIMIT ?"
    args.append(limite)
    return query(sql, args)


# Datos de ejemplo para la vista previa de plantillas (no se envía nada).
EJEMPLO = {
    "nombre": "Ana", "correo": "ana@example.test", "instalacion": "Cancha de tenis", "fecha": "sáb 17 oct", "hora_inicio": "09:00",
    "hora_fin": "10:00", "personas": "4", "periodo": "Octubre 2026", "total": "₡45\u00a0000", "pendiente": "₡45\u00a0000",
    "enlace": "https://club.example/socio/cuenta", "concepto": "Cuota de membresía", "monto": "₡45\u00a0000", "fecha_limite": "25/10/2026",
}


def vista_previa(asunto, cuerpo):
    return render(asunto, EJEMPLO), render(cuerpo, EJEMPLO)
