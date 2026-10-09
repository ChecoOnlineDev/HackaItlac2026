"""Reglas FEAT-016: herencia viva, cola paginada, puntos, evidencia y reintento."""

import base64
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.tiempo import hoy_mx
from app.modulos.almacenes.service import AlmacenService
from app.modulos.archivos.models import Adjunto
from app.modulos.catalogo.models import Articulo, Categoria, EstadoPieza
from app.modulos.catalogo.schemas import ArticuloCreate
from app.modulos.catalogo.service import CatalogoService
from app.modulos.inspecciones.models import Inspeccion

PUNTOS = {k: None for k in ("etiquetas", "costuras", "cintas", "herrajes", "conectores")}


@pytest.fixture
def pieza016(session):
    categoria = session.scalar(select(Categoria).where(Categoria.nombre == "Equipo de alturas"))
    catalogo = CatalogoService(session)
    articulo = catalogo.crear_articulo(
        ArticuloCreate(
            codigo="A016-" + uuid.uuid4().hex[:8],
            nombre="Arnés 016",
            categoria_id=categoria.id,
            requiere_inspeccion=True,
            vigencia_inspeccion_dias=30,
        ),
        actor_id=None,
    )
    pieza = catalogo.registrar_pieza(articulo.id, "P016-" + uuid.uuid4().hex[:8])
    almacen = AlmacenService(session)
    pieza.ubicacion_id = almacen.ubicacion_de_almacen(almacen.obtener_por_clave("KEP").id).id
    session.commit()
    return pieza


def test_P_10_aviso_herencia_viva_y_enteros_estrictos(session, pieza016, cliente_como):
    art = session.get(Articulo, pieza016.articulo_id)
    cat = session.get(Categoria, art.categoria_id)
    cat.dias_aviso_inspeccion = 11
    session.commit()
    servicio = CatalogoService(session)
    assert servicio.aviso_inspeccion(art) == (11, "CATEGORIA")
    cat.dias_aviso_inspeccion = 12
    session.commit()
    assert servicio.aviso_inspeccion(art) == (12, "CATEGORIA")
    art.dias_aviso_inspeccion = 3
    session.commit()
    assert servicio.aviso_inspeccion(art) == (3, "ARTICULO")
    compras = cliente_como("Compras")
    for valor in (0, 91, 1.5, True, "7"):
        respuesta = compras.patch(f"/api/articulos/{art.id}", json={"dias_aviso_inspeccion": valor})
        assert respuesta.status_code == 422, respuesta.text
        assert respuesta.json()["detalles"][0]["regla"] == "P-10"
    assert (
        compras.patch(f"/api/articulos/{art.id}", json={"dias_aviso_inspeccion": None}).status_code
        == 200
    )
    session.refresh(art)
    assert servicio.aviso_inspeccion(art) == (12, "CATEGORIA")


