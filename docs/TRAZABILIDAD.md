# Trazabilidad requisito → implementación → prueba

> La WBS agrupa los módulos como paquetes 1.3.1 a 1.3.9; verifique la numeración exacta contra el diccionario de la WBS vigente.

| Requisito del enunciado | Modelo / controlador | Vistas | Pruebas |
|---|---|---|---|
| Registro, login, perfil de socios | `models/socio.py`, `controllers/auth.py`, `portal.py` | `auth/*`, `socio/perfil.html` | `test_login_*`, `test_registro_*` |
| Bloqueo por intentos fallidos | `models/acceso.py` | `auth/login.html` | `test_bloqueo_por_intentos` |
| Recuperación por enlace de correo | `socio.solicitar_recuperacion`, `restablecer_con_token`, `services/mailer.py` | `auth/recuperar*.html` | `test_recuperacion_*` |
| Membresías individual/familiar/corporativa/honoraria | `models/membresia.py`, `admin_cobros.py` | `socio/membresia.html`, `admin/membresia*.html` | `test_estados_e_historial` |
| Beneficiarios | `membresia.agregar_beneficiario` | idem | `test_beneficiarios_*` |
| Estados activa/suspendida/vencida e historial | `membresia.cambiar_estado`, `refrescar_vencimientos` | idem | `test_estados_e_historial` |
| Invitados con límite mensual | `models/invitado.py` | `socio/invitados.html` | `test_limite_mensual_invitados` |
| Listado de esperados (recepción) | `invitado.esperados`, `admin_ops.invitados` | `admin/invitados.html` | `test_listado_esperados_*` |
| Reservas sin traslapes, horarios y aforo | `models/reserva.py` | `socio/reserva_form.html` | `test_sin_traslape_*`, `test_horario_y_aforo_*`, `test_instalacion_compartida_*` |
| Servicios adicionales | `instalacion.servicios`, `reserva_servicios` | formulario de reserva | seed + `test_estado_de_cuenta_*` |
| Modificar/cancelar mientras no inicien; historial | `reserva.modificar/cancelar` | `socio/reservas.html` | `test_modificar_cancelar_*` |
| Roles de administración | `models/admin.py`, `services/security.py` | `admin/usuarios.html` | `test_matriz_de_permisos` |
| Calendario, bloqueos, ocupación, reportes de uso | `models/instalacion.py`, `admin_ops.py` | `admin/calendario|ocupacion|reporte_uso.html` | humo de rutas, `test_horario_y_aforo_*` |
| Estado de cuenta, pago manual, morosos, PDF | `models/cuenta.py`, `services/pdf.py`, `admin_cobros.py` | `socio/cuenta_*`, `admin/cuentas|morosos.html` | `test_estado_de_cuenta_*`, `test_pdf_*` |
| Centro de notificaciones y plantillas | `models/notificacion.py`, `admin_core.py` | `admin/notificaciones|plantillas*.html` | humo de rutas, seed |
| Arquitectura MVC | `app/models`, `controllers`, `templates` | — | — |
| Accesibilidad | `_macros.html`, `base.html`, CSS | todas | `test_html_accesible_basico` |
| Seguridad (CSRF, CSP, hash, SQL parametrizado) | `services/security.py` | — | `test_csrf_se_exige`, `test_cabeceras_de_seguridad` |
| Hosting gratuito | `Procfile`, `wsgi.py` | — | [DESPLIEGUE.md](DESPLIEGUE.md) |
| Exclusiones: pasarela de pago, facturación electrónica, torneos, integraciones | no implementadas (pago manual) | — | — |
