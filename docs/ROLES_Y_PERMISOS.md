# Roles y permisos

Definidos en `app/models/admin.py` (`PERMISOS`). Un rol sin permiso recibe **403**; sin sesión se redirige al login.
La matriz está cubierta por `tests/test_web.py::test_matriz_de_permisos`.

| Módulo | General | Instalaciones | Cobros |
|---|:-:|:-:|:-:|
| Socios (consulta, estado, clave temporal) | ✔ | — | ✔ |
| Membresías | ✔ | — | ✔ |
| Usuarios administradores | ✔ | — | — |
| Instalaciones, calendario, bloqueos, ocupación | ✔ | ✔ | — |
| Reservas (gestión) | ✔ | ✔ | — |
| Reportes de uso | ✔ | ✔ | — |
| Invitados (listado para recepción) | ✔ | ✔ | ✔ |
| Estados de cuenta, pagos, morosos | ✔ | — | ✔ |
| Notificaciones (historial) | ✔ | — | ✔ |
| Plantillas de notificación | ✔ | — | — |
| Reglas del club | ✔ | — | — |

**Socios:** acceden únicamente a su propio portal (`/socio/...`); intentar abrir datos de otro socio devuelve 404.
**Separación de sesiones:** un socio no puede entrar a `/admin` y un administrador no usa el portal del socio.
