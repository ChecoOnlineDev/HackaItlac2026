"""Fixtures de las pruebas de `movimientos`.

- `compras`, `almacenista`, `supervisor`: clientes con sesión (la transacción se revierte).
- `doble_inspecciones`: reemplaza `InspeccionService` (lo construye otro agente) con un doble que
  imita su firma acordada y deja el estado de la pieza como lo haría el real.
- `sesion_independiente` y `cliente_independiente`: para las pruebas de concurrencia. El fixture
  normal usa una transacción externa con savepoints, donde dos hilos no se verían: estos usan
  conexiones propias y DATOS CONFIRMADOS que `limpieza` borra al final.
"""

import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.tiempo import hoy_mx
from app.modulos.archivos.models import Adjunto
from app.modulos.auditoria.models import Auditoria
from app.modulos.autorizaciones.models import Autorizacion
from app.modulos.catalogo.models import Articulo, Codigo, EstadoPieza, Pieza
from app.modulos.catalogo.service import CatalogoService
from app.modulos.movimientos.models import Existencia, Movimiento, SerieFolio, Vale
from app.modulos.trabajadores.models import PeriodoContrato, Trabajador
from tests.conftest import iniciar_sesion_en


@pytest.fixture(autouse=True)
def _archivos_tmp(tmp_path, monkeypatch):
    """Las firmas se guardan en una carpeta temporal."""
    monkeypatch.setattr(get_settings(), "archivos_dir", tmp_path)
    return tmp_path


@pytest.fixture
def compras(cliente_como) -> TestClient:
    return cliente_como("Compras")


@pytest.fixture
def almacenista(cliente_como) -> TestClient:
    return cliente_como("Almacenista")


@pytest.fixture
def supervisor(cliente_como) -> TestClient:
    return cliente_como("Supervisor")


@dataclass
class LlamadaInspeccion:
    pieza_id: uuid.UUID
    fecha: date
    resultado: object
    observacion: str | None
    usuario_id: uuid.UUID


class DobleInspecciones:
    """Imita `InspeccionService.registrar_inicial` (firma acordada con el agente de
    inspecciones): solo flush; fija estado e `inspeccion_vigente_hasta` con catálogo."""

    def __init__(self, session: Session, llamadas: list[LlamadaInspeccion]) -> None:
        self.session = session
        self.llamadas = llamadas

    def registrar_inicial(self, pieza_id, *, fecha, resultado, observacion, usuario_id):
        self.llamadas.append(LlamadaInspeccion(pieza_id, fecha, resultado, observacion, usuario_id))
        catalogo = CatalogoService(self.session)
        pieza = catalogo.obtener_pieza(pieza_id)
        articulo = catalogo.obtener_articulo(pieza.articulo_id)
        if str(resultado) == "APTO":
            dias = articulo.vigencia_inspeccion_dias or 180
            catalogo.actualizar_estado_pieza(
                pieza_id,
                estado=EstadoPieza.APTO,
                inspeccion_vigente_hasta=fecha + timedelta(days=dias),
                actor_id=usuario_id,
            )
        else:
            catalogo.actualizar_estado_pieza(
                pieza_id,
                estado=EstadoPieza.NO_APTO,
                inspeccion_vigente_hasta=None,
                actor_id=usuario_id,
            )
        return None


@pytest.fixture
def doble_inspecciones(monkeypatch) -> list[LlamadaInspeccion]:
    """Lista de las llamadas hechas a `registrar_inicial`."""
    llamadas: list[LlamadaInspeccion] = []
    monkeypatch.setattr(
        "app.modulos.movimientos.tipos.entrada.servicio_inspecciones",
        lambda session: DobleInspecciones(session, llamadas),
    )
    return llamadas


# ------------------------------------------------------------------ concurrencia


@dataclass
class Limpieza:
    """Registra lo que una prueba de concurrencia confirmó en la base para borrarlo después."""

    articulos: list[uuid.UUID] = field(default_factory=list)
    trabajadores: list[uuid.UUID] = field(default_factory=list)
    series: dict[tuple, int] = field(default_factory=dict)


