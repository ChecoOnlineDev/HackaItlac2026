"""Tipo DEVOLUCION (US-DEV-001, fase 4).

Trabajador -> almacén que recibe. Reglas: V-01 a V-07, V-11, V-12, V-14, RG-05, SM-05, CF-11, F-08.

- Pieza escaneada (V-01): se abona a su titular, la traiga quien la traiga; no hace falta la
  credencial ni `trabajador_id`. Por cantidad (V-03): `trabajador_id` indica de quién es y no se
  acepta más de lo que tiene. Una pieza que no está en resguardo de nadie (V-02) no genera
  movimiento.
- Dañado (V-05): una pieza entra al almacén como No apta (con su evento en el historial de la
  pieza); un artículo por cantidad va a la ubicación BAJA y NO suma existencias del almacén.
- SM-05: nunca se bloquea por el trabajador (no vigente, en baja, inactivo), por límites, por
  autorización ni por un artículo inactivo.
- F-08: firma el almacenista con su sesión (`FirmaModo.SESION`): el vale no pide firma en pantalla.

Fuera de alcance (pospuestos): V-09 (cierre sin devolución), V-10 (consumible sobrante), V-13
(pérdida o robo).
"""

import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.core.excepciones import DatosInvalidos
from app.modulos.acceso.permisos import P
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.archivos.models import TipoAdjunto
from app.modulos.archivos.service import ArchivoService, decodificar_data_url
from app.modulos.catalogo.models import EstadoPieza
from app.modulos.movimientos.cargador import hechos_de_articulo, hechos_de_pieza
from app.modulos.movimientos.contexto import (
    ContextoVale,
    DatosVale,
    Evaluacion,
    MovimientoNuevo,
    PlanBloqueo,
    RenglonEvaluado,
)
from app.modulos.movimientos.evaluador import Motivo, Titular
from app.modulos.movimientos.evaluador_devolucion import (
    HechosRenglonDevolucion,
    evaluar_renglon_devolucion,
)
from app.modulos.movimientos.models import Condicion, FirmaModo, Nivel, TipoVale, Vale
from app.modulos.movimientos.schemas import RenglonIn, ValeIn
from app.modulos.movimientos.tipos.base import (
    ManejadorTipo,
    motivos_ids,
    vista_articulo,
    vista_pieza,
    vista_titular,
)

MOTIVO_BAJA_DANADO = "Dañado al devolverlo"


def servicio_inspecciones(session: Session) -> Any:
    """`InspeccionService` del módulo `inspecciones`. Punto de enchufe para las pruebas. Se usa
    `registrar_cambio_de_estado(pieza_id, *, estado, observacion, usuario_id)` (solo flush)."""
    from app.modulos.inspecciones.service import InspeccionService

    return InspeccionService(session)


def _campo(campo: str, mensaje: str) -> DatosInvalidos:
    return DatosInvalidos(mensaje, [{"campo": campo, "mensaje": mensaje}])


def _unir_observaciones(a: str | None, b: str | None) -> str | None:
    textos = [t for t in (a, b) if t]
    unicos = list(dict.fromkeys(textos))
    return "; ".join(unicos) if unicos else None


