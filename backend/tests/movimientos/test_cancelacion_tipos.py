"""CANCELACION de devoluciones y traspasos (vales insertados, K-04, X-14) y rechazo de los tipos
que no se cancelan (recepción y no adeudo).

DEVOLUCION, TRASPASO, RECEPCION y NO_ADEUDO los implementan otros agentes: aquí sus vales y
movimientos se insertan directamente con los modelos, consistentes con las invariantes.
"""

import pytest
from fastapi.testclient import TestClient

from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.catalogo.models import EstadoPieza
from app.modulos.movimientos.models import TipoVale
from tests.movimientos.ayudas import abastecer, crear_articulo, crear_trabajador, existencia
from tests.movimientos.cancelacion_ayudas import (
    Mov,
    cancelacion,
    cantidad_en,
    entregar,
    insertar_vale,
    ub_almacen,
    ub_trabajador,
    ub_virtual,
    url,
)
from tests.movimientos.test_cancelacion_basica import detalle, foto
from tests.movimientos.test_entrega import pieza_en_kep, renglon
from tests.movimientos.test_invariantes import revisar_folios, revisar_invariantes


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


def cancelar(cliente, vale_id, **extra):
    return cliente.post(url(vale_id), json=cancelacion(**extra))


def en_transito(
    session, almacen_origen, destino, articulo, cantidad, *, pieza=None, usuario="almacenista"
):
    """Un TRASPASO insertado: almacén de origen -> EN_TRANSITO, estado EN_TRANSITO."""
    return insertar_vale(
        session,
        TipoVale.TRASPASO,
        almacen_origen,
        [
            Mov(
                articulo,
                cantidad,
                ub_almacen(session, almacen_origen),
                ub_virtual(session, UbicacionVirtual.EN_TRANSITO),
                pieza,
            )
        ],
        usuario=usuario,
        estado="EN_TRANSITO",
        destino_almacen_clave=destino,
    )


@pytest.fixture
def usuario_de_con(app, crear_usuario, iniciar_sesion):
    """Un usuario del almacén de DESTINO (CON) con `vales.cancelar_todos`, sin `almacenes.todos`."""
    usuario = crear_usuario({P.VALES_CANCELAR, P.VALES_CANCELAR_TODOS, P.VALES_VER}, almacen="CON")
    cliente = TestClient(app)
    assert iniciar_sesion(cliente, usuario).status_code == 200
    yield cliente
    cliente.close()


# --------------------------------------------------------------------------- DEVOLUCION


def test_K_04_se_cancela_una_devolucion_y_el_resguardo_regresa_al_trabajador(
    almacenista, compras, session, trabajador
):
    casco = crear_articulo(session, retornable=True)
    abastecer(compras, casco, 10)
    entregar(almacenista, trabajador, [renglon(casco.codigo, 5)])
    devolucion = insertar_vale(
        session,
        TipoVale.DEVOLUCION,
        "KEP",
        [
            Mov(
                casco,
                3,
                ub_trabajador(session, trabajador),
                ub_almacen(session, "KEP"),
                None,
                trabajador,
                "BUENO",
            )
        ],
        trabajador=trabajador,
    )
    assert existencia(session, "KEP", casco) == 8

    r = cancelar(almacenista, devolucion.id, motivo="La devolvió otro compañero")
    assert r.status_code == 201, r.text
    assert "-CAN-" in r.json()["folio"]
    assert existencia(session, "KEP", casco) == 5
    assert cantidad_en(session, ub_trabajador(session, trabajador), casco) == 5
    assert detalle(almacenista, devolucion.id)["estado"] == "CANCELADO"
    revisar_invariantes(session)
    revisar_folios(session)


def test_K_04_la_devolucion_de_una_pieza_se_cancela_si_sigue_en_el_almacen(
    almacenista, compras, session, trabajador
):
    arnes, pieza = pieza_en_kep(compras, session)
    entregar(almacenista, trabajador, [renglon(pieza.codigo)])
    devolucion = insertar_vale(
        session,
        TipoVale.DEVOLUCION,
        "KEP",
        [
            Mov(
                arnes,
                1,
                ub_trabajador(session, trabajador),
                ub_almacen(session, "KEP"),
                pieza,
                trabajador,
                "BUENO",
            )
        ],
        trabajador=trabajador,
    )
    assert cancelar(almacenista, devolucion.id).status_code == 201
    session.refresh(pieza)
    assert pieza.ubicacion_id == ub_trabajador(session, trabajador).id  # otra vez con el trabajador
    revisar_invariantes(session)


