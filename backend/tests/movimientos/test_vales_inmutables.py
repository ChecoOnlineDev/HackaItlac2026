"""RG-02, AC-07: los vales y sus movimientos no se editan ni se borran; un error se corrige con un
movimiento inverso (la cancelación)."""

import uuid

import pytest
from sqlalchemy import select

from app.modulos.movimientos.models import Movimiento, Vale
from tests.movimientos.ayudas import abastecer, crear_articulo, crear_trabajador
from tests.movimientos.cancelacion_ayudas import cancelacion, entregar, url
from tests.movimientos.test_entrega import renglon


@pytest.fixture
def trabajador(session):
    return crear_trabajador(session)


def test_RG_02_ninguna_ruta_edita_ni_borra_vales_o_movimientos(app):
    """Recorre las rutas de la aplicación: sobre vales y movimientos solo hay lectura y altas."""
    rutas = app.openapi()["paths"]  # incluye todos los routers, también los anidados
    prohibidos = {"put", "patch", "delete"}
    bajo_vales = {p: set(m) for p, m in rutas.items() if p.startswith("/api/vales")}
    # La prueba no es vacía: las rutas de vales sí existen.
    assert "/api/vales" in bajo_vales and "/api/vales/{vale_id}/cancelacion" in bajo_vales
    for ruta, metodos in rutas.items():
        if ruta.startswith("/api/vales") or "movimiento" in ruta:
            assert not (set(metodos) & prohibidos), (ruta, metodos)
    # La única escritura bajo un vale existente es la cancelación (POST).
    escrituras = {
        p
        for p, m in bajo_vales.items()
        if p not in ("/api/vales", "/api/vales/evaluar") and m - {"get", "head"}
    }
    assert escrituras == {"/api/vales/{vale_id}/cancelacion"}
    assert bajo_vales["/api/vales/{vale_id}/cancelacion"] == {"post"}


def test_RG_02_cancelar_no_altera_los_renglones_del_vale_original(
    almacenista, compras, session, trabajador
):
    guantes = crear_articulo(session, retornable=False)
    abastecer(compras, guantes, 5)
    vale = entregar(almacenista, trabajador, [renglon(guantes.codigo, 2)])

    def renglones_del_vale():
        filas = session.scalars(
            select(Movimiento)
            .where(Movimiento.vale_id == uuid.UUID(vale["id"]))
            .order_by(Movimiento.renglon)
        ).all()
        return [
            (m.id, m.renglon, m.articulo_id, m.pieza_id, m.cantidad, m.origen_id, m.destino_id)
            for m in filas
        ]

    antes = renglones_del_vale()
    assert antes
    r = almacenista.post(url(vale["id"]), json=cancelacion())
    assert r.status_code == 201, r.text
    session.expire_all()
    assert renglones_del_vale() == antes  # los mismos, sin tocar
    original = session.get(Vale, uuid.UUID(vale["id"]))
    assert original.estado == "CANCELADO"
    # La corrección es un vale nuevo con sus propios movimientos inversos.
    assert r.json()["id"] != vale["id"]
