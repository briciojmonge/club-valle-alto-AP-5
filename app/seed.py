"""Datos FICTICIOS de demostración (flask seed). No usar en producción.

Todos los datos pasan por los mismos modelos y reglas de negocio que usa la aplicación, de modo que la
carga también ejercita las validaciones. Las fechas son relativas a hoy para que la demo siempre se vea viva.
"""
from datetime import timedelta

from werkzeug.datastructures import MultiDict

from app.db import ahora_txt, execute, get_db, hoy, one
from app.models import admin as admin_model
from app.models import config, cuenta, instalacion, invitado, membresia, reserva, socio

PASSWORD_DEMO = "Demo2026!"


def _f(**campos):
    """Formulario simulado (MultiDict no acepta argumentos con nombre)."""
    return MultiDict(campos)

ADMINS = [
    ("Carlos Mora", "100000001", "admin@clubvallealto.test", "general"),
    ("Laura Vega", "100000002", "instalaciones@clubvallealto.test", "instalaciones"),
    ("Diego Solís", "100000003", "cobros@clubvallealto.test", "cobros"),
]

# nombre, cédula, correo, teléfono, dirección, nacimiento
SOCIOS = [
    ("María Fernanda Solano Vargas", "101110111", "maria.solano@example.test", "8811-0001", "Cartago, Oriental, 200 m este de la Basílica", "1988-03-14"),
    ("Carlos Andrés Rojas Mora", "202220222", "carlos.rojas@example.test", "8811-0002", "Paraíso, Cartago, urbanización Los Cedros", "1981-07-02"),
    ("Laura Patricia Jiménez Cordero", "303330333", "laura.jimenez@example.test", "8811-0003", "Tres Ríos, La Unión, Residencial Valle Verde", "1979-11-23"),
    ("Jorge Luis Castro Araya", "404440444", "jorge.castro@example.test", "8811-0004", "Oreamuno, Cartago, calle principal de Cot", "1955-01-30"),
    ("Ana Lucía Barquero Solís", "505550555", "ana.barquero@example.test", "8811-0005", "Turrialba, Cartago, barrio Las Américas", "1992-09-09"),
    ("Diego Alonso Chaves Brenes", "606660666", "diego.chaves@example.test", "8811-0006", "El Guarco, Cartago, Tejar", "1985-05-18"),
    ("Sofía Valverde Quesada", "707770777", "sofia.valverde@example.test", "8811-0007", "Cartago, San Nicolás, Residencial Los Ángeles", "1996-12-01"),
    ("Roberto Mena Salazar", "808880888", "roberto.mena@example.test", "8811-0008", "Alvarado, Pacayas, 100 m norte de la iglesia", "1974-06-27"),
]


def _d(n):
    return (hoy() + timedelta(days=n)).isoformat()


def _inst(nombre):
    return one("SELECT * FROM instalaciones WHERE nombre=?", (nombre,))


def _servicios(inst_nombre, *nombres):
    inst = _inst(inst_nombre)
    por_nombre = {s["nombre"]: str(s["id"]) for s in instalacion.servicios(inst["id"])}
    return [por_nombre[n] for n in nombres]


def _reserva(socio_id, inst_nombre, fecha, ini, fin, personas, servicios=()):
    inst = _inst(inst_nombre)
    return reserva.crear(socio_id, MultiDict([("instalacion_id", inst["id"]), ("fecha", fecha), ("hora_inicio", ini),
                                              ("hora_fin", fin), ("personas", personas)] + [("servicios", s) for s in servicios]))


