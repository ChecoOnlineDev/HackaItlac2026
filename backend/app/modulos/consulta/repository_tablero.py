"""Consultas de SOLO LECTURA del tablero (TB-01 a TB-03): nunca `add`, `flush` ni `commit`.

Cada cifra es una consulta agregada. `almacen_id=None` significa todos los almacenes.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.modulos.almacenes.models import Almacen, TipoUbicacion, Ubicacion, UbicacionVirtual
from app.modulos.catalogo.models import Articulo, Categoria, Control, EstadoPieza, Pieza
from app.modulos.consulta.repository_seguimiento import SeguimientoRepository
from app.modulos.movimientos.models import EstadoVale, Existencia, Movimiento, TipoVale, Vale
from app.modulos.solicitudes_compra.models import EstadoSolicitud, SolicitudCompra


class TableroRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ----------------------------------------------------------------------- referencias

    def almacen(self, almacen_id: uuid.UUID) -> Almacen | None:
        return self.session.get(Almacen, almacen_id)

    def categoria(self, categoria_id: uuid.UUID) -> Categoria | None:
        return self.session.get(Categoria, categoria_id)

    # ------------------------------------------------------------------------ tarjetas

    def _existencias_de_almacen(self, almacen_id: uuid.UUID | None):
        consulta = (
            select(Existencia)
            .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
            .where(Ubicacion.tipo == TipoUbicacion.ALMACEN)
        )
        if almacen_id is not None:
            consulta = consulta.where(Ubicacion.almacen_id == almacen_id)
        return consulta

    def existencias(self, almacen_id: uuid.UUID | None) -> tuple[int, int]:
        """`(unidades, artículos distintos con cantidad > 0)` en los almacenes del alcance."""
        base = self._existencias_de_almacen(almacen_id).subquery()
        unidades = self.session.scalar(select(func.coalesce(func.sum(base.c.cantidad), 0)))
        articulos = self.session.scalar(
            select(func.count(func.distinct(base.c.articulo_id))).where(base.c.cantidad > 0)
        )
        return int(unidades or 0), int(articulos or 0)

    def sin_existencia(self, almacen_id: uuid.UUID | None) -> int:
        """Artículos activos con fila de existencia en el alcance cuya suma hoy es cero."""
        base = self._existencias_de_almacen(almacen_id).subquery()
        por_articulo = (
            select(base.c.articulo_id)
            .join(Articulo, Articulo.id == base.c.articulo_id)
            .where(Articulo.activo.is_(True))
            .group_by(base.c.articulo_id)
            .having(func.sum(base.c.cantidad) == 0)
            .subquery()
        )
        return int(self.session.scalar(select(func.count()).select_from(por_articulo)) or 0)

    @staticmethod
    def _en_alcance(u, ult, almacen_id: uuid.UUID):
        """Piezas del alcance de un almacén (C-02): en él, en manos de un trabajador a quien se
        entregó desde él, o en tránsito desde o hacia él."""
        return or_(
            and_(u.tipo == TipoUbicacion.ALMACEN, u.almacen_id == almacen_id),
            and_(u.tipo == TipoUbicacion.TRABAJADOR, ult.c.vale_almacen_id == almacen_id),
            and_(
                u.tipo == TipoUbicacion.VIRTUAL,
                or_(
                    ult.c.vale_almacen_id == almacen_id, ult.c.vale_destino_almacen_id == almacen_id
                ),
            ),
        )

    def _piezas(self, columna, almacen_id: uuid.UUID | None):
        """`select(columna)` de las piezas con su ubicación y su último movimiento."""
        u = aliased(Ubicacion, name="u_tab")
        ult = SeguimientoRepository._ultimos_movimientos(None)
        consulta = (
            select(columna)
            .select_from(Pieza)
            .join(Articulo, Articulo.id == Pieza.articulo_id)
            .join(u, u.id == Pieza.ubicacion_id)
            .outerjoin(ult, and_(ult.c.pieza_id == Pieza.id, ult.c.rn == 1))
        )
        if almacen_id is not None:
            consulta = consulta.where(self._en_alcance(u, ult, almacen_id))
        return consulta, u

    def resguardo_equipo_importante(self, almacen_id: uuid.UUID | None) -> int:
        """Piezas de artículos por pieza en poder de un trabajador (no de baja), entregadas
        desde un almacén del alcance."""
        consulta, u = self._piezas(func.count(Pieza.id), almacen_id)
        consulta = consulta.where(
            Articulo.control == Control.PIEZA,
            u.tipo == TipoUbicacion.TRABAJADOR,
            Pieza.estado != EstadoPieza.BAJA,
        )
        return int(self.session.scalar(consulta) or 0)

    def inspecciones_por_vencer(self, almacen_id: uuid.UUID | None, hoy: date, hasta: date) -> int:
        """Piezas aptas de artículos con inspección que vencen entre `hoy` y `hasta`."""
        consulta, _ = self._piezas(func.count(Pieza.id), almacen_id)
        consulta = consulta.where(
            Articulo.requiere_inspeccion.is_(True),
            Pieza.estado == EstadoPieza.APTO,
            Pieza.inspeccion_vigente_hasta >= hoy,
            Pieza.inspeccion_vigente_hasta <= hasta,
        )
        return int(self.session.scalar(consulta) or 0)

    def traspasos_en_transito(self, almacen_id: uuid.UUID | None) -> int:
        consulta = select(func.count(Vale.id)).where(
            Vale.tipo == TipoVale.TRASPASO,
            Vale.estado.in_([EstadoVale.EN_TRANSITO, EstadoVale.RECIBIDO_CON_DIFERENCIAS]),
        )
        if almacen_id is not None:
            consulta = consulta.where(
                or_(Vale.almacen_id == almacen_id, Vale.destino_almacen_id == almacen_id)
            )
        return int(self.session.scalar(consulta) or 0)

    def entregas(
        self, almacen_id: uuid.UUID | None, desde: datetime, hasta_excluyente: datetime
    ) -> int:
        """Vales de ENTREGA no cancelados creados en `[desde, hasta_excluyente)` (UTC)."""
        consulta = select(func.count(Vale.id)).where(
            Vale.tipo == TipoVale.ENTREGA,
            Vale.estado != EstadoVale.CANCELADO,
            Vale.creado_en >= desde,
            Vale.creado_en < hasta_excluyente,
        )
        if almacen_id is not None:
            consulta = consulta.where(Vale.almacen_id == almacen_id)
        return int(self.session.scalar(consulta) or 0)

    def solicitudes_abiertas(self, almacen_id: uuid.UUID | None) -> int:
        consulta = select(func.count(SolicitudCompra.id)).where(
            SolicitudCompra.estado.in_([EstadoSolicitud.PENDIENTE, EstadoSolicitud.EN_COMPRA])
        )
        if almacen_id is not None:
            consulta = consulta.where(SolicitudCompra.almacen_id == almacen_id)
        return int(self.session.scalar(consulta) or 0)

    # ------------------------------------------------------------------------- consumo

    def consumo(
        self,
        *,
        desde: datetime,
        hasta_excluyente: datetime,
        almacen_id: uuid.UUID | None,
        categoria_id: uuid.UUID | None,
    ) -> list:
        """Lo entregado por artículo y almacén, neto de cancelaciones (TB-02).

        Consumibles: la misma consulta de C-08 (movimientos a CONSUMIDO menos los que salen de
        CONSUMIDO, una cancelación se fecha con el vale que cancela). Retornables: unidades de
        los movimientos de vales de ENTREGA no cancelados que llegan a un trabajador.
        Devuelve `(articulo_id, articulo, unidad, categoria_id, categoria, almacen_id, almacen,
        cantidad)`, sin renglones en cero. Puede haber un artículo en las dos mitades solo si
        cambió de tipo; el servicio los suma.
        """
        return [
            *self._consumo_consumibles(desde, hasta_excluyente, almacen_id, categoria_id),
            *self._consumo_retornables(desde, hasta_excluyente, almacen_id, categoria_id),
        ]

    @staticmethod
    def _columnas_articulo():
        return (
            Articulo.id.label("articulo_id"),
            Articulo.nombre.label("articulo"),
            Articulo.unidad,
            Categoria.id.label("categoria_id"),
            Categoria.nombre.label("categoria"),
            Vale.almacen_id.label("almacen_id"),
            Almacen.nombre.label("almacen"),
        )

    def _consumo_consumibles(self, desde, hasta_excluyente, almacen_id, categoria_id) -> list:
        origen = aliased(Ubicacion, name="u_origen")
        destino = aliased(Ubicacion, name="u_destino")
        vale_cancelado = aliased(Vale, name="vale_cancelado")
        signo = case(
            (destino.virtual == UbicacionVirtual.CONSUMIDO, Movimiento.cantidad),
            else_=-Movimiento.cantidad,
        )
        fecha = case(
            (
                and_(Vale.tipo == TipoVale.CANCELACION, vale_cancelado.id.is_not(None)),
                vale_cancelado.creado_en,
            ),
            else_=Movimiento.creado_en,
        )
        neto = func.sum(signo)
        columnas = self._columnas_articulo()
        consulta = (
            select(*columnas, neto.label("cantidad"))
            .select_from(Movimiento)
            .join(Vale, Vale.id == Movimiento.vale_id)
            .outerjoin(vale_cancelado, vale_cancelado.id == Vale.vale_origen_id)
            .join(Articulo, Articulo.id == Movimiento.articulo_id)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .join(Almacen, Almacen.id == Vale.almacen_id)
            .join(origen, origen.id == Movimiento.origen_id)
            .join(destino, destino.id == Movimiento.destino_id)
            .where(
                or_(
                    destino.virtual == UbicacionVirtual.CONSUMIDO,
                    origen.virtual == UbicacionVirtual.CONSUMIDO,
                ),
                Articulo.retornable.is_(False),
                fecha >= desde,
                fecha < hasta_excluyente,
            )
        )
        if almacen_id is not None:
            consulta = consulta.where(Vale.almacen_id == almacen_id)
        if categoria_id is not None:
            consulta = consulta.where(Articulo.categoria_id == categoria_id)
        consulta = consulta.group_by(*columnas).having(neto != 0)
        return list(self.session.execute(consulta).all())

    def _consumo_retornables(self, desde, hasta_excluyente, almacen_id, categoria_id) -> list:
        destino = aliased(Ubicacion, name="u_destino_ret")
        total = func.sum(Movimiento.cantidad)
        columnas = self._columnas_articulo()
        consulta = (
            select(*columnas, total.label("cantidad"))
            .select_from(Movimiento)
            .join(Vale, Vale.id == Movimiento.vale_id)
            .join(Articulo, Articulo.id == Movimiento.articulo_id)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .join(Almacen, Almacen.id == Vale.almacen_id)
            .join(destino, destino.id == Movimiento.destino_id)
            .where(
                Vale.tipo == TipoVale.ENTREGA,
                Vale.estado != EstadoVale.CANCELADO,
                destino.tipo == TipoUbicacion.TRABAJADOR,
                Articulo.retornable.is_(True),
                Vale.creado_en >= desde,
                Vale.creado_en < hasta_excluyente,
            )
        )
        if almacen_id is not None:
            consulta = consulta.where(Vale.almacen_id == almacen_id)
        if categoria_id is not None:
            consulta = consulta.where(Articulo.categoria_id == categoria_id)
        consulta = consulta.group_by(*columnas).having(total != 0)
        return list(self.session.execute(consulta).all())
