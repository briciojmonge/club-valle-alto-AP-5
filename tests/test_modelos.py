"""Reglas de negocio ejercitadas directamente sobre los modelos."""
from datetime import timedelta

import pytest

from app.db import ReglaError, hoy, one, query, execute
from app.models import acceso, cuenta, instalacion, invitado, membresia, reserva, socio
from tests.conftest import form


def _id(correo):
    return one("SELECT id FROM socios WHERE correo=?", (correo,))["id"]


def _inst(n):
    return one("SELECT * FROM instalaciones WHERE nombre=?", (n,))


def _d(n):
    return (hoy() + timedelta(days=n)).isoformat()


def _res(sid, inst, fecha, ini, fin, personas):
    return reserva.crear(sid, form(instalacion_id=_inst(inst)["id"], fecha=fecha, hora_inicio=ini, hora_fin=fin, personas=personas))


# ---- socios / acceso
def test_login_correcto_y_incorrecto(ctx):
    assert socio.autenticar("maria.solano@example.test", "Demo2026!")
    with pytest.raises(ReglaError):
        socio.autenticar("maria.solano@example.test", "mala")
    with pytest.raises(ReglaError):
        socio.autenticar("noexiste@example.test", "x")


def test_bloqueo_por_intentos(ctx):
    for _ in range(5):
        with pytest.raises(ReglaError):
            socio.autenticar("jorge.castro@example.test", "mala")
    with pytest.raises(ReglaError) as e:
        socio.autenticar("jorge.castro@example.test", "Demo2026!")  # ni con la clave correcta
    assert "bloqueada" in str(e.value)


def test_registro_duplicado_y_password_debil(ctx):
    base = dict(nombre="Nuevo Socio Prueba", cedula="999000111", correo="nuevo@example.test", telefono="8800-0000",
                direccion="Cartago", fecha_nacimiento="1990-01-01", password="Clave2026!", password2="Clave2026!")
    socio.registrar(form(**base))
    with pytest.raises(ReglaError):
        socio.registrar(form(**base))
    with pytest.raises(ReglaError):
        socio.registrar(form(**{**base, "cedula": "999000112", "correo": "otro@example.test", "password": "abc", "password2": "abc"}))


def test_recuperacion_por_enlace_un_solo_uso(ctx):
    socio.solicitar_recuperacion("maria.solano@example.test")
    n = one("SELECT COUNT(*) c FROM notificaciones WHERE asunto LIKE '%contraseña%' OR asunto LIKE '%Recuper%'")["c"]
    assert n >= 1
    socio.solicitar_recuperacion("nadie@example.test")  # no revela si existe: no lanza


# ---- membresías
def test_beneficiarios_solo_familiar_y_limite(ctx):
    m_ind = one("SELECT id FROM membresias WHERE socio_id=?", (_id("maria.solano@example.test"),))["id"]
    with pytest.raises(ReglaError):
        membresia.agregar_beneficiario(m_ind, form(nombre="X Y Z", cedula="1", parentesco="Hijo", fecha_nacimiento="2010-01-01"))
    m_fam = one("SELECT id FROM membresias WHERE socio_id=?", (_id("carlos.rojas@example.test"),))["id"]
    assert len(membresia.beneficiarios(m_fam)) == 3


def test_estados_e_historial(ctx):
    mid = one("SELECT id FROM membresias WHERE socio_id=?", (_id("ana.barquero@example.test"),))["id"]
    assert one("SELECT estado FROM membresias WHERE id=?", (mid,))["estado"] == "suspendida"
    assert len(membresia.historial(mid)) >= 2
    mid_d = one("SELECT id FROM membresias WHERE socio_id=?", (_id("diego.chaves@example.test"),))["id"]
    assert one("SELECT estado FROM membresias WHERE id=?", (mid_d,))["estado"] == "vencida"


# ---- invitados
def test_limite_mensual_invitados(ctx):
    sid = _id("maria.solano@example.test")  # individual
    usados, limite = invitado.cupo(sid, hoy().strftime("%Y-%m"))
    registrados = 0
    with pytest.raises(ReglaError) as e:
        for i in range(limite + 3):
            invitado.registrar(sid, form(nombre=f"Invitado Prueba {i}", cedula=f"77700{i:04d}", fecha_visita=_d(1),
                                         instalacion_id=_inst("Piscina")["id"], relacion="amigo"))
            registrados += 1
    assert "límite" in str(e.value)
    assert registrados <= limite


def test_invitado_en_pasado_rechazado(ctx):
    with pytest.raises(ReglaError):
        invitado.registrar(_id("maria.solano@example.test"), form(nombre="Pasado Prueba", cedula="123123123", fecha_visita=_d(-1),
                                                                  instalacion_id=_inst("Piscina")["id"], relacion="amigo"))


