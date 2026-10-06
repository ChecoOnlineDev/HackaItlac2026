"""Tipo ENTREGA (US-ENT-001/002/003, fases 2 y 3).

Almacén -> trabajador (retornable, E-20) o almacén -> CONSUMIDO con el trabajador anotado
(consumible, E-21). Reglas: E-01 a E-07, E-12, E-15 a E-22, E-24, E-26 a E-28, L-01 a L-05,
A-01 a A-07 (la autorización la resuelve el motor), F-02, F-03, F-05, F-12.

FEAT-003: E-09 (fuera de la dotación o más de lo recomendado, pide observación), E-10 (talla) y
E-11 (inspección por vencer) son avisos amarillos que no bloquean. Con E-09 la confirmación exige
una observación (en el renglón o en el vale): sin ella, 422 con la regla E-09.

Fuera de alcance (otras fases): E-08 (habilitaciones), E-14 (mínimos: FEAT-004).
"""

import uuid
from collections import defaultdict

from app.core.excepciones import DatosInvalidos
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.archivos.firma import validar_png_de_firma
from app.modulos.archivos.service import decodificar_data_url
from app.modulos.movimientos.contexto import (
    ContextoVale,
    DatosVale,
    Evaluacion,
    MovimientoNuevo,
    PlanBloqueo,
    RenglonEvaluado,
)
from app.modulos.movimientos.evaluador import (
    evaluar_renglon_entrega,
    excedente_limite,
    regla_e02_vigencia,
    regla_e12_pendientes_anteriores,
    tiene_para_limite,
)
from app.modulos.movimientos.exceptions import FirmaRequerida
from app.modulos.movimientos.models import Condicion, FirmaModo, Nivel, TipoVale
from app.modulos.movimientos.schemas import (
    TRAZO_PUNTOS_MINIMO,
    RenglonIn,
    ValeIn,
    contar_puntos_del_trazo,
)
from app.modulos.movimientos.tipos.base import (
    ManejadorTipo,
    motivos_ids,
    vista_articulo,
    vista_pieza,
    vista_titular,
)


def _campo(campo: str, mensaje: str) -> DatosInvalidos:
    return DatosInvalidos(mensaje, [{"campo": campo, "mensaje": mensaje}])


