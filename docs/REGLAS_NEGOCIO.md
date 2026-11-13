# Reglas de negocio

> **Importante:** según el diccionario de la WBS (1.2.1), las reglas del club deben definirse y validarse con la Gerencia. Los valores marcados con ⚠ son **supuestos de trabajo** y se cambian sin tocar el código en *Administración → Reglas del club*.

## Socios y acceso
- Registro con nombre, cédula (9–12 dígitos), correo único, teléfono, dirección y fecha de nacimiento.
- Contraseña de al menos 8 caracteres (máx. 128).
- Bloqueo temporal tras **5** intentos fallidos durante **15** minutos ⚠ (`max_intentos_login`, `minutos_bloqueo`). Mientras dura, ni la clave correcta permite entrar y se muestra «Cuenta bloqueada por intentos fallidos» (pantalla E01).
- Recuperación por enlace enviado al correo; válido 60 minutos y de un solo uso. La respuesta no revela si el correo existe.
- Mensaje genérico ante credenciales inválidas.

## Membresías
Los montos se muestran en colones (₡), como en el prototipo. Las cuotas del prototipo (₡38 000 individual, ₡45 000 familiar, ₡90 000 corporativa) se usaron como valores iniciales.

| Tipo | Cuota mensual ⚠ | Invitados/mes ⚠ | Beneficiarios ⚠ | Alta |
|---|---|---|---|---|
| Individual | ₡38 000 | 3 | 0 | socio o personal |
| Familiar | ₡45 000 | 5 | 4 | socio o personal |
| Corporativa | ₡90 000 | 10 | 0 | socio o personal |
| Honoraria | ₡0 | 6 | 0 | solo personal |

- Un socio solo puede tener **una** membresía vigente.
- Estados: activa, suspendida, vencida (automático al pasar la fecha de renovación; renovación por defecto 365 días ⚠), baja. Cada cambio queda en el historial.
- Solo se pueden registrar beneficiarios en tipos que lo permiten y hasta su límite.
- Solo una membresía **activa** permite reservar y registrar invitados.

## Invitados
- Límite mensual según el tipo de membresía; fecha de visita no pasada y dentro de la anticipación máxima (60 días ⚠).
- No se admite el mismo invitado dos veces en la misma fecha ni que el socio se registre a sí mismo.
- Recepción dispone del listado de esperados por fecha e instalación.

## Reservas
- Instalaciones: golf (06–17, aforo 4), tenis (06–21, aforo 4), piscina (08–19, aforo 60, **compartida**), salón (09–23, aforo 120) ⚠ (horarios y aforos del prototipo; el prototipo no fija el aforo del golf ni el modo de cada instalación).
- Instalación **exclusiva**: no se admiten traslapes (franjas contiguas sí). **Compartida**: se suman personas hasta el aforo.
- Se rechaza lo que quede fuera del horario, supere el aforo o caiga en un bloqueo.
- Servicios adicionales con costo (ej. raquetas ₡5 000, palos ₡15 000, sombrilla ₡3 000, montaje ₡50 000) ⚠ que se cobran en el estado de cuenta.
- Modificar o cancelar solo mientras la reserva no haya iniciado; las pasadas se marcan `finalizada`.
- Confirmación automática por defecto; con `reserva_autoconfirmar=0` quedan pendientes hasta que el personal las confirme.

## Estado de cuenta
- Se genera por periodo `YYYY-MM`: cuota de membresía + servicios de reservas del periodo; es idempotente.
- Plazo de pago de 15 días ⚠; recordatorio 3 días antes; aviso al vencer.
- El pago se registra **manualmente** por el personal de cobros (sin pasarela).
- Morosos: cargos pendientes vencidos, filtrables por días de atraso. Exportación del estado de cuenta en PDF.

## Notificaciones
Plantillas editables (solo rol general) con variables; todo envío queda en el historial con estado enviado, simulado o error.
