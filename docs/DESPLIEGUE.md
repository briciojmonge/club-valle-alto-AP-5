# Despliegue en hosting gratuito

El enunciado exige un hosting sin costo. Las condiciones de los planes gratuitos cambian con frecuencia: **verifique la oferta vigente antes de decidir**.

## Requisito clave: persistencia de SQLite
La base es un archivo. Si el hosting borra el disco al reiniciar (sistema de archivos efímero), se pierden los datos.

| Opción | Ventajas | Puntos a verificar |
|---|---|---|
| PythonAnywhere (plan gratuito) | Disco persistente, soporta Flask/WSGI, tareas programadas diarias | Lista de destinos HTTP permitidos; SMTP saliente restringido (suele permitir Gmail en el puerto 587 con contraseña de aplicación); una sola app |
| Render (plan gratuito) | Despliegue desde GitHub con `Procfile`/gunicorn | Disco **efímero**: SQLite se reinicia; requeriría una BD externa gratuita o aceptar datos de demostración (`flask seed` al arrancar) |

Para la evaluación del curso, lo más simple es un hosting con disco persistente, o bien Render con datos de demostración recargables.

## Pasos genéricos
1. Subir el código (sin `.env`, `*.db` ni `__pycache__`).
2. `pip install -r requirements.txt`.
3. Variables: `SECRET_KEY`, `BASE_URL`, `SESSION_COOKIE_SECURE=true`, opcionalmente `MAIL_*`, y `DATABASE` apuntando a una ruta persistente.
4. Comando de inicio: `gunicorn wsgi:app --workers 2 --timeout 60` (ya en `Procfile`).
5. Primera vez: `flask crear-admin` (o `flask seed --reset` para una demo).
6. Programar `flask tareas-diarias` una vez al día.

## Copias de respaldo
Copie periódicamente el archivo de `DATABASE`. Para restaurar, reemplácelo con la aplicación detenida.
