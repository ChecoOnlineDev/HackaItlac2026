"""Tipo CANCELACION (US-CAN-001, fase 7) y `POST /api/vales/{id}/cancelacion`.

Corrige un vale capturado por error sin borrar nada (RG-02): genera un vale de CANCELACION con su
propio folio (`...-CAN-...`) y los movimientos INVERSOS de los del vale original (origen y destino
invertidos, mismas piezas y cantidades). El original queda visible con `estado = CANCELADO`
(la única excepción de inmutabilidad) y el vale de cancelación apunta a él con `vale_origen_id`.

Es GENÉRICA: no conoce las reglas de cada tipo; trabaja con las filas de `movimiento` del vale
original. Reglas: K-01 a K-05, X-14, A-03, RG-02, RG-04, RG-06, RG-09, C-08.

- K-01: cancela quien hizo el vale (`vales.cancelar`) o quien tenga `vales.cancelar_todos`, con
  motivo (queda en `vale.observacion` de la cancelación). Entra a la lista de revisión: se anota en
  la auditoría (`vale.cancelar`); la lista como pantalla es pospuesta.
- K-02: los movimientos inversos copian `trabajador_id` y `condicion` del original; así el reporte
  de consumo (C-08) resta lo que la entrega de un consumible sumó.
- K-03: no se cancela si la pieza ya se movió después o si las existencias ya no alcanzan.
  409 `NO_CANCELABLE` explica por qué y no escribe nada. Un vale ya cancelado no se cancela
  otra vez.
- K-04: entradas, entregas, devoluciones y traspasos en tránsito (X-14). No una recepción, un no
  adeudo ni una cancelación.
- K-05: con `rehacer`, la respuesta trae un `borrador` con los renglones del vale original.
- A-03: la autorización que usó una entrega cancelada queda USADA; no se libera.

Lo que NO se revierte (la cancelación solo mueve existencias y ubicaciones, no deshace efectos
propios de un tipo): ver `README.md` del módulo, "Qué no revierte una cancelación".
"""

import uuid
from typing import TYPE_CHECKING, Any

from app.core.excepciones import DatosInvalidos, SinPermiso
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.auditoria.service import AuditoriaService
from app.modulos.movimientos.cargador import hechos_de_articulo, hechos_de_pieza
from app.modulos.movimientos.contexto import (
    ContextoVale,
    DatosVale,
    Evaluacion,
    MovimientoNuevo,
    PlanBloqueo,
    RenglonEvaluado,
)
from app.modulos.movimientos.evaluador import Motivo
from app.modulos.movimientos.exceptions import IdClienteEnUso, NoCancelable, ValeNoEncontrado
from app.modulos.movimientos.models import (
    EstadoVale,
    FirmaModo,
    Movimiento,
    Nivel,
    TipoVale,
    Vale,
)
from app.modulos.movimientos.schemas import CancelacionIn, ConfirmarIn, ValeIn
from app.modulos.movimientos.schemas_cancelacion import (
    BorradorOut,
    CancelacionOut,
    PiezaBorradorOut,
    RenglonBorradorOut,
    ValeCanceladoOut,
)
from app.modulos.movimientos.tipos.base import (
    ManejadorTipo,
    motivos_ids,
    vista_articulo,
    vista_pieza,
    vista_titular,
)
from app.modulos.movimientos.tipos.cancelacion_reglas import (
    HechosExistenciaCancelacion,
    HechosPiezaCancelacion,
    regla_k03_existencia,
    regla_k03_pieza,
    regla_k03_ya_cancelado,
    regla_k04_tipo,
    regla_x14_traspaso,
)

if TYPE_CHECKING:
    from app.modulos.movimientos.service import MovimientoService

_VIRTUALES = {
    UbicacionVirtual.EN_TRANSITO: "tránsito",
    UbicacionVirtual.CONSUMIDO: "consumo",
    UbicacionVirtual.BAJA: "baja",
    UbicacionVirtual.PROVEEDOR: "proveedor",
}


def _campo(campo: str, mensaje: str) -> DatosInvalidos:
    return DatosInvalidos(mensaje, [{"campo": campo, "mensaje": mensaje}])


