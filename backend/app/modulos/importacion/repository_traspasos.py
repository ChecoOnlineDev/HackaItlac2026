"""Consultas de solo lectura de la importacion de traspasos; nunca commit."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modulos.auditoria.models import Auditoria


class TraspasoImportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def fecha_de_huella(self, huella: str) -> datetime | None:
        """La fecha del traspaso importado mas reciente con esa huella (TR-08), o `None`."""
        return self.session.scalar(
            select(Auditoria.creado_en)
            .where(
                Auditoria.accion == "importacion.traspaso",
                Auditoria.despues["huella"].as_string() == huella,
            )
            .order_by(Auditoria.creado_en.desc())
            .limit(1)
        )
