"""Punto de extensión de A-06: el verificador de renglones que `autorizaciones` usa al solicitar.

`AutorizacionService.solicitar(..., verificador_renglones=...)` acepta una función
`(almacen_id, trabajador_id, renglones) -> None` que lanza `RenglonNoAutorizable` si un renglón no
se puede autorizar. Este módulo la arma con la evaluación REAL del semáforo: un renglón en rojo
(pieza no apta, inspección vencida, trabajador no vigente, código desconocido, sin existencia...)
no se envía a autorización (SM-04, A-06), aunque quien lo pide lo marque `autorizable`.

El router de `autorizaciones` la toma con `crear_verificador(session, usuario)`.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.modulos.acceso.models import Usuario
from app.modulos.autorizaciones.schemas import RenglonSolicitud
from app.modulos.autorizaciones.service import VerificadorRenglones
from app.modulos.movimientos.service import MovimientoService


def crear_verificador(session: Session, solicitante: Usuario) -> VerificadorRenglones:
    """El verificador de renglones de una solicitud hecha por `solicitante`. Solo lee."""
    servicio = MovimientoService(session)

    def verificar(
        almacen_id: uuid.UUID, trabajador_id: uuid.UUID, renglones: Sequence[RenglonSolicitud]
    ) -> None:
        servicio.verificar_renglones_autorizables(
            solicitante,
            almacen_id,
            trabajador_id,
            [(r.codigo, r.cantidad) for r in renglones],
        )

    return verificar
