"""El motor: evalúa el semáforo, confirma vales y consulta vales.

`MovimientoService` es genérico: no conoce las reglas de ningún tipo de vale. Cada tipo
(`tipos/`) le da sus ganchos (`ManejadorTipo`); el motor pone lo común:

    evaluar    permiso -> cuerpo -> contexto -> normalizar -> `evaluar` del tipo (no escribe).
    confirmar  permiso -> cuerpo -> idempotencia -> UNA transacción:
               bloquear filas (orden canónico) -> volver a evaluar -> autorización -> folio ->
               vale -> movimientos con saldos -> existencias y ubicación de piezas -> firma ->
               autorización usada -> efectos del tipo -> commit.

Solo este módulo escribe vales, movimientos, existencias, folios y `pieza.ubicacion_id`.
"""

import hashlib
import json
import secrets
import uuid
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError, InvalidRequestError
from sqlalchemy.orm import Session

from app.core import errores_bd
from app.core.excepciones import DatosInvalidos, NoEncontrado, SinPermiso
from app.core.ids import nuevo_id
from app.core.paginacion import Pagina, Paginacion
from app.core.tiempo import ZONA_MX, ahora_utc, hoy_mx
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.exceptions import AlmacenCerrado
from app.modulos.almacenes.models import EstadoAlmacen, UbicacionVirtual
from app.modulos.almacenes.service import AlmacenService
from app.modulos.archivos.models import TipoAdjunto
from app.modulos.archivos.service import ArchivoService, decodificar_data_url
from app.modulos.autorizaciones.exceptions import (
    AprobacionInvalida,
    AutorizacionInvalida,
    AutorizacionPropia,
    RequiereAprobacionDespacho,
)
from app.modulos.autorizaciones.models import Autorizacion
from app.modulos.autorizaciones.service import AutorizacionService, RenglonVale
from app.modulos.catalogo.codigos import CodigoService
from app.modulos.catalogo.models import Pieza, TipoCodigo
from app.modulos.catalogo.service import CatalogoService
from app.modulos.movimientos.cargador import Cargador
from app.modulos.movimientos.contexto import (
    ContextoVale,
    Evaluacion,
    MovimientoNuevo,
    PlanBloqueo,
    RenglonEvaluado,
)
from app.modulos.movimientos.evaluador import Motivo
from app.modulos.movimientos.exceptions import (
    ExistenciaInsuficiente,
    IdClienteEnUso,
    IdClienteOtroCuerpo,
    ValeCambio,
    ValeNoEncontrado,
)
from app.modulos.movimientos.models import (
    PREFIJO_FOLIO,
    EstadoVale,
    Movimiento,
    Nivel,
    ReservaPapel,
    TipoVale,
    Vale,
)
from app.modulos.movimientos.repository import FiltroVales, MovimientoRepository
from app.modulos.movimientos.schemas import (
    AlmacenResumenOut,
    ArticuloEvaluadoOut,
    CancelacionIn,
    CancelacionVistaOut,
    ConfirmarIn,
    EvaluacionOut,
    MotivoOut,
    PersonaOut,
    PiezaEvaluadaOut,
    RenglonConfirmadoOut,
    RenglonEvaluadoOut,
    RenglonIn,
    RenglonValeOut,
    ReservaPapelOut,
    RutaEvaluacionOut,
    TitularOut,
    TrabajadorValeOut,
    UbicacionOut,
    ValeConfirmadoOut,
    ValeDetalleOut,
    ValeFilters,
    ValeIn,
    ValeListItem,
    ValidoOut,
)
from app.modulos.movimientos.tipos import manejador_de
from app.modulos.movimientos.tipos.base import ManejadorTipo
from app.modulos.trabajadores.service import TrabajadorService

# Una confirmación que choca con otra y MySQL resuelve como interbloqueo se repite desde el
# principio; con el orden canónico de bloqueos casi nunca ocurre.
INTENTOS_INTERBLOQUEO = 3
ERRNO_INTERBLOQUEO = 1213