class CancelacionTipo(ManejadorTipo):
    tipo = TipoVale.CANCELACION
    permiso = P.VALES_CANCELAR
    requiere_firma = False
    firma_modo = FirmaModo.SESION  # F-03: basta la sesión de quien cancela

    # ------------------------------------------------------------------ validación

    def validar_cuerpo(self, cuerpo: ValeIn, *, confirmar: bool) -> None:
        if cuerpo.vale_origen_id is None:
            raise _campo("vale_origen_id", "Indica qué vale se cancela.")
        if cuerpo.renglones:
            raise _campo(
                "renglones", "La cancelación no lleva renglones: sale de los del vale original."
            )
        if confirmar:
            motivo = getattr(cuerpo, "observacion", None)
            if motivo is None or not motivo.strip():
                raise _campo("motivo", "Escribe el motivo de la cancelación.")

    def almacen_operativo(
        self, servicio: MovimientoService, usuario: Usuario, cuerpo: ValeIn
    ) -> uuid.UUID:
        """El almacén de la cancelación es el del vale original (el de origen en un traspaso).
        Aquí se hacen las comprobaciones de quién puede cancelar (K-01, X-14), que son lo primero
        que se pregunta, antes de leer nada más."""
        assert cuerpo.vale_origen_id is not None
        original = servicio.repository.vale(cuerpo.vale_origen_id)
        acceso = servicio.acceso
        todos_los_almacenes = acceso.puede_operar_todos_los_almacenes(usuario)
        if original is None or (
            not todos_los_almacenes
            and usuario.almacen_id not in (original.almacen_id, original.destino_almacen_id)
        ):
            raise ValeNoEncontrado()
        # K-01: los propios con `vales.cancelar`; los de cualquiera con `vales.cancelar_todos`.
        if original.responsable_id != usuario.id and not acceso.tiene_permiso(
            usuario, P.VALES_CANCELAR_TODOS
        ):
            raise SinPermiso("Solo puedes cancelar los vales que tú hiciste.")
        # X-14: un traspaso en tránsito lo cancela el almacén de origen, no el de destino.
        if not todos_los_almacenes and usuario.almacen_id != original.almacen_id:
            texto = "Un traspaso en tránsito lo cancela el almacén de origen."
            raise NoCancelable(texto, [{"regla": "X-14", "mensaje": texto}])
        return original.almacen_id

    # ------------------------------------------------------------------ evaluación

    def evaluar(self, ctx: ContextoVale, cuerpo: ValeIn) -> Evaluacion:
        """El semáforo de la cancelación: un renglón por movimiento del vale original (el
        inverso). Rojo si no se puede (K-03, K-04, X-14). No escribe nada. Al confirmar (con las
        filas bloqueadas) un rojo responde 409 `NO_CANCELABLE`, no `VALE_CAMBIO`."""
        assert cuerpo.vale_origen_id is not None
        repo = ctx.cargador.repository
        original = repo.vale(cuerpo.vale_origen_id)
        if original is None:  # pragma: no cover - `almacen_operativo` ya lo comprobó
            raise ValeNoEncontrado()
        previa = repo.cancelacion_de(original.id)
        evaluacion = Evaluacion()
        evaluacion.motivos_vale = [
            m
            for m in (
                regla_k04_tipo(original.tipo),
                regla_k03_ya_cancelado(original.estado, previa.folio if previa else None),
                regla_x14_traspaso(original.tipo, original.estado),
            )
            if m is not None
        ]
        revisar_renglones = not evaluacion.motivos_vale
        necesario: dict[tuple[uuid.UUID, uuid.UUID], int] = {}
        proveedor = ctx.cargador.ubicacion_virtual(UbicacionVirtual.PROVEEDOR).id
        for m, articulo, pieza in repo.renglones_de(original.id):
            motivos: list[Motivo] = []
            titular = None
            disponible = None
            if revisar_renglones:
                if pieza is not None:
                    titular = ctx.cargador.titular_de(pieza)
                    motivo = regla_k03_pieza(
                        HechosPiezaCancelacion(
                            codigo=pieza.codigo,
                            esta_en_el_destino=pieza.ubicacion_id == m.destino_id,
                            hay_movimiento_posterior=repo.hay_movimiento_posterior_de_pieza(m),
                            donde_esta=titular.descripcion
                            if titular
                            else "ya no está donde la dejó el vale",
                        )
                    )
                    if motivo:
                        motivos.append(motivo)
                if m.destino_id != proveedor:  # PROVEEDOR no lleva existencia
                    clave = (m.destino_id, m.articulo_id)
                    necesario[clave] = necesario.get(clave, 0) + m.cantidad
                    disponible = ctx.cargador.existencia(m.destino_id, m.articulo_id)
                    if not motivos:
                        motivo = regla_k03_existencia(
                            HechosExistenciaCancelacion(
                                articulo=articulo.nombre,
                                ubicacion=self._describir(repo, m.destino_id),
                                necesario=necesario[clave],
                                disponible=disponible,
                            )
                        )
                        if motivo:
                            motivos.append(motivo)
            evaluacion.renglones.append(
                RenglonEvaluado(
                    renglon=m.renglon,
                    codigo=pieza.codigo if pieza else articulo.codigo,
                    cantidad=m.cantidad,
                    motivos=motivos,
                    articulo_id=articulo.id,
                    pieza_id=pieza.id if pieza else None,
                    articulo=vista_articulo(hechos_de_articulo(articulo)),
                    pieza=vista_pieza(hechos_de_pieza(pieza)) if pieza else None,
                    titular=vista_titular(titular) if titular and motivos else None,
                    disponible=disponible,
                    extra={"movimiento": m},
                )
            )
        if ctx.bloqueado and evaluacion.nivel == Nivel.ROJO:
            raise self._no_cancelable(evaluacion)
        return evaluacion

    @staticmethod
    def _describir(repo: Any, ubicacion_id: uuid.UUID) -> str:
        datos = repo.ubicaciones([ubicacion_id]).get(ubicacion_id)
        if datos is None:  # pragma: no cover
            return "esa ubicación"
        ubicacion, nombre, clave = datos
        if ubicacion.tipo == "ALMACEN":
            return f"el almacén {clave}"
        if ubicacion.tipo == "TRABAJADOR":
            return f"{nombre} ({clave})"
        return _VIRTUALES.get(ubicacion.virtual, "esa ubicación")

    @staticmethod
    def _no_cancelable(evaluacion: Evaluacion) -> NoCancelable:
        """409 `NO_CANCELABLE` con todos los motivos (cada uno con el ID de su regla)."""
        detalles: list[dict[str, Any]] = [
            {"regla": m.regla, "mensaje": m.mensaje}
            for m in evaluacion.motivos_vale
            if m.nivel == Nivel.ROJO
        ]
        for r in evaluacion.renglones:
            detalles.extend(
                {"regla": m.regla, "renglon": r.renglon, "codigo": r.codigo, "mensaje": m.mensaje}
                for m in r.motivos
                if m.nivel == Nivel.ROJO
            )
        return NoCancelable(f"No se puede cancelar este vale. {detalles[0]['mensaje']}", detalles)

    # ---------------------------------------------------------------- confirmación

    def bloqueos(self, ctx: ContextoVale, cuerpo: ValeIn) -> PlanBloqueo:
        """El vale original, su trabajador, las existencias de origen y destino de cada
        movimiento y sus piezas (orden canónico, lo toma el motor)."""
        assert cuerpo.vale_origen_id is not None
        repo = ctx.cargador.repository
        original = repo.vale(cuerpo.vale_origen_id)
        assert original is not None
        proveedor = ctx.cargador.ubicacion_virtual(UbicacionVirtual.PROVEEDOR).id
        plan = PlanBloqueo(trabajador_id=original.trabajador_id, vales={original.id})
        for m, _articulo, _pieza in repo.renglones_de(original.id):
            for ubicacion_id in (m.origen_id, m.destino_id):
                if ubicacion_id != proveedor:
                    plan.existencias.add((ubicacion_id, m.articulo_id))
            if m.pieza_id is not None:
                plan.piezas.add(m.pieza_id)
        return plan

    def datos_vale(self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion) -> DatosVale:
        assert cuerpo.vale_origen_id is not None
        original = ctx.cargador.repository.vale(cuerpo.vale_origen_id)
        assert original is not None
        return DatosVale(
            trabajador_id=original.trabajador_id,
            periodo_contrato_id=original.periodo_contrato_id,
            vale_origen_id=original.id,
            estado=EstadoVale.EMITIDO,
            firma_modo=FirmaModo.SESION,
            observacion=getattr(cuerpo, "observacion", None),
        )

    def construir_movimientos(
        self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion
    ) -> list[MovimientoNuevo]:
        """K-02: origen y destino invertidos; misma pieza, cantidad, trabajador y condición."""
        assert cuerpo.vale_origen_id is not None
        original = ctx.cargador.repository.vale(cuerpo.vale_origen_id)
        assert original is not None
        reglas_extra = ["X-14"] if original.tipo == TipoVale.TRASPASO else []
        movimientos = []
        for r in evaluacion.renglones:
            m: Movimiento = r.extra["movimiento"]
            movimientos.append(
                MovimientoNuevo(
                    renglon=m.renglon,
                    articulo_id=m.articulo_id,
                    pieza_id=m.pieza_id,
                    cantidad=m.cantidad,
                    origen_id=m.destino_id,
                    destino_id=m.origen_id,
                    trabajador_id=m.trabajador_id,
                    condicion=m.condicion,
                    nivel=Nivel.VERDE,
                    reglas=["K-02", *reglas_extra, *motivos_ids(r)],
                )
            )
        return movimientos

    def al_confirmar(
        self,
        ctx: ContextoVale,
        cuerpo: ValeIn,
        evaluacion: Evaluacion,
        vale: Vale,
        movimientos: list[Any],
    ) -> None:
        """K-02: el original pasa a CANCELADO (única excepción de inmutabilidad). K-01: entra a
        la lista de revisión (auditoría `vale.cancelar`). La autorización que usó una entrega no
        se toca: sigue USADA (A-03)."""
        assert cuerpo.vale_origen_id is not None
        original = ctx.cargador.repository.vale(cuerpo.vale_origen_id)
        assert original is not None
        estado_previo = original.estado
        original.estado = EstadoVale.CANCELADO
        ctx.session.flush()
        AuditoriaService(ctx.session).registrar(
            usuario_id=ctx.usuario.id,
            accion="vale.cancelar",
            entidad="vale",
            entidad_id=original.id,
            antes={"folio": original.folio, "tipo": original.tipo, "estado": estado_previo},
            despues={
                "estado": EstadoVale.CANCELADO,
                "motivo": vale.observacion,
                "vale_cancelacion_id": vale.id,
                "folio_cancelacion": vale.folio,
                "para_revision": True,
            },
        )

    # ------------------------------------------------------------ endpoint propio

    def cancelar(
        self,
        servicio: MovimientoService,
        usuario: Usuario,
        vale_id: uuid.UUID,
        datos: CancelacionIn,
    ) -> CancelacionOut:
        """`POST /api/vales/{id}/cancelacion`: arma el cuerpo de la cancelación y la confirma por
        el motor (misma transacción, bloqueos, folio e idempotencia por `id_cliente`). Con
        `rehacer`, agrega el borrador (K-05)."""
        repo = servicio.repository
        previo = repo.vale_por_id_cliente(datos.id_cliente)
        if previo is not None and (
            previo.tipo != TipoVale.CANCELACION or previo.vale_origen_id != vale_id
        ):
            raise IdClienteEnUso()
        cuerpo = ConfirmarIn(
            tipo=TipoVale.CANCELACION,
            vale_origen_id=vale_id,
            id_cliente=datos.id_cliente,
            observacion=datos.motivo,
        )
        confirmada, creado = servicio.confirmar(usuario, cuerpo)
        cancelacion = repo.vale_por_id_cliente(datos.id_cliente)
        original = repo.vale(vale_id)
        assert cancelacion is not None and original is not None
        return CancelacionOut(
            **confirmada.model_dump(),
            vale_cancelado=ValeCanceladoOut(
                id=original.id, folio=original.folio, estado=EstadoVale(original.estado)
            ),
            motivo=cancelacion.observacion or datos.motivo,
            borrador=self._borrador(repo, original) if datos.rehacer else None,
            creado=creado,
        )

    @staticmethod
    def _borrador(repo: Any, original: Vale) -> BorradorOut:
        """K-05: los renglones del vale original, sin firma ni autorización, para corregirlos y
        confirmarlos como un vale nuevo. En una ENTRADA de piezas el `codigo` es el del artículo
        y `pieza` trae el código y la serie que tenía."""
        renglones = []
        for m, articulo, pieza in repo.renglones_de(original.id):
            es_entrada_de_pieza = original.tipo == TipoVale.ENTRADA and pieza is not None
            renglones.append(
                RenglonBorradorOut(
                    codigo=articulo.codigo
                    if es_entrada_de_pieza or pieza is None
                    else pieza.codigo,
                    cantidad=m.cantidad,
                    condicion=m.condicion,
                    observacion=m.observacion,
                    pieza=PiezaBorradorOut(codigo=pieza.codigo, numero_serie=pieza.numero_serie)
                    if es_entrada_de_pieza and pieza is not None
                    else None,
                )
            )
        return BorradorOut(
            tipo=TipoVale(original.tipo),
            almacen_id=original.almacen_id,
            trabajador_id=original.trabajador_id,
            destino_almacen_id=original.destino_almacen_id,
            observacion=original.observacion,
            renglones=renglones,
        )