class EntregaTipo(ManejadorTipo):
    tipo = TipoVale.ENTREGA
    permiso = P.ENTREGAS_CREAR
    requiere_firma = True
    firma_modo = FirmaModo.PANTALLA

    # ------------------------------------------------------------------ validación

    def validar_cuerpo(self, cuerpo: ValeIn, *, confirmar: bool) -> None:
        if cuerpo.trabajador_id is None:
            raise _campo("trabajador_id", "Indica a quién se entrega.")
        for i, renglon in enumerate(cuerpo.renglones):
            if renglon.pieza is not None:
                raise _campo(f"renglones.{i}.pieza", "Los datos de pieza son solo de las entradas.")
            if renglon.condicion == Condicion.DANADO:
                raise _campo(
                    f"renglones.{i}.condicion",
                    "Un equipo dañado no se entrega: márcalo como No apto.",
                )
        if not confirmar:
            return
        if not cuerpo.renglones:
            raise _campo("renglones", "Agrega al menos un renglón.")
        firma = getattr(cuerpo, "firma", None)
        if firma is None or not firma.imagen:
            raise FirmaRequerida(
                "Falta la firma del trabajador.",
                [{"campo": "firma", "mensaje": "Falta la firma del trabajador.", "regla": "F-02"}],
            )
        if firma.modo != FirmaModo.PANTALLA:
            raise _campo("firma.modo", "La entrega se firma en pantalla.")
        # F-02: la imagen debe ser un PNG completo y el trazo traer puntos de verdad.
        validar_png_de_firma(decodificar_data_url(firma.imagen))
        if contar_puntos_del_trazo(firma.trazo) < TRAZO_PUNTOS_MINIMO:
            raise _campo(
                "firma.trazo",
                f"La firma debe traer su trazo (al menos {TRAZO_PUNTOS_MINIMO} puntos). "
                "Vuelve a firmar.",
            )

    def normalizar_renglones(self, ctx: ContextoVale, cuerpo: ValeIn) -> list[RenglonIn]:
        """E-15: una pieza repetida se ignora. E-16: un artículo por cantidad repetido suma."""
        salida: list[RenglonIn] = []
        piezas: set[uuid.UUID] = set()
        por_articulo: dict[uuid.UUID, int] = {}
        desconocidos: set[str] = set()
        for renglon in cuerpo.renglones:
            ident = ctx.cargador.identificar(renglon.codigo)
            if ident.tipo == "PIEZA" and ident.pieza is not None:
                if ident.pieza.id in piezas:
                    continue  # E-15
                piezas.add(ident.pieza.id)
                salida.append(renglon)
            elif (
                ident.tipo == "ARTICULO" and ident.articulo and ident.articulo.control == "CANTIDAD"
            ):
                indice = por_articulo.get(ident.articulo.id)
                if indice is None:
                    por_articulo[ident.articulo.id] = len(salida)
                    salida.append(renglon)
                else:  # E-16
                    previo = salida[indice]
                    salida[indice] = previo.model_copy(
                        update={"cantidad": previo.cantidad + renglon.cantidad}
                    )
            else:
                clave = renglon.codigo.strip().casefold()
                if clave in desconocidos:
                    continue
                desconocidos.add(clave)
                salida.append(renglon)
        return salida

    # ------------------------------------------------------------------ evaluación

    def evaluar(self, ctx: ContextoVale, cuerpo: ValeIn) -> Evaluacion:
        carga = ctx.cargador
        assert cuerpo.trabajador_id is not None
        trabajador = carga.trabajador(cuerpo.trabajador_id)
        hechos_trabajador = carga.hechos_trabajador(trabajador)
        e02 = regla_e02_vigencia(hechos_trabajador)
        e12 = regla_e12_pendientes_anteriores(hechos_trabajador)

        evaluacion = Evaluacion(trabajador=carga.ficha(trabajador))
        evaluacion.motivos_vale = [m for m in (e02, e12) if m is not None]

        pedido: dict[uuid.UUID, int] = defaultdict(int)
        for numero, renglon in enumerate(cuerpo.renglones, start=1):
            ident = carga.identificar(renglon.codigo)
            articulo_id = ident.articulo.id if ident.articulo else None
            hechos = carga.hechos_renglon_entrega(
                codigo=renglon.codigo,
                cantidad=renglon.cantidad,
                identificacion=ident,
                ubicacion_almacen_id=ctx.ubicacion_almacen.id,
                trabajador=trabajador,
                ahora=ctx.ahora,
                pedido_previo=pedido[articulo_id] if articulo_id else 0,
            )
            resultado = evaluar_renglon_entrega(hechos, ctx.hoy, e02)
            if articulo_id:
                pedido[articulo_id] += renglon.cantidad
            evaluacion.renglones.append(
                RenglonEvaluado(
                    renglon=numero,
                    codigo=renglon.codigo,
                    cantidad=renglon.cantidad,
                    motivos=resultado.motivos,
                    articulo_id=articulo_id,
                    pieza_id=ident.pieza.id if ident.pieza else None,
                    articulo=vista_articulo(hechos.articulo) if hechos.articulo else None,
                    pieza=vista_pieza(hechos.pieza) if hechos.pieza else None,
                    titular=vista_titular(hechos.titular) if hechos.titular else None,
                    disponible=hechos.disponible if hechos.articulo else None,
                    pide_observacion=resultado.pide_observacion,
                    requiere_confirmacion=resultado.requiere_confirmacion,
                    extra={
                        "retornable": hechos.articulo.retornable if hechos.articulo else None,
                        "condicion": renglon.condicion,
                        "observacion": renglon.observacion,
                        "excedente": excedente_limite(hechos),
                        "limite": hechos.articulo.limite_cantidad if hechos.articulo else None,
                        "tiene": tiene_para_limite(hechos),
                    },
                )
            )
        return evaluacion

    # ---------------------------------------------------------------- confirmación

    def exigir_al_confirmar(self, cuerpo: ValeIn, evaluacion: Evaluacion) -> None:
        """E-09: un renglón fuera de la dotación o sobre lo recomendado necesita observación,
        la del renglón o la del vale. Con el vale en rojo responde el motor (VALE_CAMBIO)."""
        if evaluacion.nivel == Nivel.ROJO:
            return
        del_vale = (getattr(cuerpo, "observacion", None) or "").strip()
        errores = [
            {
                "campo": f"renglones.{i}.observacion",
                "mensaje": "Anota por qué se entrega fuera de lo recomendado.",
                "regla": "E-09",
            }
            for i, r in enumerate(evaluacion.renglones)
            if r.pide_observacion and not (r.extra.get("observacion") or del_vale)
        ]
        if errores:
            raise DatosInvalidos(errores[0]["mensaje"], errores)

    def bloqueos(self, ctx: ContextoVale, cuerpo: ValeIn) -> PlanBloqueo:
        carga = ctx.cargador
        assert cuerpo.trabajador_id is not None
        trabajador = carga.trabajador(cuerpo.trabajador_id)
        plan = PlanBloqueo(trabajador_id=trabajador.id)
        ubicacion_trabajador = carga.ubicacion_de_trabajador(trabajador.id)
        consumido = carga.ubicacion_virtual(UbicacionVirtual.CONSUMIDO)
        for renglon in cuerpo.renglones:
            ident = carga.identificar(renglon.codigo)
            articulo = ident.articulo
            if articulo is None:
                continue
            plan.existencias.add((ctx.ubicacion_almacen.id, articulo.id))
            destino = ubicacion_trabajador if articulo.retornable else consumido
            plan.existencias.add((destino.id, articulo.id))
            if ident.pieza is not None:
                plan.piezas.add(ident.pieza.id)
        return plan

    def datos_vale(self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion) -> DatosVale:
        assert cuerpo.trabajador_id is not None
        trabajador = ctx.cargador.trabajador(cuerpo.trabajador_id)
        periodo = ctx.cargador.trabajadores.periodo_vigente(trabajador, ctx.hoy)
        return DatosVale(
            trabajador_id=trabajador.id,
            periodo_contrato_id=periodo.id if periodo else None,
            firma_modo=FirmaModo.PANTALLA,
        )

    def construir_movimientos(
        self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion
    ) -> list[MovimientoNuevo]:
        carga = ctx.cargador
        assert cuerpo.trabajador_id is not None
        ubicacion_trabajador = carga.ubicacion_de_trabajador(cuerpo.trabajador_id)
        consumido = carga.ubicacion_virtual(UbicacionVirtual.CONSUMIDO)
        movimientos = []
        for r in evaluacion.renglones:
            assert r.articulo_id is not None
            # E-20: retornable al trabajador. E-21: consumible a CONSUMIDO con el trabajador
            # anotado (queda su historial de consumo).
            destino = ubicacion_trabajador if r.extra["retornable"] else consumido
            movimientos.append(
                MovimientoNuevo(
                    renglon=r.renglon,
                    articulo_id=r.articulo_id,
                    pieza_id=r.pieza_id,
                    cantidad=r.cantidad,
                    origen_id=ctx.ubicacion_almacen.id,
                    destino_id=destino.id,
                    trabajador_id=cuerpo.trabajador_id,
                    condicion=str(r.extra["condicion"] or Condicion.BUENO),  # E-22
                    nivel=r.nivel,
                    reglas=motivos_ids(r),
                    # E-09: sin observación propia, el renglón lleva la del vale.
                    observacion=r.extra["observacion"]
                    or (
                        (getattr(cuerpo, "observacion", None) or None)
                        if r.pide_observacion
                        else None
                    ),
                )
            )
        return movimientos
