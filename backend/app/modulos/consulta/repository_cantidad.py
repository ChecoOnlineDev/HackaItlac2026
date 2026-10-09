"""Consulta de SOLO LECTURA de lo que está en resguardo por cantidad (SG-01): nunca `add`,
`flush` ni `commit`.

Una sola consulta por lista: la existencia en la ubicación de un trabajador con su artículo y el
movimiento que se la entregó (con su vale), unido por una tabla derivada con `row_number()`.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.modulos.acceso.alcance_almacenes import condicion_almacenes
from app.modulos.almacenes.models import Almacen, TipoUbicacion, Ubicacion
from app.modulos.catalogo.models import Articulo, Control
from app.modulos.consulta.repository import _patron
from app.modulos.movimientos.models import Existencia, Movimiento, TipoVale, Vale
from app.modulos.trabajadores.models import Trabajador


@dataclass(frozen=True)
class FiltroCantidad:
    """Filtro de lo que está en resguardo por cantidad. `solo_almacen_id` limita, para quien no
    tiene `almacenes.todos`, a lo que se entregó con un vale de su almacén (AC-06)."""

    palabras: tuple[str, ...] = ()
    articulo_id: uuid.UUID | None = None
    almacen_id: uuid.UUID | None = None
    solo_almacen_id: uuid.UUID | None = None


class CantidadRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _ultimas_entregas():
        """Por (ubicación del trabajador, artículo), el movimiento que se lo entregó: se prefiere
        el de un vale de ENTREGA y, entre varios, el más reciente (igual que el reporte de
        adeudos: una cancelación que se lo regresa no cambia desde cuándo lo tiene)."""
        destino = aliased(Ubicacion, name="u_cant")
        orden = func.row_number().over(
            partition_by=(Movimiento.destino_id, Movimiento.articulo_id),
            order_by=(
                case((Vale.tipo == TipoVale.ENTREGA, 0), else_=1),
                Movimiento.creado_en.desc(),
                Movimiento.id.desc(),
            ),
        )
        return (
            select(
                Movimiento.destino_id.label("ubicacion_id"),
                Movimiento.articulo_id.label("articulo_id"),
                Movimiento.creado_en.label("desde"),
                Vale.id.label("vale_id"),
                Vale.folio.label("folio"),
                Vale.almacen_id.label("vale_almacen_id"),
                orden.label("rn"),
            )
            .select_from(Movimiento)
            .join(Vale, Vale.id == Movimiento.vale_id)
            .join(destino, destino.id == Movimiento.destino_id)
            .where(Movimiento.pieza_id.is_(None), destino.tipo == TipoUbicacion.TRABAJADOR)
            .subquery("ent")
        )

    def _base(self, columnas, filtro: FiltroCantidad):
        ent = self._ultimas_entregas()
        almacen = aliased(Almacen, name="a_ent")
        consulta = (
            select(*columnas(ent, almacen))
            .select_from(Existencia)
            .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
            .join(Trabajador, Trabajador.id == Ubicacion.trabajador_id)
            .join(Articulo, Articulo.id == Existencia.articulo_id)
            .outerjoin(
                ent,
                and_(
                    ent.c.ubicacion_id == Existencia.ubicacion_id,
                    ent.c.articulo_id == Existencia.articulo_id,
                    ent.c.rn == 1,
                ),
            )
            .outerjoin(almacen, almacen.id == ent.c.vale_almacen_id)
            .where(
                Ubicacion.tipo == TipoUbicacion.TRABAJADOR,
                Existencia.cantidad > 0,
                Articulo.control == Control.CANTIDAD,
            )
        )
        if filtro.articulo_id is not None:
            consulta = consulta.where(Articulo.id == filtro.articulo_id)
        if filtro.almacen_id is not None:
            consulta = consulta.where(condicion_almacenes(ent.c.vale_almacen_id, filtro.almacen_id))
        if filtro.solo_almacen_id is not None:
            consulta = consulta.where(
                condicion_almacenes(ent.c.vale_almacen_id, filtro.solo_almacen_id)
            )
        for palabra in filtro.palabras:
            patron = _patron(palabra)
            consulta = consulta.where(
                or_(
                    Articulo.nombre.like(patron, escape="\\"),
                    Articulo.codigo.like(patron, escape="\\"),
                    Trabajador.nombre.like(patron, escape="\\"),
                    Trabajador.numero_empleado.like(patron, escape="\\"),
                )
            )
        return consulta

    def renglones(
        self, filtro: FiltroCantidad, offset: int | None, limit: int | None
    ) -> tuple[list, int]:
        """Los renglones (por trabajador y artículo) y cuántos hay en total."""

        def columnas(ent, almacen):
            return (
                Trabajador.id.label("trabajador_id"),
                Trabajador.numero_empleado,
                Trabajador.nombre.label("trabajador"),
                Articulo.id.label("articulo_id"),
                Articulo.codigo.label("articulo_codigo"),
                Articulo.nombre.label("articulo_nombre"),
                Articulo.marca.label("articulo_marca"),
                Articulo.unidad.label("articulo_unidad"),
                Existencia.cantidad,
                ent.c.desde,
                ent.c.vale_id,
                ent.c.folio,
                ent.c.vale_almacen_id,
                almacen.clave.label("almacen_clave"),
                almacen.nombre.label("almacen_nombre"),
            )

        consulta = self._base(columnas, filtro)
        cuenta = self._base(lambda *_: (func.count(),), filtro)
        total = int(self.session.scalar(cuenta) or 0)
        consulta = consulta.order_by(Trabajador.nombre, Articulo.nombre, Articulo.id)
        if offset is not None and limit is not None:
            consulta = consulta.offset(offset).limit(limit)
        return list(self.session.execute(consulta).all()), total

    def resumen(self, filtro: FiltroCantidad) -> dict[str, int]:
        """Renglones, unidades, artículos y trabajadores distintos."""
        consulta = self._base(
            lambda *_: (
                func.count(),
                func.coalesce(func.sum(Existencia.cantidad), 0),
                func.count(func.distinct(Articulo.id)),
                func.count(func.distinct(Trabajador.id)),
            ),
            filtro,
        )
        renglones, unidades, articulos, trabajadores = (
            int(v or 0) for v in self.session.execute(consulta).one()
        )
        return {
            "renglones": renglones,
            "unidades": unidades,
            "articulos": articulos,
            "trabajadores": trabajadores,
        }
