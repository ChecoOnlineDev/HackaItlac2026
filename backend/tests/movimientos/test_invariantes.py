"""Invariantes de datos 1 a 5 (data-model.md) tras una mezcla de operaciones, y datos de prueba.

Se revisan sobre TODA la base de pruebas (la carga inicial más lo que hace cada prueba).
"""

import uuid
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import select

from app.core.tiempo import hoy_mx
from app.modulos.almacenes.models import Almacen, Ubicacion
from app.modulos.catalogo.models import Articulo, Pieza
from app.modulos.movimientos.datos_prueba import CARGA_INICIAL, cargar, id_cliente_de
from app.modulos.movimientos.models import Existencia, Movimiento, SerieFolio, Vale
from tests.movimientos.ayudas import (
    abastecer,
    almacen,
    crear_articulo,
    crear_trabajador,
    cuerpo_entrega,
    entrar_pieza,
    existencia,
    total_vales,
)
from tests.movimientos.test_entrega import pieza_en_kep, renglon

VALES = "/api/vales"


def virtual_proveedor(session) -> uuid.UUID:
    return session.scalar(select(Ubicacion.id).where(Ubicacion.virtual == "PROVEEDOR"))


def revisar_invariantes(session) -> None:
    proveedor = virtual_proveedor(session)
    movimientos = session.scalars(
        select(Movimiento).order_by(Movimiento.creado_en, Movimiento.renglon, Movimiento.id)
    ).all()
    articulos = {a.id: a for a in session.scalars(select(Articulo))}

    # 1. existencia = entradas menos salidas; y los saldos de cada movimiento cuadran.
    saldo: dict[tuple, int] = defaultdict(int)
    for m in movimientos:
        if m.origen_id != proveedor:
            saldo[(m.origen_id, m.articulo_id)] -= m.cantidad
            assert m.saldo_origen == saldo[(m.origen_id, m.articulo_id)], m.id
        else:
            assert m.saldo_origen is None
        if m.destino_id != proveedor:
            saldo[(m.destino_id, m.articulo_id)] += m.cantidad
            assert m.saldo_destino == saldo[(m.destino_id, m.articulo_id)], m.id
        else:
            assert m.saldo_destino is None
    guardado = {
        (e.ubicacion_id, e.articulo_id): e.cantidad for e in session.scalars(select(Existencia))
    }
    for clave, cantidad in saldo.items():
        assert guardado.get(clave, 0) == cantidad, f"existencia desviada en {clave}"
    for clave, cantidad in guardado.items():
        assert cantidad == saldo.get(clave, 0), f"existencia sin movimientos en {clave}"

    # 2. nunca negativa; PROVEEDOR no lleva existencia.
    assert all(c >= 0 for c in guardado.values())
    assert all(clave[0] != proveedor for clave in guardado)

    # 3. por pieza: cantidad 1 y pieza_id; por cantidad: sin pieza_id.
    for m in movimientos:
        if articulos[m.articulo_id].control == "PIEZA":
            assert m.pieza_id is not None and m.cantidad == 1
        else:
            assert m.pieza_id is None

    # 4. pieza.ubicacion_id es el destino de su último movimiento.
    ultimo: dict[uuid.UUID, uuid.UUID] = {}
    for m in movimientos:
        if m.pieza_id is not None:
            ultimo[m.pieza_id] = m.destino_id
    for pieza in session.scalars(select(Pieza)):
        if pieza.id in ultimo:
            assert pieza.ubicacion_id == ultimo[pieza.id], pieza.codigo
        else:
            assert pieza.ubicacion_id is None  # sin movimientos: todavía no tiene ubicación


def revisar_folios(session) -> None:
    """RG-06: el consecutivo no tiene huecos ni repetidos y `serie_folio` lo refleja."""
    claves = {a.id: a.clave for a in session.scalars(select(Almacen))}
    por_serie: dict[tuple, list[int]] = defaultdict(list)
    for v in session.scalars(select(Vale)):
        por_serie[(v.almacen_id, v.tipo)].append(int(v.folio.rsplit("-", 1)[1]))
        assert v.folio.startswith(f"{claves[v.almacen_id]}-")
    for (almacen_id, tipo), numeros in por_serie.items():
        assert sorted(numeros) == list(range(1, len(numeros) + 1)), (claves[almacen_id], tipo)
        ultimo = session.scalar(
            select(SerieFolio.ultimo).where(
                SerieFolio.almacen_id == almacen_id, SerieFolio.tipo == tipo
            )
        )
        assert ultimo == len(numeros)


def test_invariantes_1_a_4_con_los_datos_de_prueba(session):
    revisar_invariantes(session)
    revisar_folios(session)


def test_invariantes_1_a_4_despues_de_entradas_y_entregas(almacenista, compras, session):
    t1, t2 = crear_trabajador(session), crear_trabajador(session)
    guantes = crear_articulo(session, retornable=False)
    casco = crear_articulo(session, retornable=True)
    abastecer(compras, guantes, 30)
    abastecer(compras, casco, 10)
    _, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=60))
    _, pieza2 = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=60))
    for t, renglones in (
        (t1, [renglon(guantes.codigo, 5), renglon(casco.codigo, 2), renglon(pieza.codigo)]),
        (t2, [renglon(guantes.codigo, 7), renglon(pieza2.codigo)]),
        (t1, [renglon(casco.codigo)]),
    ):
        r = almacenista.post(VALES, json=cuerpo_entrega(t, renglones))
        assert r.status_code == 201, r.text
    assert existencia(session, "KEP", guantes) == 18
    revisar_invariantes(session)
    revisar_folios(session)


def test_un_vale_que_no_se_confirmo_no_deja_nada_invariante_9(almacenista, compras, session):
    t = crear_trabajador(session)
    guantes = crear_articulo(session)
    abastecer(compras, guantes, 2)
    antes = total_vales(session)
    r = almacenista.post(VALES, json=cuerpo_entrega(t, [renglon(guantes.codigo, 3)]))
    assert r.status_code == 409 and total_vales(session) == antes
    revisar_invariantes(session)
    revisar_folios(session)


def test_la_entrada_de_piezas_cumple_las_invariantes(compras, session):
    arnes = crear_articulo(session, control="PIEZA")
    for _ in range(3):
        r, _ = entrar_pieza(compras, arnes)
        assert r.status_code == 201
    revisar_invariantes(session)


# ------------------------------------------------------------------- datos de prueba


def test_los_datos_de_prueba_cargan_existencias_con_vales_de_entrada_reales(session):
    kep = almacen(session, "KEP")
    for clave, renglones in CARGA_INICIAL.items():
        vale = session.scalar(select(Vale).where(Vale.id_cliente == id_cliente_de(clave)))
        assert (
            vale is not None and vale.tipo == "ENTRADA" and vale.folio.startswith(f"{clave}-ING-")
        )
        assert vale.responsable_id is not None
        movs = session.scalars(select(Movimiento).where(Movimiento.vale_id == vale.id)).all()
        assert len(movs) == len(renglones)
    lentes = session.scalar(select(Articulo).where(Articulo.codigo == "LENTE-CL"))
    assert existencia(session, "KEP", lentes) >= 200 and kep


def test_los_datos_de_prueba_son_idempotentes(session):
    antes_vales = total_vales(session)
    movs = session.scalars(select(Movimiento.id)).all()
    cargar(session)
    cargar(session)
    assert total_vales(session) == antes_vales
    assert len(session.scalars(select(Movimiento.id)).all()) == len(movs)
    revisar_invariantes(session)
    revisar_folios(session)
