"""Endurecimiento de seguridad: alcance por almacén del escaneo de vales (H1, AC-06) y del
reporte de adeudos (H7, C-11).

Los datos se insertan con el constructor `datos` (ver `conftest.py`), dentro de la transacción de
la prueba.
"""

from fastapi.testclient import TestClient

from app.config import get_settings
from app.modulos.acceso.permisos import P
from app.modulos.catalogo.codigos import CodigoService
from app.modulos.catalogo.models import TipoCodigo
from tests.conftest import UsuarioPrueba, iniciar_sesion_en

ESCANEO = "/api/escaneo"
ADEUDOS = "/api/reportes/adeudos"


def _cliente_de(app, usuario: str) -> TestClient:
    cliente = TestClient(app)
    ajustes = get_settings()
    r = iniciar_sesion_en(cliente, UsuarioPrueba(usuario, ajustes.clave_datos_prueba))
    assert r.status_code == 200, r.text
    return cliente


def _tipo(cliente, codigo: str) -> str:
    r = cliente.get(f"{ESCANEO}/{codigo}")
    assert r.status_code == 200, r.text
    return r.json()["tipo"]


def _escenario_vales(datos):
    """Una ENTRADA de KEP y un TRASPASO KEP -> CON (en tránsito), con su QR y su código."""
    entrada = datos.vale("ENTRADA", "KEP", responsable="compras", codigo_qr="TOKEN-ENT-KEP")
    traspaso = datos.vale("TRASPASO", "KEP", responsable="almacenista", codigo_qr="TOKEN-TRA-KEP")
    traspaso.destino_almacen_id = datos.almacen("CON").id
    datos.session.flush()
    CodigoService(datos.session).registrar("VAL-H1-ENT", TipoCodigo.VALE, entrada.id)
    CodigoService(datos.session).registrar("VAL-H1-TRA", TipoCodigo.VALE, traspaso.id)
    return entrada, traspaso


def test_AC_06_un_almacenista_de_otro_almacen_no_escanea_un_vale_ajeno(app, datos):
    entrada, traspaso = _escenario_vales(datos)
    alm_con = _cliente_de(app, "alm_con")

    for codigo in (entrada.token, entrada.folio, "VAL-H1-ENT"):
        assert _tipo(alm_con, codigo) == "DESCONOCIDO", codigo
    # El detalle del vale confirma que no es suyo (404): el escaneo no puede decir más.
    assert alm_con.get(f"/api/vales/{entrada.id}").status_code == 404


def test_AC_06_el_receptor_de_un_traspaso_si_escanea_el_vale_que_le_llega(app, datos):
    entrada, traspaso = _escenario_vales(datos)
    alm_con = _cliente_de(app, "alm_con")

    for codigo in (traspaso.token, traspaso.folio, "VAL-H1-TRA"):
        cuerpo = alm_con.get(f"{ESCANEO}/{codigo}").json()
        assert cuerpo["tipo"] == "VALE", codigo
        assert cuerpo["id"] == str(traspaso.id)
    # Otro almacén que no es origen ni destino tampoco lo ve.
    alm_mid = _cliente_de(app, "alm_mid")
    assert _tipo(alm_mid, traspaso.token) == "DESCONOCIDO"


def test_AC_06_el_almacenista_ve_sus_vales_y_con_almacenes_todos_ve_todos(app, datos):
    entrada, traspaso = _escenario_vales(datos)
    alm_kep = _cliente_de(app, "almacenista")
    supervisor = _cliente_de(app, "supervisor")

    for cliente in (alm_kep, supervisor):
        assert _tipo(cliente, entrada.token) == "VALE"
        assert _tipo(cliente, traspaso.folio) == "VALE"


# ---------------------------------------------------------------------------------- adeudos


def _escenario_adeudos(datos):
    kep = datos.trabajador("Adeudo en KEP")
    con = datos.trabajador("Adeudo en CON")
    marro = datos.articulo("Marro H7")
    datos.existencia(datos.ub_almacen("KEP"), marro, 10)
    datos.existencia(datos.ub_almacen("CON"), marro, 10)
    datos.entrega(kep, marro, cantidad=1, almacen="KEP")
    datos.entrega(con, marro, cantidad=1, almacen="CON", responsable="alm_con")
    return kep, con


def _ids(cuerpo) -> set[str]:
    return {e["trabajador_id"] for e in cuerpo["elementos"]}


def test_C_11_un_almacenista_que_queda_sin_almacen_no_ve_adeudos(cliente_con, datos):
    _escenario_adeudos(datos)
    sin_almacen = cliente_con(P.REPORTES_ADEUDOS, P.TRABAJADORES_VER)  # sin almacén asignado

    cuerpo = sin_almacen.get(ADEUDOS, params={"tamano": 200}).json()

    assert cuerpo["total"] == 0 and cuerpo["elementos"] == []


def test_C_11_adeudos_por_permiso_rh_todos_almacenista_el_suyo_y_con_todos_los_almacenes_todos(
    cliente_como, cliente_con, datos
):
    kep, con = _escenario_adeudos(datos)

    def pedir(cliente):
        return cliente.get(ADEUDOS, params={"tamano": 200}).json()

    rh = pedir(cliente_como("Recursos Humanos"))
    almacenista = pedir(cliente_con(P.REPORTES_ADEUDOS, almacen="KEP"))
    con_todos = pedir(cliente_con(P.REPORTES_ADEUDOS, P.ALMACENES_TODOS))

    assert {str(kep.id), str(con.id)} <= _ids(rh)
    assert str(kep.id) in _ids(almacenista) and str(con.id) not in _ids(almacenista)
    assert {str(kep.id), str(con.id)} <= _ids(con_todos)
