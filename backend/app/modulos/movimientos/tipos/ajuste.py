"""CP-03: faltante físico del almacén, sin adjudicar pérdidas a trabajadores."""

from app.core.excepciones import DatosInvalidos
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.movimientos.cargador import hechos_de_articulo, hechos_de_pieza
from app.modulos.movimientos.contexto import (
    DatosVale,
    Evaluacion,
    MovimientoNuevo,
    PlanBloqueo,
    RenglonEvaluado,
)
from app.modulos.movimientos.evaluador import Motivo
from app.modulos.movimientos.models import FirmaModo, Nivel, TipoVale
from app.modulos.movimientos.schemas import CANTIDAD_MAXIMA
from app.modulos.movimientos.tipos.base import (
    ManejadorTipo,
    motivos_ids,
    vista_articulo,
    vista_pieza,
)


class AjusteTipo(ManejadorTipo):
    tipo = TipoVale.AJUSTE
    permiso = "inventario.ajustar"
    firma_modo = FirmaModo.SESION

    def validar_cuerpo(self, cuerpo, *, confirmar):
        for campo in ("trabajador_id", "destino_almacen_id", "vale_origen_id", "autorizacion_id"):
            if getattr(cuerpo, campo) is not None:
                raise DatosInvalidos(
                    "El faltante se registra a nombre del almacén.",
                    [
                        {"campo": campo, "regla": "CP-03"},
                    ],
                )
        if not (getattr(cuerpo, "observacion", None) or "").strip():
            raise DatosInvalidos(
                "Escribe qué faltó y cómo se detectó.",
                [
                    {"campo": "observacion", "regla": "CP-03"},
                ],
            )
        for i, r in enumerate(cuerpo.renglones):
            if r.pieza is not None or r.foto is not None or r.condicion is not None:
                raise DatosInvalidos(
                    "El ajuste solo necesita código, cantidad y observación.",
                    [
                        {"campo": f"renglones.{i}", "regla": "CP-03"},
                    ],
                )

    def normalizar_renglones(self, ctx, cuerpo):
        salida, indices = [], {}
        for r in cuerpo.renglones:
            clave = r.codigo.strip().casefold()
            if clave not in indices:
                indices[clave] = len(salida)
                salida.append(r)
                continue
            i = indices[clave]
            ident = ctx.cargador.identificar(r.codigo)
            if ident.pieza is None:
                anterior = salida[i]
                observacion = (
                    "; ".join(dict.fromkeys(filter(None, [anterior.observacion, r.observacion])))
                    or None
                )
                cantidad = anterior.cantidad + r.cantidad
                if len(observacion or "") > 1000 or cantidad > CANTIDAD_MAXIMA:
                    raise DatosInvalidos(
                        "Los renglones repetidos superan el límite de cantidad u observación. "
                        "Reduce el ajuste.",
                        [{"campo": "renglones", "regla": "CP-03"}],
                    )
                salida[i] = anterior.model_copy(
                    update={
                        "cantidad": cantidad,
                        "observacion": observacion,
                    }
                )
        return salida

    def evaluar(self, ctx, cuerpo):
        evaluacion = Evaluacion()
        for i, r in enumerate(cuerpo.renglones, 1):
            ident = ctx.cargador.identificar(r.codigo)
            a, p = ident.articulo, ident.pieza
            motivos = []
            disponible = ctx.cargador.existencia(ctx.ubicacion_almacen.id, a.id) if a else None
            if a is None:
                motivos.append(Motivo("RG-10", Nivel.ROJO, "No se encontró ese artículo o pieza."))
            elif p is None and a.control == "PIEZA":
                motivos.append(
                    Motivo("CP-03", Nivel.ROJO, "Escanea el código de la pieza que falta.")
                )
            elif p is not None and (p.ubicacion_id != ctx.ubicacion_almacen.id or r.cantidad != 1):
                motivos.append(
                    Motivo(
                        "CP-03",
                        Nivel.ROJO,
                        "Solo se puede ajustar una pieza que figure en este almacén.",
                    )
                )
            elif disponible < r.cantidad:
                motivos.append(
                    Motivo("RG-04", Nivel.ROJO, "La cantidad supera la existencia del almacén.")
                )
            else:
                motivos.append(
                    Motivo("CP-03", Nivel.VERDE, "El faltante se registrará a nombre del almacén.")
                )
            evaluacion.renglones.append(
                RenglonEvaluado(
                    renglon=i,
                    codigo=r.codigo,
                    cantidad=r.cantidad,
                    motivos=motivos,
                    articulo_id=a.id if a else None,
                    pieza_id=p.id if p else None,
                    articulo=vista_articulo(hechos_de_articulo(a)) if a else None,
                    pieza=vista_pieza(hechos_de_pieza(p)) if p else None,
                    disponible=disponible,
                    extra={"observacion": r.observacion},
                )
            )
        return evaluacion

    def bloqueos(self, ctx, cuerpo):
        plan = PlanBloqueo()
        baja = ctx.cargador.ubicacion_virtual(UbicacionVirtual.BAJA)
        for r in cuerpo.renglones:
            ident = ctx.cargador.identificar(r.codigo)
            if ident.articulo:
                plan.existencias.update(
                    {(ctx.ubicacion_almacen.id, ident.articulo.id), (baja.id, ident.articulo.id)}
                )
            if ident.pieza:
                plan.piezas.add(ident.pieza.id)
        return plan

    def datos_vale(self, ctx, cuerpo, evaluacion):
        return DatosVale(firma_modo=FirmaModo.SESION, observacion=cuerpo.observacion)

    def construir_movimientos(self, ctx, cuerpo, evaluacion):
        baja = ctx.cargador.ubicacion_virtual(UbicacionVirtual.BAJA)
        return [
            MovimientoNuevo(
                renglon=r.renglon,
                articulo_id=r.articulo_id,
                pieza_id=r.pieza_id,
                cantidad=r.cantidad,
                origen_id=ctx.ubicacion_almacen.id,
                destino_id=baja.id,
                motivo_baja="Faltante de almacén",
                reglas=motivos_ids(r),
                observacion="; ".join(
                    dict.fromkeys(filter(None, [cuerpo.observacion, r.extra["observacion"]]))
                ),
            )
            for r in evaluacion.renglones
        ]