def huella_del_cuerpo(cuerpo: ConfirmarIn) -> str:
    """SHA-256 del cuerpo canónico de una confirmación (llaves ordenadas, sin espacios). La imagen
    y el trazo de la firma quedan fuera: pesan mucho y un reintento puede volver a firmar sin
    que el vale cambie (el vale conserva la firma de la primera vez)."""
    datos = cuerpo.model_dump(
        mode="json", exclude={"firma": {"imagen", "trazo"}, "reserva_papel_id": True}
    )
    canonico = json.dumps(datos, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _a_utc_naive(valor: datetime) -> datetime:
    return valor.astimezone(UTC).replace(tzinfo=None)


class MovimientoService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = MovimientoRepository(session)
        self.acceso = AccesoService(session)
        self.catalogo = CatalogoService(session)
        self.trabajadores = TrabajadorService(session)
        self.almacenes = AlmacenService(session)
        self.autorizaciones = AutorizacionService(session)
        self.archivos = ArchivoService(session)
        self.codigos = CodigoService(session)

    # ================================================================ permisos y almacén

    def manejador(self, tipo: TipoVale | str) -> ManejadorTipo:
        return manejador_de(tipo)

    def exigir_permiso_del_tipo(self, usuario: Usuario, tipo: TipoVale | str) -> ManejadorTipo:
        """El permiso depende del tipo de vale (api-contracts, "Permiso y campos propios"). Se
        verifica por clave, nunca por el nombre del rol."""
        manejador = self.manejador(tipo)
        self.acceso.exigir_permiso(usuario, manejador.permiso)
        return manejador

    def resolver_almacen_del_vale(
        self,
        usuario: Usuario,
        almacen_id: uuid.UUID | None,
        por_defecto: str | None = None,
    ) -> uuid.UUID:
        """El almacén del vale (RG-07, AC-06). Con `almacenes.todos` se indica con `almacen_id`
        (o `por_defecto`, la clave de un almacén); sin él es el asignado y, si el cuerpo trae
        otro, el usuario cambió de almacén: 409 `ALMACEN_CAMBIO` (AC-13)."""
        if self.acceso.puede_operar_todos_los_almacenes(usuario):
            if almacen_id is None and por_defecto:
                return self.almacenes.obtener_por_clave(por_defecto).id
            return self.acceso.resolver_almacen(usuario, almacen_id)
        if usuario.almacen_id is None:
            raise SinPermiso("No tienes un almacén asignado.")
        self.acceso.exigir_mismo_almacen(usuario, almacen_id)
        return usuario.almacen_id

    # ======================================================================= contexto

    def _contexto(
        self,
        usuario: Usuario,
        almacen_id: uuid.UUID,
        *,
        bloqueado: bool = False,
    ) -> ContextoVale:
        almacen = self.almacenes.obtener(almacen_id)
        cargador = Cargador(
            self.repository, self.catalogo, self.trabajadores, self.almacenes, usuario
        )
        return ContextoVale(
            session=self.session,
            usuario=usuario,
            almacen=almacen,
            ubicacion_almacen=self.almacenes.ubicacion_de_almacen(almacen.id),
            cargador=cargador,
            hoy=hoy_mx(),
            ahora=ahora_utc(),
            bloqueado=bloqueado,
        )

    @staticmethod
    def _normalizar(manejador: ManejadorTipo, ctx: ContextoVale, cuerpo: ValeIn) -> ValeIn:
        renglones: list[RenglonIn] = manejador.normalizar_renglones(ctx, cuerpo)
        return cuerpo.model_copy(update={"renglones": renglones})

    # ======================================================================== evaluar

    def evaluar(self, usuario: Usuario, cuerpo: ValeIn) -> EvaluacionOut:
        """`POST /api/vales/evaluar`: el semáforo de un borrador. No escribe nada (E-28)."""
        manejador = self.exigir_permiso_del_tipo(usuario, cuerpo.tipo)
        manejador.validar_cuerpo(cuerpo, confirmar=False)
        almacen_id = manejador.almacen_operativo(self, usuario, cuerpo)
        ctx = self._contexto(usuario, almacen_id)
        evaluacion, normal = self._evaluar(manejador, ctx, cuerpo)
        self._aplicar_autorizacion(ctx, evaluacion, normal, silencioso=True)
        return self._salida_evaluacion(ctx, evaluacion)

    def reservar_papel(self, usuario: Usuario, cuerpo: ConfirmarIn) -> ReservaPapelOut:
        """Reserva folio y QR de corta duración para imprimir el ticket antes de firmarlo."""
        manejador = self.exigir_permiso_del_tipo(usuario, cuerpo.tipo)
        if cuerpo.tipo != TipoVale.ENTREGA or cuerpo.firma is None or cuerpo.firma.modo != "PAPEL":
            raise DatosInvalidos("Elige firma en papel para preparar un ticket.")
        if cuerpo.firma.imagen:
            raise DatosInvalidos("Primero imprime el ticket; adjunta la foto al confirmar.")
        manejador.validar_cuerpo(cuerpo, confirmar=False)
        evaluacion = self.evaluar(usuario, cuerpo)
        if not evaluacion.puede_confirmar:
            raise ValeCambio(detalles=evaluacion.model_dump(mode="json"))
        huella = huella_del_cuerpo(cuerpo)
        existente = self.repository.reserva_papel_por_id_cliente(cuerpo.id_cliente)
        if existente:
            if existente.responsable_id != usuario.id or existente.huella_cuerpo != huella:
                raise IdClienteOtroCuerpo()
            if existente.vence_en <= ahora_utc() and existente.vale_id is None:
                raise DatosInvalidos("El ticket venció. Vuelve a preparar e imprimir otro.")
            return ReservaPapelOut(
                id=existente.id,
                folio=existente.folio,
                token=existente.token,
                vence_en=existente.vence_en,
                ticket=existente.ticket,
                evaluacion=evaluacion,
            )
        try:
            # Mantén el orden de confirmar: usuario, almacén, trabajador y contador. La FK de
            # esta reserva no debe invertirlo contra los bloqueos de confirmación.
            self._aislar_transaccion()
            usuario = self.acceso.usuarios.bloquear(usuario.id)
            self.exigir_permiso_del_tipo(usuario, cuerpo.tipo)
            almacen_id = manejador.almacen_operativo(self, usuario, cuerpo)
            self.repository.bloquear_almacenes([almacen_id])
            assert cuerpo.trabajador_id is not None
            self.repository.bloquear_trabajador(cuerpo.trabajador_id)
            self.session.expire_all()
            usuario = self.acceso.usuarios.bloquear(usuario.id)
            ctx = self._contexto(usuario, almacen_id)
            evaluacion, normal = self._evaluar(manejador, ctx, cuerpo)
            self._aplicar_autorizacion(ctx, evaluacion, normal, silencioso=True)
            if not evaluacion.puede_confirmar:
                raise self._vale_cambio(ctx, evaluacion)
            evaluacion_salida = self._salida_evaluacion(ctx, evaluacion)
            almacen = self.almacenes.obtener(almacen_id)
            serie = self.repository.bloquear_serie(almacen.id, TipoVale.ENTREGA)
            serie.ultimo += 1
            folio = f"{almacen.clave}-{PREFIJO_FOLIO[TipoVale.ENTREGA]}-{serie.ultimo:06d}"
            trabajador = evaluacion.trabajador
            ticket = {
                "creado_en": ahora_utc().isoformat(timespec="seconds") + "Z",
                "trabajador": {
                    "nombre": trabajador.nombre,
                    "numero_empleado": trabajador.numero_empleado,
                }
                if trabajador
                else None,
                "proyecto": evaluacion_salida.proyecto.model_dump(mode="json")
                if evaluacion_salida.proyecto
                else None,
                "articulos": [
                    {
                        "renglon": r.renglon,
                        "codigo": r.codigo,
                        "codigo_pieza": r.pieza.get("codigo") if r.pieza else None,
                        "numero_serie": r.pieza.get("numero_serie") if r.pieza else None,
                        "nombre": r.articulo.get("nombre"),
                        "marca": r.articulo.get("marca"),
                        "modelo": r.articulo.get("modelo"),
                        "talla": r.articulo.get("talla"),
                        "cantidad": r.cantidad,
                    }
                    for r in evaluacion.renglones
                    if r.articulo is not None
                ],
                "observacion": cuerpo.observacion,
                "leyenda": (
                    "Recibí el equipo descrito y me comprometo a conservarlo y devolverlo "
                    "cuando corresponda."
                ),
            }
            reserva = self.repository.add_reserva_papel(
                ReservaPapel(
                    id=nuevo_id(),
                    id_cliente=cuerpo.id_cliente,
                    responsable_id=usuario.id,
                    almacen_id=almacen.id,
                    tipo=TipoVale.ENTREGA,
                    folio=folio,
                    token=secrets.token_urlsafe(16),
                    huella_cuerpo=huella,
                    ticket=ticket,
                    vence_en=ahora_utc() + timedelta(minutes=30),
                )
            )
            self.session.commit()
            return ReservaPapelOut(
                id=reserva.id,
                folio=reserva.folio,
                token=reserva.token,
                vence_en=reserva.vence_en,
                ticket=reserva.ticket,
                evaluacion=evaluacion_salida,
            )
        except DBAPIError as exc:
            self.session.rollback()
            if errores_bd.es_restriccion(exc, "uq_reserva_papel_id_cliente"):
                existente = self.repository.reserva_papel_por_id_cliente(cuerpo.id_cliente)
                if existente is not None:
                    if (
                        existente.responsable_id != usuario.id
                        or existente.huella_cuerpo != huella
                    ):
                        raise IdClienteOtroCuerpo() from exc
                    return ReservaPapelOut(
                        id=existente.id,
                        folio=existente.folio,
                        token=existente.token,
                        vence_en=existente.vence_en,
                        ticket=existente.ticket,
                        evaluacion=evaluacion_salida,
                    )
            raise
        except Exception:
            self.session.rollback()
            raise

    def _evaluar(
        self, manejador: ManejadorTipo, ctx: ContextoVale, cuerpo: ValeIn
    ) -> tuple[Evaluacion, ValeIn]:
        normal = self._normalizar(manejador, ctx, cuerpo)
        evaluacion = manejador.evaluar(ctx, normal)
        evaluacion.admite_sin_renglones = manejador.admite_sin_renglones
        self._avisar_almacen_cerrado(manejador, ctx, normal, evaluacion)
        return evaluacion, normal

    @staticmethod
    def _almacen_cerrado(manejador: ManejadorTipo, ctx: ContextoVale, cuerpo: ValeIn):
        """AL-04: el primer almacén cerrado de los que mueve el vale, o `None`."""
        for almacen in manejador.almacenes_involucrados(ctx, cuerpo):
            if almacen.estado == EstadoAlmacen.CERRADO:
                return almacen
        return None

    def _avisar_almacen_cerrado(
        self, manejador: ManejadorTipo, ctx: ContextoVale, cuerpo: ValeIn, evaluacion: Evaluacion
    ) -> None:
        """AL-04: la evaluación de un vale con un almacén cerrado trae un motivo rojo."""
        if self._almacen_cerrado(manejador, ctx, cuerpo) is not None:
            evaluacion.motivos_vale.insert(
                0, Motivo("AL-04", Nivel.ROJO, "Ese almacén está cerrado.")
            )

    def evaluar_para_autorizacion(
        self,
        usuario: Usuario,
        almacen_id: uuid.UUID,
        trabajador_id: uuid.UUID,
        renglones: list[tuple[str, int]],
    ) -> Evaluacion:
        """Evalúa una ENTREGA hipotética `(codigo, cantidad)` en `almacen_id`, sin escribir.
        La usa el verificador de `autorizaciones` (A-06)."""
        cuerpo = ValeIn(
            tipo=TipoVale.ENTREGA,
            trabajador_id=trabajador_id,
            renglones=[RenglonIn(codigo=c, cantidad=n) for c, n in renglones],
        )
        manejador = self.manejador(TipoVale.ENTREGA)
        ctx = self._contexto(usuario, almacen_id)
        evaluacion, _ = self._evaluar(manejador, ctx, cuerpo)
        return evaluacion

    def evaluar_traslado_para_autorizacion(
        self,
        usuario: Usuario,
        origen_id: uuid.UUID,
        destino_id: uuid.UUID,
        renglones: list[tuple[str, int]],
    ) -> Evaluacion:
        """Evalúa un TRASPASO hipotético `(codigo, cantidad)` de `origen_id` a `destino_id`, como
        lo evaluaría `usuario` al enviarlo, sin escribir. Lo usa el verificador de `autorizaciones`
        para una solicitud de TRASLADO (X-17, A-06). Los renglones salen normalizados."""
        cuerpo = ValeIn(
            tipo=TipoVale.TRASPASO,
            destino_almacen_id=destino_id,
            renglones=[RenglonIn(codigo=c, cantidad=n) for c, n in renglones],
        )
        manejador = self.manejador(TipoVale.TRASPASO)
        ctx = self._contexto(usuario, origen_id)
        evaluacion, _ = self._evaluar(manejador, ctx, cuerpo)
        return evaluacion

    def _aplicar_autorizacion(
        self,
        ctx: ContextoVale,
        evaluacion: Evaluacion,
        cuerpo: ValeIn,
        *,
        silencioso: bool,
    ) -> Autorizacion | None:
        """A-03: si hay naranjas y el cuerpo trae `autorizacion_id`, la valida contra ellos
        (mismo almacén, mismo trabajador, mismos renglones y cantidades, un solo uso). Marca como
        autorizados los naranjas que cubre. Al evaluar no falla: deja el motivo en
        `evaluacion.autorizacion_error`."""
        if cuerpo.tipo == TipoVale.TRASPASO:
            return self._aplicar_autorizacion_de_traslado(
                ctx, evaluacion, cuerpo, silencioso=silencioso
            )
        if evaluacion.requiere_aprobacion_despacho:
            return self._aplicar_despacho(ctx, evaluacion, cuerpo, silencioso=silencioso)
        naranjas = [r for r in evaluacion.renglones if r.nivel == Nivel.NARANJA]
        if not naranjas or cuerpo.autorizacion_id is None or cuerpo.trabajador_id is None:
            return None
        try:
            autorizacion = self.autorizaciones.validar_para_vale(
                cuerpo.autorizacion_id,
                ctx.almacen.id,
                cuerpo.trabajador_id,
                [RenglonVale(r.codigo, r.cantidad) for r in naranjas],
                ctx.usuario,
            )
        except (AutorizacionInvalida, AprobacionInvalida, AutorizacionPropia, NoEncontrado) as exc:
            if not silencioso:
                raise
            evaluacion.autorizacion_error = exc.mensaje
            return None
        for r in naranjas:
            r.autorizado = True
        return autorizacion

    def _aplicar_despacho(self, ctx, evaluacion, cuerpo, *, silencioso):
        requeridos = [
            r for r in evaluacion.renglones if r.extra.get("es_epp") or r.nivel == Nivel.NARANJA
        ]
        for r in requeridos:
            r.extra["aprobacion"] = "PENDIENTE"
        if cuerpo.autorizacion_id is None:
            if not silencioso:
                raise RequiereAprobacionDespacho(
                    detalles={
                        "regla": "DE-01",
                        "renglones": [
                            {"renglon": r.renglon, "codigo": r.codigo} for r in requeridos
                        ],
                    }
                )
            return None
        proyecto_id = evaluacion.proyecto["id"] if evaluacion.proyecto else None
        try:
            a = self.autorizaciones.validar_despacho_para_vale(
                cuerpo.autorizacion_id,
                ctx.almacen.id,
                cuerpo.trabajador_id,
                proyecto_id,
                [RenglonVale(r.codigo, r.cantidad, r.renglon) for r in requeridos],
                ctx.usuario,
                bloquear=ctx.bloqueado,
            )
        except (AutorizacionInvalida, AprobacionInvalida, AutorizacionPropia, NoEncontrado) as exc:
            if not silencioso:
                raise
            evaluacion.autorizacion_error = exc.mensaje
            a = self.autorizaciones.repository.get(cuerpo.autorizacion_id)
            # DE-13: explicar cada renglón sin considerar válida una aprobación de otro vale.
            if (
                a
                and a.almacen_id == ctx.almacen.id
                and a.trabajador_id == cuerpo.trabajador_id
                and a.tipo == "DESPACHO"
            ):
                resoluciones = {
                    r["codigo"].strip().casefold(): r for r in a.renglones_resueltos or []
                }
                for r in requeridos:
                    decidido = resoluciones.get(r.codigo.strip().casefold())
                    if a.estado == "PENDIENTE":
                        continue
                    r.extra["aprobacion"] = (
                        "NO_INCLUIDO"
                        if decidido is None
                        else "RECHAZADO"
                        if decidido["decision"] == "RECHAZADO"
                        else "CANTIDAD_MAYOR"
                        if r.cantidad > decidido["cantidad"]
                        else "APROBADO"
                    )
                    r.extra["motivo_rechazo"] = decidido.get("motivo") if decidido else None
            return None
        for r in requeridos:
            r.extra["aprobacion"] = "APROBADO"
            if r.nivel == Nivel.NARANJA:
                r.autorizado = True
        evaluacion.autorizado_vale = True
        return a

    def _aplicar_autorizacion_de_traslado(
        self,
        ctx: ContextoVale,
        evaluacion: Evaluacion,
        cuerpo: ValeIn,
        *,
        silencioso: bool,
    ) -> Autorizacion | None:
        """X-17 y X-19: el motivo naranja X-17 del vale lo cubre una autorización de TRASLADO
        aprobada, vigente, sin usar, del mismo origen y destino, que cubra cada renglón (solo se
        pueden quitar renglones). Al evaluar no falla: deja el motivo en `autorizacion_error`.
        Sin X-17 (envío propio, ruta habitual...) no se usa ni se gasta ninguna autorización."""
        if cuerpo.autorizacion_id is None or not any(
            m.regla == "X-17" for m in evaluacion.motivos_vale
        ):
            return None
        assert cuerpo.destino_almacen_id is not None
        try:
            autorizacion = self.autorizaciones.validar_traslado_para_vale(
                cuerpo.autorizacion_id,
                ctx.almacen.id,
                cuerpo.destino_almacen_id,
                [RenglonVale(r.codigo, r.cantidad) for r in evaluacion.renglones],
                ctx.usuario,
            )
        except (AutorizacionInvalida, AutorizacionPropia, NoEncontrado) as exc:
            if not silencioso:
                raise
            evaluacion.autorizacion_error = exc.mensaje
            return None
        evaluacion.autorizado_vale = True
        return autorizacion

    # ======================================================================= confirmar

    def confirmar(
        self,
        usuario: Usuario,
        cuerpo: ConfirmarIn,
        *,
        dispositivo: str | None = None,
        aislar: bool = True,
        commit: bool = True,
        lote_id: uuid.UUID | None = None,
    ) -> tuple[ValeConfirmadoOut, bool]:
        """`POST /api/vales`. Devuelve `(vale, creado)`: `creado` es falso si el `id_cliente` ya
        existía (idempotencia: se devuelve el vale que se guardó la primera vez).

        `aislar` y `commit` son para los datos de prueba, que corren dentro de la transacción de
        `app/datos_prueba.py`: sin ellos no se abre transacción propia ni se hace commit."""
        manejador = self.exigir_permiso_del_tipo(usuario, cuerpo.tipo)
        manejador.validar_cuerpo(cuerpo, confirmar=True)

        existente = self.repository.vale_por_id_cliente(cuerpo.id_cliente)
        if existente is not None:
            return self._repetido(existente, usuario, cuerpo), False

        for intento in range(1, INTENTOS_INTERBLOQUEO + 1):
            try:
                return self._confirmar_una_vez(
                    manejador,
                    usuario,
                    cuerpo,
                    dispositivo,
                    aislar=aislar,
                    commit=commit,
                    lote_id=lote_id,
                )
            except DBAPIError as exc:
                if commit:
                    self.session.rollback()
                traducido = self._traducir(exc)
                if traducido is not None:
                    raise traducido from exc
                if errores_bd.es_restriccion(exc, "uq_vale_id_cliente") and commit:
                    existente = self.repository.vale_por_id_cliente(cuerpo.id_cliente)
                    if existente is not None:
                        return self._repetido(existente, usuario, cuerpo), False
                interbloqueo = errores_bd.violacion(exc).errno == ERRNO_INTERBLOQUEO
                if interbloqueo and commit and intento < INTENTOS_INTERBLOQUEO:
                    continue
                raise
            except Exception:
                if commit:
                    self.session.rollback()
                raise
        raise AssertionError("inalcanzable")  # pragma: no cover

    def _confirmar_una_vez(
        self,
        manejador: ManejadorTipo,
        usuario: Usuario,
        cuerpo: ConfirmarIn,
        dispositivo: str | None,
        *,
        aislar: bool,
        commit: bool,
        lote_id: uuid.UUID | None,
    ) -> tuple[ValeConfirmadoOut, bool]:
        if aislar:
            self._aislar_transaccion()
        # DE-16: leer la autonomía vigente, no la identidad cargada al autenticar.
        usuario = self.acceso.usuarios.bloquear(usuario.id)
        self.exigir_permiso_del_tipo(usuario, cuerpo.tipo)
        almacen_id = manejador.almacen_operativo(self, usuario, cuerpo)
        ctx = self._contexto(usuario, almacen_id, bloqueado=True)
        normal = self._normalizar(manejador, ctx, cuerpo)
        assert isinstance(normal, ConfirmarIn)

        # 1. Bloquear en orden canónico y descartar lo leído antes de bloquear.
        plan = manejador.bloqueos(ctx, normal)
        self._bloquear(plan, ctx, manejador, normal)
        self.session.expire_all()
        self.acceso.usuarios.bloquear(usuario.id)
        self.repository.bloquear_almacenes(
            [a.id for a in manejador.almacenes_involucrados(ctx, normal)]
        )
        ctx.cargador.olvidar_lecturas()

        # 2. Otra confirmación con el mismo `id_cliente` pudo ganar mientras esperábamos.
        ganador = self.repository.vale_por_id_cliente(cuerpo.id_cliente)
        if ganador is not None:
            if commit:
                self.session.rollback()
            return self._repetido(ganador, usuario, cuerpo), False

        # 3. AL-04: un almacén cerrado no recibe ni envía. Se mira ya con las filas bloqueadas y la
        #    sesión limpia, así un cierre que se confirmó mientras esperábamos sí se ve.
        cerrado = self._almacen_cerrado(manejador, ctx, normal)
        if cerrado is not None:
            raise AlmacenCerrado(cerrado)

        # 3b. Volver a evaluar, ya con las filas bloqueadas (RG-08).
        evaluacion = manejador.evaluar(ctx, normal)
        evaluacion.admite_sin_renglones = manejador.admite_sin_renglones
        manejador.exigir_al_confirmar(normal, evaluacion)
        if evaluacion.nivel == Nivel.ROJO:
            raise self._vale_cambio(ctx, evaluacion)
        autorizacion = self._aplicar_autorizacion(ctx, evaluacion, normal, silencioso=False)
        if not evaluacion.puede_confirmar:
            raise self._vale_cambio(ctx, evaluacion)

        reserva_papel = None
        if cuerpo.firma and cuerpo.firma.modo == "PAPEL":
            if cuerpo.reserva_papel_id is None:
                raise DatosInvalidos("Vuelve a preparar e imprimir el ticket antes de confirmar.")
            reserva_papel = self.repository.reserva_papel(cuerpo.reserva_papel_id, bloquear=True)
            if (
                reserva_papel is None
                or reserva_papel.responsable_id != usuario.id
                or reserva_papel.almacen_id != ctx.almacen.id
                or reserva_papel.tipo != TipoVale.ENTREGA
                or reserva_papel.id_cliente != cuerpo.id_cliente
                or reserva_papel.huella_cuerpo != huella_del_cuerpo(cuerpo)
                or reserva_papel.vale_id is not None
                or reserva_papel.vence_en <= ahora_utc()
            ):
                raise DatosInvalidos("El ticket reservado venció o cambió. Vuelve a prepararlo.")
        elif cuerpo.reserva_papel_id is not None:
            raise DatosInvalidos("La reserva solo se usa al firmar con papel.")

        # 4. Vale: folio, token y responsable (RG-06, F-03, F-05).
        datos = manejador.datos_vale(ctx, normal, evaluacion)
        if reserva_papel is not None:
            proyecto_ticket = (reserva_papel.ticket.get("proyecto") or {}).get("id")
            proyecto_actual = str(datos.proyecto_id) if datos.proyecto_id is not None else None
            if proyecto_ticket != proyecto_actual:
                raise DatosInvalidos(
                    "El proyecto del ticket cambió. Vuelve a preparar e imprimirlo."
                )
        vale = self.repository.add_vale(
            Vale(
                id=nuevo_id(),
                id_cliente=cuerpo.id_cliente,
                huella_cuerpo=huella_del_cuerpo(cuerpo),
                lote_id=lote_id,
                tipo=manejador.tipo,
                folio=reserva_papel.folio
                if reserva_papel
                else self._asignar_folio(ctx, manejador.tipo),
                almacen_id=ctx.almacen.id,
                trabajador_id=datos.trabajador_id,
                periodo_contrato_id=datos.periodo_contrato_id,
                proyecto_id=datos.proyecto_id,
                destino_almacen_id=datos.destino_almacen_id,
                vale_origen_id=datos.vale_origen_id,
                estado=datos.estado,
                responsable_id=usuario.id,
                autorizacion_id=autorizacion.id if autorizacion else None,
                observacion=datos.observacion or cuerpo.observacion,
                firma_modo=datos.firma_modo,
                token=reserva_papel.token if reserva_papel else secrets.token_urlsafe(16),
                dispositivo=dispositivo[:200] if dispositivo else None,
                creado_en=ctx.ahora,
            )
        )
        if reserva_papel:
            reserva_papel.vale_id = vale.id

        # 5. Movimientos, existencias y ubicación de las piezas (RG-01).
        nuevos = manejador.construir_movimientos(ctx, normal, evaluacion)
        movimientos = self._escribir_movimientos(ctx, vale, nuevos)

        # 6. Firma del trabajador (F-02) y autorización usada (A-03), en la misma transacción.
        if manejador.requiere_firma:
            self._guardar_firma(usuario, vale, cuerpo)
        if autorizacion is not None:
            self.autorizaciones.marcar_usada(autorizacion.id)
        self._registrar_codigos(vale)

        # 7. Efectos propios del tipo.
        manejador.al_confirmar(ctx, normal, evaluacion, vale, movimientos)
        from app.modulos.movimientos.sello import SelloService

        SelloService(self.session).sellar(vale, movimientos)

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        # El router programa USADA y traslado lateral después del commit (NT-07/X-20).
        return self._confirmada(vale), True

    def _aislar_transaccion(self) -> None:
        """Empieza una transacción limpia en READ COMMITTED.

        La autenticación ya leyó en esta sesión: en REPEATABLE READ (el valor por defecto de
        MySQL) esa lectura fija una foto de los datos y, tras esperar un bloqueo, las lecturas
        normales no verían lo que la otra confirmación guardó. En READ COMMITTED cada consulta ve
        lo último confirmado. En las pruebas la sesión va dentro de una transacción externa y no
        se toca el nivel."""
        self.session.commit()
        if isinstance(self.session.get_bind(), Connection):
            return
        try:
            self.session.connection(execution_options={"isolation_level": "READ COMMITTED"})
        except InvalidRequestError:  # pragma: no cover - ya había una transacción abierta
            pass

    def _bloquear(
        self, plan: PlanBloqueo, ctx: ContextoVale, manejador: ManejadorTipo, cuerpo: ValeIn
    ) -> None:
        """Orden de bloqueo: usuario, almacenes, vales, trabajador, existencias por ubicación y
        artículo, piezas y contador de folios. Todos los tipos lo siguen: sin interbloqueos."""
        self.repository.bloquear_almacenes(
            [a.id for a in manejador.almacenes_involucrados(ctx, cuerpo)]
        )
        self.repository.bloquear_vales(plan.vales)
        if plan.trabajador_id is not None:
            self.repository.bloquear_trabajador(plan.trabajador_id)
        self.repository.bloquear_existencias(plan.existencias)
        self.repository.bloquear_piezas(plan.piezas)
        self.repository.bloquear_serie(ctx.almacen.id, manejador.tipo)

    def _asignar_folio(self, ctx: ContextoVale, tipo: TipoVale) -> str:
        """RG-06: `CLAVE-TIPO-CONSECUTIVO` desde `serie_folio`, ya bloqueada. Consecutivo sin
        huecos: si la transacción falla, el contador tampoco avanza."""
        serie = self.repository.bloquear_serie(ctx.almacen.id, tipo)
        serie.ultimo += 1
        self.session.flush()
        return f"{ctx.almacen.clave}-{PREFIJO_FOLIO[TipoVale(tipo)]}-{serie.ultimo:06d}"

    def _escribir_movimientos(
        self, ctx: ContextoVale, vale: Vale, nuevos: list[MovimientoNuevo]
    ) -> list[Movimiento]:
        """Inserta los movimientos con sus saldos y mueve las existencias y las piezas con el
        mismo delta (invariantes 1 a 4). PROVEEDOR no lleva existencia."""
        proveedor = self.almacenes.ubicacion_virtual(UbicacionVirtual.PROVEEDOR).id
        claves = set()
        for m in nuevos:
            if m.origen_id != proveedor:
                claves.add((m.origen_id, m.articulo_id))
            if m.destino_id != proveedor:
                claves.add((m.destino_id, m.articulo_id))
        filas = self.repository.existencias_bloqueadas(claves)
        faltan = claves - filas.keys()
        if faltan:  # el tipo no las anunció en `bloqueos`: se crean y bloquean aquí
            self.repository.bloquear_existencias(faltan)
            filas.update(self.repository.existencias_bloqueadas(faltan))

        escritos: list[Movimiento] = []
        for m in nuevos:
            saldo_origen = None
            saldo_destino = None
            if m.origen_id != proveedor:
                origen = filas[(m.origen_id, m.articulo_id)]
                if origen.cantidad < m.cantidad:  # RG-04
                    raise ExistenciaInsuficiente()
                origen.cantidad -= m.cantidad
                saldo_origen = origen.cantidad
            if m.destino_id != proveedor:
                destino = filas[(m.destino_id, m.articulo_id)]
                destino.cantidad += m.cantidad
                saldo_destino = destino.cantidad
            if m.pieza_id is not None:
                self._mover_pieza(m, proveedor)
            self.session.flush()
            escritos.append(
                self.repository.add_movimiento(
                    Movimiento(
                        id=nuevo_id(),
                        vale_id=vale.id,
                        renglon=m.renglon,
                        articulo_id=m.articulo_id,
                        pieza_id=m.pieza_id,
                        cantidad=m.cantidad,
                        origen_id=m.origen_id,
                        destino_id=m.destino_id,
                        trabajador_id=m.trabajador_id,
                        condicion=m.condicion,
                        motivo_baja=m.motivo_baja,
                        nivel=m.nivel,
                        reglas=m.reglas or None,
                        observacion=m.observacion,
                        saldo_origen=saldo_origen,
                        saldo_destino=saldo_destino,
                        creado_en=vale.creado_en,
                    )
                )
            )
        return escritos

    def _mover_pieza(self, m: MovimientoNuevo, proveedor: uuid.UUID) -> None:
        """Invariante 4: la pieza queda en el destino de su último movimiento. Debe salir de
        donde dice el movimiento (la entrada la saca de PROVEEDOR: aún no tiene ubicación)."""
        assert m.pieza_id is not None
        pieza = self.repository.pieza_bloqueada(m.pieza_id)
        assert isinstance(pieza, Pieza)
        sale_de_proveedor = m.origen_id == proveedor and pieza.ubicacion_id is None
        if pieza.ubicacion_id != m.origen_id and not sale_de_proveedor:
            raise ExistenciaInsuficiente("La pieza ya no está en el lugar de origen.")
        pieza.ubicacion_id = m.destino_id

    def _guardar_firma(self, usuario: Usuario, vale: Vale, cuerpo: ConfirmarIn) -> None:
        """F-02: guarda la imagen de la firma, ligada al vale (ADR-005)."""
        assert cuerpo.firma is not None and cuerpo.firma.imagen is not None
        contenido = decodificar_data_url(cuerpo.firma.imagen)
        adjunto = self.archivos.guardar(
            tipo=(
                TipoAdjunto.TICKET_FIRMADO if cuerpo.firma.modo == "PAPEL" else TipoAdjunto.FIRMA
            ),
            contenido=contenido,
            subido_por=usuario.id,
            vale_id=vale.id,
        )
        # `vale` y `adjunto` se apuntan entre sí: el vale ya existe; aquí se completa su alta.
        vale.firma_adjunto_id = adjunto.id
        self.session.flush()

    def _registrar_codigos(self, vale: Vale) -> None:
        """El QR del vale lleva su `token`; el folio también se puede teclear (RG-10)."""
        self.codigos.registrar(vale.token, TipoCodigo.VALE, vale.id)
        self.codigos.registrar(vale.folio, TipoCodigo.VALE, vale.id)

    def _repetido(self, vale: Vale, usuario: Usuario, cuerpo: ConfirmarIn) -> ValeConfirmadoOut:
        """Idempotencia: el mismo `id_cliente` con el MISMO cuerpo devuelve el vale ya guardado,
        nunca otro. Con otro cuerpo, 409: no se oculta un cambio devolviendo el vale original."""
        if vale.responsable_id != usuario.id or vale.tipo != cuerpo.tipo:
            raise IdClienteEnUso()
        if vale.huella_cuerpo is not None and vale.huella_cuerpo != huella_del_cuerpo(cuerpo):
            raise IdClienteOtroCuerpo()
        return self._confirmada(vale)

    def _vale_cambio(self, ctx: ContextoVale, evaluacion: Evaluacion) -> ValeCambio:
        salida = self._salida_evaluacion(ctx, evaluacion)
        return ValeCambio(detalles=salida.model_dump(mode="json"))

    @staticmethod
    def _traducir(exc: DBAPIError):
        """Un constraint de la base que protege una invariante, como error de dominio."""
        if errores_bd.es_restriccion(exc, "ck_existencia_cantidad_no_negativa"):
            return ExistenciaInsuficiente()
        return None

    # ====================================================================== consultas

    def obtener(
        self, usuario: Usuario, vale_id: uuid.UUID, *, incluir_renglones: bool = True
    ) -> ValeDetalleOut:
        """`GET /api/vales/{id}`. Fuera de su alcance (AC-06) responde 404."""
        vale = self.repository.vale(vale_id)
        if vale is None or not self._en_alcance(usuario, vale):
            raise ValeNoEncontrado()
        return self.detalle(vale, usuario=usuario, incluir_renglones=incluir_renglones)

    def firma_de(self, usuario: Usuario, vale_id: uuid.UUID) -> tuple[str, bytes]:
        """`GET /api/vales/{id}/firma`: el tipo de contenido y los bytes de la firma del trabajador.
        Misma visibilidad que el vale (AC-06); 404 si el vale no tiene firma en pantalla."""
        vale = self.repository.vale(vale_id)
        if vale is None or not self._en_alcance(usuario, vale) or vale.firma_adjunto_id is None:
            raise ValeNoEncontrado("Este vale no tiene firma guardada.")
        adjunto, contenido = self.archivos.leer(vale.firma_adjunto_id)
        return adjunto.mime, contenido

    def obtener_por_token(
        self, usuario: Usuario, token: str, *, incluir_renglones: bool = True
    ) -> ValeDetalleOut:
        """`GET /api/vales/por-token/{token}`: el vale que abre su QR."""
        vale = self.repository.vale_por_token(token.strip())
        if vale is None or not self._en_alcance(usuario, vale):
            raise ValeNoEncontrado()
        return self.detalle(vale, usuario=usuario, incluir_renglones=incluir_renglones)

    def _en_alcance(self, usuario: Usuario, vale: Vale) -> bool:
        return self.acceso.en_alcance(usuario, vale.almacen_id, vale.destino_almacen_id)

    def listar(
        self, usuario: Usuario, filtros: ValeFilters, paginacion: Paginacion
    ) -> Pagina[ValeListItem]:
        """`GET /api/vales`. Sin `almacenes.todos`, solo los del almacén asignado (AC-06), también
        al filtrar por otro almacén o por usuario."""
        almacen_id = filtros.almacen_id
        almacenes_id = None
        if not self.acceso.puede_operar_todos_los_almacenes(usuario):
            asignados = self.acceso.almacenes_del_usuario(usuario.id)
            if not asignados:
                raise SinPermiso("No tienes un almacén asignado.")
            if almacen_id is not None and almacen_id not in asignados:
                return Pagina[ValeListItem](elementos=[], total=0)
            almacenes_id = frozenset(asignados)
        filas, total = self.repository.listar(
            FiltroVales(
                tipo=filtros.tipo,
                almacen_id=almacen_id,
                almacenes_id=almacenes_id,
                desde=_inicio_del_dia(filtros.desde) if filtros.desde else None,
                hasta=_inicio_del_dia(filtros.hasta + timedelta(days=1)) if filtros.hasta else None,
                trabajador_id=filtros.trabajador_id,
                usuario_id=filtros.usuario_id,
                offset=paginacion.offset,
                limit=paginacion.limit,
            )
        )
        return Pagina[ValeListItem](
            elementos=[
                ValeListItem(
                    id=v.id,
                    folio=v.folio,
                    tipo=v.tipo,
                    estado=v.estado,
                    almacen=AlmacenResumenOut(id=a.id, clave=a.clave, nombre=a.nombre),
                    trabajador=PersonaOut(id=t.id, nombre=t.nombre) if t else None,
                    numero_empleado=t.numero_empleado if t else None,
                    responsable=PersonaOut(id=u.id, nombre=u.nombre),
                    renglones=n,
                    creado_en=v.creado_en,
                )
                for v, a, t, u, n in filas
            ],
            total=total,
        )

    def detalle(
        self, vale: Vale, *, usuario: Usuario | None = None, incluir_renglones: bool = True
    ) -> ValeDetalleOut:
        """El vale completo para mostrarlo o imprimirlo (E-24). Nunca trae costos (F-12)."""
        almacen = self.almacenes.obtener(vale.almacen_id)
        destino = (
            self.almacenes.obtener(vale.destino_almacen_id) if vale.destino_almacen_id else None
        )
        responsable = self.repository.usuario(vale.responsable_id)
        assert responsable is not None
        trabajador = None
        if vale.trabajador_id is not None:
            t = self.trabajadores.obtener(vale.trabajador_id)
            periodo = (
                self.repository.periodo(vale.periodo_contrato_id)
                if vale.periodo_contrato_id
                else None
            )
            trabajador = TrabajadorValeOut(
                id=t.id,
                numero_empleado=t.numero_empleado,
                nombre=t.nombre,
                puesto=periodo.puesto if periodo else None,
                area_obra=periodo.area_obra if periodo else None,
            )
        filas = self.repository.renglones_de(vale.id) if incluir_renglones else []
        ubicaciones = self.repository.ubicaciones(
            [m.origen_id for m, _, _ in filas] + [m.destino_id for m, _, _ in filas]
        )

        def ubicacion(ubicacion_id: uuid.UUID) -> UbicacionOut:
            ub, nombre, clave = ubicaciones[ubicacion_id]
            return UbicacionOut(tipo=ub.virtual or ub.tipo, nombre=nombre, clave=clave)

        origen_vale = self.repository.vale(vale.vale_origen_id) if vale.vale_origen_id else None
        proyecto = None
        if vale.proyecto_id is not None:
            from app.modulos.proyectos.service import ProyectoService

            p = ProyectoService(self.session).obtener(vale.proyecto_id)
            proyecto = {"id": p.id, "clave": p.clave, "nombre": p.nombre}
        salida = ValeDetalleOut(
            cancelacion=self._cancelacion_vista(vale),
            id=vale.id,
            folio=vale.folio,
            token=vale.token,
            tipo=vale.tipo,
            estado=vale.estado,
            almacen=AlmacenResumenOut(id=almacen.id, clave=almacen.clave, nombre=almacen.nombre),
            destino_almacen=AlmacenResumenOut(
                id=destino.id, clave=destino.clave, nombre=destino.nombre
            )
            if destino
            else None,
            trabajador=trabajador,
            proyecto=proyecto,
            responsable=PersonaOut(id=responsable.id, nombre=responsable.nombre),
            observacion=vale.observacion,
            firma_modo=vale.firma_modo,
            tiene_firma=vale.firma_adjunto_id is not None,
            valido=self.valido_de(vale),
            vale_origen_id=vale.vale_origen_id,
            vale_origen_folio=origen_vale.folio if origen_vale else None,
            dispositivo=vale.dispositivo,
            creado_en=vale.creado_en,
            renglones=[
                RenglonValeOut(
                    renglon=m.renglon,
                    articulo_id=a.id,
                    articulo=a.nombre,
                    marca=a.marca,
                    modelo=a.modelo,
                    talla=a.talla,
                    codigo_articulo=a.codigo,
                    pieza_id=p.id if p else None,
                    codigo_pieza=p.codigo if p else None,
                    numero_serie=p.numero_serie if p else None,
                    cantidad=m.cantidad,
                    condicion=m.condicion,
                    nivel=m.nivel,
                    reglas=list(m.reglas or []),
                    observacion=m.observacion,
                    origen=ubicacion(m.origen_id),
                    destino=ubicacion(m.destino_id),
                    saldo_origen=m.saldo_origen,
                    saldo_destino=m.saldo_destino,
                )
                for m, a, p in filas
            ],
        )
        if usuario is not None:
            from app.modulos.consulta.service_bitacora import BitacoraService

            salida = salida.model_copy(
                update=BitacoraService(self.session).enriquecer_detalle(vale.id, usuario)
            )
        return salida

    def _cancelacion_vista(self, vale: Vale) -> CancelacionVistaOut | None:
        """K-02: el vale CANCELADO muestra el folio y el motivo de su cancelación."""
        if vale.estado != EstadoVale.CANCELADO:
            return None
        cancelacion = self.repository.cancelacion_de(vale.id)
        if cancelacion is None:
            return None
        quien = self.repository.usuario(cancelacion.responsable_id)
        assert quien is not None
        return CancelacionVistaOut(
            id=cancelacion.id,
            folio=cancelacion.folio,
            motivo=cancelacion.observacion,
            responsable=PersonaOut(id=quien.id, nombre=quien.nombre),
            creado_en=cancelacion.creado_en,
        )

    def valido_de(self, vale: Vale) -> ValidoOut | None:
        """A-04: "Validó", con los datos de `autorizaciones`. En el envío propio de un traslado
        lateral (X-16) no hay autorización: valida quien envió (`medio = ENVIO_PROPIO`)."""
        if vale.autorizacion_id is None:
            if vale.tipo == TipoVale.ENTREGA and self.repository.tiene_regla(vale.id, "DE-07"):
                responsable = self.repository.usuario(vale.responsable_id)
                return ValidoOut(
                    autorizacion_id=None,
                    solicito=None,
                    autorizo=PersonaOut(id=responsable.id, nombre=responsable.nombre),
                    medio="DESPACHO_PROPIO",
                    resuelta_en=vale.creado_en,
                    motivo="Validó su propio despacho de EPP.",
                )
            return self._valido_envio_propio(vale)
        autorizacion = self.autorizaciones.obtener(vale.autorizacion_id)
        datos = self.autorizaciones.datos_valido(autorizacion)
        if datos is None:
            return None
        solicito = self.repository.usuario(autorizacion.solicitada_por)
        return ValidoOut(
            autorizacion_id=autorizacion.id,
            solicito=PersonaOut(id=solicito.id, nombre=solicito.nombre) if solicito else None,
            autorizo=PersonaOut(id=datos.usuario_id, nombre=datos.nombre),
            medio=datos.medio.value,
            resuelta_en=datos.resuelta_en,
            motivo=datos.motivo,
        )

    def _valido_envio_propio(self, vale: Vale) -> ValidoOut | None:
        """X-16: se deriva de la regla en los movimientos del vale y de su responsable."""
        if vale.tipo != TipoVale.TRASPASO:
            return None
        if not self.repository.tiene_regla(vale.id, "X-16"):
            return None
        responsable = self.repository.usuario(vale.responsable_id)
        assert responsable is not None
        return ValidoOut(
            autorizacion_id=None,
            solicito=None,
            autorizo=PersonaOut(id=responsable.id, nombre=responsable.nombre),
            medio="ENVIO_PROPIO",
            resuelta_en=vale.creado_en,
            motivo=vale.observacion or "",
        )

    def _confirmada(self, vale: Vale) -> ValeConfirmadoOut:
        filas = self.repository.renglones_de(vale.id)
        return ValeConfirmadoOut(
            id=vale.id,
            folio=vale.folio,
            token=vale.token,
            creado_en=vale.creado_en,
            renglones=[
                RenglonConfirmadoOut(
                    renglon=m.renglon,
                    codigo=p.codigo if p else a.codigo,
                    articulo=a.nombre,
                    cantidad=m.cantidad,
                    nivel=m.nivel,
                    reglas=list(m.reglas or []),
                )
                for m, a, p in filas
            ],
        )

    # ============================================================= salida de evaluación

    @staticmethod
    def _salida_renglon(r: RenglonEvaluado) -> RenglonEvaluadoOut:
        return RenglonEvaluadoOut(
            renglon=r.renglon,
            codigo=r.codigo,
            articulo=ArticuloEvaluadoOut(**r.articulo) if r.articulo else None,
            pieza=PiezaEvaluadaOut(**r.pieza) if r.pieza else None,
            titular=TitularOut(**r.titular) if r.titular else None,
            cantidad=r.cantidad,
            disponible=r.disponible,
            nivel=r.nivel,
            motivos=[
                MotivoOut(regla=m.regla, nivel=m.nivel, mensaje=m.mensaje, codigo=m.codigo)
                for m in r.motivos
            ],
            pide_observacion=r.pide_observacion,
            autorizable=r.autorizable,
            requiere_confirmacion=r.requiere_confirmacion,
            autorizado=r.autorizado,
            es_epp=r.extra.get("es_epp", False),
            requiere_aprobacion=r.extra.get("requiere_aprobacion", False),
            aprobacion=r.extra.get("aprobacion"),
            motivo_rechazo=r.extra.get("motivo_rechazo"),
        )

    def _salida_evaluacion(self, ctx: ContextoVale, evaluacion: Evaluacion) -> EvaluacionOut:
        almacen = ctx.almacen
        return EvaluacionOut(
            nivel=evaluacion.nivel,
            puede_confirmar=evaluacion.puede_confirmar,
            requiere_aprobacion_despacho=evaluacion.requiere_aprobacion_despacho,
            despacho={"modo": evaluacion.despacho_modo},
            pide_observacion=evaluacion.pide_observacion,
            motivos=[
                MotivoOut(
                    regla=m.regla,
                    nivel=m.nivel,
                    mensaje=m.mensaje,
                    codigo=m.codigo,
                    autorizable=m.regla == "X-17",
                    autorizado=m.regla == "X-17" and evaluacion.autorizado_vale,
                )
                for m in evaluacion.motivos_vale
            ],
            almacen=AlmacenResumenOut(id=almacen.id, clave=almacen.clave, nombre=almacen.nombre),
            trabajador=evaluacion.trabajador,
            proyecto=evaluacion.proyecto,
            proyectos_del_trabajador=evaluacion.proyectos_del_trabajador,
            pide_proyecto=evaluacion.pide_proyecto,
            autorizacion_error=evaluacion.autorizacion_error,
            ruta=RutaEvaluacionOut(
                clase=evaluacion.ruta.clase,
                autoriza=evaluacion.ruta.autoriza,
                autorizadores_disponibles=evaluacion.ruta.autorizadores_disponibles,
            )
            if evaluacion.ruta
            else None,
            renglones=[self._salida_renglon(r) for r in evaluacion.renglones],
        )

    # ================================================== operaciones propias de otros endpoints

    def traspasos_por_recibir(
        self, usuario: Usuario, *, solo_contar: bool = False, almacen_id: uuid.UUID | None = None
    ):
        """`GET /api/traspasos/por-recibir`: lo resuelve el tipo RECEPCION."""
        manejador = self.exigir_permiso_del_tipo(usuario, TipoVale.RECEPCION)
        return manejador.por_recibir(self, usuario, solo_contar=solo_contar, almacen_id=almacen_id)

    def emitir_no_adeudo(self, usuario: Usuario, trabajador_id: uuid.UUID, datos):
        """`POST /api/trabajadores/{id}/no-adeudo`: lo resuelve el tipo NO_ADEUDO."""
        manejador = self.exigir_permiso_del_tipo(usuario, TipoVale.NO_ADEUDO)
        return manejador.emitir_no_adeudo(self, usuario, trabajador_id, datos)

    def cancelar(self, usuario: Usuario, vale_id: uuid.UUID, datos: CancelacionIn):
        """`POST /api/vales/{id}/cancelacion`: lo resuelve el tipo CANCELACION."""
        manejador = self.exigir_permiso_del_tipo(usuario, TipoVale.CANCELACION)
        return manejador.cancelar(self, usuario, vale_id, datos)


def _inicio_del_dia(dia: date) -> datetime:
    """Medianoche del centro de México de ese día, en UTC sin zona (como se guarda)."""
    return _a_utc_naive(datetime.combine(dia, time.min, tzinfo=ZONA_MX))
