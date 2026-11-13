# Manual de administración

Acceso: `/admin/login`. El menú muestra solo los módulos de su rol ([ROLES_Y_PERMISOS.md](ROLES_Y_PERMISOS.md)).

## Panel
Resumen de socios, reservas del día, morosos y accesos rápidos.

## Socios y membresías (general, cobros)
- **Socios:** buscar, ver detalle, suspender/reactivar y generar **clave temporal** (se muestra una sola vez; el socio debe cambiarla).
- **Membresías:** alta por el personal (incluye honoraria), modificar tipo/cuota/renovación, cambiar estado con motivo, renovar, administrar beneficiarios. Todo queda en el historial.

## Instalaciones y reservas (general, instalaciones)
- **Instalaciones:** horario, aforo, modo (exclusiva/compartida), servicios adicionales y su costo; activar/desactivar.
- **Bloquear:** botón de cada tarjeta de instalación; pide fecha, desde/hasta y motivo, e impide nuevas reservas en ese horario (no se puede si ya hay reservas).
- **Reservas:** filtrar, ver, confirmar pendientes, editar y cancelar.
- **Calendario semanal** y **Ocupación en tiempo real** (con actualización automática opcional cada 60 s).
- **Reporte de uso** por instalación y rango de fechas (imprimible).
- **Invitados esperados:** listado por fecha para la recepción (todos los roles).

## Cobros (general, cobros)
- **Cobros:** elija periodo y estado, genere los estados de cuenta (idempotente) y use **Registrar pago** (ventana con socio, rubro, monto y fecha de pago; la fecha no puede ser futura).
- **Morosos:** cargos vencidos con días de atraso.
- **Tareas diarias:** botón/comando que marca membresías vencidas y genera avisos de pago.

## Comunicación y configuración
- **Notificaciones:** historial con estado (enviado, simulado, error) y detalle.
- **Plantillas de correo** (solo general): elija la plantilla en la lista, edite asunto y cuerpo con las variables listadas y use **Vista previa** (datos de ejemplo, no se envía nada) antes de **Guardar**.
- **Reglas del club** (solo general): intentos de login, bloqueo, plazos, anticipación, cuotas y límites por tipo de membresía.
- **Usuarios administradores** (solo general): crear, cambiar rol, activar/desactivar.