def test_K_03_la_devolucion_de_una_pieza_no_se_cancela_si_ya_se_entrego_a_otro(
    almacenista, compras, session, trabajador
):
    arnes, pieza = pieza_en_kep(compras, session)
    entregar(almacenista, trabajador, [renglon(pieza.codigo)])
    devolucion = insertar_vale(
        session,
        TipoVale.DEVOLUCION,
        "KEP",
        [
            Mov(
                arnes,
                1,
                ub_trabajador(session, trabajador),
                ub_almacen(session, "KEP"),
                pieza,
                trabajador,
                "BUENO",
            )
        ],
        trabajador=trabajador,
    )
    otro = crear_trabajador(session)
    entregar(almacenista, otro, [renglon(pieza.codigo)])
    antes = foto(session)
    r = cancelar(almacenista, devolucion.id)
    assert r.status_code == 409 and r.json()["codigo"] == "NO_CANCELABLE"
    assert otro.numero_empleado in r.json()["mensaje"]
    assert foto(session) == antes


def test_K_03_una_devolucion_de_dano_a_baja_se_cancela_y_no_revierte_el_estado_de_la_pieza(
    almacenista, compras, session, trabajador
):
    """Decisión documentada: una pieza devuelta dañada quedó No apta (V-05, lo hace la
    DEVOLUCION); la cancelación mueve la pieza de vuelta al trabajador pero NO la rehabilita."""
    arnes, pieza = pieza_en_kep(compras, session)
    entregar(almacenista, trabajador, [renglon(pieza.codigo)])
    devolucion = insertar_vale(
        session,
        TipoVale.DEVOLUCION,
        "KEP",
        [
            Mov(
                arnes,
                1,
                ub_trabajador(session, trabajador),
                ub_almacen(session, "KEP"),
                pieza,
                trabajador,
                "DANADO",
            )
        ],
        trabajador=trabajador,
    )
    pieza.estado = EstadoPieza.NO_APTO  # lo que hace la DEVOLUCION al recibirla dañada
    session.flush()
    assert cancelar(almacenista, devolucion.id).status_code == 201
    session.refresh(pieza)
    assert pieza.estado == EstadoPieza.NO_APTO
    assert pieza.ubicacion_id == ub_trabajador(session, trabajador).id


def test_K_04_se_cancela_una_devolucion_de_articulo_danado_enviado_a_baja(
    almacenista, compras, session, trabajador
):
    casco = crear_articulo(session, retornable=True)
    abastecer(compras, casco, 6)
    entregar(almacenista, trabajador, [renglon(casco.codigo, 4)])
    baja = ub_virtual(session, UbicacionVirtual.BAJA)
    devolucion = insertar_vale(
        session,
        TipoVale.DEVOLUCION,
        "KEP",
        [
            Mov(
                casco,
                1,
                ub_trabajador(session, trabajador),
                ub_almacen(session, "KEP"),
                None,
                trabajador,
                "BUENO",
            ),
            Mov(
                casco,
                2,
                ub_trabajador(session, trabajador),
                baja,
                None,
                trabajador,
                "DANADO",
            ),
        ],
        trabajador=trabajador,
    )
    assert cantidad_en(session, baja, casco) == 2
    r = cancelar(almacenista, devolucion.id)
    assert r.status_code == 201, r.text
    assert cantidad_en(session, baja, casco) == 0
    assert cantidad_en(session, ub_trabajador(session, trabajador), casco) == 4
    assert existencia(session, "KEP", casco) == 2
    revisar_invariantes(session)


# ---------------------------------------------------------------------------- TRASPASO


