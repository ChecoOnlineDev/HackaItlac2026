"""BT-01…10: agrupación SQL, alcance, privacidad y datos completos para el PDF."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.tiempo import ahora_utc
from app.modulos.acceso.models import Usuario
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.almacenes.service import AlmacenService
from app.modulos.catalogo.models import Articulo, Categoria
from app.modulos.consulta.exportacion import texto_fecha_hora
from app.modulos.consulta.service_bitacora import BitacoraService
from app.modulos.movimientos.models import Movimiento, Vale


@pytest.fixture
def contexto17(session):
    admin = session.scalar(select(Usuario).where(Usuario.usuario == "admin"))
    almacenes = AlmacenService(session)
    kep = almacenes.obtener_por_clave("KEP")
    mid = almacenes.obtener_por_clave("MID")
    categoria = session.scalar(select(Categoria).limit(1))
    articulo = Articulo(
        codigo="BT17-" + uuid.uuid4().hex[:8],
        nombre="Máquina de prueba Ñ",
        categoria_id=categoria.id,
        control="CANTIDAD",
        retornable=False,
        costo_unitario=Decimal("9876.54"),
    )
    session.add(articulo)
    session.flush()
    lote = uuid.uuid4()

    def vale(clave="KEP", lote_id=None, n=1):
        almacen = kep if clave == "KEP" else mid
        v = Vale(
            id_cliente=uuid.uuid4(),
            folio="BT17-" + uuid.uuid4().hex[:8],
            tipo="ENTRADA",
            estado="EMITIDO",
            almacen_id=almacen.id,
            responsable_id=admin.id,
            token=uuid.uuid4().hex,
            lote_id=lote_id,
            creado_en=ahora_utc(),
        )
        session.add(v)
        session.flush()
        for i in range(n):
            session.add(
                Movimiento(
                    vale_id=v.id,
                    renglon=i + 1,
                    articulo_id=articulo.id,
                    cantidad=2,
                    origen_id=almacenes.ubicacion_virtual(UbicacionVirtual.PROVEEDOR).id,
                    destino_id=almacenes.ubicacion_de_almacen(almacen.id).id,
                    nivel="VERDE",
                    reglas=["BT-01"],
                )
            )
        session.commit()
        return v

    return admin, kep, mid, articulo, lote, vale


def test_BT_01_BT_02_BT_10_pagina_por_lote_y_filtro_directo(contexto17, cliente_como):
    _, kep, _, _, lote, crear = contexto17
    a, b = crear(lote_id=lote, n=2), crear(lote_id=lote, n=3)
    respuesta = cliente_como("Administrador").get(
        "/api/bitacora", params={"lote_id": str(lote), "tamano": 1}
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["total"] == 1
    item = datos["elementos"][0]
    assert item["clase"] == "LOTE"
    assert {v["id"] for v in item["vales"]} == {str(a.id), str(b.id)}
    assert item["renglones"] == 5 and item["unidades"] == 10


def test_BT_03_coincidencias_y_csv_no_costos(contexto17, cliente_como):
    _, _, _, articulo, lote, crear = contexto17
    vale = crear(lote_id=lote, n=3)
    cliente = cliente_como("Administrador")
    respuesta = cliente.get("/api/bitacora", params={"lote_id": str(lote), "q": articulo.codigo})
    assert respuesta.status_code == 200, respuesta.text
    item = respuesta.json()["elementos"][0]
    assert item["coincidencias"] == 3
    assert item["direccion"] is None
    csv = cliente.get("/api/bitacora", params={"lote_id": str(lote), "formato": "csv"})
    assert csv.status_code == 200 and "csv" in csv.headers["content-type"]
    assert "9876.54" not in csv.text and "costo" not in csv.text.lower()
    assert texto_fecha_hora(vale.creado_en) in csv.text


def test_BT_01_BT_06_alcance_no_filtra_partes_ajenas(contexto17, cliente_como):
    _, _, mid, _, lote, crear = contexto17
    propia = crear(lote_id=lote)
    ajena = crear(clave="MID", lote_id=lote)
    cliente = cliente_como("Supervisor")
    r = cliente.get("/api/bitacora", params={"lote_id": str(lote)})
    assert r.status_code == 200, r.text
    assert r.json()["elementos"][0]["id"] == str(propia.id)
    assert str(ajena.id) not in r.text
    assert cliente.get(f"/api/vales/{ajena.id}/renglones").status_code == 404
    assert cliente.get("/api/bitacora", params={"almacen_id": str(mid.id)}).json()["total"] == 0
    vacio = cliente.get("/api/bitacora", params={"almacen_id": str(mid.id), "formato": "csv"})
    assert vacio.status_code == 200 and "csv" in vacio.headers["content-type"]
    assert len(vacio.text.strip().splitlines()) == 1


def test_BT_04_direccion_entrada_y_cancelacion(contexto17, cliente_como, session):
    _, kep, _, _, lote, crear = contexto17
    v = crear(lote_id=lote)
    v.estado = "CANCELADO"
    session.commit()
    r = cliente_como("Administrador").get(
        "/api/bitacora", params={"lote_id": str(lote), "almacen_id": str(kep.id)}
    )
    assert r.status_code == 200, r.text
    item = r.json()["elementos"][0]
    assert item["direccion"] == "ENTRADA" and item["estado_texto"] == "Cancelado"


def test_BT_05_valor_un_articulo_no_revela_precio(contexto17, session):
    admin, _, _, _, _, crear = contexto17
    v = crear(n=3)
    salida = BitacoraService(session).enriquecer_detalle(v.id, admin)
    assert salida["resumen"]["categorias"][0]["valor"] is None
    assert salida["resumen"]["valor_total"] is None
    assert "9876.54" not in str(salida)


def test_BT_06_BT_07_BT_09_renglones_500_paginados_sin_datos_reservados(contexto17, cliente_como):
    _, _, _, _, _, crear = contexto17
    v = crear(n=501)
    cliente = cliente_como("Administrador")
    a = cliente.get(f"/api/vales/{v.id}/renglones", params={"tamano": 500})
    b = cliente.get(f"/api/vales/{v.id}/renglones", params={"tamano": 500, "pagina": 2})
    assert a.status_code == b.status_code == 200, a.text
    assert a.json()["total"] == 501 and len(a.json()["elementos"]) == 500
    assert b.json()["elementos"][0]["renglon"] == 501
    assert "9876.54" not in a.text and "costo_unitario" not in a.text
    assert cliente.get(f"/api/vales/{v.id}/renglones", params={"tamano": 501}).status_code == 422


def test_BT_03_BT_08_lote_resumen_todas_partes_y_fecha(contexto17, session):
    admin, _, _, _, lote, crear = contexto17
    a = crear(lote_id=lote, n=2)
    crear(lote_id=lote, n=3)
    detalle = BitacoraService(session).enriquecer_detalle(a.id, admin)
    assert detalle["lote"]["partes"] == 2 and detalle["lote"]["renglones"] == 5
    assert len(detalle["relacionados"]) == 1


def test_BT_01_permiso_servidor_y_solo_mios(contexto17, cliente_como):
    _, _, _, _, lote, crear = contexto17
    crear(lote_id=lote)
    assert cliente_como("Recursos Humanos").get("/api/bitacora").status_code == 403
    r = cliente_como("Supervisor").get(
        "/api/bitacora", params={"lote_id": str(lote), "solo_mios": True}
    )
    assert r.status_code == 200 and r.json()["total"] == 0


def test_BT_02_BT_10_importacion_real_persiste_lote_sin_reescribir(session, cliente_como):
    from tests.importacion.ayudas import confirmacion, fila, unico

    cliente = cliente_como("Administrador")
    cuerpo = confirmacion([fila(unico("BTREAL"), cantidad=3)])
    r = cliente.post("/api/importacion", json=cuerpo)
    assert r.status_code == 201, r.text
    datos = r.json()
    assert datos["lote_id"] == cuerpo["id_lote"]
    v = session.get(Vale, uuid.UUID(datos["vales"][0]["id"]))
    assert str(v.lote_id) == cuerpo["id_lote"]
    sello = v.hash
    repetida = cliente.post("/api/importacion", json=cuerpo)
    assert repetida.status_code == 200 and repetida.json()["repetida"]
    assert v.hash == sello
    bitacora = cliente.get("/api/bitacora", params={"lote_id": cuerpo["id_lote"]})
    assert bitacora.status_code == 200 and bitacora.json()["total"] == 1


def test_BT_05_BT_06_detalle_sin_renglones_y_compatibilidad(contexto17, cliente_como, monkeypatch):
    from app.modulos.movimientos.repository import MovimientoRepository

    _, _, _, _, lote, crear = contexto17
    v = crear(lote_id=lote, n=3)
    cliente = cliente_como("Administrador")
    completo = cliente.get(f"/api/vales/{v.id}")
    assert completo.status_code == 200 and len(completo.json()["renglones"]) == 3

    def prohibido(*args):
        raise AssertionError("El encabezado no debe cargar los movimientos completos")

    monkeypatch.setattr(MovimientoRepository, "renglones_de", prohibido)
    solo = cliente.get(f"/api/vales/{v.id}", params={"renglones": False})
    assert solo.status_code == 200, solo.text
    assert solo.json()["renglones"] == [] and solo.json()["lote"]["renglones"] == 3
    assert solo.json()["resumen"]["categorias"][0]["unidades"] == 6
    assert "9876.54" not in solo.text


def test_BT_02_lote_id_no_es_campo_publico(contexto17, cliente_como):
    _, _, _, articulo, lote, _ = contexto17
    r = cliente_como("Administrador").post(
        "/api/vales",
        json={
            "tipo": "ENTRADA",
            "id_cliente": str(uuid.uuid4()),
            "lote_id": str(lote),
            "renglones": [{"codigo": articulo.codigo, "cantidad": 1}],
        },
    )
    assert r.status_code == 422
