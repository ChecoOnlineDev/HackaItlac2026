"""Persistencia de `solicitudes_compra`: add, flush y consultas; nunca commit.

Solo LEE el vale de ENTRADA (`movimientos` es su dueño): aquí no se escribe inventario.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, func, or_, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.modulos.acceso.models import Usuario
from app.modulos.almacenes.models import Almacen
from app.modulos.catalogo.models import Articulo
from app.modulos.movimientos.models import Vale
from app.modulos.solicitudes_compra.models import (
    EstadoSolicitud,
    SerieSolicitudCompra,
    SolicitudCompra,
    SolicitudCompraEvento,
    Urgencia,
)

E = EstadoSolicitud


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass(frozen=True)
class ConsultaSolicitudes:
    """Qué listar. `almacen_alcance` es el límite del usuario (`None`: todos los almacenes);
    `almacen_id` es el filtro que él pidió."""

    almacen_alcance: uuid.UUID | None = None
    almacen_id: uuid.UUID | None = None
    estado: str | None = None
    urgencia: str | None = None
    q: str | None = None
    desde: datetime | None = None
    hasta: datetime | None = None
    solicitante_id: uuid.UUID | None = None


# Fila de una lista: la solicitud con todo lo que la acompaña.
Fila = tuple[SolicitudCompra, Almacen, Usuario, Articulo | None, Vale | None]


class SolicitudCompraRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------ escritura

    def add(self, solicitud: SolicitudCompra) -> SolicitudCompra:
        self.session.add(solicitud)
        self.session.flush()
        return solicitud

    def add_evento(self, evento: SolicitudCompraEvento) -> SolicitudCompraEvento:
        self.session.add(evento)
        self.session.flush()
        return evento

    def bloquear_serie(self, almacen_id: uuid.UUID) -> SerieSolicitudCompra:
        """Fila del contador de folios del almacén, bloqueada (se crea en cero la primera vez)."""
        tabla = SerieSolicitudCompra.__table__
        sentencia = mysql_insert(tabla).values(almacen_id=almacen_id, ultimo=0)
        self.session.execute(sentencia.on_duplicate_key_update(ultimo=tabla.c.ultimo))
        self.session.flush()
        serie = self.session.scalar(
            select(SerieSolicitudCompra)
            .where(SerieSolicitudCompra.almacen_id == almacen_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        assert serie is not None
        return serie

    # ------------------------------------------------------------------- lectura

    def get(self, solicitud_id: uuid.UUID, *, bloquear: bool = False) -> SolicitudCompra | None:
        """Con `bloquear` toma el renglón `FOR UPDATE`: dos cambios a la vez se serializan."""
        consulta = select(SolicitudCompra).where(SolicitudCompra.id == solicitud_id)
        if bloquear:
            consulta = consulta.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(consulta)

    def get_por_id_cliente(self, id_cliente: uuid.UUID) -> SolicitudCompra | None:
        return self.session.scalar(
            select(SolicitudCompra).where(SolicitudCompra.id_cliente == id_cliente)
        )

    def almacen(self, almacen_id: uuid.UUID) -> Almacen:
        almacen = self.session.get(Almacen, almacen_id)
        assert almacen is not None
        return almacen

    def usuario(self, usuario_id: uuid.UUID) -> Usuario:
        usuario = self.session.get(Usuario, usuario_id)
        assert usuario is not None
        return usuario

    def articulo(self, articulo_id: uuid.UUID | None) -> Articulo | None:
        return self.session.get(Articulo, articulo_id) if articulo_id else None

    def vale(self, vale_id: uuid.UUID | None) -> Vale | None:
        return self.session.get(Vale, vale_id) if vale_id else None

    def eventos(self, solicitud_id: uuid.UUID) -> list[tuple[SolicitudCompraEvento, Usuario]]:
        filas = self.session.execute(
            select(SolicitudCompraEvento, Usuario)
            .join(Usuario, Usuario.id == SolicitudCompraEvento.usuario_id)
            .where(SolicitudCompraEvento.solicitud_id == solicitud_id)
            .order_by(SolicitudCompraEvento.creado_en, SolicitudCompraEvento.id)
        ).all()
        return [(e, u) for e, u in filas]

    # --------------------------------------------------------------------- listas

    def _filtros(self, c: ConsultaSolicitudes) -> list:
        filtros = []
        if c.almacen_alcance is not None:
            filtros.append(SolicitudCompra.almacen_id == c.almacen_alcance)
        if c.almacen_id is not None:
            filtros.append(SolicitudCompra.almacen_id == c.almacen_id)
        if c.estado is not None:
            filtros.append(SolicitudCompra.estado == c.estado)
        if c.urgencia is not None:
            filtros.append(SolicitudCompra.urgencia == c.urgencia)
        if c.solicitante_id is not None:
            filtros.append(SolicitudCompra.solicitante_id == c.solicitante_id)
        if c.desde is not None:
            filtros.append(SolicitudCompra.creada_en >= c.desde)
        if c.hasta is not None:
            filtros.append(SolicitudCompra.creada_en < c.hasta)
        if c.q:
            patron = f"%{_escapar_like(c.q)}%"
            filtros.append(
                or_(
                    SolicitudCompra.folio.like(patron, escape="\\"),
                    SolicitudCompra.descripcion.like(patron, escape="\\"),
                    SolicitudCompra.motivo.like(patron, escape="\\"),
                    Articulo.nombre.like(patron, escape="\\"),
                    Articulo.codigo.like(patron, escape="\\"),
                )
            )
        return filtros

    def _base(self, *columnas):
        return (
            select(*columnas)
            .select_from(SolicitudCompra)
            .join(Almacen, Almacen.id == SolicitudCompra.almacen_id)
            .join(Usuario, Usuario.id == SolicitudCompra.solicitante_id)
            .outerjoin(Articulo, Articulo.id == SolicitudCompra.articulo_id)
            .outerjoin(Vale, Vale.id == SolicitudCompra.vale_entrada_id)
        )

    def contar(self, consulta: ConsultaSolicitudes) -> int:
        total = self.session.scalar(
            self._base(func.count(SolicitudCompra.id)).where(*self._filtros(consulta))
        )
        return total or 0

    def listar(self, consulta: ConsultaSolicitudes, *, offset: int, limit: int) -> list[Fila]:
        """Orden (SC-03): primero lo que espera a Compras (PENDIENTE), luego EN_COMPRA, luego
        COMPRADA y al final lo cerrado; en cada grupo, las urgentes primero y las más antiguas
        primero. Lo cerrado va de la más reciente a la más antigua."""
        rango_estado = case(
            (SolicitudCompra.estado == E.PENDIENTE, 0),
            (SolicitudCompra.estado == E.EN_COMPRA, 1),
            (SolicitudCompra.estado == E.COMPRADA, 2),
            else_=3,
        )
        abierta = rango_estado < 3
        rango_urgencia = case((SolicitudCompra.urgencia == Urgencia.URGENTE, 0), else_=1)
        filas = self.session.execute(
            self._base(SolicitudCompra, Almacen, Usuario, Articulo, Vale)
            .where(*self._filtros(consulta))
            .order_by(
                rango_estado,
                case((abierta, rango_urgencia), else_=0),
                case((abierta, SolicitudCompra.creada_en), else_=None),
                SolicitudCompra.creada_en.desc(),
                SolicitudCompra.id,
            )
            .offset(offset)
            .limit(limit)
        ).all()
        return [tuple(f) for f in filas]  # type: ignore[misc]
