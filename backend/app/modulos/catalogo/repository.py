"""Persistencia del módulo `catalogo`: add, flush y consultas; nunca commit.

Las consultas de `movimiento` y `trabajador` son de SOLO LECTURA: esas tablas son de otros módulos.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.orm import Session

from app.modulos.catalogo.models import (
    Articulo,
    Categoria,
    Codigo,
    Control,
    EstadoPieza,
    Pieza,
    TipoCodigo,
)
from app.modulos.movimientos.models import Movimiento
from app.modulos.trabajadores.models import EstadoTrabajador, PeriodoContrato, Trabajador


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass(frozen=True)
class FiltroArticulos:
    q: str | None = None
    categoria_id: uuid.UUID | None = None
    activo: bool | None = None
    offset: int = 0
    limit: int = 50


class CategoriaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, categoria_id: uuid.UUID) -> Categoria | None:
        return self.session.get(Categoria, categoria_id)

    def get_by_nombre(self, nombre: str) -> Categoria | None:
        return self.session.scalar(select(Categoria).where(Categoria.nombre == nombre))

    def listar(
        self, *, activo: bool | None, offset: int, limit: int
    ) -> tuple[list[Categoria], int]:
        condiciones = [] if activo is None else [Categoria.activo == activo]
        total = self.session.scalar(select(func.count()).select_from(Categoria).where(*condiciones))
        filas = self.session.scalars(
            select(Categoria)
            .where(*condiciones)
            .order_by(Categoria.nombre)
            .offset(offset)
            .limit(limit)
        )
        return list(filas), int(total or 0)

    def add(self, categoria: Categoria) -> Categoria:
        self.session.add(categoria)
        self.session.flush()
        return categoria


class ArticuloRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, articulo_id: uuid.UUID) -> Articulo | None:
        return self.session.get(Articulo, articulo_id)

    def get_by_codigo(self, codigo: str) -> Articulo | None:
        return self.session.scalar(select(Articulo).where(Articulo.codigo == codigo))

    def listar(self, filtro: FiltroArticulos) -> tuple[list[tuple[Articulo, str]], int]:
        """`(articulo, nombre de su categoría)` ordenados por nombre, y el total sin paginar."""
        condiciones = []
        if filtro.q and filtro.q.strip():
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

        total = self.session.scalar(select(func.count()).select_from(Articulo).where(*condiciones))
        filas = self.session.execute(
            select(Articulo, Categoria.nombre)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .where(*condiciones)
            .order_by(Articulo.nombre, Articulo.codigo)
            .offset(filtro.offset)
            .limit(filtro.limit)
        ).all()
        return [(a, n) for a, n in filas], int(total or 0)

    def add(self, articulo: Articulo) -> Articulo:
        self.session.add(articulo)
        self.session.flush()
        return articulo

    def eliminar(self, articulo: Articulo) -> None:
        """Borra el artículo y su código (solo si no tiene movimientos; lo verifica el service)."""
        self.session.execute(
            delete(Codigo).where(Codigo.tipo == TipoCodigo.ARTICULO, Codigo.ref_id == articulo.id)
        )
        self.session.delete(articulo)
        self.session.flush()

    def tiene_movimientos(self, articulo_id: uuid.UUID) -> bool:
        """Solo lectura: `movimiento` es del módulo `movimientos`."""
        return bool(
            self.session.scalar(select(exists().where(Movimiento.articulo_id == articulo_id)))
        )

    def tiene_piezas(self, articulo_id: uuid.UUID) -> bool:
        return bool(self.session.scalar(select(exists().where(Pieza.articulo_id == articulo_id))))


class PiezaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, pieza_id: uuid.UUID) -> Pieza | None:
        return self.session.get(Pieza, pieza_id)

    def get_by_serie(self, articulo_id: uuid.UUID, numero_serie: str) -> Pieza | None:
        return self.session.scalar(
            select(Pieza).where(
                Pieza.articulo_id == articulo_id, Pieza.numero_serie == numero_serie
            )
        )

    def add(self, pieza: Pieza) -> Pieza:
        self.session.add(pieza)
        self.session.flush()
        return pieza

    def quitar_inspeccion_vigente(self, articulo_id: uuid.UUID) -> int:
        """Deja sin inspección vigente a todas las piezas del artículo (CF-09)."""
        resultado = self.session.execute(
            update(Pieza)
            .where(Pieza.articulo_id == articulo_id, Pieza.inspeccion_vigente_hasta.is_not(None))
            .values(inspeccion_vigente_hasta=None)
        )
        return resultado.rowcount or 0


class EtiquetaRepository:
    """Lecturas para las hojas de QR (US-ETQ-001). Devuelve `(codigo, texto)`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def piezas(self) -> list[tuple[str, str]]:
        """Una por pieza que no está de baja: nombre del artículo, talla y serie."""
        filas = self.session.execute(
            select(Pieza.codigo, Articulo.nombre, Articulo.talla, Pieza.numero_serie)
            .join(Articulo, Articulo.id == Pieza.articulo_id)
            .where(Pieza.estado != EstadoPieza.BAJA)
            .order_by(Articulo.nombre, Pieza.codigo)
        ).all()
        resultado = []
        for codigo, nombre, talla, serie in filas:
            partes = [nombre]
            if talla:
                partes.append(f"talla {talla}")
            if serie:
                partes.append(f"serie {serie}")
            resultado.append((codigo, " · ".join(partes)))
        return resultado

    def estantes(self) -> list[tuple[str, str]]:
        """Una por artículo activo por cantidad (I-07): su código de producto y su nombre."""
        filas = self.session.execute(
            select(Articulo.codigo, Articulo.nombre)
            .where(Articulo.control == Control.CANTIDAD, Articulo.activo.is_(True))
            .order_by(Articulo.nombre, Articulo.codigo)
        ).all()
        return [(c, n) for c, n in filas]

    def credenciales(self) -> list[tuple[str, str, str, str | None]]:
        """Solo lectura de `trabajador`: `(codigo, nombre, numero_empleado, puesto)` de los
        trabajadores que no están inactivos. Nunca CURP ni NSS (RG-13)."""
        filas = self.session.execute(
            select(Codigo.codigo, Trabajador.id, Trabajador.nombre, Trabajador.numero_empleado)
            .join(Trabajador, Trabajador.id == Codigo.ref_id)
            .where(
                Codigo.tipo == TipoCodigo.TRABAJADOR,
                Trabajador.estado != EstadoTrabajador.INACTIVO,
            )
            .order_by(Trabajador.nombre, Codigo.codigo)
        ).all()
        # El puesto es el del periodo de contrato vigente: el más reciente (el primero que
        # aparece al ordenar por inicio y alta, de más nuevo a más viejo).
        puestos: dict[uuid.UUID, str | None] = {}
        if filas:
            periodos = self.session.execute(
                select(PeriodoContrato.trabajador_id, PeriodoContrato.puesto)
                .where(PeriodoContrato.trabajador_id.in_([f[1] for f in filas]))
                .order_by(PeriodoContrato.inicio.desc(), PeriodoContrato.creado_en.desc())
            ).all()
            for trabajador_id, puesto in periodos:
                puestos.setdefault(trabajador_id, puesto)
        return [(c, n, e, puestos.get(tid)) for c, tid, n, e in filas]
