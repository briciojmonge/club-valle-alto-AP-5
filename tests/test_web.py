"""Pruebas de extremo a extremo con el cliente HTTP de Flask: permisos, CSRF, recorridos y páginas."""
import re

import pytest

from app import create_app, seed
from app.models.admin import PERMISOS
from tests.conftest import PASS, entrar

# módulo -> una ruta GET representativa
RUTAS_MODULO = {
    "socios": "/admin/socios", "membresias": "/admin/membresias", "usuarios_admin": "/admin/usuarios",
    "instalaciones": "/admin/instalaciones", "reservas": "/admin/reservas", "reportes_uso": "/admin/reportes/uso",
    "invitados": "/admin/invitados", "cuentas": "/admin/cuentas", "notificaciones": "/admin/notificaciones",
    "plantillas": "/admin/plantillas", "reglas": "/admin/reglas",
}
ADMINS = {"general": "admin@clubvallealto.test", "instalaciones": "instalaciones@clubvallealto.test", "cobros": "cobros@clubvallealto.test"}


def test_paginas_publicas(client):
    for r in ("/", "/login", "/registro", "/recuperar", "/admin/login", "/salud"):
        assert client.get(r).status_code == 200, r


def test_rutas_protegidas_redirigen(client):
    for r in ("/socio", "/socio/reservas", "/admin", "/admin/socios"):
        resp = client.get(r)
        assert resp.status_code == 302 and "login" in resp.headers["Location"], r


def test_recorrido_socio(maria):
    for r in ("/socio", "/socio/perfil", "/socio/membresia", "/socio/invitados", "/socio/reservas",
              "/socio/reservas/nueva", "/socio/cuenta"):
        assert maria.get(r).status_code == 200, r


def test_pdf_estado_cuenta_http(maria, ctx):
    from app.models import cuenta
    r = maria.get(f"/socio/cuenta/{cuenta.periodo_actual()}/pdf")
    assert r.status_code == 200 and r.data[:4] == b"%PDF"


def test_socio_no_entra_a_admin_ni_viceversa(maria, client):
    assert maria.get("/admin").status_code in (302, 403)
    c2 = client.application.test_client()
    entrar(c2, ADMINS["general"], admin=True)
    assert c2.get("/socio").status_code in (302, 403)


def test_no_ve_reserva_ajena(maria, ctx):
    from app.db import one
    ajena = one("SELECT r.id FROM reservas r JOIN socios s ON s.id=r.socio_id WHERE s.correo<>'maria.solano@example.test'")["id"]
    assert maria.get(f"/socio/reservas/{ajena}").status_code == 404


@pytest.mark.parametrize("rol", list(ADMINS))
def test_matriz_de_permisos(app, rol):
    c = app.test_client()
    entrar(c, ADMINS[rol], admin=True)
    assert c.get("/admin").status_code == 200
    for modulo, ruta in RUTAS_MODULO.items():
        esperado = 200 if rol in PERMISOS[modulo] else 403
        got = c.get(ruta, follow_redirects=True).status_code
        assert got == esperado, f"{rol} → {ruta}: {got} (esperado {esperado})"


def test_todas_las_paginas_admin_y_socio(app):
    import re as _re
    for login, correo, pref, admin in (("/admin/login", ADMINS["general"], "/admin", True), ("/login", "maria.solano@example.test", "/socio", False)):
        c = app.test_client()
        entrar(c, correo, admin=admin)
        for r in app.url_map.iter_rules():
            if "GET" not in r.methods or not r.rule.startswith(pref):
                continue
            url = _re.sub(r"<int:\w+>", "1", r.rule).replace("<periodo>", "2026-10")
            if "<" in url:
                continue
            assert c.get(url, follow_redirects=True).status_code in (200, 404), url


