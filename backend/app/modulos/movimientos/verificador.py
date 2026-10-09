"""Punto de integración de A-02 y A-06: la evaluación REAL de los renglones de una solicitud.

`AutorizacionService.solicitar(..., verificador_renglones=...)` recibe una función
`(almacen_id, trabajador_id, renglones pedidos) -> renglones evaluados`. Este módulo la arma con
la evaluación del semáforo del servidor:

- Del cliente solo se toma `codigo` y `cantidad`. El artículo, el límite, lo que ya tiene, el
  excedente, la regla y el mensaje salen de la evaluación: eso es lo que se guarda y lo que lee
  quien autoriza.
- Solo un renglón NARANJA se puede autorizar. Uno en rojo (pieza no apta, inspección vencida,
  trabajador no vigente, código desconocido, sin existencia...) no se envía (SM-04, A-06), y uno
  verde o amarillo no lo necesita: se rechaza con 422 `RENGLON_NO_AUTORIZABLE`.

El router de `autorizaciones` la toma con `crear_verificador(session, usuario)` (entregas) y
`crear_verificador_traslado(session, usuario)` (traslados, X-17).
"""

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.modulos.acceso.models import Usuario
from app.modulos.autorizaciones.exceptions import RenglonNoAutorizable
from app.modulos.autorizaciones.schemas import RenglonSolicitud, RenglonSolicitudIn
from app.modulos.autorizaciones.service import VerificadorRenglones, VerificadorTraslado
from app.modulos.movimientos.contexto import RenglonEvaluado
from app.modulos.movimientos.evaluador import GRAVEDAD
from app.modulos.movimientos.models import Nivel
from app.modulos.movimientos.service import MovimientoService


def _renglon_de_la_evaluacion(r: RenglonEvaluado) -> RenglonSolicitud:
    """El renglón de la solicitud con lo que dice la evaluación del servidor (nunca el cliente)."""
    motivo = next(m for m in r.motivos if m.nivel == Nivel.NARANJA)
    return RenglonSolicitud(
        codigo=r.codigo,
        articulo_id=r.articulo_id,
        articulo=(r.articulo or {}).get("nombre"),
        cantidad=r.cantidad,
        limite=r.extra.get("limite"),
        tiene=r.extra.get("tiene"),
        excedente=r.extra.get("excedente") or 0,
        regla=motivo.regla,
        mensaje=motivo.mensaje[:255],
        autorizable=True,
    )


def crear_verificador(session: Session, solicitante: Usuario) -> VerificadorRenglones:
    """El verificador de renglones de una solicitud hecha por `solicitante`. Solo lee."""
    servicio = MovimientoService(session)

    def verificar(
        almacen_id: uuid.UUID,
        trabajador_id: uuid.UUID,
        renglones: Sequence[RenglonSolicitudIn],
    ) -> list[RenglonSolicitud]:
        evaluacion = servicio.evaluar_para_autorizacion(
            solicitante,
            almacen_id,
            trabajador_id,
            [(r.codigo, r.cantidad) for r in renglones],
        )
        salida: list[RenglonSolicitud] = []
        for r in evaluacion.renglones:
            if r.nivel == Nivel.NARANJA:
                salida.append(_renglon_de_la_evaluacion(r))
                continue
            motivos = [{"regla": m.regla, "mensaje": m.mensaje} for m in r.motivos]
            if r.nivel == Nivel.ROJO:
                rojo = next(m for m in r.motivos if m.nivel == Nivel.ROJO)
                mensaje = (
                    f"El renglón {r.codigo} está en rojo y no se puede enviar a autorización "
                    f"({rojo.mensaje}) (A-06)."
                )
                regla = rojo.regla
            else:
                mensaje = f"El renglón {r.codigo} no necesita autorización del supervisor."
                regla = r.motivos[0].regla if r.motivos else None
            raise RenglonNoAutorizable(
                mensaje,
                {"codigo": r.codigo, "regla": regla, "nivel": r.nivel.value, "motivos": motivos},
            )
        if not salida:
            raise RenglonNoAutorizable("No hay renglones que autorizar.", {"regla": None})
        return salida

    return verificar


def _renglon_de_traslado(r: RenglonEvaluado) -> RenglonSolicitud:
    """El renglón de la solicitud de un traslado, con lo que dice la evaluación del servidor.
    Un renglón verde o amarillo viaja tal cual (el supervisor ve sus avisos, por ejemplo X-04)."""
    motivo = max(r.motivos, key=lambda m: GRAVEDAD[m.nivel], default=None)
    return RenglonSolicitud(
        codigo=r.codigo,
        articulo_id=r.articulo_id,
        articulo=(r.articulo or {}).get("nombre"),
        cantidad=r.cantidad,
        regla=motivo.regla if motivo else "X-17",
        mensaje=motivo.mensaje[:255] if motivo else None,
        autorizable=True,
    )


def crear_verificador_traslado(session: Session, solicitante: Usuario) -> VerificadorTraslado:
    """El verificador de renglones de una solicitud de TRASLADO hecha por `solicitante`.

    Evalúa el traspaso como lo evaluaría `solicitante` al enviarlo (X-17, A-06): un renglón o un
    vale en rojo no se autoriza (422 `RENGLON_NO_AUTORIZABLE`), y si el traslado no pide
    autorización (ruta habitual, o `solicitante` es el supervisor del origen y su envío es la
    autorización, X-16) tampoco. Solo lee."""
    servicio = MovimientoService(session)

    def verificar(
        origen_id: uuid.UUID,
        destino_id: uuid.UUID,
        renglones: Sequence[RenglonSolicitudIn],
    ) -> list[RenglonSolicitud]:
        evaluacion = servicio.evaluar_traslado_para_autorizacion(
            solicitante, origen_id, destino_id, [(r.codigo, r.cantidad) for r in renglones]
        )
        for r in evaluacion.renglones:
            if r.nivel == Nivel.ROJO:
                rojo = next(m for m in r.motivos if m.nivel == Nivel.ROJO)
                raise RenglonNoAutorizable(
                    f"El renglón {r.codigo} está en rojo y no se puede enviar a autorización "
                    f"({rojo.mensaje}) (A-06).",
                    {
                        "codigo": r.codigo,
                        "regla": rojo.regla,
                        "nivel": r.nivel.value,
                        "motivos": [{"regla": m.regla, "mensaje": m.mensaje} for m in r.motivos],
                    },
                )
        rojo_del_vale = next((m for m in evaluacion.motivos_vale if m.nivel == Nivel.ROJO), None)
        if rojo_del_vale is not None:
            raise RenglonNoAutorizable(
                f"El traslado está en rojo y no se puede enviar a autorización "
                f"({rojo_del_vale.mensaje}) (A-06).",
                {"codigo": None, "regla": rojo_del_vale.regla, "nivel": Nivel.ROJO.value},
            )
        if not any(m.regla == "X-17" for m in evaluacion.motivos_vale):
            raise RenglonNoAutorizable(
                "Este traslado no necesita la autorización del supervisor.",
                {"codigo": None, "regla": "X-17"},
            )
        if not evaluacion.renglones:
            raise RenglonNoAutorizable("No hay renglones que autorizar.", {"regla": None})
        return [_renglon_de_traslado(r) for r in evaluacion.renglones]

    return verificar