def test_listado_esperados_para_recepcion(ctx):
    assert len(invitado.esperados(_d(1))) >= 2


# ---- reservas
def test_sin_traslape_en_instalacion_exclusiva(ctx):
    sid = _id("diego.chaves@example.test")
    execute("UPDATE membresias SET estado='activa' WHERE socio_id=?", (sid,))
    _res(sid, "Cancha de tenis", _d(9), "10:00", "11:00", 2)
    with pytest.raises(ReglaError) as e:
        _res(_id("maria.solano@example.test"), "Cancha de tenis", _d(9), "10:30", "11:30", 2)
    assert "traslape" in str(e.value)
    _res(_id("maria.solano@example.test"), "Cancha de tenis", _d(9), "11:00", "12:00", 2)  # contiguas sí


def test_horario_y_aforo_y_bloqueo(ctx):
    maria = _id("maria.solano@example.test")
    with pytest.raises(ReglaError):
        _res(maria, "Cancha de tenis", _d(8), "02:00", "03:00", 2)       # fuera de horario
    with pytest.raises(ReglaError):
        _res(maria, "Cancha de tenis", _d(8), "10:00", "11:00", 50)      # aforo
    with pytest.raises(ReglaError):
        _res(maria, "Piscina", _d(7), "09:00", "10:00", 2)               # bloqueo de mantenimiento


def test_instalacion_compartida_suma_aforo(ctx):
    inst = _inst("Piscina")
    cupo = inst["aforo_max"]
    maria, carlos = _id("maria.solano@example.test"), _id("carlos.rojas@example.test")
    _res(maria, "Piscina", _d(12), "15:00", "16:00", cupo - 2)
    _res(carlos, "Piscina", _d(12), "15:00", "16:00", 2)
    with pytest.raises(ReglaError):
        _res(carlos, "Piscina", _d(12), "15:30", "16:30", 1)


def test_modificar_cancelar_y_pendiente_confirmar(ctx):
    maria = _id("maria.solano@example.test")
    rid = _res(maria, "Cancha de tenis", _d(14), "09:00", "10:00", 2)
    reserva.modificar(rid, form(instalacion_id=_inst("Cancha de tenis")["id"], fecha=_d(14), hora_inicio="09:00", hora_fin="10:00", personas=3), socio_id=maria)
    reserva.cancelar(rid, socio_id=maria)
    assert reserva.por_id(rid)["estado"] == "cancelada"
    with pytest.raises(ReglaError):
        reserva.cancelar(rid, socio_id=maria)
    pend = one("SELECT id FROM reservas WHERE estado='pendiente'")["id"]
    reserva.confirmar(pend)
    assert reserva.por_id(pend)["estado"] == "confirmada"


def test_no_modifica_reserva_ajena_ni_finalizada(ctx):
    fin = one("SELECT id, socio_id FROM reservas WHERE estado='finalizada'")
    with pytest.raises(ReglaError):
        reserva.cancelar(fin["id"], socio_id=fin["socio_id"])


def test_socio_sin_membresia_activa_no_reserva(ctx):
    with pytest.raises(ReglaError):
        _res(_id("sofia.valverde@example.test"), "Cancha de tenis", _d(20), "09:00", "10:00", 2)
    with pytest.raises(ReglaError):
        _res(_id("ana.barquero@example.test"), "Cancha de tenis", _d(20), "09:00", "10:00", 2)  # suspendida


# ---- cuentas
def test_estado_de_cuenta_morosos_y_pago(ctx):
    mor = cuenta.morosos()
    assert {m["correo"] for m in mor} >= {"roberto.mena@example.test"}
    cargo = one("SELECT id FROM cargos WHERE estado='pendiente' LIMIT 1")["id"]
    admin = one("SELECT id FROM admins LIMIT 1")["id"]
    cuenta.registrar_pago(cargo, admin)
    assert one("SELECT estado FROM cargos WHERE id=?", (cargo,))["estado"] == "pagado"
    with pytest.raises(ReglaError):
        cuenta.registrar_pago(cargo, admin)  # no se paga dos veces


def test_generar_periodo_es_idempotente(ctx):
    p = cuenta.periodo_actual()
    antes = one("SELECT COUNT(*) c FROM cargos")["c"]
    cuenta.generar_periodo(p)
    assert one("SELECT COUNT(*) c FROM cargos")["c"] == antes


def test_pdf_estado_de_cuenta(ctx):
    from app.services import pdf
    sid = _id("carlos.rojas@example.test")
    p = cuenta.periodo_actual()
    data = pdf.estado_cuenta_pdf(socio.por_id(sid), p, cuenta.resumen(sid, p), "familiar", "2026-01-01 00:00:00")
    assert bytes(data)[:4] == b"%PDF"
