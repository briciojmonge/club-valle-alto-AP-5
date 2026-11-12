import re
import pytest
from werkzeug.datastructures import MultiDict

from app import create_app
from app import seed

PASS = "Demo2026!"


@pytest.fixture()
def app(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "t.db"), "TESTING": True, "CSRF_ENABLED": False})
    with app.app_context():
        seed.cargar(reset=True)
    return app


@pytest.fixture()
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture()
def client(app):
    return app.test_client()


def entrar(client, correo, admin=False):
    r = client.post("/admin/login" if admin else "/login", data={"correo": correo, "password": PASS})
    assert r.status_code == 302
    return client


@pytest.fixture()
def maria(client):
    return entrar(client, "maria.solano@example.test")


@pytest.fixture()
def admin(client):
    return entrar(client, "admin@clubvallealto.test", admin=True)


def form(**kw):
    return MultiDict(kw)
