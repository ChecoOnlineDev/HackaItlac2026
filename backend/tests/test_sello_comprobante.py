"""F-06/F-07/F-12: alteraciones detectadas y comprobante sin sesión ni datos reservados."""

import uuid

from sqlalchemy import select

from app.modulos.movimientos.models import Movimiento, Vale
from app.modulos.movimientos.sello import SelloService
from tests.movimientos.ayudas import abastecer, crear_articulo


def test_F_06_sello_detecta_cambio_cantidad_y_excluye_estado(session, cliente_como):
    articulo = crear_articulo(session)
    emitido = abastecer(cliente_como("Compras"), articulo, 10)
    vale = session.get(Vale, uuid.UUID(emitido["id"]))
    sello = SelloService(session)
    assert sello.verificar_almacen(vale.almacen_id)["estados"][vale.id] == "Íntegro"
    vale.estado = "CANCELADO"
    session.flush()
    assert sello.verificar_almacen(vale.almacen_id)["estados"][vale.id] == "Íntegro"
    movimiento = session.scalar(select(Movimiento).where(Movimiento.vale_id == vale.id))
    movimiento.cantidad += 1
    session.flush()
    resultado = sello.verificar_almacen(vale.almacen_id)
    assert resultado["estados"][vale.id] == "Alterado"
    assert resultado["primer_alterado"]["id"] == vale.id


def test_F_07_comprobante_publico_sin_costos_datos_personales_ni_firma(
    session, client, cliente_como
):
    articulo = crear_articulo(session, costo_unitario="123.45")
    emitido = abastecer(cliente_como("Compras"), articulo, 3)
    r = client.get(f"/api/publico/vales/{emitido['token']}")
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["folio"] == emitido["folio"] and datos["integridad"] == "Íntegro"
    assert datos["articulos"][0]["cantidad"] == 3
    texto = r.text.lower()
    assert all(f'"{campo}"' not in texto for campo in ("costo", "curp", "nss", "firma", "sha256"))
    assert client.get("/api/publico/vales/no-existe").status_code == 404
    assert client.get("/api/reportes/integridad").status_code == 401
    r = cliente_como("Administrador").get("/api/reportes/integridad")
    assert r.status_code == 200 and r.json()["integro"]


def test_F_06_segundo_sello_apunta_al_primero_y_reporte_detecta_primero(session, cliente_como):
    cliente = cliente_como("Compras")
    articulo = crear_articulo(session)
    uno = abastecer(cliente, articulo, 3)
    dos = abastecer(cliente, articulo, 4)
    primero = session.get(Vale, uuid.UUID(uno["id"]))
    segundo = session.get(Vale, uuid.UUID(dos["id"]))
    assert segundo.sello_anterior_id == primero.id and segundo.hash_anterior == primero.hash
    primero.observacion = "Alteración directa"
    session.flush()
    informe = SelloService(session).verificar_almacen(primero.almacen_id)
    assert informe["primer_alterado"]["id"] == primero.id
    assert informe["estados"][segundo.id] == "Alterado"