def test_P_11_pendientes_sql_conteos_y_paginacion(session, pieza016, cliente_como):
    cliente = cliente_como("Almacenista")
    pieza016.inspeccion_vigente_hasta = hoy_mx() - timedelta(days=1)
    session.commit()
    respuesta = cliente.get(
        "/api/inspecciones/pendientes", params={"q": pieza016.codigo, "tamano": 1}
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 1 and cuerpo["conteos"]["vencidas"] == 1
    assert cuerpo["elementos"][0]["accion"] == "INSPECCIONAR"
    assert cuerpo["elementos"][0]["dias_restantes"] == -1
    assert cliente.get(
        "/api/inspecciones/pendientes", params={"q": pieza016.codigo, "solo_contar": True}
    ).json() == {"conteos": cuerpo["conteos"]}
    pieza016.inspeccion_vigente_hasta = hoy_mx()
    session.commit()
    assert (
        cliente.get(
            "/api/inspecciones/pendientes", params={"q": pieza016.codigo, "estado": "POR_VENCER"}
        ).json()["total"]
        == 1
    )
    pieza016.estado = EstadoPieza.NO_APTO
    session.commit()
    resultado = cliente.get(
        "/api/inspecciones/pendientes", params={"q": pieza016.codigo, "estado": "POR_VENCER"}
    ).json()
    assert resultado["total"] == 0 and resultado["conteos"]["no_aptas"] == 1
    assert cliente_como("Compras").get("/api/inspecciones/pendientes").status_code == 403


def test_P_14_cinco_puntos_y_observacion_apta_con_falla(pieza016, cliente_como):
    cliente = cliente_como("Almacenista")
    ruta = f"/api/piezas/{pieza016.id}/inspecciones"
    assert cliente.post(ruta, json={"resultado": "APTO"}).status_code == 422
    datos = {"resultado": "APTO", "puntos": PUNTOS | {"costuras": False}}
    fallo = cliente.post(ruta, json=datos)
    assert fallo.status_code == 422 and fallo.json()["detalles"][0]["regla"] == "P-14"
    datos["observacion"] = "La costura secundaria no afecta el uso; revisión completa."
    respuesta = cliente.post(ruta, json=datos)
    assert respuesta.status_code == 201 and respuesta.json()["puntos"] == datos["puntos"]


def test_P_14_P_16_foto_atomica_idempotencia_y_ficha(session, pieza016, cliente_como):
    cliente = cliente_como("Almacenista")
    ruta = f"/api/piezas/{pieza016.id}/inspecciones"
    datos = {
        "resultado": "APTO",
        "puntos": PUNTOS,
        "id_cliente": str(uuid.uuid4()),
        "foto": "data:image/png;base64,"
        + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"prueba-inspeccion").decode(),
    }
    primera = cliente.post(ruta, json=datos)
    assert primera.status_code == 201, primera.text
    segunda = cliente.post(ruta, json=datos)
    assert segunda.status_code == 200 and segunda.json()["id"] == primera.json()["id"]
    assert segunda.json()["repetida"] is True
    assert (
        len(
            list(
                session.scalars(
                    select(Inspeccion).where(
                        Inspeccion.id_cliente == uuid.UUID(datos["id_cliente"])
                    )
                )
            )
        )
        == 1
    )
    assert (
        len(
            list(
                session.scalars(
                    select(Adjunto).where(Adjunto.inspeccion_id == uuid.UUID(primera.json()["id"]))
                )
            )
        )
        == 1
    )
    assert cliente.get(primera.json()["foto"]["url"]).status_code == 200
    assert (
        cliente.post(ruta, json=datos | {"observacion": "Contenido diferente"}).status_code == 409
    )
    ficha = cliente.get(f"/api/piezas/{pieza016.id}")
    assert ficha.status_code == 200, ficha.text
    assert ficha.json()["ultima_inspeccion"]["foto"] == primera.json()["foto"]
    assert ficha.json()["historial"][0]["puntos"] == PUNTOS


def test_P_16_lote_transacciones_independientes_y_repeticion(session, pieza016, cliente_como):
    cliente = cliente_como("Almacenista")
    registro = {
        "codigo": pieza016.codigo,
        "id_cliente": str(uuid.uuid4()),
        "resultado": "APTO",
        "puntos": PUNTOS,
    }
    lote = {
        "id_lote": str(uuid.uuid4()),
        "piezas": [registro, registro | {"codigo": "NO-EXISTE", "id_cliente": str(uuid.uuid4())}],
    }
    primera = cliente.post("/api/inspecciones/lotes", json=lote)
    assert primera.status_code == 200, primera.text
    assert primera.json()["guardadas"] == 1 and primera.json()["rechazadas"] == 1
    segunda = cliente.post("/api/inspecciones/lotes", json=lote)
    assert segunda.json()["repetidas"] == 1 and segunda.json()["guardadas"] == 0


def test_P_17_mantenimiento_y_transito_no_admiten_inspeccion(session, pieza016, cliente_como):
    cliente = cliente_como("Almacenista")
    ruta = f"/api/piezas/{pieza016.id}/inspecciones"
    datos = {"resultado": "APTO", "puntos": PUNTOS}
    pieza016.estado = EstadoPieza.EN_MANTENIMIENTO
    session.commit()
    respuesta = cliente.post(ruta, json=datos)
    assert respuesta.status_code == 409 and respuesta.json()["codigo"] == "PIEZA_EN_MANTENIMIENTO"
    retorno = cliente.post(
        f"/api/piezas/{pieza016.id}/estado",
        json={"estado": "NO_APTO", "observacion": "Mantenimiento terminado"},
    )
    assert retorno.status_code == 200, retorno.text
    assert cliente.post(ruta, json=datos).status_code == 201
