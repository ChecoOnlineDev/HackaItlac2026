"""Tipo NO_ADEUDO y `POST /api/trabajadores/{id}/no-adeudo` (US-BAJ-001, fase 4).

B-04: con los pendientes en cero (solo cuentan los retornables, B-03) el almacén emite el vale de
no adeudo, con folio `...-NAD-...`. B-08: al emitirse el trabajador queda Inactivo, en la misma
transacción. Con pendientes: 409 `CON_PENDIENTES` con la lista (invariante 8 del data-model).
B-01: si el trabajador está Activo, el almacenista inicia la baja al pedir el vale (queda en Baja
en proceso y se le muestran sus pendientes). Vale SIN movimientos y sin renglones; firma de sesión.
"""

import uuid
from typing import Any

from app.core.excepciones import DatosInvalidos
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.movimientos.contexto import (
    ContextoVale,
    DatosVale,
    Evaluacion,
    MovimientoNuevo,
    PlanBloqueo,
)
from app.modulos.movimientos.evaluador import Motivo
from app.modulos.movimientos.exceptions import IdClienteEnUso, ValeCambio
from app.modulos.movimientos.models import FirmaModo, Nivel, TipoVale, Vale
from app.modulos.movimientos.schemas import ConfirmarIn, NoAdeudoIn, ValeIn
from app.modulos.movimientos.schemas_no_adeudo import NoAdeudoOut, TrabajadorNoAdeudoOut
from app.modulos.movimientos.tipos.base import ManejadorTipo
from app.modulos.trabajadores.exceptions import EstadoTrabajadorInvalido, TrabajadorConPendientes
from app.modulos.trabajadores.models import EstadoTrabajador
from app.modulos.trabajadores.schemas import TEXTO_ESTADO


def _campo(campo: str, mensaje: str) -> DatosInvalidos:
    return DatosInvalidos(mensaje, [{"campo": campo, "mensaje": mensaje}])


def _con_pendientes(servicio, trabajador, usuario) -> TrabajadorConPendientes | None:
    """B-04: el 409 con la lista de lo que falta (sin costos), o `None` si no debe nada."""
    pendientes = servicio.trabajadores.ficha_breve(trabajador, usuario).resguardo
    if not pendientes:
        return None
    return TrabajadorConPendientes(
        "No se puede emitir el vale de no adeudo: todavía tiene equipo pendiente de devolver.",
        {
            "regla": "B-04",
            "pendientes": [p.model_dump(mode="json") for p in pendientes],
        },
    )


