# Sistema de Gestión para Club Valle Alto

Proyecto base funcional del curso **IC4810 Administración de Proyectos** (TEC, grupo 05).
Plataforma web, con la interfaz del prototipo de pantallas (PrototipoAP2), para la gestión de socios, membresías, invitados, reservas de instalaciones, estado de cuenta y notificaciones.

**Pila:** Python 3 · Flask (MVC) · SQLite · plantillas Jinja2 · HTML/CSS/JS sin frameworks · fpdf2 (PDF) · gunicorn.

## Inicio rápido

```bash
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
flask seed --reset          # crea la BD con datos FICTICIOS de demostración
flask run                   # http://127.0.0.1:5000
pytest                      # 42 pruebas automáticas
```

Credenciales de demostración (todas con la contraseña `Demo2026!`): ver [docs/INSTALACION.md](docs/INSTALACION.md).

## Qué incluye

| Módulo (WBS 1.3.x) | Socio | Administración |
|---|---|---|
| Socios | registro, login, bloqueo por intentos, perfil, recuperación por enlace | consulta, estado, clave temporal |
| Membresías | alta, beneficiarios, historial | alta/modificación/renovación, estados |
| Invitados | registro con límite mensual | listado de esperados para recepción |
| Reservas | crear, modificar, cancelar, historial | calendario, reservas, ocupación, bloqueos |
| Estado de cuenta | consulta y PDF | cargos, pago manual, morosos |
| Notificaciones | — | plantillas editables, historial |
| Administradores | — | roles general / instalaciones / cobros |

Fuera de alcance (según el enunciado): pasarelas de pago, facturación electrónica, torneos e integraciones externas.

## Documentación (`docs/`)

| Documento | Contenido |
|---|---|
| [INSTALACION.md](docs/INSTALACION.md) | Instalación, configuración, credenciales de demo, comandos |
| [ARQUITECTURA.md](docs/ARQUITECTURA.md) | MVC, capas, flujo de una petición, seguridad |
| [MODELO_DATOS.md](docs/MODELO_DATOS.md) | Diagrama ER y diccionario de datos |
| [DISENO_UI.md](docs/DISENO_UI.md) | Correspondencia entre las 28 pantallas del prototipo y la aplicación |
| [REGLAS_NEGOCIO.md](docs/REGLAS_NEGOCIO.md) | Reglas implementadas y valores **por validar con la Gerencia** |
| [ROLES_Y_PERMISOS.md](docs/ROLES_Y_PERMISOS.md) | Matriz de permisos |
| [RUTAS.md](docs/RUTAS.md) | Listado de rutas (generado desde la aplicación) |
| [MANUAL_SOCIO.md](docs/MANUAL_SOCIO.md) / [MANUAL_ADMIN.md](docs/MANUAL_ADMIN.md) | Guías de uso |
| [DESPLIEGUE.md](docs/DESPLIEGUE.md) | Hosting gratuito y variables de entorno |
| [PRUEBAS.md](docs/PRUEBAS.md) | Estrategia y casos automatizados |
| [TRAZABILIDAD.md](docs/TRAZABILIDAD.md) | WBS y requisitos → código y pruebas |

## Estructura

```
app/
  __init__.py        fábrica de la aplicación, filtros y comandos CLI
  schema.sql         esquema SQLite (restricciones e índices únicos)
  db.py  seed.py     acceso a datos y datos de demostración
  models/            M: reglas de negocio y consultas
  controllers/       C: blueprints (auth, portal, admin_core, admin_ops, admin_cobros)
  services/          seguridad, validadores, PDF, correo
  templates/ static/ V: vistas, CSS y JS
tests/               pytest
docs/                documentación
```

> Todos los datos de `flask seed` son ficticios (correos `@example.test`). No los use en producción.
