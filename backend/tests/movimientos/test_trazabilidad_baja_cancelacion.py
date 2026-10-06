"""Trazabilidad de la baja y la cancelación: US-BAJ-001 (sin costos) y US-CAN-001 (ambos vales
visibles en el reporte de movimientos y en el historial de la pieza)."""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest

from app.core.tiempo import hoy_mx
from tests.movimientos.ayudas import abastecer, crear_articulo, crear_trabajador, cuerpo_entrega
from tests.movimientos.ayudas_devolucion import cantidad_entregada, pieza_entregada
from tests.movimientos.cancelacion_ayudas import cancelacion, url
from tests.movimientos.test_entrega import pieza_en_kep, renglon
from tests.movimientos.test_trazabilidad_acceso import claves

VALES = "/api/vales"


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


# ------------------------------------------------------------------------------ US-BAJ-001


def test_US_BAJ_001_RG_12_la_lista_de_pendientes_de_la_baja_no_trae_costos(
    almacenista, compras, session, trabajador
):
    art, pieza = pieza_entregada(
        compras, almacenista, session, trabajador, costo_unitario=Decimal("456.78")
    )
    por_cantidad = cantidad_entregada(
        compras, almacenista, session, trabajador, entregado=2, costo_unitario=Decimal("123.45")
    )

    r = almacenista.post(f"/api/trabajadores/{trabajador.id}/baja")

    assert r.status_code == 200, r.text
    baja = r.json()
    por_codigo = {p["codigo"]: p for p in baja["pendientes"]}
    # La lista sí trae lo que pide B-02: código, fecha, folio y almacén...
    assert set(por_codigo) == {pieza.codigo, por_cantidad.codigo}
    assert por_codigo[pieza.codigo]["folio"].startswith("KEP-ENT-")
    assert por_codigo[pieza.codigo]["almacen_clave"] == "KEP"
    assert (
        por_codigo[pieza.codigo]["entregado_en"]
        and por_codigo[por_cantidad.codigo]["cantidad"] == 2
    )
    # ... y ninguna clave ni valor de costo, a cualquier profundidad del JSON.
    assert not [c for c in claves(baja) if "costo" in c.lower() or "precio" in c.lower()]
    assert "456.78" not in r.text and "123.45" not in r.text
    # Lo mismo en la ficha (resguardo) y en el rechazo del vale de no adeudo con pendientes.
    ficha = almacenista.get(f"/api/trabajadores/{trabajador.id}")
    assert ficha.status_code == 200 and len(ficha.json()["resguardo"]) == 2
    assert not [c for c in claves(ficha.json()) if "costo" in c.lower()]
    assert "456.78" not in ficha.text and "123.45" not in ficha.text
    rechazo = almacenista.post(
        f"/api/trabajadores/{trabajador.id}/no-adeudo", json={"id_cliente": str(uuid.uuid4())}
    )
    assert rechazo.status_code == 409 and rechazo.json()["codigo"] == "CON_PENDIENTES"
    assert not [c for c in claves(rechazo.json()) if "costo" in c.lower()]
    assert "456.78" not in rechazo.text and "123.45" not in rechazo.text
    assert art.costo_unitario == Decimal("456.78")  # el costo sí existe en el catálogo


# ------------------------------------------------------------------------------ US-CAN-001


def test_US_CAN_001_tras_cancelar_ambos_vales_salen_en_el_reporte_y_en_el_historial_de_la_pieza(
    almacenista, supervisor, cliente_como, compras, session, trabajador
):
    _, pieza = pieza_en_kep(compras, session, vigente_hasta=hoy_mx() + timedelta(days=60))
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 10)
    entrega = almacenista.post(
        VALES, json=cuerpo_entrega(trabajador, [renglon(pieza.codigo), renglon(guantes.codigo, 2)])
    ).json()

    r = almacenista.post(url(entrega["id"]), json=cancelacion("Me equivoqué de trabajador"))

    assert r.status_code == 201, r.text
    anulacion = r.json()
    assert anulacion["vale_cancelado"]["id"] == entrega["id"]
    assert anulacion["folio"] != entrega["folio"] and anulacion["folio"].startswith("KEP-CAN-")

    # El reporte de movimientos trae los dos vales: el original y su cancelación.
    # El Almacenista no tiene reportes: los ve el supervisor de Kepler y quien ve todos los
    # almacenes (el Administrador).
    for cliente in (supervisor, cliente_como("Administrador")):
        reporte = cliente.get(
            "/api/reportes/movimientos", params={"trabajador_id": str(trabajador.id)}
        )
        assert reporte.status_code == 200, reporte.text
        filas = reporte.json()["elementos"]
        por_vale = {}
        for fila in filas:
            por_vale.setdefault((fila["folio"], fila["tipo"]), []).append(fila)
        assert set(por_vale) == {(entrega["folio"], "ENTREGA"), (anulacion["folio"], "CANCELACION")}
        # Cada uno con sus dos renglones; los de la cancelación son los inversos.
        original, inversa = (
            por_vale[(entrega["folio"], "ENTREGA")],
            por_vale[(anulacion["folio"], "CANCELACION")],
        )
        assert len(original) == len(inversa) == 2
        assert {(f["codigo_articulo"], f["cantidad"]) for f in original} == {
            (f["codigo_articulo"], f["cantidad"]) for f in inversa
        }
        pieza_original = next(f for f in original if f["pieza"])
        pieza_inversa = next(f for f in inversa if f["pieza"])
        assert (pieza_inversa["origen"], pieza_inversa["destino"]) == (
            pieza_original["destino"],
            pieza_original["origen"],
        )

    # El historial de la pieza trae la entrada, la entrega y la cancelación, en ese orden.
    historial = almacenista.get(f"/api/piezas/{pieza.id}").json()["historial"]
    movimientos = [h for h in reversed(historial) if h["tipo"] == "MOVIMIENTO"]
    assert [(h["tipo_vale"], h["folio"]) for h in movimientos][1:] == [
        ("ENTREGA", entrega["folio"]),
        ("CANCELACION", anulacion["folio"]),
    ]
    assert movimientos[-1]["origen"] == movimientos[1]["destino"]  # el regreso es el inverso
    assert movimientos[-1]["destino"] == movimientos[1]["origen"]
    # El vale original sigue visible, marcado como cancelado, con el folio de su cancelación.
    detalle = almacenista.get(f"{VALES}/{entrega['id']}").json()
    assert detalle["estado"] == "CANCELADO"
    assert detalle["cancelacion"]["folio"] == anulacion["folio"]