def test_K_04_se_cancela_un_traspaso_en_transito_y_la_existencia_regresa_al_origen(
    almacenista, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    traspaso = en_transito(session, "KEP", "CON", guantes, 6)
    assert existencia(session, "KEP", guantes) == 4
    transito = ub_virtual(session, UbicacionVirtual.EN_TRANSITO)
    assert cantidad_en(session, transito, guantes) == 6

    r = cancelar(almacenista, traspaso.id, motivo="Se había mandado al almacén equivocado")
    assert r.status_code == 201, r.text
    assert existencia(session, "KEP", guantes) == 10
    assert cantidad_en(session, transito, guantes) == 0
    original = detalle(almacenista, traspaso.id)
    assert original["estado"] == "CANCELADO"
    assert original["cancelacion"]["motivo"] == "Se había mandado al almacén equivocado"
    vale_can = detalle(almacenista, r.json()["id"])
    assert vale_can["almacen"]["clave"] == "KEP" and "-CAN-" in vale_can["folio"]
    assert vale_can["renglones"][0]["origen"]["tipo"] == "EN_TRANSITO"
    assert vale_can["renglones"][0]["reglas"] == ["K-02", "X-14"]
    revisar_invariantes(session)
    revisar_folios(session)


def test_K_04_se_cancela_un_traspaso_de_piezas_y_vuelven_al_almacen_de_origen(
    almacenista, compras, session
):
    arnes, pieza = pieza_en_kep(compras, session)
    traspaso = en_transito(session, "KEP", "CON", arnes, 1, pieza=pieza)
    assert pieza.ubicacion_id == ub_virtual(session, UbicacionVirtual.EN_TRANSITO).id
    assert cancelar(almacenista, traspaso.id).status_code == 201
    session.refresh(pieza)
    assert pieza.ubicacion_id == ub_almacen(session, "KEP").id
    assert existencia(session, "KEP", arnes) == 1
    revisar_invariantes(session)


def test_X_14_un_traspaso_en_transito_lo_cancela_el_origen_no_el_destino(
    almacenista, usuario_de_con, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    traspaso = en_transito(session, "KEP", "CON", guantes, 6)
    antes = foto(session)

    r = cancelar(usuario_de_con, traspaso.id)
    assert r.status_code == 409 and r.json()["codigo"] == "NO_CANCELABLE", r.text
    assert r.json()["detalles"][0]["regla"] == "X-14"
    assert "almacén de origen" in r.json()["mensaje"]
    assert foto(session) == antes and existencia(session, "KEP", guantes) == 4

    assert cancelar(almacenista, traspaso.id).status_code == 201  # el origen sí


def test_X_14_un_traspaso_ya_recibido_no_se_cancela(almacenista, supervisor, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    traspaso = en_transito(session, "KEP", "CON", guantes, 6)
    insertar_vale(
        session,
        TipoVale.RECEPCION,
        "CON",
        [
            Mov(
                guantes,
                6,
                ub_virtual(session, UbicacionVirtual.EN_TRANSITO),
                ub_almacen(session, "CON"),
            )
        ],
        vale_origen=traspaso,
        usuario="supervisor",
    )
    traspaso.estado = "RECIBIDO"  # lo que hace la RECEPCION con el original
    session.flush()
    antes = foto(session)
    for cliente in (almacenista, supervisor):
        r = cancelar(cliente, traspaso.id)
        assert r.status_code == 409 and r.json()["codigo"] == "NO_CANCELABLE", r.text
        assert r.json()["detalles"][0]["regla"] == "X-14"
        assert "antes de la recepción" in r.json()["mensaje"]
    assert foto(session) == antes
    assert existencia(session, "CON", guantes) == 6


def test_X_14_un_traspaso_recibido_con_diferencias_tampoco_se_cancela(
    almacenista, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    traspaso = en_transito(session, "KEP", "CON", guantes, 6)
    traspaso.estado = "RECIBIDO_CON_DIFERENCIAS"
    session.flush()
    r = cancelar(almacenista, traspaso.id)
    assert r.status_code == 409 and r.json()["detalles"][0]["regla"] == "X-14"


def test_X_14_quien_no_hizo_el_traspaso_ni_tiene_cancelar_todos_recibe_403(
    app, crear_usuario, iniciar_sesion, almacenista, compras, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    traspaso = en_transito(session, "KEP", "CON", guantes, 2)
    destino = crear_usuario({P.VALES_CANCELAR, P.VALES_VER}, almacen="CON")
    with TestClient(app) as cliente:
        iniciar_sesion(cliente, destino)
        assert cancelar(cliente, traspaso.id).status_code == 403


# ----------------------------------------------------------- lo que no se cancela (K-04)


def test_K_04_una_recepcion_no_se_cancela(almacenista, supervisor, compras, session):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    traspaso = en_transito(session, "KEP", "CON", guantes, 6)
    recepcion = insertar_vale(
        session,
        TipoVale.RECEPCION,
        "CON",
        [
            Mov(
                guantes,
                6,
                ub_virtual(session, UbicacionVirtual.EN_TRANSITO),
                ub_almacen(session, "CON"),
            )
        ],
        vale_origen=traspaso,
        usuario="supervisor",
    )
    traspaso.estado = "RECIBIDO"
    session.flush()
    antes = foto(session)
    r = cancelar(supervisor, recepcion.id)
    assert r.status_code == 409 and r.json()["codigo"] == "NO_CANCELABLE", r.text
    assert [d["regla"] for d in r.json()["detalles"]] == ["K-04"]
    assert "recepción no se cancela" in r.json()["mensaje"]
    assert foto(session) == antes and existencia(session, "CON", guantes) == 6
    assert detalle(supervisor, recepcion.id)["estado"] == "EMITIDO"


def test_K_04_un_vale_de_no_adeudo_no_se_cancela(almacenista, session, trabajador):
    no_adeudo = insertar_vale(session, TipoVale.NO_ADEUDO, "KEP", [], trabajador=trabajador)
    antes = foto(session)
    r = cancelar(almacenista, no_adeudo.id)
    assert r.status_code == 409 and r.json()["codigo"] == "NO_CANCELABLE", r.text
    assert [d["regla"] for d in r.json()["detalles"]] == ["K-04"]
    assert "no adeudo no se cancela" in r.json()["mensaje"]
    assert foto(session) == antes
    assert detalle(almacenista, no_adeudo.id)["estado"] == "EMITIDO"
