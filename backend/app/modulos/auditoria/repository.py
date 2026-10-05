"""Persistencia del módulo `auditoria`. Solo inserta."""

from sqlalchemy.orm import Session

from app.modulos.auditoria.models import Auditoria


class AuditoriaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, registro: Auditoria) -> Auditoria:
        self.session.add(registro)
        self.session.flush()
        return registro
