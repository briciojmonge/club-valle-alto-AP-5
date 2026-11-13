# Instalación y puesta en marcha

## Requisitos
Python 3.10 o superior y `pip`. No se requiere servidor de base de datos (SQLite viene con Python).

## Pasos
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # producción;  requirements-dev.txt añade pytest
cp .env.example .env                     # y edite SECRET_KEY
flask init-db                            # crea tablas y catálogos (también ocurre solo al arrancar)
flask seed --reset                       # (opcional) datos ficticios de demostración
flask run
```
Abra http://127.0.0.1:5000. El archivo `.flaskenv` ya define `FLASK_APP=app`.

## Variables de entorno
| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave de sesión. **Obligatoria y aleatoria en producción.** |
| `DATABASE` | Ruta del archivo SQLite (por defecto `instance/club.db`). |
| `BASE_URL` | URL pública; se usa en los enlaces de recuperación de contraseña. |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_USE_TLS`, `MAIL_FROM` | Correo saliente. Sin `MAIL_SERVER` los mensajes quedan en el historial con estado **simulado**. |
| `SESSION_COOKIE_SECURE` | `true` cuando el sitio se sirve por HTTPS. |

## Credenciales de demostración
Todas usan la contraseña **`Demo2026!`** (solo existen tras `flask seed`).

| Rol | Correo | Acceso |
|---|---|---|
| Administrador general (Carlos Mora) | admin@clubvallealto.test | `/admin/login` |
| Admin. de instalaciones (Laura Vega) | instalaciones@clubvallealto.test | `/admin/login` |
| Admin. de cobros (Diego Solís) | cobros@clubvallealto.test | `/admin/login` |
| Socia (individual, con reservas) | maria.solano@example.test | `/login` |
| Socio (familiar, con beneficiarios) | carlos.rojas@example.test | `/login` |
| Socia (corporativa, morosa) | laura.jimenez@example.test | `/login` |
| Socio (honoraria) | jorge.castro@example.test | `/login` |
| Socia (membresía suspendida) | ana.barquero@example.test | `/login` |
| Socio (membresía vencida) | diego.chaves@example.test | `/login` |
| Socia (sin membresía) | sofia.valverde@example.test | `/login` |
| Socio (moroso, reserva pendiente) | roberto.mena@example.test | `/login` |

## Comandos
| Comando | Función |
|---|---|
| `flask seed [--reset]` | Carga datos de prueba (`--reset` borra los existentes). |
| `flask crear-admin` | Crea un administrador real (pide nombre, cédula, correo, rol y contraseña). |
| `flask tareas-diarias` | Marca membresías vencidas, finaliza reservas pasadas y genera avisos de pago. Programarlo una vez al día. |
| `flask init-db` | Crea tablas y catálogos sin tocar los datos. |
| `pytest` | Ejecuta las pruebas. |

## Puesta en producción
1. No ejecute `flask seed`; cree el primer administrador con `flask crear-admin`.
2. Defina `SECRET_KEY`, `BASE_URL` y `SESSION_COOKIE_SECURE=true`.
3. Inicie con `gunicorn wsgi:app` (ver `Procfile`). Más detalles en [DESPLIEGUE.md](DESPLIEGUE.md).