@pytest.fixture
def sesion_independiente(engine) -> Iterator[Callable[[], Session]]:
    """Fábrica de sesiones con conexión propia (sus commits son reales)."""
    abiertas: list[Session] = []

    def _nueva() -> Session:
        sesion = Session(bind=engine, autoflush=False, expire_on_commit=False)
        abiertas.append(sesion)
        return sesion

    yield _nueva
    for s in abiertas:
        s.close()


@pytest.fixture
def limpieza(sesion_independiente) -> Iterator[Limpieza]:
    """Guarda el contador de folios y, al final, borra lo creado por la prueba."""
    datos = Limpieza()
    antes = sesion_independiente()
    for fila in antes.scalars(select(SerieFolio)):
        datos.series[(fila.almacen_id, fila.tipo)] = fila.ultimo
    antes.close()
    yield datos

    s = sesion_independiente()
    try:
        articulos = datos.articulos
        vales = list(
            s.scalars(select(Movimiento.vale_id).where(Movimiento.articulo_id.in_(articulos)))
        )
        autorizaciones = [
            a for a in s.scalars(select(Vale.autorizacion_id).where(Vale.id.in_(vales))) if a
        ]
        s.execute(update(Vale).where(Vale.id.in_(vales)).values(firma_adjunto_id=None))
        s.execute(delete(Adjunto).where(Adjunto.vale_id.in_(vales)))
        s.execute(delete(Movimiento).where(Movimiento.vale_id.in_(vales)))
        s.execute(delete(Codigo).where(Codigo.ref_id.in_(vales)))
        s.execute(delete(Vale).where(Vale.id.in_(vales)))
        s.execute(delete(Autorizacion).where(Autorizacion.id.in_(autorizaciones)))
        piezas = list(s.scalars(select(Pieza.id).where(Pieza.articulo_id.in_(articulos))))
        s.execute(delete(Codigo).where(Codigo.ref_id.in_(piezas)))
        s.execute(delete(Pieza).where(Pieza.articulo_id.in_(articulos)))
        s.execute(delete(Existencia).where(Existencia.articulo_id.in_(articulos)))
        s.execute(delete(Codigo).where(Codigo.ref_id.in_(articulos)))
        s.execute(delete(Articulo).where(Articulo.id.in_(articulos)))
        for trabajador_id in datos.trabajadores:
            from app.modulos.almacenes.models import Ubicacion

            ubicacion = s.scalar(
                select(Ubicacion.id).where(Ubicacion.trabajador_id == trabajador_id)
            )
            if ubicacion is not None:
                s.execute(delete(Existencia).where(Existencia.ubicacion_id == ubicacion))
                s.execute(delete(Ubicacion).where(Ubicacion.id == ubicacion))
            s.execute(delete(Codigo).where(Codigo.ref_id == trabajador_id))
            s.execute(delete(PeriodoContrato).where(PeriodoContrato.trabajador_id == trabajador_id))
            s.execute(delete(Trabajador).where(Trabajador.id == trabajador_id))
        for (almacen_id, tipo), ultimo in datos.series.items():
            s.execute(
                update(SerieFolio)
                .where(SerieFolio.almacen_id == almacen_id, SerieFolio.tipo == tipo)
                .values(ultimo=ultimo)
            )
        for serie in s.scalars(select(SerieFolio)).all():
            if (serie.almacen_id, serie.tipo) not in datos.series:
                s.delete(serie)  # la serie nació en esta prueba
        s.execute(delete(Auditoria).where(Auditoria.entidad_id.in_([str(a) for a in articulos])))
        s.commit()
    finally:
        s.close()


@pytest.fixture
def cliente_independiente(engine, usuario_por_rol) -> Iterator[Callable[[str], TestClient]]:
    """Clientes que usan una sesión nueva por petición, con commits reales."""
    from app.main import create_app

    app = create_app()  # sin sobrescribir `get_session`: usa el motor real
    clientes: list[TestClient] = []

    def _cliente(rol: str) -> TestClient:
        c = TestClient(app)
        assert iniciar_sesion_en(c, usuario_por_rol(rol)).status_code == 200
        clientes.append(c)
        return c

    yield _cliente
    for c in clientes:
        c.close()


def vigencia_de(dias: int) -> date:
    return hoy_mx() + timedelta(days=dias)
