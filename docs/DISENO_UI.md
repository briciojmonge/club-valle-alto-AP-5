# Diseño de interfaz y correspondencia con el prototipo

La interfaz sigue el prototipo **PrototipoAP2** (28 pantallas). Elementos comunes: barra lateral verde con acento dorado en la opción activa, barra superior con «nombre · rol» y *Cerrar sesión*, tarjetas blancas con borde suave, tablas con encabezado gris, etiquetas de estado en forma de píldora y montos en colones (`₡45 000`). Los estilos están en `app/static/css/estilos.css`; la estructura, en `base.html` (con sesión) y `acceso.html` (pantallas de ingreso).

| Prototipo | Pantalla | Ruta | Plantilla |
|---|---|---|---|
| S01 | Inicio de sesión | `/login` (`/admin/login` para el personal) | `auth/login.html` |
| S02 | Registro de socio | `/registro` | `auth/registro.html` |
| S03 | Recuperar contraseña | `/recuperar` | `auth/recuperar.html` |
| E01 | Inicio de sesión bloqueada | `/login` tras los intentos fallidos | `auth/login.html` (alerta roja) |
| E02 | Nueva contraseña | `/recuperar/<token>` | `auth/restablecer.html` |
| S04 | Panel del socio | `/socio` | `socio/inicio.html` |
| S05 | Mi perfil | `/socio/perfil` | `socio/perfil.html` |
| S06 | Mi membresía | `/socio/membresia` | `socio/membresia.html` |
| S07 | Mis invitados | `/socio/invitados` | `socio/invitados.html` |
| S08 | Nueva reserva | `/socio/reservas/nueva` | `socio/reserva_form.html` |
| S09 | Mis reservas | `/socio/reservas` | `socio/reservas.html` |
| S10 | Estado de cuenta | `/socio/cuenta` | `socio/cuenta.html` |
| S11 | Panel administrativo | `/admin` | `admin/panel.html` |
| S12 | Socios | `/admin/socios` | `admin/socios.html` |
| S13 | Detalle de socio y membresía | `/admin/socios/<id>` | `admin/socio_detalle.html` |
| S14 | Invitados del día | `/admin/invitados` | `admin/invitados.html` |
| S15 | Instalaciones | `/admin/instalaciones` | `admin/instalaciones.html` |
| S16 | Calendario de reservas | `/admin/calendario` | `admin/calendario.html` |
| S17 | Ocupación y reportes | `/admin/ocupacion` | `admin/ocupacion.html` |
| S18 | Cobros | `/admin/cuentas` | `admin/cuentas.html` |
| S19 | Socios morosos | `/admin/morosos` | `admin/morosos.html` |
| S20 | Plantillas de notificación | `/admin/plantillas/<código>` | `admin/plantilla_form.html` |
| S21 | Historial de notificaciones | `/admin/notificaciones` | `admin/notificaciones.html` |
| S22 | Administradores | `/admin/usuarios` | `admin/usuarios.html` |
| M01 | Modal agregar beneficiario | en `/socio/membresia` | `dialog#m-benef-nuevo` (y `m-benef-<id>` para editar) |
| M02 | Modal cancelar reserva | en `/socio/reservas` y `/admin/calendario` | `dialog#m-cancelar-<id>` |
| M03 | Modal bloquear instalación | en `/admin/instalaciones` | `dialog#m-bloq-<id>` |
| M04 | Modal registrar pago | en `/admin/cuentas` | `dialog#m-pago-<socio>` |

## Ventanas emergentes
Los pop-ups usan el elemento nativo `<dialog>` (cierra con Esc, atrapa el foco y se anuncia a lectores de pantalla). `app.js` los abre con `data-modal="id"` y los cierra con `data-cerrar`, el botón *Cancelar* o un clic fuera. Cualquier ventana nueva debe seguir el mismo patrón: macro `abrir_modal` + `<dialog class="modal">` + botones *Cancelar* (secundario) y acción (primario, o rojo si es destructiva).

## Diferencias y ampliaciones respecto al prototipo
- **Navegación extra para el personal:** *Membresías*, *Reservas* y *Reglas del club*, necesarias para cubrir requisitos que el prototipo no dibuja (alta de membresías por el personal, listado de reservas y reglas configurables). Cada rol ve solo sus opciones.
- **Panel del socio (S04), Mi perfil (S05) y vistas de la sección 1–10:** se reprodujeron composición, tarjetas y textos; los datos son los reales de la base.
- **Tipografía:** el prototipo usa Inter; por la política de seguridad de contenido (sin fuentes externas) se declara `Inter` con *fallback* a la fuente del sistema. Para usarla siempre, copie los archivos de la fuente a `app/static/fonts/` y declare `@font-face`.
- **Ventanas sin JavaScript:** las ventanas modales requieren JS; el resto de la aplicación funciona sin él.
- **Tiempo de atraso (S19)** se ofrece como «Todos / más de 30 / más de 60 días»; **Rubro** resume cuotas y servicios por socio.
- Los datos de las capturas (nombres, montos) son ilustrativos; la demostración (`flask seed`) usa datos ficticios propios con montos coherentes con el prototipo.
