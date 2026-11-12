"""Envío de correo. Sin MAIL_SERVER configurado el mensaje no se envía: queda como 'simulado'."""
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app


def enviar_correo(destinatario, asunto, cuerpo):
    """Devuelve (estado, detalle) con estado en {'enviado','simulado','error'}."""
    cfg = current_app.config
    if not cfg.get("MAIL_SERVER"):
        return "simulado", "SMTP no configurado: el mensaje solo se guardó en el historial."
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = cfg["MAIL_FROM"]
    msg["To"] = destinatario
    msg.set_content(cuerpo)
    try:
        if cfg["MAIL_USE_TLS"]:
            with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=10) as s:
                s.starttls(context=ssl.create_default_context())
                if cfg["MAIL_USERNAME"]:
                    s.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
                s.send_message(msg)
        else:
            with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=10) as s:
                if cfg["MAIL_USERNAME"]:
                    s.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
                s.send_message(msg)
        return "enviado", ""
    except Exception as exc:  # el fallo de correo nunca debe tumbar la operación principal
        return "error", f"{type(exc).__name__}: {exc}"[:300]