def test_csrf_se_exige(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "c.db"), "TESTING": True})  # CSRF activo
    with app.app_context():
        seed.cargar(reset=True)
    c = app.test_client()
    assert c.post("/login", data={"correo": "maria.solano@example.test", "password": PASS}).status_code == 400
    html = c.get("/login").get_data(as_text=True)
    token = re.search(r'name="_csrf" value="([^"]+)"', html).group(1)
    ok = c.post("/login", data={"correo": "maria.solano@example.test", "password": PASS, "_csrf": token})
    assert ok.status_code == 302


def test_cabeceras_de_seguridad(client):
    r = client.get("/")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "script-src" in csp and "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]
    assert r.headers.get("X-Content-Type-Options") == "nosniff"


def test_html_accesible_basico(client):
    html = client.get("/login").get_data(as_text=True)
    assert '<html lang="es"' in html
    assert "saltar" in html          # enlace «saltar al contenido»
    assert "<label" in html
    assert "style=" not in html      # sin estilos en línea (CSP)


def test_reserva_por_formulario_y_traslape(maria, ctx):
    from datetime import timedelta
    from app.db import hoy, one
    inst = one("SELECT id FROM instalaciones WHERE nombre='Cancha de tenis'")["id"]
    fecha = (hoy() + timedelta(days=15)).isoformat()
    datos = {"instalacion_id": inst, "fecha": fecha, "hora_inicio": "08:00", "hora_fin": "09:00", "personas": 2}
    assert maria.post("/socio/reservas/nueva", data=datos).status_code == 302
    r = maria.post("/socio/reservas/nueva", data=datos)  # mismo horario: debe rechazar con mensaje
    assert r.status_code == 200 and "traslape" in r.get_data(as_text=True)


def test_admin_crea_bloqueo_y_cobra(admin, ctx):
    from app.db import one
    cargo = one("SELECT id FROM cargos WHERE estado='pendiente' LIMIT 1")["id"]
    assert admin.post(f"/admin/cuentas/{cargo}/pago").status_code == 302
    assert one("SELECT estado FROM cargos WHERE id=?", (cargo,))["estado"] == "pagado"


# ---------------------------------------------------------------- pantallas del prototipo (PrototipoAP2)
def test_montos_en_colones(maria):
    html = maria.get("/socio").get_data(as_text=True)
    assert "₡" in html and "$" not in html.replace("</", "")


def test_modales_del_prototipo_presentes(app):
    """Cada pop-up del prototipo existe como <dialog>: M01 beneficiario, M02 cancelar reserva, M03 bloquear, M04 registrar pago."""
    c = app.test_client(); entrar(c, "carlos.rojas@example.test")
    assert 'id="m-benef-nuevo"' in c.get("/socio/membresia").get_data(as_text=True)
    assert 'id="m-cancelar-' in c.get("/socio/reservas").get_data(as_text=True)
    a = app.test_client(); entrar(a, ADMINS["general"], admin=True)
    assert 'id="m-bloq-' in a.get("/admin/instalaciones").get_data(as_text=True)
    b = app.test_client(); entrar(b, ADMINS["cobros"], admin=True)
    assert 'id="m-pago-' in b.get("/admin/cuentas").get_data(as_text=True)


def test_editar_y_quitar_beneficiario(app, ctx):
    from app.db import one
    c = app.test_client(); entrar(c, "carlos.rojas@example.test")
    b = one("SELECT id FROM beneficiarios LIMIT 1")["id"]
    r = c.post(f"/socio/membresia/beneficiarios/{b}/editar", data={"nombre": "Nombre Editado Prueba", "cedula": "202220399", "parentesco": "Hijo",
                                                                  "fecha_nacimiento": "2014-02-02"})
    assert r.status_code == 302
    assert one("SELECT nombre FROM beneficiarios WHERE id=?", (b,))["nombre"] == "Nombre Editado Prueba"


def test_socio_cambia_tipo_de_membresia(maria, ctx):
    from app.db import one
    assert maria.post("/socio/membresia/cambiar", data={"tipo": "corporativa"}).status_code == 302
    m = one("SELECT tipo, cuota FROM membresias m JOIN socios s ON s.id=m.socio_id WHERE s.correo='maria.solano@example.test'")
    assert m["tipo"] == "corporativa" and m["cuota"] == 90000


