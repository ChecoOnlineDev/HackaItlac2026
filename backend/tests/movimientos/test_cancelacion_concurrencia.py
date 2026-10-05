"""Concurrencia real de la CANCELACION (K-03, RG-04, RG-08, RG-09): hilos con conexiones propias y
datos confirmados que `limpieza` borra al final (aquí además se desligan los vales de cancelación,
que apuntan a su original con `vale_origen_id`)."""

import uuid

import pytest
from sqlalchemy import delete, func, select, update

from app.modulos.auditoria.models import Auditoria
from app.modulos.movimientos.models import Existencia, Movimiento, Vale
from tests.movimientos.ayudas import abastecer, cuerpo_entrega
from tests.movimientos.cancelacion_ayudas import cancelacion, url
from tests.movimientos.test_concurrencia import Escenario, en_paralelo, renglon

VALES = "/api/vales"


@pytest.fixture
def escenario(sesion_independiente, limpieza, cliente_independiente):
    return Escenario(sesion_independiente, limpieza, cliente_independiente)


@pytest.fixture(autouse=True)
def desligar_cancelaciones(limpieza, sesion_independiente):
    """Se desmonta ANTES que `limpieza` (depende de ella): suelta `vale_origen_id` y la auditoría
    de las cancelaciones para que `limpieza` pueda borrar los vales."""
    yield
    s = sesion_independiente()
    try:
        vales = list(
            s.scalars(
                select(Movimiento.vale_id).where(Movimiento.articulo_id.in_(limpieza.articulos))
            )
        )
        s.execute(update(Vale).where(Vale.id.in_(vales)).values(vale_origen_id=None))
        s.execute(delete(Auditoria).where(Auditoria.entidad_id.in_([str(v) for v in vales])))
        s.commit()
    finally:
        s.close()


def total_en_almacenes(s, articulo):
    from app.modulos.almacenes.models import Ubicacion

    return s.scalar(
        select(func.coalesce(func.sum(Existencia.cantidad), 0))
        .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
        .where(Existencia.articulo_id == articulo.id, Ubicacion.almacen_id.is_not(None))
    )


def cancelaciones_de(s, vale_id):
    return s.scalars(
        select(Vale).where(Vale.vale_origen_id == uuid.UUID(vale_id), Vale.tipo == "CANCELACION")
    ).all()


def test_K_03_dos_cancelaciones_simultaneas_del_mismo_vale_solo_una_gana(
    escenario, sesion_independiente
):
    guantes = escenario.articulo(retornable=False)
    abastecer(escenario.compras, guantes, 10)
    t = escenario.trabajador()
    almacenista = escenario.clientes("Almacenista")
    vale = almacenista.post(VALES, json=cuerpo_entrega(t, [renglon(guantes.codigo, 4)])).json()
    c1, c2 = escenario.clientes("Almacenista"), escenario.clientes("Supervisor")

    r1, r2 = en_paralelo(
        [
            lambda: c1.post(url(vale["id"]), json=cancelacion()),
            lambda: c2.post(url(vale["id"]), json=cancelacion()),
        ]
    )
    assert sorted([r1.status_code, r2.status_code]) == [201, 409], (r1.text, r2.text)
    perdedor = r1 if r1.status_code == 409 else r2
    assert perdedor.json()["codigo"] == "NO_CANCELABLE"
    assert perdedor.json()["detalles"][0]["regla"] == "K-03"
    assert "ya está cancelado" in perdedor.json()["mensaje"]

    s = sesion_independiente()
    assert len(cancelaciones_de(s, vale["id"])) == 1  # RG-09: el que perdió no dejó nada
    assert total_en_almacenes(s, guantes) == 10  # los 4 regresaron una sola vez
    assert s.scalar(select(Vale.estado).where(Vale.id == uuid.UUID(vale["id"]))) == "CANCELADO"


def test_K_03_un_doble_toque_simultaneo_con_el_mismo_id_cliente_crea_una_sola_cancelacion(
    escenario, sesion_independiente
):
    guantes = escenario.articulo(retornable=False)
    abastecer(escenario.compras, guantes, 10)
    t = escenario.trabajador()
    almacenista = escenario.clientes("Almacenista")
    vale = almacenista.post(VALES, json=cuerpo_entrega(t, [renglon(guantes.codigo, 4)])).json()
    c1, c2 = escenario.clientes("Almacenista"), escenario.clientes("Almacenista")
    cuerpo = cancelacion()

    r1, r2 = en_paralelo(
        [
            lambda: c1.post(url(vale["id"]), json=cuerpo),
            lambda: c2.post(url(vale["id"]), json=cuerpo),
        ]
    )
    # Mismo usuario (otra sesión) o no, el resultado es uno: 201 y 200 con el mismo vale.
    assert sorted([r1.status_code, r2.status_code]) == [200, 201], (r1.text, r2.text)
    assert r1.json() == r2.json()
    s = sesion_independiente()
    assert len(cancelaciones_de(s, vale["id"])) == 1
    assert total_en_almacenes(s, guantes) == 10


def test_RG_04_cancelar_una_entrada_y_entregar_lo_mismo_a_la_vez_nunca_deja_negativo(
    escenario, sesion_independiente
):
    guantes = escenario.articulo(retornable=False)
    entrada = abastecer(escenario.compras, guantes, 10)
    t = escenario.trabajador()
    almacenista, compras = escenario.clientes("Almacenista"), escenario.clientes("Compras")

    r_entrega, r_cancelacion = en_paralelo(
        [
            lambda: almacenista.post(VALES, json=cuerpo_entrega(t, [renglon(guantes.codigo, 8)])),
            lambda: compras.post(url(entrada["id"]), json=cancelacion()),
        ]
    )
    # Gana una sola: o se entregaron 8 (y la entrada ya no se cancela) o se canceló la entrada
    # (y ya no hay qué entregar).
    assert sorted([r_entrega.status_code, r_cancelacion.status_code]) in ([201, 409], [409, 201]), (
        r_entrega.text,
        r_cancelacion.text,
    )
    s = sesion_independiente()
    cantidades = s.scalars(
        select(Existencia.cantidad).where(Existencia.articulo_id == guantes.id)
    ).all()
    assert min(cantidades) >= 0
    if r_entrega.status_code == 201:
        assert r_cancelacion.json()["codigo"] == "NO_CANCELABLE"
        assert total_en_almacenes(s, guantes) == 2
    else:
        assert r_entrega.json()["codigo"] == "VALE_CAMBIO"
        assert total_en_almacenes(s, guantes) == 0
