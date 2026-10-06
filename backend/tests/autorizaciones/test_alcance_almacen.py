"""AC-06 y A-01: una autorización es del almacén en que se pidió.

Solo la ven y la resuelven los supervisores de ese almacén y el Administrador. El verificador falso
de `conftest.py` arma los renglones; aquí se prueba el alcance, no la evaluación.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.modulos.acceso.permisos import P
from app.modulos.trabajadores.models import Trabajador
from tests.conftest import UsuarioPrueba, iniciar_sesion_en

RUTA = "/api/autorizaciones"


def _cliente(app, usuario: str) -> TestClient:
    ajustes = get_settings()
    c = TestClient(app)
    asegurado = iniciar_sesion_en(
        c, UsuarioPrueba(usuario, ajustes.clave_datos_prueba, ajustes.pin_datos_prueba)
    )
    assert asegurado.status_code == 200, asegurado.text
    return c


@pytest.fixture
def trabajador(session) -> Trabajador:
    t = Trabajador(numero_empleado=f"E-{uuid.uuid4().hex[:8]}", nombre="Juan Pérez")
    session.add(t)
    session.flush()
    return t


def _pedir(cliente: TestClient, trabajador: Trabajador) -> str:
    cuerpo = {
        "trabajador_id": str(trabajador.id),
        "renglones": [{"codigo": "ALT-024", "cantidad": 3}],
        "motivo": "Trabajo especial",
    }
    r = cliente.post(RUTA, json=cuerpo)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _ids(cliente: TestClient) -> list[str]:
    r = cliente.get(RUTA)
    assert r.status_code == 200, r.text
    return [e["id"] for e in r.json()["elementos"]]


def test_A_01_AC_06_el_supervisor_de_midrex_no_ve_ni_resuelve_lo_de_kepler(app, trabajador):
    de_kepler = _pedir(_cliente(app, "almacenista"), trabajador)
    sup_mid = _cliente(app, "sup_mid")
    assert de_kepler not in _ids(sup_mid)
    assert sup_mid.get(f"{RUTA}/{de_kepler}").status_code == 404
    r = sup_mid.post(f"{RUTA}/{de_kepler}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 404
    # El supervisor de Kepler sí.
    assert de_kepler in _ids(_cliente(app, "supervisor"))


def test_A_01_AC_06_el_supervisor_de_midrex_ve_y_resuelve_lo_de_midrex(app, trabajador):
    de_midrex = _pedir(_cliente(app, "alm_mid"), trabajador)
    sup_mid = _cliente(app, "sup_mid")
    assert de_midrex in _ids(sup_mid)
    assert sup_mid.get(f"{RUTA}/{de_midrex}").status_code == 200
    r = sup_mid.post(f"{RUTA}/{de_midrex}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 200 and r.json()["estado"] == "APROBADA"
    # Y el de Kepler no ve la de Midrex.
    assert de_midrex not in _ids(_cliente(app, "supervisor"))


def test_A_01_AC_06_el_administrador_ve_las_autorizaciones_de_todos_los_almacenes(app, trabajador):
    de_kepler = _pedir(_cliente(app, "almacenista"), trabajador)
    de_midrex = _pedir(_cliente(app, "alm_mid"), trabajador)
    ids = _ids(_cliente(app, "admin"))
    assert de_kepler in ids and de_midrex in ids


def test_AC_06_un_supervisor_sin_almacen_asignado_no_ve_nada(
    app, trabajador, crear_usuario, iniciar_sesion
):
    de_kepler = _pedir(_cliente(app, "almacenista"), trabajador)
    sin_almacen = crear_usuario({P.AUTORIZACIONES_RESOLVER}, pin="4321")
    c = TestClient(app)
    iniciar_sesion(c, sin_almacen)
    assert c.get(RUTA).status_code == 403
    assert c.get(f"{RUTA}/{de_kepler}").status_code == 404
    r = c.post(f"{RUTA}/{de_kepler}/resolucion", json={"decision": "APROBAR"})
    assert r.status_code == 404


def test_A_01_AC_06_con_el_pin_de_un_supervisor_de_otro_almacen_se_rechaza(app, trabajador):
    """El almacenista de Midrex no puede usar a un supervisor de Kepler para autorizar en Midrex."""
    de_midrex = _pedir(_cliente(app, "alm_mid"), trabajador)
    ajustes = get_settings()
    r = _cliente(app, "alm_mid").post(
        f"{RUTA}/{de_midrex}/resolucion",
        json={"decision": "APROBAR", "usuario": "supervisor", "pin": ajustes.pin_datos_prueba},
    )
    assert r.status_code == 403, r.text
    # El supervisor de su propio almacén sí autoriza con su PIN.
    r = _cliente(app, "alm_mid").post(
        f"{RUTA}/{de_midrex}/resolucion",
        json={"decision": "APROBAR", "usuario": "sup_mid", "pin": ajustes.pin_datos_prueba},
    )
    assert r.status_code == 200 and r.json()["medio"] == "PIN"
