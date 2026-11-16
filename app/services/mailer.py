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
    etapa = "configuración"
    try:
        if cfg["MAIL_USE_SSL"] and cfg["MAIL_USE_TLS"]:
            raise ValueError("MAIL_USE_SSL y MAIL_USE_TLS no pueden activarse a la vez.")
        etapa = "conexión"
        if cfg["MAIL_USE_SSL"]:
            conexion = smtplib.SMTP_SSL(
                cfg["MAIL_SERVER"],
                cfg["MAIL_PORT"],
                timeout=10,
                context=ssl.create_default_context(),
            )
        else:
            conexion = smtplib.SMTP(
                cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=10
            )
        with conexion as s:
            if cfg["MAIL_USE_TLS"]:
                etapa = "STARTTLS"
                s.starttls(context=ssl.create_default_context())
            if cfg["MAIL_USERNAME"]:
                etapa = "autenticación"
                metodo = cfg["MAIL_AUTH_METHOD"]
                if metodo == "auto":
                    s.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
                elif metodo == "login":
                    if not (cfg["MAIL_USE_TLS"] or cfg["MAIL_USE_SSL"]):
                        raise smtplib.SMTPNotSupportedError("AUTH LOGIN requiere TLS.")
                    s.ehlo_or_helo_if_needed()
                    if "LOGIN" not in s.esmtp_features.get("auth", "").upper().split():
                        raise smtplib.SMTPNotSupportedError("El servidor no anuncia AUTH LOGIN.")
                    s.user, s.password = cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"]
                    s.auth("LOGIN", s.auth_login, initial_response_ok=False)
                else:
                    raise ValueError("MAIL_AUTH_METHOD debe ser auto o login.")
            etapa = "envío"
            s.send_message(msg)
            etapa = "cierre"
        return "enviado", ""
    except Exception as exc:  # el fallo de correo nunca debe tumbar la operación principal
        return "error", f"{type(exc).__name__} (etapa: {etapa}): {exc}"[:300]
