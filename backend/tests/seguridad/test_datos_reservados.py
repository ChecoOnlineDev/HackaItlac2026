"""Endurecimiento (H10, AC-05): un alta duplicada no filtra la CURP ni a la persona.

Quien da de alta (`trabajadores.administrar`) pero no tiene `trabajadores.ver_datos_personales`
solo debe saber que ya existe, no que fue por la CURP ni quién es.
"""

from fastapi.testclient import TestClient

from app.modulos.acceso.permisos import P
from tests.conftest import iniciar_sesion_en
from tests.test_trabajadores import dar_de_alta, payload

CURP = "HHHH900101HDFRRR09"


def _cliente(app, crear_usuario, *permisos: str) -> TestClient:
    usuario = crear_usuario(set(permisos), almacen=None)
    cliente = TestClient(app)
    assert iniciar_sesion_en(cliente, usuario).status_code == 200
    return cliente


def test_AC_05_sin_ver_datos_personales_una_curp_repetida_solo_dice_que_ya_existe(
    app, cliente_como, crear_usuario
):
    dar_de_alta(cliente_como("Recursos Humanos"), curp=CURP, nombre="Persona Reservada")
    sin_permiso = _cliente(app, crear_usuario, P.TRABAJADORES_ADMINISTRAR, P.TRABAJADORES_VER)

    r = sin_permiso.post("/api/trabajadores", json=payload(curp=CURP))

    assert r.status_code == 409
    cuerpo = r.json()
    assert cuerpo["codigo"] == "TRABAJADOR_EXISTE"
    assert "coincide_por" not in (cuerpo["detalles"] or {})
    assert "trabajador" not in (cuerpo["detalles"] or {})
    assert "Persona Reservada" not in r.text and "CURP" not in r.text and "curp" not in r.text


def test_AC_05_con_ver_datos_personales_la_curp_repetida_ofrece_el_reingreso(
    cliente_como,
):
    rh = cliente_como("Recursos Humanos")
    existente = dar_de_alta(rh, curp=CURP.replace("09", "08"), nombre="Persona Visible")

    r = rh.post("/api/trabajadores", json=payload(curp=CURP.replace("09", "08")))

    assert r.status_code == 409
    assert r.json()["detalles"]["coincide_por"] == "curp"
    assert r.json()["detalles"]["trabajador"]["id"] == existente["id"]


def test_AC_05_el_numero_de_empleado_repetido_sigue_ofreciendo_el_reingreso_sin_el_permiso(
    app, cliente_como, crear_usuario
):
    existente = dar_de_alta(cliente_como("Recursos Humanos"), nombre="Persona Con Numero")
    sin_permiso = _cliente(app, crear_usuario, P.TRABAJADORES_ADMINISTRAR, P.TRABAJADORES_VER)

    r = sin_permiso.post(
        "/api/trabajadores", json=payload(numero_empleado=existente["numero_empleado"])
    )

    assert r.status_code == 409
    assert r.json()["detalles"]["coincide_por"] == "numero_empleado"