def test_registrar_pago_con_fecha(admin, ctx):
    from app.db import one
    cargo = one("SELECT id FROM cargos WHERE estado='pendiente' LIMIT 1")["id"]
    admin.post(f"/admin/cuentas/{cargo}/pago", data={"fecha_pago": "2026-11-01"})
    assert one("SELECT fecha_pago FROM cargos WHERE id=?", (cargo,))["fecha_pago"].startswith("2026-11-01")
    otro = one("SELECT id FROM cargos WHERE estado='pendiente' LIMIT 1")["id"]
    admin.post(f"/admin/cuentas/{otro}/pago", data={"fecha_pago": "2099-01-01"})   # futura: se rechaza
    assert one("SELECT estado FROM cargos WHERE id=?", (otro,))["estado"] == "pendiente"


def test_plantilla_vista_previa_no_guarda(admin, ctx):
    from app.db import one
    antes = one("SELECT asunto FROM plantillas_notificacion WHERE codigo='reserva_confirmada'")["asunto"]
    r = admin.post("/admin/plantillas/reserva_confirmada", data={"asunto": "Hola {nombre} en {instalacion}", "cuerpo": "x", "accion": "previsualizar"})
    assert "Hola Ana en Cancha de tenis" in r.get_data(as_text=True)
    assert one("SELECT asunto FROM plantillas_notificacion WHERE codigo='reserva_confirmada'")["asunto"] == antes


def test_calendario_semanal_con_detalle(admin, ctx):
    from app.db import one
    r = one("SELECT id, instalacion_id, fecha FROM reservas WHERE estado='confirmada' ORDER BY fecha DESC LIMIT 1")
    html = admin.get(f"/admin/calendario?instalacion_id={r['instalacion_id']}&fecha={r['fecha']}&reserva={r['id']}").get_data(as_text=True)
    assert "Detalle de la reserva" in html and "cal-evento" in html


def test_ocupacion_y_reportes(admin):
    html = admin.get("/admin/ocupacion").get_data(as_text=True)
    assert "Demanda por instalación" in html and "Mayor demanda" in html and "<progress" in html


def test_bloqueo_desde_modal(admin, ctx):
    from datetime import timedelta
    from app.db import hoy, one
    iid = one("SELECT id FROM instalaciones WHERE nombre='Cancha de golf'")["id"]
    fecha = (hoy() + timedelta(days=30)).isoformat()
    r = admin.post(f"/admin/instalaciones/{iid}/bloqueos", data={"fecha": fecha, "hora_inicio": "08:00", "hora_fin": "10:00", "motivo": "Mantenimiento", "volver": "lista"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/admin/instalaciones")
    assert one("SELECT 1 FROM bloqueos WHERE instalacion_id=? AND fecha=?", (iid, fecha))


def test_sin_ids_duplicados_en_ninguna_pagina(app):
    """Un id repetido rompe la asociación etiqueta-campo (accesibilidad); se revisan todas las páginas GET."""
    import re as _re
    from collections import Counter
    for correo, pref, admin in (("carlos.rojas@example.test", "/socio", False), (ADMINS["general"], "/admin", True)):
        c = app.test_client(); entrar(c, correo, admin=admin)
        for r in app.url_map.iter_rules():
            if "GET" not in r.methods or not r.rule.startswith(pref):
                continue
            url = _re.sub(r"<int:\w+>", "1", r.rule).replace("<periodo>", "2026-10").replace("<codigo>", "reserva_confirmada")
            if "<" in url:
                continue
            resp = c.get(url, follow_redirects=True)
            if resp.status_code != 200 or "html" not in resp.content_type:
                continue
            ids = _re.findall(r'\sid="([^"]+)"', resp.get_data(as_text=True))
            repetidos = [i for i, n in Counter(ids).items() if n > 1]
            assert not repetidos, f"{url}: ids repetidos {repetidos}"
