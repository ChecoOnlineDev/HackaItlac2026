"""Persistencia: add, flush y consultas; nunca commit.

Es el único lugar que escribe `vale`, `movimiento`, `existencia` y `serie_folio`, y la ubicación de
las piezas (`pieza.ubicacion_id`). Las consultas sobre tablas de otros módulos (pieza, ubicación,
trabajador, usuario, periodo) son de solo lectura, salvo el bloqueo `FOR UPDATE` de filas que la
confirmación necesita (no cambia datos).

Bloqueos de la confirmación, en este orden canónico (así dos confirmaciones nunca se
interbloquean): vales, trabajador, existencias por `(ubicacion_id, articulo_id)`, piezas por `id`
y, al final, `serie_folio`.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.modulos.acceso.models import Usuario
from app.modulos.almacenes.models import Almacen, Ubicacion
from app.modulos.catalogo.models import Articulo, EstadoPieza, Pieza
from app.modulos.movimientos.models import (
    Existencia,
    Movimiento,
    SerieFolio,
    TipoVale,
    Vale,
)
from app.modulos.trabajadores.models import PeriodoContrato, Trabajador

Clave = tuple[uuid.UUID, uuid.UUID]  # (ubicacion_id, articulo_id)


@dataclass(frozen=True)
class FiltroVales:
    tipo: str | None = None
    almacen_id: uuid.UUID | None = None
    desde: datetime | None = None  # UTC, inclusive
    hasta: datetime | None = None  # UTC, exclusivo
    trabajador_id: uuid.UUID | None = None
    usuario_id: uuid.UUID | None = None
    offset: int = 0
    limit: int = 50


class MovimientoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------------ vales

    def vale(self, vale_id: uuid.UUID) -> Vale | None:
        return self.session.get(Vale, vale_id)

    def vale_por_id_cliente(self, id_cliente: uuid.UUID) -> Vale | None:
        return self.session.scalar(select(Vale).where(Vale.id_cliente == id_cliente))

    def vale_por_token(self, token: str) -> Vale | None:
        return self.session.scalar(select(Vale).where(Vale.token == token))

    def add_vale(self, vale: Vale) -> Vale:
        self.session.add(vale)
        self.session.flush()
        return vale

    def add_movimiento(self, movimiento: Movimiento) -> Movimiento:
        self.session.add(movimiento)
        self.session.flush()
        return movimiento

    def renglones_de(self, vale_id: uuid.UUID) -> list[tuple[Movimiento, Articulo, Pieza | None]]:
        filas = self.session.execute(
            select(Movimiento, Articulo, Pieza)
            .join(Articulo, Articulo.id == Movimiento.articulo_id)
            .outerjoin(Pieza, Pieza.id == Movimiento.pieza_id)
            .where(Movimiento.vale_id == vale_id)
            .order_by(Movimiento.renglon)
        ).all()
        return [(m, a, p) for m, a, p in filas]

    def listar(
        self, filtro: FiltroVales
    ) -> tuple[list[tuple[Vale, Almacen, Trabajador | None, Usuario, int]], int]:
        condiciones = []
        if filtro.tipo is not None:
            condiciones.append(Vale.tipo == filtro.tipo)
        if filtro.almacen_id is not None:
            condiciones.append(Vale.almacen_id == filtro.almacen_id)
        if filtro.desde is not None:
            condiciones.append(Vale.creado_en >= filtro.desde)
        if filtro.hasta is not None:
            condiciones.append(Vale.creado_en < filtro.hasta)
        if filtro.trabajador_id is not None:
            condiciones.append(Vale.trabajador_id == filtro.trabajador_id)
        if filtro.usuario_id is not None:
            condiciones.append(Vale.responsable_id == filtro.usuario_id)
        total = self.session.scalar(select(func.count()).select_from(Vale).where(*condiciones))
        renglones = (
            select(func.count(Movimiento.id))
            .where(Movimiento.vale_id == Vale.id)
            .correlate(Vale)
            .scalar_subquery()
        )
        filas = self.session.execute(
            select(Vale, Almacen, Trabajador, Usuario, renglones)
            .join(Almacen, Almacen.id == Vale.almacen_id)
            .outerjoin(Trabajador, Trabajador.id == Vale.trabajador_id)
            .join(Usuario, Usuario.id == Vale.responsable_id)
            .where(*condiciones)
            .order_by(Vale.creado_en.desc(), Vale.id.desc())
            .offset(filtro.offset)
            .limit(filtro.limit)
        ).all()
        return [(v, a, t, u, int(n or 0)) for v, a, t, u, n in filas], int(total or 0)

    # ------------------------------------------------------- lectura de hechos (sin bloqueo)

    def existencia(self, ubicacion_id: uuid.UUID, articulo_id: uuid.UUID) -> int:
        cantidad = self.session.scalar(
            select(Existencia.cantidad).where(
                Existencia.ubicacion_id == ubicacion_id, Existencia.articulo_id == articulo_id
            )
        )
        return int(cantidad or 0)

    def piezas_aptas_en(self, ubicacion_id: uuid.UUID, articulo_id: uuid.UUID) -> int:
        """Disponible de un artículo por pieza: solo cuentan las Aptas de esa ubicación (I-05)."""
        total = self.session.scalar(
            select(func.count(Pieza.id)).where(
                Pieza.ubicacion_id == ubicacion_id,
                Pieza.articulo_id == articulo_id,
                Pieza.estado == EstadoPieza.APTO,
            )
        )
        return int(total or 0)

    def consumido_desde(
        self,
        trabajador_id: uuid.UUID,
        articulo_id: uuid.UUID,
        consumido_id: uuid.UUID,
        desde: datetime,
    ) -> int:
        """L-03: lo entregado como consumible al trabajador después de `desde` (UTC, exclusivo:
        una entrega hecha hace exactamente N días ya no cuenta). No cuenta vales cancelados."""
        total = self.session.scalar(
            select(func.coalesce(func.sum(Movimiento.cantidad), 0))
            .join(Vale, Vale.id == Movimiento.vale_id)
            .where(
                Vale.tipo == TipoVale.ENTREGA,
                Vale.estado != "CANCELADO",
                Movimiento.trabajador_id == trabajador_id,
                Movimiento.articulo_id == articulo_id,
                Movimiento.destino_id == consumido_id,
                Movimiento.creado_en > desde,
            )
        )
        return int(total or 0)

    def pieza_por_serie(self, articulo_id: uuid.UUID, numero_serie: str) -> Pieza | None:
        """Solo lectura: I-02, la serie no se repite dentro de un artículo."""
        return self.session.scalar(
            select(Pieza).where(
                Pieza.articulo_id == articulo_id, Pieza.numero_serie == numero_serie
            )
        )

    def ubicacion(self, ubicacion_id: uuid.UUID) -> Ubicacion | None:
        return self.session.get(Ubicacion, ubicacion_id)

    def ubicaciones(
        self, ids: Iterable[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[Ubicacion, str, str | None]]:
        """`{id: (ubicación, nombre, clave)}`; el nombre es el del almacén o trabajador, o la
        ubicación virtual."""
        ids = list(set(ids))
        if not ids:
            return {}
        filas = self.session.execute(
            select(Ubicacion, Almacen, Trabajador)
            .outerjoin(Almacen, Almacen.id == Ubicacion.almacen_id)
            .outerjoin(Trabajador, Trabajador.id == Ubicacion.trabajador_id)
            .where(Ubicacion.id.in_(ids))
        ).all()
        salida = {}
        for ub, almacen, trabajador in filas:
            if almacen is not None:
                salida[ub.id] = (ub, almacen.nombre, almacen.clave)
            elif trabajador is not None:
                salida[ub.id] = (ub, trabajador.nombre, trabajador.numero_empleado)
            else:
                salida[ub.id] = (ub, ub.virtual or "", None)
        return salida

    def periodo(self, periodo_id: uuid.UUID) -> PeriodoContrato | None:
        return self.session.get(PeriodoContrato, periodo_id)

    def usuario(self, usuario_id: uuid.UUID) -> Usuario | None:
        return self.session.get(Usuario, usuario_id)

    # ------------------------------------------------------------------------ bloqueos

    def bloquear_vales(self, ids: Iterable[uuid.UUID]) -> None:
        for vale_id in sorted(set(ids)):
            self.session.execute(select(Vale.id).where(Vale.id == vale_id).with_for_update())

    def bloquear_trabajador(self, trabajador_id: uuid.UUID) -> None:
        """Serializa las confirmaciones de un mismo trabajador (límites y autorización)."""
        self.session.execute(
            select(Trabajador.id).where(Trabajador.id == trabajador_id).with_for_update()
        )

    def bloquear_existencias(self, claves: Iterable[Clave]) -> None:
        """Toma `FOR UPDATE` cada existencia en orden; las que no existen se crean en cero.

        `INSERT ... ON DUPLICATE KEY UPDATE cantidad = cantidad` toma el bloqueo exclusivo de la
        fila sin la carrera de dos inserciones simultáneas.
        """
        tabla = Existencia.__table__
        for ubicacion_id, articulo_id in sorted(set(claves), key=lambda c: (str(c[0]), str(c[1]))):
            sentencia = mysql_insert(tabla).values(
                ubicacion_id=ubicacion_id, articulo_id=articulo_id, cantidad=0
            )
            self.session.execute(sentencia.on_duplicate_key_update(cantidad=tabla.c.cantidad))
        self.session.flush()

    def existencias_bloqueadas(self, claves: Iterable[Clave]) -> dict[Clave, Existencia]:
        """Las filas de existencia ya bloqueadas, para actualizarlas con el saldo nuevo."""
        resultado: dict[Clave, Existencia] = {}
        for clave in sorted(set(claves), key=lambda c: (str(c[0]), str(c[1]))):
            fila = self.session.scalar(
                select(Existencia)
                .where(Existencia.ubicacion_id == clave[0], Existencia.articulo_id == clave[1])
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if fila is not None:
                resultado[clave] = fila
        return resultado

    def bloquear_piezas(self, ids: Iterable[uuid.UUID]) -> None:
        for pieza_id in sorted(set(ids), key=str):
            self.session.execute(select(Pieza.id).where(Pieza.id == pieza_id).with_for_update())

    def pieza_bloqueada(self, pieza_id: uuid.UUID) -> Pieza | None:
        return self.session.scalar(
            select(Pieza)
            .where(Pieza.id == pieza_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def bloquear_serie(self, almacen_id: uuid.UUID, tipo: str) -> SerieFolio:
        """Fila del contador de folios, bloqueada (se crea en cero la primera vez)."""
        tabla = SerieFolio.__table__
        sentencia = mysql_insert(tabla).values(almacen_id=almacen_id, tipo=tipo, ultimo=0)
        self.session.execute(sentencia.on_duplicate_key_update(ultimo=tabla.c.ultimo))
        self.session.flush()
        serie = self.session.scalar(
            select(SerieFolio)
            .where(SerieFolio.almacen_id == almacen_id, SerieFolio.tipo == tipo)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        assert serie is not None
        return serie
