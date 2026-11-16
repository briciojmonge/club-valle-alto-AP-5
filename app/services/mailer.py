"""Envío de correo por SMTP o por la API de Resend."""
import json
import smtplib
import ssl
from email.message import EmailMessage
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app


def enviar_correo(destinatario, asunto, cuerpo):
    """Devuelve (estado, detalle) con estado en {'enviado','simulado','error'}."""
    cfg = current_app.config
    proveedor = cfg["MAIL_PROVIDER"]
    if proveedor == "resend":
        return _enviar_resend(cfg, destinatario, asunto, cuerpo)
    if proveedor != "smtp":
        return "error", "MAIL_PROVIDER debe ser smtp o resend."
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


def _enviar_resend(cfg, destinatario, asunto, cuerpo):
    if not cfg["RESEND_API_KEY"].strip():
        return "error", "Resend configurado sin RESEND_API_KEY."

    datos = json.dumps({
        "from": cfg["MAIL_FROM"],
        "to": [destinatario],
        "subject": asunto,
        "text": cuerpo,
    }).encode("utf-8")
    try:
        solicitud = Request(
            "https://api.resend.com/emails",
            data=datos,
            headers={
                "Authorization": f"Bearer {cfg['RESEND_API_KEY']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(solicitud, timeout=10) as respuesta:
            resultado = json.load(respuesta)
        if not isinstance(resultado, dict) or not isinstance(resultado.get("id"), str) or not resultado["id"]:
            return "error", "Respuesta de Resend sin identificador de envío."
        return "enviado", ""
    except HTTPError as exc:
        return "error", f"Resend rechazó el envío (HTTP {exc.code})."
    except (URLError, TimeoutError, OSError, HTTPException, ValueError):
        return "error", "Error de conexión o respuesta no válida de Resend."