class NoAdeudoTipo(ManejadorTipo):
    tipo = TipoVale.NO_ADEUDO
    permiso = P.NO_ADEUDO_EMITIR
    firma_modo = FirmaModo.SESION
    admite_sin_renglones = True

    def validar_cuerpo(self, cuerpo: ValeIn, *, confirmar: bool) -> None:
        if cuerpo.trabajador_id is None:
            raise _campo("trabajador_id", "Indica de qué trabajador es el vale de no adeudo.")
        if cuerpo.renglones:
            raise _campo("renglones", "El vale de no adeudo no lleva renglones.")

    def evaluar(self, ctx: ContextoVale, cuerpo: ValeIn) -> Evaluacion:
        assert cuerpo.trabajador_id is not None
        carga = ctx.cargador
        trabajador = carga.trabajador(cuerpo.trabajador_id)
        ficha = carga.ficha(trabajador)
        evaluacion = Evaluacion(trabajador=ficha)
        if trabajador.estado == EstadoTrabajador.INACTIVO:
            evaluacion.motivos_vale.append(
                Motivo(
                    "B-08", Nivel.ROJO, "Su baja ya se completó: el trabajador ya está Inactivo."
                )
            )
        elif ficha.resguardo:
            n = len(ficha.resguardo)
            cosa = "un equipo pendiente" if n == 1 else f"{n} equipos pendientes"
            evaluacion.motivos_vale.append(
                Motivo("B-04", Nivel.ROJO, f"Tiene {cosa} de devolver. No procede el no adeudo.")
            )
        else:
            evaluacion.motivos_vale.append(
                Motivo("B-04", Nivel.VERDE, "Sin pendientes: procede el vale de no adeudo.")
            )
        return evaluacion

    def bloqueos(self, ctx: ContextoVale, cuerpo: ValeIn) -> PlanBloqueo:
        return PlanBloqueo(trabajador_id=cuerpo.trabajador_id)

    def datos_vale(self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion) -> DatosVale:
        assert cuerpo.trabajador_id is not None
        trabajador = ctx.cargador.trabajador(cuerpo.trabajador_id)
        periodo = ctx.cargador.trabajadores.periodo_vigente(trabajador, ctx.hoy)
        return DatosVale(
            trabajador_id=trabajador.id,
            periodo_contrato_id=periodo.id if periodo else None,
            firma_modo=FirmaModo.SESION,
        )

    def construir_movimientos(
        self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion
    ) -> list[MovimientoNuevo]:
        return []

    def al_confirmar(
        self,
        ctx: ContextoVale,
        cuerpo: ValeIn,
        evaluacion: Evaluacion,
        vale: Vale,
        movimientos: list[Any],
    ) -> None:
        """B-08: el trabajador queda Inactivo (la misma transacción del vale)."""
        assert cuerpo.trabajador_id is not None
        trabajador = ctx.cargador.trabajador(cuerpo.trabajador_id)
        ctx.cargador.trabajadores.marcar_inactivo(trabajador, ctx.usuario)

    # ------------------------------------------------------------ el endpoint propio

    def emitir_no_adeudo(
        self,
        servicio,
        usuario: Usuario,
        trabajador_id: uuid.UUID,
        datos: NoAdeudoIn,
    ) -> NoAdeudoOut:
        """`POST /api/trabajadores/{id}/no-adeudo`. Idempotente por `id_cliente`."""
        trabajador = servicio.trabajadores.obtener(trabajador_id)
        cuerpo = ConfirmarIn(
            tipo=TipoVale.NO_ADEUDO,
            trabajador_id=trabajador_id,
            id_cliente=datos.id_cliente,
            observacion=datos.observacion,
        )
        existente = servicio.repository.vale_por_id_cliente(datos.id_cliente)
        if existente is not None:
            if existente.trabajador_id != trabajador_id:
                raise IdClienteEnUso()
            vale, creado = servicio.confirmar(usuario, cuerpo)
            return self._salida(servicio, vale, trabajador_id, repetido=not creado)

        if trabajador.estado == EstadoTrabajador.INACTIVO:
            raise EstadoTrabajadorInvalido(
                "El trabajador ya está inactivo: su baja ya se completó.", {"regla": "B-08"}
            )
        if trabajador.estado == EstadoTrabajador.ACTIVO:
            # B-01: el almacenista inicia la baja cuando el trabajador pide su vale. Queda en
            # Baja en proceso aunque haya pendientes (se confirma antes de responder el 409).
            # Iniciar la baja tiene su propio permiso: emitir el vale no lo da (tabla 8.2).
            servicio.acceso.exigir_permiso(usuario, P.TRABAJADORES_INICIAR_BAJA)
            servicio.trabajadores.iniciar_baja(trabajador_id, usuario)
            trabajador = servicio.trabajadores.obtener(trabajador_id)
        conflicto = _con_pendientes(servicio, trabajador, usuario)
        if conflicto is not None:
            raise conflicto
        try:
            vale, creado = servicio.confirmar(usuario, cuerpo)
        except ValeCambio:
            # Algo cambió entre la revisión y el bloqueo: si es que ahora debe equipo, se dice.
            trabajador = servicio.trabajadores.obtener(trabajador_id)
            conflicto = _con_pendientes(servicio, trabajador, usuario)
            if conflicto is not None:
                raise conflicto from None
            raise
        return self._salida(servicio, vale, trabajador_id, repetido=not creado)

    @staticmethod
    def _salida(servicio, vale, trabajador_id: uuid.UUID, *, repetido: bool) -> NoAdeudoOut:
        trabajador = servicio.trabajadores.obtener(trabajador_id)
        return NoAdeudoOut(
            **vale.model_dump(),
            trabajador=TrabajadorNoAdeudoOut(
                id=trabajador.id,
                numero_empleado=trabajador.numero_empleado,
                nombre=trabajador.nombre,
                estado=trabajador.estado,
                estado_texto=TEXTO_ESTADO[trabajador.estado],
            ),
            repetido=repetido,
        )
