"""Consultas de SOLO LECTURA del valor del inventario (FEAT-012, VI-01 a VI-07): nunca `add`,
`flush` ni `commit`.

Cada consulta devuelve filas `(almacen_id, articulo_id, categoria, costo, cantidad)` ya sumadas por
almacén y artículo. El costo sale solo para multiplicar en el servicio; no viaja en la respuesta.
Las existencias cubren también a los artículos por pieza (no se une con `pieza`).
"""

import uuid

from sqlalchemy import and_, case, func, literal_column, select
from sqlalchemy.orm import Session, aliased

from app.modulos.acceso.alcance_almacenes import condicion_almacenes
from app.modulos.almacenes.models import Almacen, TipoUbicacion, Ubicacion, UbicacionVirtual
from app.modulos.catalogo.models import Articulo, Categoria
from app.modulos.movimientos.models import Existencia, Movimiento, TipoVale, Vale


class ValorRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def almacen(self, almacen_id: uuid.UUID) -> Almacen | None:
        return self.session.get(Almacen, almacen_id)

    def almacenes(self) -> list[Almacen]:
        return list(self.session.scalars(select(Almacen).order_by(Almacen.nombre)))

    def _columnas(self, almacen_col):
        return (
            almacen_col.label("almacen_id"),
            Existencia.articulo_id.label("articulo_id"),
            Categoria.nombre.label("categoria"),
            Articulo.costo_unitario.label("costo"),
            func.sum(Existencia.cantidad).label("cantidad"),
        )

    def en_almacen(self, almacen_id: uuid.UUID | None) -> list:
        """Existencia en las ubicaciones de almacén del alcance."""
        columnas = self._columnas(Ubicacion.almacen_id)
        consulta = (
            select(*columnas)
            .select_from(Existencia)
            .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
            .join(Articulo, Articulo.id == Existencia.articulo_id)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .where(Ubicacion.tipo == TipoUbicacion.ALMACEN, Existencia.cantidad > 0)
        )
        if almacen_id is not None:
            consulta = consulta.where(condicion_almacenes(Ubicacion.almacen_id, almacen_id))
        consulta = consulta.group_by(
            Ubicacion.almacen_id, Existencia.articulo_id, Categoria.nombre, Articulo.costo_unitario
        )
        return list(self.session.execute(consulta).all())

    @staticmethod
    def _ultimas_entregas():
        """Por (ubicación del trabajador, artículo), el movimiento que se lo entregó: se prefiere
        el de un vale de ENTREGA y, entre varios, el más reciente. Incluye piezas."""
        destino = aliased(Ubicacion, name="u_val")
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
                Vale.almacen_id.label("vale_almacen_id"),
                orden.label("rn"),
            )
            .select_from(Movimiento)
            .join(Vale, Vale.id == Movimiento.vale_id)
            .join(destino, destino.id == Movimiento.destino_id)
            .where(destino.tipo == TipoUbicacion.TRABAJADOR)
            .subquery("ent_val")
        )

    def en_resguardo(self, almacen_id: uuid.UUID | None) -> list:
        """Existencia en manos de trabajadores, atribuida al almacén del vale de su última
        entrega. Con `almacen_id` solo lo atribuido a él; sin él, todo (una existencia sin
        entrega localizable queda con `almacen_id` nulo)."""
        ent = self._ultimas_entregas()
        columnas = self._columnas(ent.c.vale_almacen_id)
        consulta = (
            select(*columnas)
            .select_from(Existencia)
            .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
            .join(Articulo, Articulo.id == Existencia.articulo_id)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .outerjoin(
                ent,
                and_(
                    ent.c.ubicacion_id == Existencia.ubicacion_id,
                    ent.c.articulo_id == Existencia.articulo_id,
                    ent.c.rn == 1,
                ),
            )
            .where(Ubicacion.tipo == TipoUbicacion.TRABAJADOR, Existencia.cantidad > 0)
        )
        if almacen_id is not None:
            consulta = consulta.where(condicion_almacenes(ent.c.vale_almacen_id, almacen_id))
        consulta = consulta.group_by(
            ent.c.vale_almacen_id, Existencia.articulo_id, Categoria.nombre, Articulo.costo_unitario
        )
        return list(self.session.execute(consulta).all())

    def en_transito(self) -> list:
        """Existencia en la ubicación virtual EN_TRANSITO (solo se da para «todos»)."""
        columnas = self._columnas(literal_column("NULL"))
        consulta = (
            select(*columnas)
            .select_from(Existencia)
            .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
            .join(Articulo, Articulo.id == Existencia.articulo_id)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .where(Ubicacion.virtual == UbicacionVirtual.EN_TRANSITO, Existencia.cantidad > 0)
            .group_by(Existencia.articulo_id, Categoria.nombre, Articulo.costo_unitario)
        )
        return list(self.session.execute(consulta).all())
