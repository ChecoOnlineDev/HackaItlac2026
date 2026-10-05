"""Endurecimiento (H9): la idempotencia por `id_cliente` no oculta un cambio de cuerpo.

El mismo `id_cliente` con el MISMO cuerpo devuelve el vale ya guardado (200). Con otro cuerpo
responde 409 `CONFLICTO` en vez de devolver el vale original como si fuera lo que se pidió.
"""

import uuid

import pytest
from sqlalchemy import update

from app.modulos.movimientos.models import Vale
from tests.movimientos.ayudas import (
    a_data_url,
    abastecer,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    existencia,
    firma_valida,
    png_valido,
    total_vales,
)
from tests.movimientos.test_entrega import renglon

VALES = "/api/vales"


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


@pytest.fixture
def guantes(compras, session):
    articulo = crear_articulo(session)
    abastecer(compras, articulo, 10)
    return articulo


def test_idempotencia_el_mismo_cuerpo_devuelve_el_mismo_vale(
    almacenista, session, trabajador, guantes
):
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo, 2)])

    primero = almacenista.post(VALES, json=cuerpo)
    segundo = almacenista.post(VALES, json=cuerpo)

    assert primero.status_code == 201 and segundo.status_code == 200
    assert primero.json()["id"] == segundo.json()["id"]
    assert existencia(session, "KEP", guantes) == 8  # no se entregó dos veces


def test_H9_el_mismo_id_cliente_con_otro_cuerpo_da_409_conflicto(
    almacenista, session, trabajador, guantes
):
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo, 2)])
    assert almacenista.post(VALES, json=cuerpo).status_code == 201
    vales = total_vales(session)

    cambiado = cuerpo | {"renglones": [renglon(guantes.codigo, 5)]}
    r = almacenista.post(VALES, json=cambiado)

    assert r.status_code == 409, r.text
    assert r.json()["codigo"] == "CONFLICTO"
    assert "otros datos" in r.json()["mensaje"]
    assert total_vales(session) == vales and existencia(session, "KEP", guantes) == 8


def test_H9_cambiar_el_trabajador_o_la_observacion_tambien_es_otro_cuerpo(
    almacenista, session, trabajador, guantes
):
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo)], observacion="Primera")
    assert almacenista.post(VALES, json=cuerpo).status_code == 201

    otra_observacion = almacenista.post(VALES, json=cuerpo | {"observacion": "Segunda"})
    otro_trabajador = almacenista.post(
        VALES, json=cuerpo | {"trabajador_id": str(crear_trabajador(session).id)}
    )

    assert otra_observacion.status_code == 409 and otro_trabajador.status_code == 409


def test_H9_volver_a_firmar_en_un_reintento_no_cambia_el_vale(
    almacenista, session, trabajador, guantes
):
    # La imagen y el trazo de la firma no cuentan: el vale conserva la firma de la primera vez.
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo)])
    primero = almacenista.post(VALES, json=cuerpo)
    otra_firma = firma_valida(imagen=a_data_url(png_valido(320, 160)))

    segundo = almacenista.post(VALES, json=cuerpo | {"firma": otra_firma})

    assert segundo.status_code == 200 and segundo.json()["id"] == primero.json()["id"]


def test_H9_un_vale_sin_huella_guardada_se_sigue_tratando_como_repeticion(
    almacenista, session, trabajador, guantes
):
    # Los vales anteriores a la columna `huella_cuerpo` no tienen huella: no hay con qué comparar.
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo, 2)])
    primero = almacenista.post(VALES, json=cuerpo)
    session.execute(
        update(Vale).where(Vale.id == uuid.UUID(primero.json()["id"])).values(huella_cuerpo=None)
    )
    session.flush()

    segundo = almacenista.post(VALES, json=cuerpo | {"renglones": [renglon(guantes.codigo, 5)]})

    assert segundo.status_code == 200 and segundo.json()["id"] == primero.json()["id"]


def test_H9_el_id_cliente_de_otro_usuario_sigue_siendo_un_conflicto(
    almacenista, supervisor, session, trabajador, guantes
):
    cuerpo = cuerpo_entrega(trabajador, [renglon(guantes.codigo)])
    assert almacenista.post(VALES, json=cuerpo).status_code == 201

    r = supervisor.post(VALES, json=cuerpo)

    assert r.status_code == 409
