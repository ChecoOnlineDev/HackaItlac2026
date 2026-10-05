"""Persistencia: add, flush y consultas; nunca commit."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modulos.acceso.models import Usuario
from app.modulos.catalogo.models import Pieza
from app.modulos.inspecciones.models import AjusteVigencia, EventoPieza, Inspeccion


class InspeccionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def bloquear_pieza(self, pieza_id: uuid.UUID) -> None:
        """Toma la fila de la pieza `FOR UPDATE`: dos cambios a la vez se serializan."""
        self.session.execute(select(Pieza.id).where(Pieza.id == pieza_id).with_for_update())

    def add_inspeccion(self, inspeccion: Inspeccion) -> Inspeccion:
        self.session.add(inspeccion)
        self.session.flush()
        return inspeccion

    def add_evento(self, evento: EventoPieza) -> EventoPieza:
        self.session.add(evento)
        self.session.flush()
        return evento

    def add_ajuste(self, ajuste: AjusteVigencia) -> AjusteVigencia:
        self.session.add(ajuste)
        self.session.flush()
        return ajuste

    def ultima_inspeccion(self, pieza_id: uuid.UUID) -> Inspeccion | None:
        return self.session.scalar(
            select(Inspeccion)
            .where(Inspeccion.pieza_id == pieza_id)
            .order_by(Inspeccion.creado_en.desc(), Inspeccion.id.desc())
            .limit(1)
        )

    def inspecciones_de(self, pieza_id: uuid.UUID) -> list[Inspeccion]:
        return list(self.session.scalars(select(Inspeccion).where(Inspeccion.pieza_id == pieza_id)))

    def eventos_de(self, pieza_id: uuid.UUID) -> list[EventoPieza]:
        return list(
            self.session.scalars(select(EventoPieza).where(EventoPieza.pieza_id == pieza_id))
        )

    def ajustes_de(self, pieza_id: uuid.UUID) -> list[AjusteVigencia]:
        return list(
            self.session.scalars(select(AjusteVigencia).where(AjusteVigencia.pieza_id == pieza_id))
        )

    def nombres_de_usuarios(self, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not ids:
            return {}
        filas = self.session.execute(
            select(Usuario.id, Usuario.nombre).where(Usuario.id.in_(ids))
        ).all()
        return {i: n for i, n in filas}
