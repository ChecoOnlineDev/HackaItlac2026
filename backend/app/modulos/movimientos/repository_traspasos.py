"""Consultas de los traspasos (solo lectura): lo enviado y lo ya recibido de cada traspaso.

Un traspaso (vale TRASPASO) manda renglones a EN_TRANSITO; cada recepción (vale RECEPCION con
`vale_origen_id` = el traspaso) saca de EN_TRANSITO lo que llegó. Lo pendiente de un renglón es lo
enviado menos lo recibido. Nunca escribe ni hace commit: los bloqueos y las inserciones son del
repository del motor.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modulos.acceso.models import Usuario
from app.modulos.almacenes.models import Almacen
from app.modulos.catalogo.models import Articulo, Pieza
from app.modulos.movimientos.models import EstadoVale, Movimiento, TipoVale, Vale

# Estados de un traspaso al que todavía le falta recibirse algo.
ESTADOS_POR_RECIBIR = (EstadoVale.EN_TRANSITO, EstadoVale.RECIBIDO_CON_DIFERENCIAS)

Clave = tuple[uuid.UUID, uuid.UUID | None]  # (articulo_id, pieza_id)


@dataclass
class LineaTraspaso:
    """Un renglón del traspaso con lo enviado y lo recibido hasta ahora."""

    renglon: int
    articulo: Articulo
    pieza: Pieza | None
    enviada: int
    recibida: int = 0

    @property
    def pendiente(self) -> int:
        return max(self.enviada - self.recibida, 0)

    @property
    def clave(self) -> Clave:
        return (self.articulo.id, self.pieza.id if self.pieza else None)


class TraspasoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def vale(self, vale_id: uuid.UUID) -> Vale | None:
        return self.session.get(Vale, vale_id)

    def almacen(self, almacen_id: uuid.UUID) -> Almacen | None:
        return self.session.get(Almacen, almacen_id)

    # ---------------------------------------------------------------- un traspaso

    def lineas(self, traspaso_id: uuid.UUID) -> list[LineaTraspaso]:
        """Los renglones de un traspaso con lo ya recibido. Los artículos por cantidad que se
        repiten se suman en un solo renglón."""
        return self.lineas_de([traspaso_id])[traspaso_id]

    def lineas_de(self, traspaso_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, list[LineaTraspaso]]:
        ids = list(set(traspaso_ids))
        salida: dict[uuid.UUID, list[LineaTraspaso]] = {i: [] for i in ids}
        if not ids:
            return salida
        enviadas = self.session.execute(
            select(Movimiento, Articulo, Pieza)
            .join(Articulo, Articulo.id == Movimiento.articulo_id)
            .outerjoin(Pieza, Pieza.id == Movimiento.pieza_id)
            .where(Movimiento.vale_id.in_(ids))
            .order_by(Movimiento.vale_id, Movimiento.renglon)
        ).all()
        por_clave: dict[tuple[uuid.UUID, Clave], LineaTraspaso] = {}
        for movimiento, articulo, pieza in enviadas:
            clave = (movimiento.vale_id, (articulo.id, pieza.id if pieza else None))
            linea = por_clave.get(clave)
            if linea is None:
                linea = LineaTraspaso(movimiento.renglon, articulo, pieza, movimiento.cantidad)
                por_clave[clave] = linea
                salida[movimiento.vale_id].append(linea)
            else:
                linea.enviada += movimiento.cantidad
        for (vale_id, clave), cantidad in self.recibido_por_clave(ids).items():
            linea = por_clave.get((vale_id, clave))
            if linea is not None:
                linea.recibida = cantidad
        return salida

    def recibido_por_clave(
        self, traspaso_ids: Iterable[uuid.UUID]
    ) -> dict[tuple[uuid.UUID, Clave], int]:
        """`{(traspaso, (articulo, pieza)): cantidad}` recibida en las recepciones del traspaso.
        Una recepción no se cancela (K-04), así que todas cuentan."""
        ids = list(set(traspaso_ids))
        if not ids:
            return {}
        filas = self.session.execute(
            select(
                Vale.vale_origen_id,
                Movimiento.articulo_id,
                Movimiento.pieza_id,
                func.sum(Movimiento.cantidad),
            )
            .join(Vale, Vale.id == Movimiento.vale_id)
            .where(Vale.tipo == TipoVale.RECEPCION, Vale.vale_origen_id.in_(ids))
            .group_by(Vale.vale_origen_id, Movimiento.articulo_id, Movimiento.pieza_id)
        ).all()
        return {(v, (a, p)): int(total) for v, a, p, total in filas}

    def pendiente_total(self, traspaso_id: uuid.UUID) -> int:
        return sum(linea.pendiente for linea in self.lineas(traspaso_id))

    # ------------------------------------------------------------ lista por recibir

    def por_recibir(self, destino_id: uuid.UUID | None) -> list[Vale]:
        """Traspasos con algo En tránsito hacia `destino_id` (o hacia cualquiera si es `None`),
        del más antiguo al más nuevo: primero lo que lleva más tiempo en camino."""
        consulta = (
            select(Vale)
            .where(Vale.tipo == TipoVale.TRASPASO, Vale.estado.in_(ESTADOS_POR_RECIBIR))
            .order_by(Vale.creado_en, Vale.id)
        )
        if destino_id is not None:
            consulta = consulta.where(Vale.destino_almacen_id == destino_id)
        return list(self.session.scalars(consulta))

    def contar_por_recibir(self, destino_id: uuid.UUID | None) -> int:
        consulta = (
            select(func.count())
            .select_from(Vale)
            .where(Vale.tipo == TipoVale.TRASPASO, Vale.estado.in_(ESTADOS_POR_RECIBIR))
        )
        if destino_id is not None:
            consulta = consulta.where(Vale.destino_almacen_id == destino_id)
        return int(self.session.scalar(consulta) or 0)

    def almacenes(self, ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Almacen]:
        ids = list(set(ids))
        if not ids:
            return {}
        return {a.id: a for a in self.session.scalars(select(Almacen).where(Almacen.id.in_(ids)))}

    def usuarios(self, ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Usuario]:
        ids = list(set(ids))
        if not ids:
            return {}
        return {u.id: u for u in self.session.scalars(select(Usuario).where(Usuario.id.in_(ids)))}

    def recepciones_de(self, traspaso_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, list[Vale]]:
        ids = list(set(traspaso_ids))
        salida: dict[uuid.UUID, list[Vale]] = {i: [] for i in ids}
        if not ids:
            return salida
        for vale in self.session.scalars(
            select(Vale)
            .where(Vale.tipo == TipoVale.RECEPCION, Vale.vale_origen_id.in_(ids))
            .order_by(Vale.creado_en, Vale.id)
        ):
            salida[vale.vale_origen_id].append(vale)
        return salida
