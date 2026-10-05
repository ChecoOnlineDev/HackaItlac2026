"""Concurrencia real del NO_ADEUDO (B-04, B-08): hilos con conexiones propias.

El vale de no adeudo no tiene movimientos, así que `limpieza` no lo encuentra por artículo: la
fixture `limpiar_no_adeudo` lo borra antes de que `limpieza` borre al trabajador.
"""

import uuid

import pytest
from sqlalchemy import delete, func, select

from app.modulos.catalogo.models import Codigo
from app.modulos.movimientos.models import Vale
from app.modulos.trabajadores.models import EstadoTrabajador, Trabajador
from tests.movimientos.ayudas import abastecer, cuerpo_entrega
from tests.movimientos.ayudas_devolucion import VALES, cuerpo_devolucion, renglon
from tests.movimientos.test_concurrencia import Escenario, en_paralelo


@pytest.fixture
def escenario(sesion_independiente, limpieza, cliente_independiente):
    return Escenario(sesion_independiente, limpieza, cliente_independiente)


@pytest.fixture(autouse=True)
def limpiar_no_adeudo(sesion_independiente, limpieza):
    yield
    s = sesion_independiente()
    try:
        vales = list(
            s.scalars(
                select(Vale.id).where(
                    Vale.trabajador_id.in_(limpieza.trabajadores), Vale.tipo == "NO_ADEUDO"
                )
            )
        )
        s.execute(delete(Codigo).where(Codigo.ref_id.in_(vales)))
        s.execute(delete(Vale).where(Vale.id.in_(vales)))
        s.commit()
    finally:
        s.close()


def ruta(trabajador) -> str:
    return f"/api/trabajadores/{trabajador.id}/no-adeudo"


def test_B_08_dos_no_adeudo_simultaneos_emiten_solo_uno(escenario, sesion_independiente):
    t = escenario.trabajador()
    c1, c2 = escenario.clientes("Almacenista"), escenario.clientes("Almacenista")
    r1, r2 = en_paralelo(
        [
            lambda: c1.post(ruta(t), json={"id_cliente": str(uuid.uuid4())}),
            lambda: c2.post(ruta(t), json={"id_cliente": str(uuid.uuid4())}),
        ]
    )
    assert sorted([r1.status_code, r2.status_code]) == [201, 409], (r1.text, r2.text)
    s = sesion_independiente()
    n = s.scalar(
        select(func.count())
        .select_from(Vale)
        .where(Vale.trabajador_id == t.id, Vale.tipo == "NO_ADEUDO")
    )
    assert n == 1
    assert s.get(Trabajador, t.id).estado == EstadoTrabajador.INACTIVO


def test_B_04_la_devolucion_y_el_no_adeudo_simultaneos_nunca_dejan_inactivo_a_quien_debe(
    escenario, sesion_independiente
):
    casco = escenario.articulo(retornable=True)
    abastecer(escenario.compras, casco, 3)
    t = escenario.trabajador()
    almacenista = escenario.clientes("Almacenista")
    assert (
        almacenista.post(VALES, json=cuerpo_entrega(t, [renglon(casco.codigo)])).status_code == 201
    )
    c1, c2 = escenario.clientes("Almacenista"), escenario.clientes("Almacenista")
    r_dev, r_nad = en_paralelo(
        [
            lambda: c1.post(VALES, json=cuerpo_devolucion([renglon(casco.codigo)], t)),
            lambda: c2.post(ruta(t), json={"id_cliente": str(uuid.uuid4())}),
        ]
    )
    assert r_dev.status_code == 201, r_dev.text
    s = sesion_independiente()
    estado = s.get(Trabajador, t.id).estado
    if r_nad.status_code == 201:
        # La devolución llegó primero: ya no debía nada cuando se emitió.
        assert estado == EstadoTrabajador.INACTIVO
    else:
        assert r_nad.status_code == 409 and r_nad.json()["codigo"] == "CON_PENDIENTES"
        assert estado == EstadoTrabajador.BAJA_EN_PROCESO