def _reserva_directa(socio_id, inst_nombre, fecha, ini, fin, personas, estado, servicios=()):
    """Inserta una reserva en un estado que el flujo normal no permite crear (pasadas, pendientes, canceladas)."""
    inst = _inst(inst_nombre)
    rid = execute(
        "INSERT INTO reservas(socio_id, instalacion_id, fecha, hora_inicio, hora_fin, personas, estado, creado_en, actualizado_en) "
        "VALUES (?,?,?,?,?,?,?,?,?)", (socio_id, inst["id"], fecha, ini, fin, personas, estado, ahora_txt(), ahora_txt()))
    costos = {str(s["id"]): s["costo"] for s in instalacion.servicios(inst["id"])}
    for sid in servicios:
        execute("INSERT INTO reserva_servicios(reserva_id, servicio_id, costo) VALUES (?,?,?)", (rid, int(sid), costos[sid]))
    return rid


def reiniciar():
    db = get_db()
    tablas = ["notificaciones", "estados_cuenta", "cargos", "reserva_servicios", "reservas", "invitados", "bloqueos",
              "beneficiarios", "membresia_historial", "membresias", "reset_tokens", "socios", "admins"]
    for t in tablas:
        db.execute(f"DELETE FROM {t}")
    db.execute("DELETE FROM sqlite_sequence WHERE name IN (%s)" % ",".join("?" * len(tablas)), tablas)
    db.commit()


