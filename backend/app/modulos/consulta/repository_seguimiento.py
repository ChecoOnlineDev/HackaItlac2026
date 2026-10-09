"""Consulta de SOLO LECTURA del seguimiento de piezas (C-13): nunca `add`, `flush` ni `commit`.

Una sola consulta por lista: la pieza con su artículo, su ubicación actual (con el almacén o el
trabajador) y el último movimiento que la dejó ahí (con su vale), unido por una tabla derivada
con `row_number()`. No hay una consulta por pieza.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.modulos.almacenes.models import Almacen, TipoUbicacion, Ubicacion, UbicacionVirtual
from app.modulos.catalogo.alto_valor import expresion_alto_valor, expresion_vigilancia
from app.modulos.catalogo.models import Articulo, Categoria, EstadoPieza, Pieza
from app.modulos.consulta.repository import ConsultaRepository, Lugar, _patron
from app.modulos.movimientos.models import Movimiento, TipoVale, Vale

MAXIMO_PALABRAS = 6


@dataclass(frozen=True)
class FiltroSeguimiento:
    """Lo que filtra el listado. `visibles` limita al alcance de quien no tiene `almacenes.todos`
    (AC-06): `(almacen_id del usuario, puede ver trabajadores)`; `None` = sin límite."""

    palabras: tuple[str, ...] = ()
    articulo_id: uuid.UUID | None = None
    almacen_id: uuid.UUID | None = None
    estado: str | None = None
    ubicacion: str | None = None
    serie_pendiente: bool | None = None
    # SG-04: `True` deja solo las piezas de las categorías de alto valor.
    alto_valor: bool | None = None
    visibles: tuple[uuid.UUID | None, bool] | None = field(default=None)


class SeguimientoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _ultimos_movimientos(articulo_id: uuid.UUID | None):
        """Por pieza, el movimiento que la dejó en su ubicación actual. Con un trabajador se
        prefiere el de un vale de ENTREGA: una cancelación que le regresa el equipo no cambia
        desde cuándo lo tiene (igual que el reporte de adeudos)."""
        destino = aliased(Ubicacion, name="u_ult")
        orden = func.row_number().over(
            partition_by=Movimiento.pieza_id,
            order_by=(
                case(
                    (
                        and_(
                            destino.tipo == TipoUbicacion.TRABAJADOR, Vale.tipo == TipoVale.ENTREGA
                        ),
                        0,
                    ),
                    else_=1,
                ),
                Movimiento.creado_en.desc(),
                Movimiento.id.desc(),
            ),
        )
        consulta = (
            select(
                Movimiento.pieza_id.label("pieza_id"),
                Movimiento.creado_en.label("desde"),
                Vale.id.label("vale_id"),
                Vale.folio.label("folio"),
                Vale.almacen_id.label("vale_almacen_id"),
                Vale.destino_almacen_id.label("vale_destino_almacen_id"),
                orden.label("rn"),
            )
            .select_from(Movimiento)
            .join(
                Pieza,
                and_(Pieza.id == Movimiento.pieza_id, Pieza.ubicacion_id == Movimiento.destino_id),
            )
            .join(Vale, Vale.id == Movimiento.vale_id)
            .join(destino, destino.id == Movimiento.destino_id)
        )
        if articulo_id is not None:
            consulta = consulta.where(Pieza.articulo_id == articulo_id)
        return consulta.subquery("ult")

    def _base(self, columnas, filtro: FiltroSeguimiento, *, con_estado_y_ubicacion: bool):
        """`select(*columnas)` con los joins y los filtros. Devuelve `(consulta, lugar, ult,
        destino_traspaso)` para armar columnas y orden."""
        lugar = Lugar("ub")
        ult = self._ultimos_movimientos(filtro.articulo_id)
        destino_traspaso = aliased(Almacen, name="a_trs")
        consulta = (
            select(*columnas(lugar, ult, destino_traspaso))
            .select_from(Pieza)
            .join(Articulo, Articulo.id == Pieza.articulo_id)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
        )
        consulta = lugar.unir(consulta, Pieza.ubicacion_id, externa=True)
        consulta = consulta.outerjoin(
            ult, and_(ult.c.pieza_id == Pieza.id, ult.c.rn == 1)
        ).outerjoin(destino_traspaso, destino_traspaso.id == ult.c.vale_destino_almacen_id)
        u = lugar.u

        if filtro.visibles is not None:  # AC-06
            almacen_usuario, ver_trabajadores = filtro.visibles
            consulta = consulta.where(
                ConsultaRepository._pieza_visible(u, almacen_usuario, ver_trabajadores)
            )
        if filtro.articulo_id is not None:
            consulta = consulta.where(Pieza.articulo_id == filtro.articulo_id)
        if filtro.alto_valor:
            consulta = consulta.where(expresion_vigilancia())
        if filtro.serie_pendiente is not None:
            consulta = consulta.where(
                Pieza.numero_serie.is_(None)
                if filtro.serie_pendiente
                else Pieza.numero_serie.is_not(None)
            )
        for palabra in filtro.palabras:
            patron = _patron(palabra)
            consulta = consulta.where(
                or_(
                    Articulo.nombre.like(patron, escape="\\"),
                    Articulo.codigo.like(patron, escape="\\"),
                    Pieza.numero_serie.like(patron, escape="\\"),
                    Pieza.codigo.like(patron, escape="\\"),
                    lugar.t.nombre.like(patron, escape="\\"),
                    lugar.t.numero_empleado.like(patron, escape="\\"),
                )
            )
        if filtro.almacen_id is not None:
            x = filtro.almacen_id
            consulta = consulta.where(
                or_(
                    and_(u.tipo == TipoUbicacion.ALMACEN, u.almacen_id == x),
                    and_(u.tipo == TipoUbicacion.TRABAJADOR, ult.c.vale_almacen_id == x),
                    and_(
                        u.tipo == TipoUbicacion.VIRTUAL,
                        or_(ult.c.vale_almacen_id == x, ult.c.vale_destino_almacen_id == x),
                    ),
                )
            )
        if con_estado_y_ubicacion:
            if filtro.estado is not None:
                consulta = consulta.where(Pieza.estado == filtro.estado)
            if filtro.ubicacion is not None:
                consulta = consulta.where(self._condicion_ubicacion(u, filtro.ubicacion))
        return consulta, lugar, ult, destino_traspaso

    @staticmethod
    def _condicion_ubicacion(u, ubicacion: str):
        if ubicacion == "ALMACEN":
            return u.tipo == TipoUbicacion.ALMACEN
        if ubicacion == "TRABAJADOR":
            return u.tipo == TipoUbicacion.TRABAJADOR
        if ubicacion == "TRANSITO":
            return and_(u.tipo == TipoUbicacion.VIRTUAL, u.virtual == UbicacionVirtual.EN_TRANSITO)
        if ubicacion == "BAJA":
            return and_(u.tipo == TipoUbicacion.VIRTUAL, u.virtual == UbicacionVirtual.BAJA)
        if ubicacion == "OTRA":
            return and_(
                u.tipo == TipoUbicacion.VIRTUAL,
                u.virtual.not_in([UbicacionVirtual.EN_TRANSITO, UbicacionVirtual.BAJA]),
            )
        return u.id.is_(None)  # NINGUNA

    def trabajador_de_ubicacion(self, ubicacion_id: uuid.UUID | None) -> uuid.UUID | None:
        """El trabajador dueño de una ubicación (`None` si es de un almacén o virtual)."""
        if ubicacion_id is None:
            return None
        return self.session.scalar(
            select(Ubicacion.trabajador_id).where(
                Ubicacion.id == ubicacion_id, Ubicacion.tipo == TipoUbicacion.TRABAJADOR
            )
        )

    def piezas(
        self, filtro: FiltroSeguimiento, offset: int | None, limit: int | None
    ) -> tuple[list, int]:
        """Las filas del listado (ordenadas por artículo y código) y cuántas hay en total."""

        def columnas(lugar: Lugar, ult, destino_traspaso):
            return (
                Pieza.id,
                Pieza.codigo,
                Pieza.numero_serie,
                Pieza.estado,
                Pieza.inspeccion_vigente_hasta,
                Articulo.id.label("articulo_id"),
                Articulo.codigo.label("articulo_codigo"),
                Articulo.nombre.label("articulo_nombre"),
                Articulo.marca.label("articulo_marca"),
                Categoria.nombre.label("categoria_nombre"),
                func.coalesce(expresion_alto_valor(), False).label("alto_valor"),
                Articulo.requiere_inspeccion,
                *lugar.columnas(),
                ult.c.desde,
                ult.c.vale_id,
                ult.c.folio,
                ult.c.vale_almacen_id,
                ult.c.vale_destino_almacen_id,
                destino_traspaso.clave.label("trs_clave"),
                destino_traspaso.nombre.label("trs_nombre"),
            )

        consulta, _, _, _ = self._base(columnas, filtro, con_estado_y_ubicacion=True)
        cuenta, _, _, _ = self._base(
            lambda *_: (func.count(Pieza.id),), filtro, con_estado_y_ubicacion=True
        )
        total = int(self.session.scalar(cuenta) or 0)
        consulta = consulta.order_by(Articulo.nombre, Articulo.codigo, Pieza.codigo, Pieza.id)
        if offset is not None and limit is not None:
            consulta = consulta.offset(offset).limit(limit)
        return list(self.session.execute(consulta).all()), total

    def resumen(self, filtro: FiltroSeguimiento) -> dict[str, int]:
        """Conteos sin aplicar `estado` ni `ubicacion` (las tarjetas cambian entre ellos)."""

        def columnas(lugar: Lugar, ult, destino_traspaso):
            u = lugar.u

            def cuenta(condicion):
                return func.coalesce(func.sum(case((condicion, 1), else_=0)), 0)

            return (
                func.count(Pieza.id),
                cuenta(u.tipo == TipoUbicacion.ALMACEN),
                cuenta(u.tipo == TipoUbicacion.TRABAJADOR),
                cuenta(self._condicion_ubicacion(u, "TRANSITO")),
                cuenta(Pieza.estado == EstadoPieza.NO_APTO),
            )

        consulta, _, _, _ = self._base(columnas, filtro, con_estado_y_ubicacion=False)
        fila = self.session.execute(consulta).one()
        total, almacen, resguardo, transito, no_aptas = (int(v or 0) for v in fila)
        return {
            "total": total,
            "en_almacen": almacen,
            "en_resguardo": resguardo,
            "en_transito": transito,
            "no_aptas": no_aptas,
        }
