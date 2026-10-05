"""Persistencia del módulo `archivos`. Solo `add`, `flush` y consultas; nunca commit."""

import uuid

from sqlalchemy.orm import Session

from app.modulos.archivos.models import Adjunto


class AdjuntoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, adjunto_id: uuid.UUID) -> Adjunto | None:
        return self.session.get(Adjunto, adjunto_id)

    def add(self, adjunto: Adjunto) -> Adjunto:
        self.session.add(adjunto)
        self.session.flush()
        return adjunto
