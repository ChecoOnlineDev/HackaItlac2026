"""Ayudas de las pruebas de DEVOLUCION y NO_ADEUDO: entregas reales por la API y cuerpos."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modulos.catalogo.models import Articulo, Pieza
from app.modulos.trabajadores.models import Trabajador
from tests.movimientos.ayudas import (
    PNG_B64,
    abastecer,
    crear_articulo,
    cuerpo_entrega,
    entrar_pieza,
)

VALES = "/api/vales"
EVALUAR = "/api/vales/evaluar"
FOTO = f"data:image/png;base64,{PNG_B64}"


def renglon(codigo: str, cantidad: int = 1, condicion: str | None = "BUENO", **extra) -> dict:
    return {"codigo": codigo, "cantidad": cantidad, "condicion": condicion} | extra


def cuerpo_devolucion(renglones: list[dict], trabajador: Trabajador | None = None, **extra) -> dict:
    cuerpo = {"tipo": "DEVOLUCION", "id_cliente": str(uuid.uuid4()), "renglones": renglones}
    if trabajador is not None:
        cuerpo["trabajador_id"] = str(trabajador.id)
    return cuerpo | extra


def evaluar_devolucion(cliente: TestClient, renglones: list[dict], trabajador=None, **extra):
    cuerpo = cuerpo_devolucion(renglones, trabajador, **extra)
    cuerpo.pop("id_cliente")
    r = cliente.post(EVALUAR, json=cuerpo)
    assert r.status_code == 200, r.text
    return r.json()


def motivos(evaluacion: dict, indice: int = 0) -> list[str]:
    return [m["regla"] for m in evaluacion["renglones"][indice]["motivos"]]


def entregar(almacenista: TestClient, trabajador: Trabajador, renglones: list[dict]) -> dict:
    """Una ENTREGA real por la API."""
    r = almacenista.post(VALES, json=cuerpo_entrega(trabajador, renglones))
    assert r.status_code == 201, r.text
    return r.json()


def pieza_entregada(
    compras: TestClient,
    almacenista: TestClient,
    session: Session,
    trabajador: Trabajador,
    **articulo,
) -> tuple[Articulo, Pieza]:
    """Un artículo por pieza nuevo, entrado a Kepler y entregado al trabajador."""
    arts = {"requiere_inspeccion": False} | articulo
    art = crear_articulo(session, control="PIEZA", **arts)
    r, codigo = entrar_pieza(compras, art)
    assert r.status_code == 201, r.text
    entregar(almacenista, trabajador, [{"codigo": codigo, "cantidad": 1}])
    pieza = session.scalar(select(Pieza).where(Pieza.codigo == codigo))
    return art, pieza


def cantidad_entregada(
    compras: TestClient,
    almacenista: TestClient,
    session: Session,
    trabajador: Trabajador,
    cantidad: int = 5,
    entregado: int = 3,
    **articulo,
) -> Articulo:
    """Un artículo retornable por cantidad: entran `cantidad` y se entregan `entregado`."""
    art = crear_articulo(session, retornable=True, **articulo)
    abastecer(compras, art, cantidad)
    entregar(almacenista, trabajador, [{"codigo": art.codigo, "cantidad": entregado}])
    return art
