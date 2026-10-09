"""Endurecimiento (H3): lo que el supervisor lee al autorizar lo arma el servidor (A-02, A-06).

De una solicitud el servidor toma solo `codigo` y `cantidad` por renglón; artículo, límite, lo que
tiene, el excedente, la regla y el mensaje salen de SU evaluación. Un renglón que la evaluación
real no marque naranja no se envía a autorización.
"""

import uuid

import pytest
from sqlalchemy import select

from app.modulos.autorizaciones.models import Autorizacion
from tests.movimientos.ayudas import (
    abastecer,
    crear_articulo,
    crear_trabajador,
)
from tests.movimientos.ayudas import (
    cuerpo_entrega as _cuerpo_entrega,
)
from tests.movimientos.test_entrega import renglon


def cuerpo_entrega(*args, **kw):
    # PR-10: estas pruebas verifican autorizaciones, con trabajadores sin proyecto.
    return _cuerpo_entrega(*args, observacion="Entrega de prueba sin proyecto", **kw)


VALES = "/api/vales"
AUT = "/api/autorizaciones"

FALSOS = {
    "articulo_id": str(uuid.uuid4()),
    "articulo": "Cinta adhesiva",
    "limite": 999,
    "tiene": 999,
    "excedente": 77,
    "regla": "L-01",
    "mensaje": "Mensaje inventado por el cliente",
    "autorizable": True,
}


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


@pytest.fixture
def excedente(almacenista, compras, session, trabajador):
    """Un retornable con límite 1 que el trabajador ya tiene: pedir otro es naranja (L-02)."""
    arnes = crear_articulo(session, retornable=True, limite_cantidad=1, nombre="Arnés H3")
    abastecer(compras, arnes, 10)
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, [renglon(arnes.codigo)]))
    assert r.status_code == 201, r.text
    return arnes


def _solicitar(cliente, trabajador, renglones):
    return cliente.post(
        AUT,
        json={"trabajador_id": str(trabajador.id), "renglones": renglones, "motivo": "Trabajo"},
    )


def test_A_02_los_datos_que_lee_el_supervisor_son_los_de_la_evaluacion_del_servidor(
    almacenista, supervisor, session, trabajador, excedente
):
    r = _solicitar(almacenista, trabajador, [{"codigo": excedente.codigo, "cantidad": 1} | FALSOS])
    assert r.status_code == 201, r.text

    lista = supervisor.get(f"{AUT}?estado=PENDIENTE").json()["elementos"]
    tarjeta = next(e for e in lista if e["id"] == r.json()["id"])
    (reng,) = tarjeta["renglones"]
    assert reng["articulo"] == "Arnés H3" and reng["articulo"] != FALSOS["articulo"]
    assert reng["articulo_id"] == str(excedente.id)
    assert reng["regla"] == "L-02"
    assert (reng["limite"], reng["tiene"], reng["excedente"]) == (1, 1, 1)
    assert reng["mensaje"] != FALSOS["mensaje"] and "límite" in reng["mensaje"]
    assert tarjeta["excedente_total"] == 1

    # Lo guardado también es lo real, no lo que mandó el cliente.
    fila = session.scalar(select(Autorizacion).where(Autorizacion.id == uuid.UUID(r.json()["id"])))
    assert fila.detalle["renglones"][0]["articulo"] == "Arnés H3"
    assert fila.detalle["renglones"][0]["excedente"] == 1


def test_A_02_pedir_mas_de_lo_que_dice_la_evaluacion_calcula_el_excedente_del_servidor(
    almacenista, supervisor, trabajador, excedente
):
    # El cliente declara excedente 1 pero pide 5: el servidor calcula tiene 1 + 5 - límite 1 = 5.
    r = _solicitar(
        almacenista, trabajador, [{"codigo": excedente.codigo, "cantidad": 5, "excedente": 1}]
    )
    assert r.status_code == 201, r.text
    lista = supervisor.get(f"{AUT}?estado=PENDIENTE").json()["elementos"]
    tarjeta = next(e for e in lista if e["id"] == r.json()["id"])
    assert tarjeta["renglones"][0]["excedente"] == 5 and tarjeta["excedente_total"] == 5


def test_A_06_un_renglon_verde_no_se_envia_a_autorizacion(
    almacenista, compras, session, trabajador, excedente
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)

    r = _solicitar(almacenista, trabajador, [{"codigo": guantes.codigo, "cantidad": 1} | FALSOS])

    assert r.status_code == 422, r.text
    assert r.json()["codigo"] == "RENGLON_NO_AUTORIZABLE"
    assert r.json()["detalles"]["codigo"] == guantes.codigo


def test_A_06_un_renglon_rojo_no_se_envia_a_autorizacion_aunque_el_cliente_diga_que_si(
    almacenista, trabajador
):
    r = _solicitar(
        almacenista, trabajador, [{"codigo": "NO-EXISTE-H3", "cantidad": 1, "autorizable": True}]
    )

    assert r.status_code == 422, r.text
    assert r.json()["codigo"] == "RENGLON_NO_AUTORIZABLE"
    assert r.json()["detalles"]["regla"]


def test_A_06_basta_un_renglon_que_no_sea_naranja_para_rechazar_la_solicitud(
    almacenista, compras, session, trabajador, excedente
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    antes = session.scalars(select(Autorizacion.id)).all()

    r = _solicitar(
        almacenista,
        trabajador,
        [{"codigo": excedente.codigo, "cantidad": 1}, {"codigo": guantes.codigo, "cantidad": 1}],
    )

    assert r.status_code == 422
    assert session.scalars(select(Autorizacion.id)).all() == antes  # no se guardó nada
