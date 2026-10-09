"""Persistencia: add, flush y consultas; nunca commit."""

import uuid
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modulos.acceso.models import Usuario
from app.modulos.almacenes.models import Almacen
from app.modulos.autorizaciones.models import Autorizacion, EstadoAutorizacion
from app.modulos.trabajadores.models import Trabajador


class AutorizacionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, autorizacion: Autorizacion) -> Autorizacion:
        self.session.add(autorizacion)
        self.session.flush()
        return autorizacion

    def por_id_cliente(self, id_cliente):
        return self.session.scalar(
            select(Autorizacion).where(Autorizacion.id_cliente == id_cliente)
        )

    def es_epp(self, articulo_id):
        from app.modulos.catalogo.models import Articulo, Categoria

        return (
            self.session.scalar(
                select(Categoria.tipo)
                .join(Articulo, Articulo.categoria_id == Categoria.id)
                .where(Articulo.id == articulo_id)
            )
            == "EPP"
        )

    def contiene_epp(self, codigos):
        from app.modulos.catalogo.models import Articulo, Categoria, Codigo, Pieza

        return bool(
            self.session.scalar(
                select(func.count())
                .select_from(Codigo)
                .outerjoin(Pieza, (Codigo.ref_id == Pieza.id) & (Codigo.tipo == "PIEZA"))
                .join(Articulo, (Articulo.id == Codigo.ref_id) | (Articulo.id == Pieza.articulo_id))
                .join(Categoria, Categoria.id == Articulo.categoria_id)
                .where(Codigo.codigo.in_(codigos), Categoria.tipo == "EPP")
            )
        )

    def get(self, autorizacion_id: uuid.UUID, *, bloquear: bool = False) -> Autorizacion | None:
        """Con `bloquear` toma el renglón `FOR UPDATE`: dos resoluciones a la vez se serializan
        (y dos vales con la misma autorización: el segundo la ve ya USADA)."""
        consulta = select(Autorizacion).where(Autorizacion.id == autorizacion_id)
        if bloquear:
            consulta = consulta.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(consulta)

    def almacenes(self, ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Almacen]:
        ids = list(set(ids))
        if not ids:
            return {}
        return {a.id: a for a in self.session.scalars(select(Almacen).where(Almacen.id.in_(ids)))}

    def trabajador(self, trabajador_id: uuid.UUID) -> Trabajador | None:
        return self.session.get(Trabajador, trabajador_id)

    def usuario(self, usuario_id: uuid.UUID) -> Usuario | None:
        return self.session.get(Usuario, usuario_id)

    def usuario_por_nombre(self, nombre_usuario: str) -> Usuario | None:
        return self.session.scalar(select(Usuario).where(Usuario.usuario == nombre_usuario))

    def vencer_pendientes(
        self, ahora: datetime, almacen_id: uuid.UUID | set[uuid.UUID] | None
    ) -> None:
        """PENDIENTE -> VENCIDA para las que ya pasaron su `vence_en` (en un almacén o en todos)."""
        sentencia = (
            update(Autorizacion)
            .where(
                Autorizacion.estado == EstadoAutorizacion.PENDIENTE,
                Autorizacion.vence_en <= ahora,
            )
            .values(estado=EstadoAutorizacion.VENCIDA)
        )
        if almacen_id is not None:
            sentencia = sentencia.where(
                Autorizacion.almacen_id.in_(almacen_id)
                if isinstance(almacen_id, set)
                else Autorizacion.almacen_id == almacen_id
            )
        self.session.execute(sentencia)
        self.session.flush()
        self.session.expire_all()

    def listar(
        self,
        *,
        estado: str | None,
        almacen_id: uuid.UUID | set[uuid.UUID] | None,
        offset: int,
        limit: int,
        tipo: str | None = None,
    ) -> tuple[list[tuple[Autorizacion, Trabajador | None, Usuario]], int]:
        filtros = []
        if estado is not None:
            filtros.append(Autorizacion.estado == estado)
        if tipo is not None:
            filtros.append(Autorizacion.tipo == tipo)
        if almacen_id is not None:
            filtros.append(
                Autorizacion.almacen_id.in_(almacen_id)
                if isinstance(almacen_id, set)
                else Autorizacion.almacen_id == almacen_id
            )
        total = self.session.scalar(select(func.count()).select_from(Autorizacion).where(*filtros))
        filas = self.session.execute(
            select(Autorizacion, Trabajador, Usuario)
            .outerjoin(Trabajador, Trabajador.id == Autorizacion.trabajador_id)
            .join(Usuario, Usuario.id == Autorizacion.solicitada_por)
            .where(*filtros)
            .order_by(Autorizacion.creado_en, Autorizacion.id)
            .offset(offset)
            .limit(limit)
        ).all()
        return [(a, t, u) for a, t, u in filas], total or 0
