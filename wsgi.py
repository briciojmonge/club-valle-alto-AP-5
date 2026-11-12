"""Punto de entrada WSGI para hosting (gunicorn wsgi:app, PythonAnywhere, etc.)."""
import os

try:  # carga .env si python-dotenv está instalado (el comando `flask` ya lo hace por sí solo)
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:  # pragma: no cover
    pass

from app import create_app  # noqa: E402

app = create_app()
