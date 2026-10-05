"""Reglas de negocio y control de la transacción del módulo `inspecciones` (P-01 a P-07).

Decisiones:
- Cualquier pieza puede inspeccionarse, también las de artículos que no requieren inspección
  (CF-06 solo decide qué se exige antes de entregar, P-02) y las que están con un trabajador.
  Una pieza dada de baja no cambia (`PiezaEnBaja`).
- La vigencia de una inspección Apta es hoy más `vigencia_inspeccion_dias` del artículo; sin días
  en el artículo no hay vencimiento. Una inspección No apta no toca `inspeccion_vigente_hasta`.
- Una inspección vence al terminar su fecha: una que vence hoy todavía vale (E-06).
- El historial va del más reciente al más antiguo.

`registrar_inicial` es el servicio de `movimientos` (I-03): solo hace `flush`; el commit es de quien
llama. Los métodos de los endpoints hacen el commit aquí.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.errores_bd import ERRNO_CHECK, violacion
from app.core.excepciones import DatosInvalidos
from app.core.tiempo import hoy_mx
from app.modulos.acceso.models import Usuario
from app.modulos.auditoria.service import AuditoriaService
from app.modulos.catalogo.models import Articulo, EstadoPieza, Pieza
from app.modulos.catalogo.service import CatalogoService
from app.modulos.inspecciones.exceptions import (
    AjusteNoPermitido,
    AjustePropio,
    EstadoSinCambio,
    PiezaEnBaja,
    VigenciaExcedida,
)
from app.modulos.inspecciones.models import (
    AjusteVigencia,
    EventoPieza,
    Inspeccion,
    ResultadoInspeccion,
)
from app.modulos.inspecciones.repository import InspeccionRepository
from app.modulos.inspecciones.schemas import (
    AjusteVigenciaIn,
    AjusteVigenciaOut,
    EstadoCambiadoOut,
    HistorialItem,
    InspeccionCreate,
    InspeccionOut,
    MarcarNoAptaIn,
    PiezaEstadoOut,
)

__all__ = ["InspeccionService", "ResultadoInspeccion"]


def _observacion_obligatoria(observacion: str | None, regla: str) -> str:
    texto = (observacion or "").strip()
    if not texto:
        raise DatosInvalidos(
            "Anota qué daño o falla encontraste.",
            [{"campo": "observacion", "mensaje": "La observación es obligatoria.", "regla": regla}],
        )
    return texto


class InspeccionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = InspeccionRepository(session)
        self.catalogo = CatalogoService(session)
        self.auditoria = AuditoriaService(session)

    # ------------------------------------------------------------- transacción

    @contextmanager
    def _transaccion(self) -> Iterator[None]:
        """Una operación = una transacción: confirma al salir bien y revierte si algo falla."""
        try:
            yield
            self.session.commit()
        except DBAPIError as exc:
            self.session.rollback()
            if violacion(exc).errno == ERRNO_CHECK:
                raise DatosInvalidos(
                    "Revisa los datos capturados.",
                    [{"campo": violacion(exc).restriccion, "mensaje": "Valor no válido."}],
                ) from exc
            raise
        except Exception:
            self.session.rollback()
            raise

    # ----------------------------------------------------------------- ayudas

    def _pieza_para_cambiar(self, pieza_id: uuid.UUID) -> Pieza:
        """La pieza bloqueada para modificarla; 404 si no existe, 409 si está en baja."""
        self.catalogo.obtener_pieza(pieza_id)
        self.repository.bloquear_pieza(pieza_id)
        pieza = self.catalogo.obtener_pieza(pieza_id)
        self.session.refresh(pieza)
        if pieza.estado == EstadoPieza.BAJA:
            raise PiezaEnBaja()
        return pieza

    @staticmethod
    def _vigente_hasta(articulo: Articulo, fecha: date) -> date | None:
        dias = articulo.vigencia_inspeccion_dias
        return fecha + timedelta(days=dias) if dias else None

    @staticmethod
    def _estado_out(pieza: Pieza) -> PiezaEstadoOut:
        return PiezaEstadoOut(
            id=pieza.id,
            estado=pieza.estado,
            inspeccion_vigente_hasta=pieza.inspeccion_vigente_hasta,
        )

    def _aplicar_inspeccion(
        self,
        pieza: Pieza,
        *,
        fecha: date,
        resultado: ResultadoInspeccion,
        puntos: dict[str, bool] | None,
        observacion: str | None,
        usuario_id: uuid.UUID,
    ) -> Inspeccion:
        """Inserta la inspección y fija el estado y la vigencia de la pieza. Solo flush (P-01)."""
        resultado = ResultadoInspeccion(resultado)
        if resultado == ResultadoInspeccion.NO_APTO:
            observacion = _observacion_obligatoria(observacion, "P-01")
        else:
            observacion = (observacion or "").strip() or None
        articulo = self.catalogo.obtener_articulo(pieza.articulo_id)
        apto = resultado == ResultadoInspeccion.APTO
        vigente_hasta = self._vigente_hasta(articulo, fecha) if apto else None
        estado_anterior = pieza.estado
        vigencia_anterior = pieza.inspeccion_vigente_hasta

        inspeccion = self.repository.add_inspeccion(
            Inspeccion(
                pieza_id=pieza.id,
                fecha=fecha,
                resultado=resultado,
                puntos=puntos or None,
                observacion=observacion,
                vigente_hasta=vigente_hasta,
                usuario_id=usuario_id,
            )
        )
        if apto:
            self.catalogo.actualizar_estado_pieza(
                pieza.id,
                estado=EstadoPieza.APTO,
                inspeccion_vigente_hasta=vigente_hasta,
                actor_id=usuario_id,
            )
        else:
            self.catalogo.actualizar_estado_pieza(
                pieza.id, estado=EstadoPieza.NO_APTO, actor_id=usuario_id
            )
        self.auditoria.registrar(
            usuario_id=usuario_id,
            accion="inspeccion.registrar",
            entidad="inspeccion",
            entidad_id=inspeccion.id,
            antes={
                "estado": estado_anterior,
                "inspeccion_vigente_hasta": vigencia_anterior,
            },
            despues={
                "pieza_id": pieza.id,
                "fecha": fecha,
                "resultado": resultado.value,
                "vigente_hasta": vigente_hasta,
                "observacion": observacion,
            },
        )
        return inspeccion

    # ---------------------------------------------------- servicio de movimientos

    def registrar_inicial(
        self,
        pieza_id: uuid.UUID,
        *,
        fecha: date,
        resultado: ResultadoInspeccion,
        observacion: str | None,
        usuario_id: uuid.UUID,
    ) -> Inspeccion:
        """Inspección inicial al dar entrada a una pieza (I-03). Solo flush.

        Fija el estado y la vigencia de la pieza vía `CatalogoService`. Un resultado No apto
        exige observación (`DatosInvalidos`, P-01).
        """
        pieza = self.catalogo.obtener_pieza(pieza_id)
        return self._aplicar_inspeccion(
            pieza,
            fecha=fecha,
            resultado=resultado,
            puntos=None,
            observacion=observacion,
            usuario_id=usuario_id,
        )

    def registrar_cambio_de_estado(
        self,
        pieza_id: uuid.UUID,
        *,
        estado: EstadoPieza,
        observacion: str,
        usuario_id: uuid.UUID,
    ) -> EventoPieza | None:
        """Cambio de estado de una pieza que `movimientos` provoca con un vale (una devolución
        dañada, V-05): deja su evento en el historial y cambia el estado vía `CatalogoService`.
        Solo `flush`; el commit es de quien llama. No hace nada (y devuelve `None`) si la pieza
        ya está en ese estado o está dada de baja."""
        pieza = self.catalogo.obtener_pieza(pieza_id)
        if pieza.estado in (estado, EstadoPieza.BAJA):
            return None
        anterior = pieza.estado
        evento = self.repository.add_evento(
            EventoPieza(
                pieza_id=pieza.id,
                estado_anterior=anterior,
                estado_nuevo=estado,
                observacion=observacion,
                usuario_id=usuario_id,
            )
        )
        self.catalogo.actualizar_estado_pieza(pieza.id, estado=estado, actor_id=usuario_id)
        self.auditoria.registrar(
            usuario_id=usuario_id,
            accion="pieza.cambio_de_estado",
            entidad="evento_pieza",
            entidad_id=evento.id,
            antes={"estado": anterior},
            despues={"pieza_id": pieza.id, "estado": estado.value, "origen": "movimiento"},
        )
        return evento

    # ------------------------------------------------------------- endpoints

    def registrar(
        self, pieza_id: uuid.UUID, datos: InspeccionCreate, usuario: Usuario
    ) -> InspeccionOut:
        """P-01: Apto deja la pieza APTO y vigente; No apto la deja NO_APTO (P-03)."""
        with self._transaccion():
            pieza = self._pieza_para_cambiar(pieza_id)
            puntos = datos.puntos.model_dump(exclude_none=True) if datos.puntos else None
            inspeccion = self._aplicar_inspeccion(
                pieza,
                fecha=hoy_mx(),
                resultado=datos.resultado,
                puntos=puntos,
                observacion=datos.observacion,
                usuario_id=usuario.id,
            )
        return InspeccionOut(
            id=inspeccion.id,
            pieza_id=pieza.id,
            fecha=inspeccion.fecha,
            resultado=ResultadoInspeccion(inspeccion.resultado),
            puntos=inspeccion.puntos,
            observacion=inspeccion.observacion,
            vigente_hasta=inspeccion.vigente_hasta,
            usuario_id=inspeccion.usuario_id,
            creado_en=inspeccion.creado_en,
            pieza=self._estado_out(pieza),
        )

    def marcar_no_apta(
        self, pieza_id: uuid.UUID, datos: MarcarNoAptaIn, usuario: Usuario
    ) -> EstadoCambiadoOut:
        """P-03: cualquiera con `piezas.inspeccionar` marca No apta con observación."""
        with self._transaccion():
            pieza = self._pieza_para_cambiar(pieza_id)
            observacion = _observacion_obligatoria(datos.observacion, "P-03")
            if pieza.estado == EstadoPieza.NO_APTO:
                raise EstadoSinCambio()
            anterior = pieza.estado
            evento = self.repository.add_evento(
                EventoPieza(
                    pieza_id=pieza.id,
                    estado_anterior=anterior,
                    estado_nuevo=EstadoPieza.NO_APTO,
                    observacion=observacion,
                    usuario_id=usuario.id,
                )
            )
            self.catalogo.actualizar_estado_pieza(
                pieza.id, estado=EstadoPieza.NO_APTO, actor_id=usuario.id
            )
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="pieza.marcar_no_apta",
                entidad="evento_pieza",
                entidad_id=evento.id,
                antes={"estado": anterior},
                despues={"pieza_id": pieza.id, "estado": EstadoPieza.NO_APTO.value},
            )
        return EstadoCambiadoOut(
            evento_id=evento.id, estado_anterior=anterior, pieza=self._estado_out(pieza)
        )

    def ajustar_vigencia(
        self, pieza_id: uuid.UUID, datos: AjusteVigenciaIn, usuario: Usuario
    ) -> AjusteVigenciaOut:
        """P-07: cambia solo la fecha hasta la que vale la inspección vigente de la pieza."""
        with self._transaccion():
            pieza = self._pieza_para_cambiar(pieza_id)
            if pieza.estado == EstadoPieza.NO_APTO:
                raise AjusteNoPermitido(
                    "La pieza está No apta: solo una inspección la regresa a Apta.",
                    {"regla": "P-07"},
                )
            inspeccion = self.repository.ultima_inspeccion(pieza.id)
            if inspeccion is None or inspeccion.resultado != ResultadoInspeccion.APTO:
                raise AjusteNoPermitido(
                    "La pieza no tiene una inspección Apta a la que ajustar la vigencia.",
                    {"regla": "P-07"},
                )
            if inspeccion.usuario_id == usuario.id:
                raise AjustePropio(detalles={"regla": "P-07"})
            articulo = self.catalogo.obtener_articulo(pieza.articulo_id)
            tope = self._vigente_hasta(articulo, inspeccion.fecha) or inspeccion.vigente_hasta
            if tope is None or datos.vigente_hasta > tope:
                raise VigenciaExcedida(
                    "La vigencia no puede pasar de la fecha de la inspección más la del artículo"
                    + (f" ({tope.strftime('%d/%m/%Y')})." if tope else "."),
                    [
                        {
                            "campo": "vigente_hasta",
                            "mensaje": "Fecha fuera del tope permitido.",
                            "regla": "P-07",
                        }
                    ],
                )
            anterior = pieza.inspeccion_vigente_hasta
            if anterior == datos.vigente_hasta:
                raise DatosInvalidos(
                    "Esa ya es la fecha de vigencia de la pieza.",
                    [{"campo": "vigente_hasta", "mensaje": "Sin cambio.", "regla": "P-07"}],
                )
            ajuste = self.repository.add_ajuste(
                AjusteVigencia(
                    pieza_id=pieza.id,
                    inspeccion_id=inspeccion.id,
                    vigente_hasta_anterior=anterior,
                    vigente_hasta_nuevo=datos.vigente_hasta,
                    motivo=datos.motivo,
                    usuario_id=usuario.id,
                )
            )
            self.catalogo.actualizar_estado_pieza(
                pieza.id, inspeccion_vigente_hasta=datos.vigente_hasta, actor_id=usuario.id
            )
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="pieza.ajustar_vigencia",
                entidad="ajuste_vigencia",
                entidad_id=ajuste.id,
                antes={"inspeccion_vigente_hasta": anterior},
                despues={
                    "pieza_id": pieza.id,
                    "inspeccion_id": inspeccion.id,
                    "inspeccion_vigente_hasta": datos.vigente_hasta,
                    "motivo": datos.motivo,
                },
            )
        return AjusteVigenciaOut(
            id=ajuste.id,
            pieza_id=pieza.id,
            inspeccion_id=inspeccion.id,
            vigente_hasta_anterior=ajuste.vigente_hasta_anterior,
            vigente_hasta_nuevo=ajuste.vigente_hasta_nuevo,
            motivo=ajuste.motivo,
            usuario_id=ajuste.usuario_id,
            creado_en=ajuste.creado_en,
            pieza=self._estado_out(pieza),
        )

    # ---------------------------------------------------------------- lectura

    def historial_de_pieza(self, pieza_id: uuid.UUID) -> list[HistorialItem]:
        """Inspecciones, cambios de estado y ajustes de la pieza, del más reciente al más antiguo.

        Para `consulta` (línea de tiempo de la ficha, C-02). Solo lee; 404 si no existe.
        """
        self.catalogo.obtener_pieza(pieza_id)
        inspecciones = self.repository.inspecciones_de(pieza_id)
        eventos = self.repository.eventos_de(pieza_id)
        ajustes = self.repository.ajustes_de(pieza_id)
        nombres = self.repository.nombres_de_usuarios(
            {x.usuario_id for x in (*inspecciones, *eventos, *ajustes)}
        )

        items: list[HistorialItem] = []
        for i in inspecciones:
            items.append(
                HistorialItem(
                    tipo="INSPECCION",
                    id=i.id,
                    fecha=i.creado_en,
                    usuario_id=i.usuario_id,
                    usuario=nombres.get(i.usuario_id),
                    resultado=ResultadoInspeccion(i.resultado),
                    fecha_inspeccion=i.fecha,
                    puntos=i.puntos,
                    vigente_hasta=i.vigente_hasta,
                    observacion=i.observacion,
                )
            )
        for e in eventos:
            items.append(
                HistorialItem(
                    tipo="ESTADO",
                    id=e.id,
                    fecha=e.creado_en,
                    usuario_id=e.usuario_id,
                    usuario=nombres.get(e.usuario_id),
                    estado_anterior=e.estado_anterior,
                    estado_nuevo=e.estado_nuevo,
                    observacion=e.observacion,
                )
            )
        for a in ajustes:
            items.append(
                HistorialItem(
                    tipo="AJUSTE_VIGENCIA",
                    id=a.id,
                    fecha=a.creado_en,
                    usuario_id=a.usuario_id,
                    usuario=nombres.get(a.usuario_id),
                    inspeccion_id=a.inspeccion_id,
                    vigente_hasta_anterior=a.vigente_hasta_anterior,
                    vigente_hasta_nuevo=a.vigente_hasta_nuevo,
                    motivo=a.motivo,
                )
            )
        claves: dict[uuid.UUID, Any] = {x.id: (x.fecha, x.id) for x in items}
        items.sort(key=lambda x: claves[x.id], reverse=True)
        return items