def cargar(reset=False):
    if reset:
        reiniciar()
    elif one("SELECT 1 FROM socios LIMIT 1") or one("SELECT 1 FROM admins LIMIT 1"):
        raise SystemExit("La base de datos ya contiene usuarios. Use «flask seed --reset» para reemplazarlos por los datos de prueba.")
    config.cargar_catalogos_iniciales()

    # ---- administradores y socios
    admin_ids = {}
    for nombre, ced, correo, rol in ADMINS:
        admin_ids[rol] = admin_model.crear(_f(nombre=nombre, cedula=ced, correo=correo, rol=rol, password=PASSWORD_DEMO))
    actor = f"admin:{admin_ids['general']}"
    ids = {}
    for nombre, ced, correo, tel, direccion, nac in SOCIOS:
        ids[correo.split("@")[0].split(".")[0]] = socio.registrar(_f(
            nombre=nombre, cedula=ced, correo=correo, telefono=tel, direccion=direccion, fecha_nacimiento=nac,
            password=PASSWORD_DEMO, password2=PASSWORD_DEMO))
    maria, carlos, laura, jorge, ana, diego, sofia, roberto = (ids[k] for k in
        ("maria", "carlos", "laura", "jorge", "ana", "diego", "sofia", "roberto"))

    # ---- membresías (sofía queda sin membresía para demostrar el alta por autoservicio)
    inscripcion = hoy() - timedelta(days=200)
    mids = {}
    for clave, sid, tipo in (("maria", maria, "individual"), ("carlos", carlos, "familiar"), ("laura", laura, "corporativa"),
                             ("jorge", jorge, "honoraria"), ("ana", ana, "individual"), ("roberto", roberto, "individual")):
        mids[clave] = membresia.crear(sid, tipo, actor, por_personal=True, fecha_inscripcion=inscripcion)
    # Diego: su fecha de renovación ya pasó, así que el sistema la marca como vencida.
    mids["diego"] = membresia.crear(diego, "individual", actor, por_personal=True, fecha_inscripcion=hoy() - timedelta(days=400))
    membresia.cambiar_estado(mids["ana"], "suspendida", "Solicitud de la socia (demostración)", actor)
    membresia.refrescar_vencimientos()
    for nombre, ced, parentesco, nac in (("Elena Mora Campos", "202220301", "Cónyuge", "1983-02-11"),
                                         ("Mateo Rojas Mora", "202220302", "Hijo", "2012-08-30"),
                                         ("Valeria Rojas Mora", "202220303", "Hija", "2015-04-05")):
        membresia.agregar_beneficiario(mids["carlos"], _f(nombre=nombre, cedula=ced, parentesco=parentesco, fecha_nacimiento=nac))

    # ---- reservas futuras (pasan por las validaciones reales) y casos especiales
    _reserva(maria, "Cancha de tenis", _d(2), "16:00", "17:00", 2, _servicios("Cancha de tenis", "Alquiler de raquetas"))
    _reserva(maria, "Cancha de golf", _d(3), "07:00", "11:00", 2, _servicios("Cancha de golf", "Alquiler de palos"))
    _reserva(carlos, "Piscina", _d(1), "10:00", "12:00", 5)
    _reserva(laura, "Salón de eventos", _d(5), "18:00", "23:00", 60, _servicios("Salón de eventos", "Montaje de mobiliario", "Equipo de sonido"))
    _reserva_directa(maria, "Cancha de tenis", _d(0), "19:00", "20:00", 2, "confirmada")   # reserva de hoy para la demo
    _reserva_directa(roberto, "Cancha de tenis", _d(2), "18:00", "19:00", 2, "pendiente")
    _reserva_directa(carlos, "Cancha de golf", _d(4), "08:00", "12:00", 3, "cancelada")
    # Reservas ya realizadas (una con servicios en el mes anterior, que alimenta el estado de cuenta)
    primero_mes = hoy().replace(day=1)
    mes_anterior = primero_mes - timedelta(days=1)
    _reserva_directa(carlos, "Salón de eventos", (mes_anterior - timedelta(days=4)).isoformat(), "15:00", "22:00", 40, "finalizada",
                     _servicios("Salón de eventos", "Montaje de mobiliario"))
    _reserva_directa(maria, "Cancha de tenis", _d(-6), "17:00", "18:00", 2, "finalizada")
    _reserva_directa(laura, "Piscina", _d(-3), "09:00", "11:00", 8, "finalizada")

    # ---- bloqueos de instalaciones y reglas de invitados
    general = admin_ids["general"]
    instalacion.crear_bloqueo(_inst("Piscina")["id"], _f(fecha=_d(7), hora_inicio="08:00", hora_fin="12:00",
                                                                 motivo="Mantenimiento y limpieza de la piscina"), general)
    instalacion.crear_bloqueo(_inst("Salón de eventos")["id"], _f(fecha=_d(10), hora_inicio="14:00", hora_fin="22:00",
                                                                          motivo="Evento privado de la Gerencia"), general)
    for nombre, ced, rel, dias, inst_n in (("Pablo Vargas León", "909990901", "amigo", 1, "Piscina"),
                                           ("Sandra Mora Campos", "909990902", "familiar", 1, "Piscina"),
                                           ("Esteban Ureña Gómez", "909990903", "amigo", 2, "Cancha de tenis")):
        invitado.registrar(carlos if dias == 1 else maria, _f(nombre=nombre, cedula=ced, fecha_visita=_d(dias),
                                                                    instalacion_id=_inst(inst_n)["id"], relacion=rel))

    invitado.registrar(carlos, _f(nombre="Lucía Mena Araya", cedula="909990904", fecha_visita=_d(0),
                                  instalacion_id=_inst("Piscina")["id"], relacion="familiar"))

    # ---- estados de cuenta: dos meses anteriores (con morosidad) y el mes actual
    periodo_actual = cuenta.periodo_actual()
    periodo_ant = mes_anterior.strftime("%Y-%m")
    periodo_ant2 = (mes_anterior.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    for periodo, atraso, morosos in ((periodo_ant2, 65, ("roberto",)), (periodo_ant, 20, ("roberto", "laura"))):
        cuenta.generar_periodo(periodo)
        execute("UPDATE cargos SET fecha_limite=? WHERE periodo=?", (_d(-atraso), periodo))
        sin_pagar = {ids[m] for m in morosos}
        for c in get_db().execute("SELECT id, socio_id FROM cargos WHERE periodo=? AND estado='pendiente'", (periodo,)).fetchall():
            if c["socio_id"] not in sin_pagar:
                cuenta.registrar_pago(c["id"], admin_ids["cobros"])
    cuenta.generar_periodo(periodo_actual)
    cuenta.tareas_diarias()   # avisos de pago vencido para los morosos de la demostración


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit("Use: flask --app app seed --reset")
