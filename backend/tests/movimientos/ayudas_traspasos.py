"""Ayudas de las pruebas de traspasos (TRASPASO y RECEPCION).

`cliente_almacen("CON")` da un cliente con la sesión del almacenista de ese almacén (los datos de
prueba traen uno por almacén: `almacenista` en KEP, `alm_con`, `alm_mid`, `alm_hyl`...). Se
importa en cada archivo de pruebas de traspasos (no está en `conftest.py` para no tocarlo).
"""

import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.modulos.almacenes.models import Almacen, Ubicacion
from app.modulos.almacenes.service import AlmacenService
from app.modulos.catalogo.models import Articulo, Pieza
from app.modulos.movimientos.models import Existencia, Movimiento, Vale
from tests.conftest import UsuarioPrueba, iniciar_sesion_en

VALES = "/api/vales"
EVALUAR = "/api/vales/evaluar"
POR_RECIBIR = "/api/traspasos/por-recibir"

USUARIO_DE_ALMACEN = {
    "KEP": "almacenista",
    "CON": "alm_con",
    "MID": "alm_mid",
    "HYL": "alm_hyl",
    "LAM": "alm_lam",
    "MIN": "alm_min",
}


@pytest.fixture
def cliente_almacen(app) -> Iterator[Callable[[str], TestClient]]:
    """`cliente_almacen("CON")`: TestClient con la sesión del almacenista de ese almacén."""
    ajustes = get_settings()
    clientes: list[TestClient] = []

    def _cliente(clave: str) -> TestClient:
        c = TestClient(app)
        usuario = UsuarioPrueba(USUARIO_DE_ALMACEN[clave], ajustes.clave_datos_prueba)
        assert iniciar_sesion_en(c, usuario).status_code == 200
        clientes.append(c)
        return c

    yield _cliente
    for c in clientes:
        c.close()


def almacen_id(session: Session, clave: str) -> uuid.UUID:
    return AlmacenService(session).obtener_por_clave(clave).id


def renglon(codigo: str, cantidad: int = 1, **extra) -> dict:
    return {"codigo": codigo, "cantidad": cantidad} | extra


def cuerpo_traspaso(session: Session, destino: str, renglones: list[dict], **extra) -> dict:
    return {
        "tipo": "TRASPASO",
        "destino_almacen_id": str(almacen_id(session, destino)),
        "id_cliente": str(uuid.uuid4()),
        "renglones": renglones,
    } | extra


def cuerpo_recepcion(traspaso_id: str | uuid.UUID, renglones: list[dict], **extra) -> dict:
    return {
        "tipo": "RECEPCION",
        "vale_origen_id": str(traspaso_id),
        "id_cliente": str(uuid.uuid4()),
        "renglones": renglones,
        # RG-14: una recepción con diferencias exige observación; las completas no la usan.
        "observacion": "Faltó en el contenedor",
    } | extra


def enviar(cliente: TestClient, session: Session, destino: str, renglones: list[dict], **extra):
    """Confirma un TRASPASO y devuelve su respuesta JSON (debe ser 201)."""
    r = cliente.post(VALES, json=cuerpo_traspaso(session, destino, renglones, **extra))
    assert r.status_code == 201, r.text
    return r.json()


def recibir(cliente: TestClient, traspaso: dict | str, renglones: list[dict], **extra):
    """Confirma una RECEPCION y devuelve su respuesta JSON (debe ser 201)."""
    traspaso_id = traspaso["id"] if isinstance(traspaso, dict) else traspaso
    r = cliente.post(VALES, json=cuerpo_recepcion(traspaso_id, renglones, **extra))
    assert r.status_code == 201, r.text
    return r.json()


def evaluar_traspaso(cliente: TestClient, session: Session, destino: str, renglones, **extra):
    r = cliente.post(EVALUAR, json=cuerpo_traspaso(session, destino, renglones, **extra))
    assert r.status_code == 200, r.text
    return r.json()


def evaluar_recepcion(cliente: TestClient, traspaso: dict | str, renglones, **extra):
    traspaso_id = traspaso["id"] if isinstance(traspaso, dict) else traspaso
    r = cliente.post(EVALUAR, json=cuerpo_recepcion(traspaso_id, renglones, **extra))
    assert r.status_code == 200, r.text
    return r.json()


def reglas(evaluacion: dict, indice: int | None = None) -> list[str]:
    """IDs de regla de los motivos del vale (`indice=None`) o de un renglón."""
    motivos = (
        evaluacion["motivos"] if indice is None else evaluacion["renglones"][indice]["motivos"]
    )
    return [m["regla"] for m in motivos]


def vale(session: Session, vale_id: str | uuid.UUID) -> Vale:
    """El vale tal como está en la base ahora (descarta lo que la sesión tenía en memoria)."""
    session.expire_all()
    return session.get(Vale, uuid.UUID(str(vale_id)))


def ubicacion_virtual(session: Session, virtual: str) -> uuid.UUID:
    return session.scalar(select(Ubicacion.id).where(Ubicacion.virtual == virtual))


def en_transito(session: Session, articulo: Articulo) -> int:
    """Existencia En tránsito de un artículo."""
    session.expire_all()
    return (
        session.scalar(
            select(Existencia.cantidad).where(
                Existencia.ubicacion_id == ubicacion_virtual(session, "EN_TRANSITO"),
                Existencia.articulo_id == articulo.id,
            )
        )
        or 0
    )


def total_en_almacenes(session: Session, articulo: Articulo) -> int:
    """Lo que cuenta en TODOS los almacenes juntos (no incluye lo que está En tránsito)."""
    session.expire_all()
    filas = session.scalars(
        select(Existencia.cantidad)
        .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
        .where(Existencia.articulo_id == articulo.id, Ubicacion.almacen_id.is_not(None))
    ).all()
    return sum(filas)


def pieza(session: Session, codigo: str) -> Pieza:
    session.expire_all()
    return session.scalar(select(Pieza).where(Pieza.codigo == codigo))


def ubicacion_de_pieza(session: Session, codigo: str) -> str:
    """Dónde está la pieza: la clave del almacén, o el nombre de la ubicación virtual."""
    p = pieza(session, codigo)
    ub = session.get(Ubicacion, p.ubicacion_id)
    if ub.almacen_id is not None:
        return session.get(Almacen, ub.almacen_id).clave
    return ub.virtual or ub.tipo


def movimientos_del_vale(session: Session, vale_id: str | uuid.UUID) -> list[Movimiento]:
    session.expire_all()
    return list(
        session.scalars(
            select(Movimiento)
            .where(Movimiento.vale_id == uuid.UUID(str(vale_id)))
            .order_by(Movimiento.renglon)
        )
    )