class DevolucionTipo(ManejadorTipo):
    tipo = TipoVale.DEVOLUCION
    permiso = P.DEVOLUCIONES_CREAR
    # F-08: firma el almacenista con su sesión; el trabajador recibe el comprobante (el vale).
    requiere_firma = False
    firma_modo = FirmaModo.SESION

    # ------------------------------------------------------------------ validación

    def validar_cuerpo(self, cuerpo: ValeIn, *, confirmar: bool) -> None:
        for i, renglon in enumerate(cuerpo.renglones):
            if renglon.pieza is not None:
                raise _campo(f"renglones.{i}.pieza", "Los datos de pieza son solo de las entradas.")
            if renglon.foto is not None and renglon.condicion != Condicion.DANADO:
                raise _campo(
                    f"renglones.{i}.foto", "La foto es solo para el equipo que regresa dañado."
                )
            if confirmar and renglon.foto is not None:
                decodificar_data_url(renglon.foto)  # 422 si no es una imagen válida
        if confirmar and not cuerpo.renglones:
            raise _campo("renglones", "Agrega al menos un renglón.")

    def normalizar_renglones(self, ctx: ContextoVale, cuerpo: ValeIn) -> list[RenglonIn]:
        """Una pieza repetida se ignora; un artículo por cantidad repetido con la misma condición
        suma (con otra condición queda aparte: una parte buena y otra dañada son dos renglones)."""
        salida: list[RenglonIn] = []
        piezas: set[uuid.UUID] = set()
        por_clave: dict[tuple[uuid.UUID, str | None], int] = {}
        desconocidos: set[str] = set()
        for renglon in cuerpo.renglones:
            ident = ctx.cargador.identificar(renglon.codigo)
            if ident.tipo == "PIEZA" and ident.pieza is not None:
                if ident.pieza.id in piezas:
                    continue
                piezas.add(ident.pieza.id)
                salida.append(renglon)
            elif (
                ident.tipo == "ARTICULO" and ident.articulo and ident.articulo.control == "CANTIDAD"
            ):
                clave = (ident.articulo.id, renglon.condicion)
                indice = por_clave.get(clave)
                if indice is None:
                    por_clave[clave] = len(salida)
                    salida.append(renglon)
                else:
                    previo = salida[indice]
                    salida[indice] = previo.model_copy(
                        update={
                            "cantidad": previo.cantidad + renglon.cantidad,
                            "observacion": _unir_observaciones(
                                previo.observacion, renglon.observacion
                            ),
                            "foto": previo.foto or renglon.foto,
                        }
                    )
            else:
                texto = renglon.codigo.strip().casefold()
                if texto in desconocidos:
                    continue
                desconocidos.add(texto)
                salida.append(renglon)
        return salida

    # ------------------------------------------------------------------ evaluación

    def evaluar(self, ctx: ContextoVale, cuerpo: ValeIn) -> Evaluacion:
        carga = ctx.cargador
        indicado = carga.trabajador(cuerpo.trabajador_id) if cuerpo.trabajador_id else None
        titular_indicado = None
        if indicado is not None:
            titular_indicado = Titular(
                "TRABAJADOR",
                indicado.id,
                indicado.nombre,
                f"la tiene {indicado.nombre} ({indicado.numero_empleado})",
                numero_empleado=indicado.numero_empleado,
            )
        evaluacion = Evaluacion()
        devuelto: dict[uuid.UUID, int] = defaultdict(int)
        titulares: dict[uuid.UUID, Any] = {}

        for numero, renglon in enumerate(cuerpo.renglones, start=1):
            ident = carga.identificar(renglon.codigo)
            articulo = ident.articulo
            pieza = ident.pieza
            titular: Titular | None = None
            en_resguardo = 0
            entrego = None
            origen_id: uuid.UUID | None = None
            titular_trabajador = None

            if pieza is not None:
                titular = carga.titular_de(pieza)
                if titular is not None and titular.tipo == "TRABAJADOR":
                    assert titular.id is not None
                    titular_trabajador = carga.trabajador(titular.id)
                    origen_id = pieza.ubicacion_id
                    entrego = _entrego(carga, titular_trabajador, pieza_id=pieza.id)
                    en_resguardo = 1
            elif articulo is not None and articulo.control == "CANTIDAD" and indicado is not None:
                titular = titular_indicado
                titular_trabajador = indicado
                ubicacion = carga.ubicacion_de_trabajador(indicado.id)
                origen_id = ubicacion.id
                en_resguardo = carga.existencia(ubicacion.id, articulo.id)
                entrego = _entrego(carga, indicado, articulo_id=articulo.id)
            if titular_trabajador is not None:
                titulares[titular_trabajador.id] = titular_trabajador

            hechos = HechosRenglonDevolucion(
                codigo=renglon.codigo,
                cantidad=renglon.cantidad,
                condicion=renglon.condicion,
                observacion=renglon.observacion,
                articulo=hechos_de_articulo(articulo) if articulo else None,
                pieza=hechos_de_pieza(pieza) if pieza else None,
                codigo_ajeno=ident.tipo == "OTRO",
                titular=titular,
                en_resguardo=en_resguardo,
                pedido_previo=devuelto[articulo.id] if articulo and pieza is None else 0,
                entrego_almacen_id=entrego.almacen_id if entrego else None,
                entrego_almacen_texto=(
                    f"{entrego.almacen_clave}, {entrego.almacen}" if entrego else None
                ),
                ubicacion_almacen_id=ctx.almacen.id,
            )
            resultado = evaluar_renglon_devolucion(hechos)
            if articulo and pieza is None:
                devuelto[articulo.id] += renglon.cantidad
            evaluacion.renglones.append(
                RenglonEvaluado(
                    renglon=numero,
                    codigo=renglon.codigo,
                    cantidad=renglon.cantidad,
                    motivos=resultado.motivos,
                    articulo_id=articulo.id if articulo else None,
                    pieza_id=pieza.id if pieza else None,
                    articulo=vista_articulo(hechos.articulo) if hechos.articulo else None,
                    pieza=vista_pieza(hechos.pieza) if hechos.pieza else None,
                    titular=vista_titular(titular) if titular else None,
                    # Lo que el titular tiene en resguardo de este artículo (una pieza, 1 o 0).
                    disponible=en_resguardo if articulo else None,
                    pide_observacion=resultado.pide_observacion,
                    extra={
                        "condicion": renglon.condicion,
                        "observacion": renglon.observacion,
                        "sin_movimiento": resultado.sin_movimiento,
                        "origen_id": origen_id,
                        "trabajador_id": titular_trabajador.id if titular_trabajador else None,
                        "control": articulo.control if articulo else None,
                    },
                )
            )

        # Una devolución sin nada que recibir no es un vale (V-02: no genera movimiento).
        if evaluacion.renglones and all(r.extra["sin_movimiento"] for r in evaluacion.renglones):
            evaluacion.motivos_vale.append(
                Motivo("V-02", Nivel.ROJO, "No hay nada que devolver en este vale.")
            )
        ficha_de = indicado or (next(iter(titulares.values())) if len(titulares) == 1 else None)
        if ficha_de is not None:
            evaluacion.trabajador = carga.ficha(ficha_de)
        return evaluacion

    # ---------------------------------------------------------------- confirmación

    def bloqueos(self, ctx: ContextoVale, cuerpo: ValeIn) -> PlanBloqueo:
        carga = ctx.cargador
        plan = PlanBloqueo()
        baja = carga.ubicacion_virtual(UbicacionVirtual.BAJA)
        trabajadores: set[uuid.UUID] = set()
        for renglon in cuerpo.renglones:
            ident = carga.identificar(renglon.codigo)
            articulo = ident.articulo
            if articulo is None:
                continue
            if ident.pieza is not None:
                titular = carga.titular_de(ident.pieza)
                if titular is None or titular.tipo != "TRABAJADOR" or titular.id is None:
                    continue  # V-02: no se mueve nada
                trabajadores.add(titular.id)
                assert ident.pieza.ubicacion_id is not None
                plan.existencias.add((ident.pieza.ubicacion_id, articulo.id))
                plan.existencias.add((ctx.ubicacion_almacen.id, articulo.id))
                plan.piezas.add(ident.pieza.id)
            elif articulo.control == "CANTIDAD" and cuerpo.trabajador_id is not None:
                trabajadores.add(cuerpo.trabajador_id)
                ubicacion = carga.ubicacion_de_trabajador(cuerpo.trabajador_id)
                plan.existencias.add((ubicacion.id, articulo.id))
                destino = baja if renglon.condicion == Condicion.DANADO else ctx.ubicacion_almacen
                plan.existencias.add((destino.id, articulo.id))
        # Orden canónico: los trabajadores (por id) van antes que las existencias.
        if len(trabajadores) == 1:
            plan.trabajador_id = next(iter(trabajadores))
        else:
            for trabajador_id in sorted(trabajadores, key=str):
                carga.repository.bloquear_trabajador(trabajador_id)
        return plan

    def datos_vale(self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion) -> DatosVale:
        """El vale es del trabajador al que se abona; si vienen piezas de varios titulares, el
        vale no lleva uno solo (cada movimiento anota el suyo)."""
        con_movimiento = [r for r in evaluacion.renglones if not r.extra["sin_movimiento"]]
        trabajadores = {r.extra["trabajador_id"] for r in con_movimiento}
        trabajador_id = next(iter(trabajadores)) if len(trabajadores) == 1 else None
        periodo = None
        if trabajador_id is not None:
            trabajador = ctx.cargador.trabajador(trabajador_id)
            periodo = ctx.cargador.trabajadores.periodo_vigente(trabajador, ctx.hoy)
        return DatosVale(
            trabajador_id=trabajador_id,
            periodo_contrato_id=periodo.id if periodo else None,
            firma_modo=FirmaModo.SESION,
        )

    def construir_movimientos(
        self, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion
    ) -> list[MovimientoNuevo]:
        baja = ctx.cargador.ubicacion_virtual(UbicacionVirtual.BAJA)
        movimientos = []
        for r in evaluacion.renglones:
            if r.extra["sin_movimiento"]:
                continue  # V-02
            assert r.articulo_id is not None and r.extra["origen_id"] is not None
            danado = r.extra["condicion"] == Condicion.DANADO
            # V-05: un artículo por cantidad dañado no regresa a existencias; una pieza dañada
            # entra al almacén (como No apta).
            a_baja = danado and r.pieza_id is None
            movimientos.append(
                MovimientoNuevo(
                    renglon=r.renglon,
                    articulo_id=r.articulo_id,
                    pieza_id=r.pieza_id,
                    cantidad=r.cantidad,
                    origen_id=r.extra["origen_id"],
                    destino_id=baja.id if a_baja else ctx.ubicacion_almacen.id,
                    trabajador_id=r.extra["trabajador_id"],
                    condicion=str(r.extra["condicion"]),
                    motivo_baja=MOTIVO_BAJA_DANADO if a_baja else None,
                    nivel=r.nivel,
                    reglas=motivos_ids(r),
                    observacion=r.extra["observacion"],
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
        """V-05: la pieza dañada queda No apta (con su evento) y la foto se guarda ligada al
        movimiento. Todo en la transacción del vale."""
        por_renglon = {m.renglon: m for m in movimientos}
        servicio = None
        archivos = ArchivoService(ctx.session)
        for r in evaluacion.renglones:
            if r.extra["sin_movimiento"] or r.extra["condicion"] != Condicion.DANADO:
                continue
            if r.pieza_id is not None:
                if servicio is None:
                    servicio = servicio_inspecciones(ctx.session)
                servicio.registrar_cambio_de_estado(
                    r.pieza_id,
                    estado=EstadoPieza.NO_APTO,
                    observacion=f"Devuelta dañada ({vale.folio}): {r.extra['observacion']}",
                    usuario_id=ctx.usuario.id,
                )
            foto = cuerpo.renglones[r.renglon - 1].foto
            if foto:
                archivos.guardar(
                    tipo=TipoAdjunto.FOTO_DANO,
                    contenido=decodificar_data_url(foto),
                    subido_por=ctx.usuario.id,
                    vale_id=vale.id,
                    movimiento_id=por_renglon[r.renglon].id,
                )


def _entrego(carga, trabajador, *, pieza_id=None, articulo_id=None):
    """El pendiente del trabajador que corresponde al renglón (dice qué almacén lo entregó)."""
    for p in carga.ficha(trabajador).resguardo:
        if pieza_id is not None and p.pieza_id == pieza_id:
            return p
        if articulo_id is not None and p.pieza_id is None and p.articulo_id == articulo_id:
            return p
    return None
