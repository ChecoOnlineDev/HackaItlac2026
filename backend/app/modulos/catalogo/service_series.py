"""Serie pendiente (P-08, I-02): poner el número de serie a una pieza que entró sin él.

`catalogo` es el único escritor de `pieza.numero_serie` después de la entrada. Solo se pone una
serie a una pieza que no la tiene; cambiar una registrada no entra en esta etapa. No es un
movimiento: no toca existencias ni ubicación. Este servicio controla la transacción.
"""

import uuid
from typing import Any

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.errores_bd import ERRNO_UNICO, violacion
from app.modulos.acceso.models import Usuario
from app.modulos.auditoria.service import AuditoriaService
from app.modulos.catalogo.exceptions import (
    PiezaDeBaja,
    PiezaNoEncontrada,
    SerieRepetida,
    SerieYaRegistrada,
)
from app.modulos.catalogo.models import EstadoPieza
from app.modulos.catalogo.repository import PiezaRepository
from app.modulos.consulta.schemas import PiezaFichaOut
from app.modulos.consulta.service import ConsultaService


class SerieService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.piezas = PiezaRepository(session)
        self.auditoria = AuditoriaService(session)
        self.consulta = ConsultaService(session)

    def registrar_serie(
        self, pieza_id: uuid.UUID, numero_serie: str, usuario: Usuario
    ) -> PiezaFichaOut:
        """P-08. 404 si no existe o está fuera del alcance (AC-06); 409 `SERIE_YA_REGISTRADA`,
        `SERIE_REPETIDA` o, si está de baja, `CONFLICTO`. Responde la ficha de la pieza."""
        # La ficha aplica el alcance de AC-06 y responde 404 igual que una pieza inexistente.
        self.consulta.ficha_pieza(pieza_id, usuario)
        try:
            pieza = self.piezas.bloquear(pieza_id)
            if pieza is None:
                raise PiezaNoEncontrada()
            if pieza.estado == EstadoPieza.BAJA:
                raise PiezaDeBaja()
            if pieza.numero_serie:
                raise SerieYaRegistrada(detalles={"regla": "P-08"})
            serie = numero_serie.strip()
            otra = self.piezas.get_by_serie(pieza.articulo_id, serie)
            if otra is not None:
                raise SerieRepetida(detalles=self._detalles_repetida(otra.id, otra.codigo, usuario))
            pieza.numero_serie = serie
            self.session.flush()
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="pieza.registrar_serie",
                entidad="pieza",
                entidad_id=pieza.id,
                antes={"numero_serie": None},
                despues={"numero_serie": serie},
            )
            self.session.commit()
        except DBAPIError as exc:
            self.session.rollback()
            if violacion(exc).errno == ERRNO_UNICO:
                raise SerieRepetida(detalles={"regla": "I-02"}) from exc
            raise
        except Exception:
            self.session.rollback()
            raise
        return self.consulta.ficha_pieza(pieza_id, usuario)

    def _detalles_repetida(
        self, otra_id: uuid.UUID, codigo: str, usuario: Usuario
    ) -> dict[str, Any]:
        """La pieza que ya tiene la serie, solo si el usuario puede verla (AC-06)."""
        detalles: dict[str, Any] = {"regla": "I-02"}
        try:
            self.consulta.ficha_pieza(otra_id, usuario)
        except PiezaNoEncontrada:
            return detalles
        detalles["pieza"] = {"id": str(otra_id), "codigo": codigo}
        return detalles
