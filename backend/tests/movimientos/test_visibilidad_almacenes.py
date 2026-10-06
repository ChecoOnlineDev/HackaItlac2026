# ruff: noqa: F811  (los fixtures importados se piden por nombre en cada prueba)
"""AC-06 y E-03 en los vales: quien no tiene `almacenes.todos` no se entera de qué hay en otros
almacenes, pero Devolver y Recibir siguen funcionando.

El almacenista de Kepler es `almacenista`; el de Midrex, `alm_mid`; el de Contratistas, `alm_con`.
"""

from datetime import timedelta

import pytest

from app.core.tiempo import hoy_mx
from tests.movimientos.ayudas import abastecer, crear_articulo, crear_trabajador
from tests.movimientos.ayudas_devolucion import (
    evaluar_devolucion,
    pieza_entregada,
)
from tests.movimientos.ayudas_devolucion import (
    motivos as motivos_devolucion,
)
from tests.movimientos.ayudas_devolucion import (
    renglon as renglon_devolucion,
)
from tests.movimientos.ayudas_traspasos import (
    cliente_almacen,  # noqa: F401  (fixture)
    enviar,
    evaluar_traspaso,
    recibir,
    reglas,
    renglon,
    vale,
)
from tests.movimientos.test_entrega import evaluar, pieza_en_kep


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


def vigencia_pieza():
    return hoy_mx() + timedelta(days=30)


def test_E_03_una_pieza_en_transito_hacia_mi_almacen_se_explica_al_almacenista_de_destino(
    compras, almacenista, cliente_almacen, session, trabajador
):
    _, pieza = pieza_en_kep(compras, session, vigente_hasta=vigencia_pieza())
    enviar(almacenista, session, "MID", [renglon(pieza.codigo)])
    midrex = cliente_almacen("MID")

    ev = evaluar(midrex, trabajador, [renglon(pieza.codigo)])

    mensaje = ev["renglones"][0]["motivos"][0]["mensaje"]
    assert "E-03" in [m["regla"] for m in ev["renglones"][0]["motivos"]]
    assert "tránsito" in mensaje


def test_E_03_una_pieza_en_transito_hacia_otro_almacen_no_se_explica_al_almacenista_ajeno(
    compras, almacenista, cliente_almacen, session, trabajador
):
    _, pieza = pieza_en_kep(compras, session, vigente_hasta=vigencia_pieza())
    enviar(almacenista, session, "MID", [renglon(pieza.codigo)])
    contratistas = cliente_almacen("CON")

    ev = evaluar(contratistas, trabajador, [renglon(pieza.codigo)])

    r = ev["renglones"][0]
    assert r["motivos"][0]["mensaje"] == (
        "Esta pieza no está registrada en tu almacén. No se puede entregar."
    )
    assert "Midrex (MID)" not in str(r) and "tránsito" not in str(r)


def test_X_02_una_pieza_de_otro_almacen_no_dice_donde_esta_al_intentar_enviarla(
    compras, cliente_almacen, session
):
    _, pieza = pieza_en_kep(compras, session, vigente_hasta=vigencia_pieza())
    midrex = cliente_almacen("MID")

    ev = evaluar_traspaso(midrex, session, "CON", [renglon(pieza.codigo)])

    assert "X-02" in reglas(ev, 0)
    mensaje = ev["renglones"][0]["motivos"][0]["mensaje"]
    assert mensaje == "Esta pieza no está registrada en tu almacén. No se puede enviar."
    assert "Kepler" not in str(ev) and "KEP" not in str(ev)


def test_V_01_devolver_una_pieza_que_vino_de_otro_almacen_sigue_abonandose_a_su_titular(
    compras, almacenista, cliente_almacen, session, trabajador
):
    # AC-06 no rompe Devolver: la pieza está en resguardo del trabajador y cualquier almacén que
    # la reciba identifica a su titular, aunque la haya entregado Kepler.
    _, pieza = pieza_entregada(compras, almacenista, session, trabajador)
    midrex = cliente_almacen("MID")

    ev = evaluar_devolucion(midrex, [renglon_devolucion(pieza.codigo)])

    assert motivos_devolucion(ev) == ["V-01", "V-07"]  # V-07: lo entregó otro almacén
    assert ev["renglones"][0]["nivel"] != "ROJO"
    assert trabajador.numero_empleado in ev["renglones"][0]["motivos"][0]["mensaje"]


def test_V_02_una_pieza_que_esta_en_otro_almacen_no_dice_cual_al_intentar_devolverla(
    compras, cliente_almacen, session
):
    _, pieza = pieza_en_kep(compras, session, vigente_hasta=vigencia_pieza())
    midrex = cliente_almacen("MID")

    ev = evaluar_devolucion(midrex, [renglon_devolucion(pieza.codigo)])

    assert motivos_devolucion(ev) == ["V-02"]
    assert "Kepler" not in str(ev) and "KEP" not in str(ev)


def test_X_09_recibir_un_traspaso_sigue_funcionando_para_el_almacen_de_destino(
    compras, almacenista, cliente_almacen, session
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    traspaso = enviar(almacenista, session, "MID", [renglon(guantes.codigo, 2)])
    midrex = cliente_almacen("MID")

    recibir(midrex, traspaso, [renglon(guantes.codigo, 2)])

    assert vale(session, traspaso["id"]).estado == "RECIBIDO"


def test_E_04_la_cantidad_mayor_solo_habla_del_almacen_propio(
    cliente_almacen, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 8)  # hay 8 en Kepler y ninguno en Midrex
    midrex = cliente_almacen("MID")

    ev = evaluar(midrex, trabajador, [renglon(guantes.codigo, 3)])

    mensaje = ev["renglones"][0]["motivos"][0]["mensaje"]
    assert ev["renglones"][0]["motivos"][0]["regla"] == "E-04"
    assert "hay 0" in mensaje and "8" not in mensaje
