"""FEAT-004: mínimos, estados y cantidad disponible."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.modulos.acceso.permisos import P
from app.modulos.almacenes.service import AlmacenService
from app.modulos.catalogo.models import Articulo, Pieza
from app.modulos.catalogo.models_minimos import Minimo
from app.modulos.movimientos.evaluador_minimos import regla_minimo
from app.modulos.movimientos.models import Existencia
from tests.conftest import iniciar_sesion_en
from tests.inspecciones.test_modulo_inspecciones import _articulo, _en_almacen
from tests.movimientos.ayudas import crear_articulo, crear_trabajador


@pytest.mark.parametrize("regla", ["E-14", "X-05"])
def test_E_14_X_05_aviso_solo_cuando_salida_deja_bajo_minimo(regla):
    motivo = regla_minimo(regla, 5, 6, 2)
    assert motivo.regla == regla and motivo.nivel == "AMARILLO"
    assert regla_minimo(regla, 5, 6, 1) is None
    assert regla_minimo(regla, None, 6, 2) is None
    assert regla_minimo(regla, 5, 2, 0) is None


@pytest.mark.parametrize("tipo, regla", [("ENTREGA", "E-14"), ("TRASPASO", "X-05")])
def test_E_14_X_05_evaluacion_api_usa_minimo_y_conserva_seguridad(
    session, cliente_como, tipo, regla
):
    servicio = AlmacenService(session)
    almacen = servicio.obtener_por_clave("KEP")
    ubicacion = servicio.ubicacion_de_almacen(almacen.id)
    articulo = crear_articulo(session, requiere_inspeccion=False)
    session.add(Existencia(ubicacion_id=ubicacion.id, articulo_id=articulo.id, cantidad=6))
    session.add(Minimo(almacen_id=almacen.id, articulo_id=articulo.id, cantidad=5))
    session.flush()
    cuerpo = {"tipo": tipo, "renglones": [{"codigo": articulo.codigo, "cantidad": 2}]}
    if tipo == "ENTREGA":
        cuerpo["trabajador_id"] = str(crear_trabajador(session).id)
    else:
        cuerpo["destino_almacen_id"] = str(servicio.obtener_por_clave("CON").id)
    cliente = cliente_como("Administrador")
    cuerpo["almacen_id"] = str(almacen.id)
    r = cliente.post("/api/vales/evaluar", json=cuerpo)
    assert r.status_code == 200, r.text
    fila = r.json()["renglones"][0]
    assert regla in [m["regla"] for m in fila["motivos"]]
    assert fila["nivel"] == "AMARILLO"
    assert fila["pide_observacion"] is False


def test_I_05_permiso_configuracion_sin_stock_filtro_y_eliminacion(
    session, app, crear_usuario, cliente_como
):
    almacen = AlmacenService(session).obtener_por_clave("KEP")
    articulo = session.scalar(select(Articulo).where(Articulo.control == "CANTIDAD"))
    ruta = f"/api/almacenes/{almacen.id}/minimos"
    datos = {"minimos": [{"articulo_id": str(articulo.id), "cantidad": 99999}]}
    assert cliente_como("Almacenista").put(ruta, json=datos).status_code == 403
    usuario = crear_usuario({P.INVENTARIO_MINIMOS, P.INVENTARIO_VER}, almacen="KEP")
    with TestClient(app) as cliente:
        assert iniciar_sesion_en(cliente, usuario).status_code == 200
        assert cliente.put(ruta, json=datos).status_code == 200
        r = cliente.get(f"/api/almacenes/{almacen.id}/existencias", params={"bajo_minimo": True})
        assert r.status_code == 200, r.text
        fila = next(x for x in r.json()["elementos"] if x["articulo_id"] == str(articulo.id))
        assert fila["minimo"] == 99999 and fila["bajo_minimo"] is True
        datos["minimos"][0]["cantidad"] = None
        assert cliente.put(ruta, json=datos).status_code == 200
        assert session.get(Minimo, (almacen.id, articulo.id)) is None
        ajeno = AlmacenService(session).obtener_por_clave("MID")
        assert cliente.get(f"/api/almacenes/{ajeno.id}/minimos").status_code == 404


def test_I_05_minimo_sin_existencia_se_muestra_y_no_admite_decimales(session, app, crear_usuario):
    articulo = _articulo(session, f"MIN-{uuid.uuid4().hex[:8]}")
    almacen = AlmacenService(session).obtener_por_clave("KEP")
    usuario = crear_usuario({P.INVENTARIO_MINIMOS, P.INVENTARIO_VER}, almacen="KEP")
    with TestClient(app) as cliente:
        iniciar_sesion_en(cliente, usuario)
        ruta = f"/api/almacenes/{almacen.id}/minimos"
        datos = {"minimos": [{"articulo_id": str(articulo.id), "cantidad": 5}]}
        assert cliente.put(ruta, json=datos).status_code == 200
        filas = cliente.get(
            f"/api/almacenes/{almacen.id}/existencias", params={"bajo_minimo": True}
        ).json()["elementos"]
        fila = next(x for x in filas if x["articulo_id"] == str(articulo.id))
        assert fila["cantidad"] == fila["disponible"] == 0
        datos["minimos"][0]["cantidad"] = 0.5
        assert cliente.put(ruta, json=datos).status_code == 422


@pytest.mark.parametrize("requiere", [False, True])
def test_P_06_mantenimiento_no_disponible_y_regreso_condicionado(session, cliente_como, requiere):
    articulo = _articulo(session, f"MANT-{uuid.uuid4().hex[:8]}", requiere=requiere)
    pieza = Pieza(articulo_id=articulo.id, codigo=f"P-{uuid.uuid4().hex[:10]}")
    _en_almacen(session, pieza, "KEP")
    session.add(pieza)
    session.flush()
    cliente = cliente_como("Almacenista")
    ruta = f"/api/piezas/{pieza.id}/estado"
    assert (
        cliente.post(ruta, json={"estado": "EN_MANTENIMIENTO", "observacion": ""}).status_code
        == 422
    )
    r = cliente.post(ruta, json={"estado": "EN_MANTENIMIENTO", "observacion": "Reparar"})
    assert r.status_code == 200, r.text
    assert r.json()["pieza"]["estado"] == "EN_MANTENIMIENTO"
    r = cliente.post(ruta, json={"estado": "APTO", "observacion": "Reparada"})
    assert r.status_code == (422 if requiere else 200), r.text
    if requiere:
        assert r.json()["detalles"][0]["regla"] == "P-06"
