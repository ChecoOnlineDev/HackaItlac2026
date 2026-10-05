"""Persistencia del módulo `almacenes`. Solo `add`, `flush` y consultas; nunca commit."""

import uuid
from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.modulos.almacenes.models import Almacen, TipoUbicacion, Ubicacion, UbicacionVirtual
from app.modulos.catalogo.models import Articulo, Categoria, Control, EstadoPieza, Pieza
from app.modulos.movimientos.models import Existencia
from app.modulos.trabajadores.models import Trabajador


@dataclass(frozen=True)
class FiltroExistencias:
    q: str | None = None
    categoria_id: uuid.UUID | None = None
    activo: bool | None = None
    offset: int = 0
    limit: int = 50


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class AlmacenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, almacen_id: uuid.UUID) -> Almacen | None:
        return self.session.get(Almacen, almacen_id)

    def get_by_clave(self, clave: str) -> Almacen | None:
        return self.session.scalar(select(Almacen).where(Almacen.clave == clave))

    def listar(self) -> list[Almacen]:
        return list(self.session.scalars(select(Almacen).order_by(Almacen.clave)))

    def add(self, almacen: Almacen) -> Almacen:
        self.session.add(almacen)
        self.session.flush()
        return almacen

    def hijos(self, padre_id: uuid.UUID) -> list[Almacen]:
        consulta = select(Almacen).where(Almacen.padre_id == padre_id).order_by(Almacen.clave)
        return list(self.session.scalars(consulta))

    # ------------------------------------------------- existencias (solo lectura)
    # La tabla `existencia` es de `movimientos`: aquí solo se lee.

    @staticmethod
    def _disponible():
        """Existencia que se puede entregar. En artículos por pieza solo cuentan las piezas Aptas
        que están en esa ubicación; en los de cantidad, la existencia completa (I-05)."""
        aptas = (
            select(func.count(Pieza.id))
            .where(
                Pieza.ubicacion_id == Existencia.ubicacion_id,
                Pieza.articulo_id == Existencia.articulo_id,
                Pieza.estado == EstadoPieza.APTO,
            )
            .correlate(Existencia)
            .scalar_subquery()
        )
        return case((Articulo.control == Control.PIEZA, aptas), else_=Existencia.cantidad)

    def existencias_de_almacen(
        self, ubicacion_id: uuid.UUID, filtro: FiltroExistencias
    ) -> tuple[list, int]:
        """Artículos con existencia en esa ubicación: `(filas, total)`, ordenados por nombre."""
        condiciones = [Existencia.ubicacion_id == ubicacion_id, Existencia.cantidad > 0]
        if filtro.q:
            patron = f"%{_escapar_like(filtro.q.strip())}%"
            condiciones.append(
                Articulo.nombre.ilike(patron, escape="\\")
                | Articulo.codigo.ilike(patron, escape="\\")
                | Articulo.marca.ilike(patron, escape="\\")
                | Articulo.modelo.ilike(patron, escape="\\")
            )
        if filtro.categoria_id is not None:
            condiciones.append(Articulo.categoria_id == filtro.categoria_id)
        if filtro.activo is not None:
            condiciones.append(Articulo.activo == filtro.activo)

        base = (
            select(Articulo, Categoria.nombre, Existencia.cantidad, self._disponible())
            .join(Existencia, Existencia.articulo_id == Articulo.id)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .where(*condiciones)
        )
        total = self.session.scalar(
            select(func.count())
            .select_from(Articulo)
            .join(Existencia, Existencia.articulo_id == Articulo.id)
            .where(*condiciones)
        )
        filas = self.session.execute(
            base.order_by(Articulo.nombre, Articulo.codigo)
            .offset(filtro.offset)
            .limit(filtro.limit)
        ).all()
        return list(filas), int(total or 0)

    def existencias_de_articulo(self, articulo_id: uuid.UUID) -> list:
        """Dónde hay de un artículo: `(Almacen, cantidad, disponible)` por almacén."""
        consulta = (
            select(Almacen, Existencia.cantidad, self._disponible())
            .join(Ubicacion, Ubicacion.almacen_id == Almacen.id)
            .join(Existencia, Existencia.ubicacion_id == Ubicacion.id)
            .join(Articulo, Articulo.id == Existencia.articulo_id)
            .where(Existencia.articulo_id == articulo_id, Existencia.cantidad > 0)
            .order_by(Almacen.clave)
        )
        return list(self.session.execute(consulta).all())

    def poseedores_de_articulo(self, articulo_id: uuid.UUID) -> list:
        """Quién lo tiene: `(Trabajador, cantidad)` por trabajador con existencia."""
        consulta = (
            select(Trabajador, Existencia.cantidad)
            .join(Ubicacion, Ubicacion.trabajador_id == Trabajador.id)
            .join(Existencia, Existencia.ubicacion_id == Ubicacion.id)
            .where(Existencia.articulo_id == articulo_id, Existencia.cantidad > 0)
            .order_by(Trabajador.nombre)
        )
        return list(self.session.execute(consulta).all())


class UbicacionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, ubicacion_id: uuid.UUID) -> Ubicacion | None:
        return self.session.get(Ubicacion, ubicacion_id)

    def de_almacen(self, almacen_id: uuid.UUID) -> Ubicacion | None:
        return self.session.scalar(select(Ubicacion).where(Ubicacion.almacen_id == almacen_id))

    def de_trabajador(self, trabajador_id: uuid.UUID) -> Ubicacion | None:
        return self.session.scalar(
            select(Ubicacion).where(Ubicacion.trabajador_id == trabajador_id)
        )

    def virtual(self, virtual: UbicacionVirtual) -> Ubicacion | None:
        return self.session.scalar(select(Ubicacion).where(Ubicacion.virtual == virtual.value))

    def add(self, ubicacion: Ubicacion) -> Ubicacion:
        self.session.add(ubicacion)
        self.session.flush()
        return ubicacion

    def crear_de_almacen(self, almacen_id: uuid.UUID) -> Ubicacion:
        return self.add(Ubicacion(tipo=TipoUbicacion.ALMACEN, almacen_id=almacen_id))

    def crear_de_trabajador(self, trabajador_id: uuid.UUID) -> Ubicacion:
        return self.add(Ubicacion(tipo=TipoUbicacion.TRABAJADOR, trabajador_id=trabajador_id))

    def crear_virtual(self, virtual: UbicacionVirtual) -> Ubicacion:
        return self.add(Ubicacion(tipo=TipoUbicacion.VIRTUAL, virtual=virtual.value))
