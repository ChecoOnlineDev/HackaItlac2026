"""Concurrencia real de la DEVOLUCION (RG-08, RG-09, RG-06): hilos con conexiones propias.

Mismo esquema que `test_concurrencia.py`: datos confirmados que `limpieza` borra al final.
"""

import uuid

import pytest
from sqlalchemy import func, select

from app.modulos.almacenes.models import Ubicacion
from app.modulos.catalogo.models import Pieza
from app.modulos.movimientos.models import Existencia, Movimiento, Vale
from tests.movimientos.ayudas import abastecer, cuerpo_entrega
from tests.movimientos.ayudas_devolucion import VALES, cuerpo_devolucion, renglon
from tests.movimientos.test_concurrencia import Escenario, en_paralelo


@pytest.fixture
def escenario(sesion_independiente, limpieza, cliente_independiente):
    return Escenario(sesion_independiente, limpieza, cliente_independiente)


def entregar(escenario, trabajador, codigo, cantidad=1):
    r = escenario.clientes("Almacenista").post(
        VALES, json=cuerpo_entrega(trabajador, [{"codigo": codigo, "cantidad": cantidad}])
    )
    assert r.status_code == 201, r.text


def devoluciones_de(s, articulo_id):
    return s.scalars(
        select(Vale.id)
        .join(Movimiento, Movimiento.vale_id == Vale.id)
        .where(Movimiento.articulo_id == articulo_id, Vale.tipo == "DEVOLUCION")
    ).all()


def en_almacenes(s, articulo_id) -> int:
    return (
        s.scalar(
            select(func.sum(Existencia.cantidad))
            .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
            .where(Existencia.articulo_id == articulo_id, Ubicacion.almacen_id.is_not(None))
        )
        or 0
    )


def test_V_01_dos_devoluciones_simultaneas_de_la_misma_pieza_solo_una_gana(
    escenario, sesion_independiente
):
    arnes = escenario.articulo(control="PIEZA", requiere_inspeccion=False)
    codigo = escenario.pieza_en_kep(arnes)
    t = escenario.trabajador()
    entregar(escenario, t, codigo)
    c1, c2 = escenario.clientes("Almacenista"), escenario.clientes("Almacenista")

    r1, r2 = en_paralelo(
        [
            lambda: c1.post(VALES, json=cuerpo_devolucion([renglon(codigo)])),
            lambda: c2.post(VALES, json=cuerpo_devolucion([renglon(codigo)])),
        ]
    )
    assert sorted([r1.status_code, r2.status_code]) == [201, 409], (r1.text, r2.text)
    perdedor = r1 if r1.status_code == 409 else r2
    assert perdedor.json()["codigo"] == "VALE_CAMBIO"
    # El que perdió ya no encuentra la pieza con el trabajador: V-02, nada que devolver.
    assert [m["regla"] for m in perdedor.json()["detalles"]["renglones"][0]["motivos"]] == ["V-02"]

    s = sesion_independiente()
    assert len(devoluciones_de(s, arnes.id)) == 1  # RG-09: el que perdió no dejó nada
    pieza = s.scalar(select(Pieza).where(Pieza.codigo == codigo))
    assert pieza.ubicacion_id is not None and en_almacenes(s, arnes.id) == 1
    assert (
        s.scalar(
            select(Existencia.cantidad).where(
                Existencia.articulo_id == arnes.id, Existencia.ubicacion_id == pieza.ubicacion_id
            )
        )
        == 1
    )


def test_V_03_dos_devoluciones_por_cantidad_que_juntas_pasan_de_lo_que_tiene(
    escenario, sesion_independiente
):
    casco = escenario.articulo(retornable=True)
    abastecer(escenario.compras, casco, 6)
    t = escenario.trabajador()
    entregar(escenario, t, casco.codigo, 3)
    c1, c2 = escenario.clientes("Almacenista"), escenario.clientes("Almacenista")

    r1, r2 = en_paralelo(
        [
            lambda: c1.post(VALES, json=cuerpo_devolucion([renglon(casco.codigo, 2)], t)),
            lambda: c2.post(VALES, json=cuerpo_devolucion([renglon(casco.codigo, 2)], t)),
        ]
    )
    assert sorted([r1.status_code, r2.status_code]) == [201, 409], (r1.text, r2.text)
    perdedor = r1 if r1.status_code == 409 else r2
    assert perdedor.json()["detalles"]["renglones"][0]["motivos"][0]["regla"] == "V-03"
    s = sesion_independiente()
    assert len(devoluciones_de(s, casco.id)) == 1
    assert en_almacenes(s, casco.id) == 3 + 2  # lo que quedó en el almacén más lo devuelto
    cantidades = s.scalars(select(Existencia.cantidad).where(Existencia.articulo_id == casco.id))
    assert min(cantidades) >= 0


def test_idempotencia_dos_devoluciones_simultaneas_con_el_mismo_id_cliente(
    escenario, sesion_independiente
):
    casco = escenario.articulo(retornable=True)
    abastecer(escenario.compras, casco, 4)
    t = escenario.trabajador()
    entregar(escenario, t, casco.codigo, 3)
    c1, c2 = escenario.clientes("Almacenista"), escenario.clientes("Almacenista")
    cuerpo = cuerpo_devolucion([renglon(casco.codigo, 2)], t)

    r1, r2 = en_paralelo([lambda: c1.post(VALES, json=cuerpo), lambda: c2.post(VALES, json=cuerpo)])
    assert sorted([r1.status_code, r2.status_code]) == [200, 201], (r1.text, r2.text)
    assert r1.json() == r2.json()
    s = sesion_independiente()
    assert (
        s.scalar(
            select(func.count())
            .select_from(Vale)
            .where(Vale.id_cliente == uuid.UUID(cuerpo["id_cliente"]))
        )
        == 1
    )
    assert en_almacenes(s, casco.id) == 1 + 2  # una sola devolución


def test_RG_06_los_folios_de_devoluciones_simultaneas_son_consecutivos(
    escenario, sesion_independiente
):
    casco = escenario.articulo(retornable=True)
    abastecer(escenario.compras, casco, 10)
    trabajadores = [escenario.trabajador() for _ in range(4)]
    for t in trabajadores:
        entregar(escenario, t, casco.codigo)
    clientes = [escenario.clientes("Almacenista") for _ in trabajadores]
    resultados = en_paralelo(
        [
            (lambda c=c, t=t: c.post(VALES, json=cuerpo_devolucion([renglon(casco.codigo)], t)))
            for c, t in zip(clientes, trabajadores, strict=True)
        ]
    )
    assert [r.status_code for r in resultados] == [201] * 4, [r.text for r in resultados]
    numeros = sorted(int(r.json()["folio"].rsplit("-", 1)[1]) for r in resultados)
    assert numeros == list(range(numeros[0], numeros[0] + 4))
    assert all("-DEV-" in r.json()["folio"] for r in resultados)
    s = sesion_independiente()
    assert en_almacenes(s, casco.id) == 10
