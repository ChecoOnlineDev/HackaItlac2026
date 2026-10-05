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

import secrets
import uuid
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError, InvalidRequestError
from sqlalchemy.orm import Session

from app.core import errores_bd
from app.core.excepciones import NoEncontrado, SinPermiso
from app.core.ids import nuevo_id
from app.core.paginacion import Pagina, Paginacion
from app.core.tiempo import ZONA_MX, ahora_utc, hoy_mx
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.models import UbicacionVirtual
from app.modulos.almacenes.service import AlmacenService
from app.modulos.archivos.models import TipoAdjunto
from app.modulos.archivos.service import ArchivoService, decodificar_data_url
from app.modulos.autorizaciones.exceptions import (
    AutorizacionInvalida,
    AutorizacionPropia,
    RenglonNoAutorizable,
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
from app.modulos.movimientos.exceptions import (
    AlmacenCambio,
    ExistenciaInsuficiente,
    IdClienteEnUso,
    ValeCambio,
    ValeNoEncontrado,
)
from app.modulos.movimientos.models import (
    PREFIJO_FOLIO,
    Movimiento,
    Nivel,
    TipoVale,
    Vale,
)
from app.modulos.movimientos.repository import FiltroVales, MovimientoRepository
from app.modulos.movimientos.schemas import (
    AlmacenResumenOut,
    ArticuloEvaluadoOut,
    ConfirmarIn,
    EvaluacionOut,
    MotivoOut,
    PersonaOut,
    PiezaEvaluadaOut,
    RenglonConfirmadoOut,
    RenglonEvaluadoOut,
    RenglonIn,
    RenglonValeOut,
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
        if almacen_id is not None and almacen_id != usuario.almacen_id:
            actual = self.almacenes.obtener(usuario.almacen_id)
            raise AlmacenCambio(
                detalles={
                    "almacen": {
                        "id": str(actual.id),
                        "clave": actual.clave,
                        "nombre": actual.nombre,
                    }
                }
            )
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

    def _evaluar(
        self, manejador: ManejadorTipo, ctx: ContextoVale, cuerpo: ValeIn
    ) -> tuple[Evaluacion, ValeIn]:
        normal = self._normalizar(manejador, ctx, cuerpo)
        evaluacion = manejador.evaluar(ctx, normal)
        evaluacion.admite_sin_renglones = manejador.admite_sin_renglones
        return evaluacion, normal

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

    def verificar_renglones_autorizables(
        self,
        usuario: Usuario,
        almacen_id: uuid.UUID,
        trabajador_id: uuid.UUID,
        renglones: list[tuple[str, int]],
    ) -> None:
        """A-06 y SM-04: lanza `RenglonNoAutorizable` si alguno de los renglones está en rojo
        en la evaluación real (pieza no apta, inspección vencida, trabajador no vigente,
        código desconocido, sin existencia...)."""
        evaluacion = self.evaluar_para_autorizacion(usuario, almacen_id, trabajador_id, renglones)
        for r in evaluacion.renglones:
            rojos = [m for m in r.motivos if m.nivel == Nivel.ROJO]
            if rojos:
                raise RenglonNoAutorizable(
                    f"El renglón {r.codigo} está en rojo y no se puede enviar a autorización "
                    f"({rojos[0].mensaje}) (A-06).",
                    {
                        "codigo": r.codigo,
                        "regla": rojos[0].regla,
                        "motivos": [{"regla": m.regla, "mensaje": m.mensaje} for m in rojos],
                    },
                )

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
        except (AutorizacionInvalida, AutorizacionPropia, NoEncontrado) as exc:
            if not silencioso:
                raise
            evaluacion.autorizacion_error = exc.mensaje
            return None
        for r in naranjas:
            r.autorizado = True
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
                    manejador, usuario, cuerpo, dispositivo, aislar=aislar, commit=commit
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
    ) -> tuple[ValeConfirmadoOut, bool]:
        if aislar:
            self._aislar_transaccion()
        almacen_id = manejador.almacen_operativo(self, usuario, cuerpo)
        ctx = self._contexto(usuario, almacen_id, bloqueado=True)
        normal = self._normalizar(manejador, ctx, cuerpo)
        assert isinstance(normal, ConfirmarIn)

        # 1. Bloquear en orden canónico y descartar lo leído antes de bloquear.
        plan = manejador.bloqueos(ctx, normal)
        self._bloquear(plan, ctx, manejador)
        self.session.expire_all()
        ctx.cargador.olvidar_lecturas()

        # 2. Otra confirmación con el mismo `id_cliente` pudo ganar mientras esperábamos.
        ganador = self.repository.vale_por_id_cliente(cuerpo.id_cliente)
        if ganador is not None:
            if commit:
                self.session.rollback()
            return self._repetido(ganador, usuario, cuerpo), False

        # 3. Volver a evaluar, ya con las filas bloqueadas (RG-08).
        evaluacion = manejador.evaluar(ctx, normal)
        evaluacion.admite_sin_renglones = manejador.admite_sin_renglones
        if evaluacion.nivel == Nivel.ROJO:
            raise self._vale_cambio(ctx, evaluacion)
        autorizacion = self._aplicar_autorizacion(ctx, evaluacion, normal, silencioso=False)
        if not evaluacion.puede_confirmar:
            raise self._vale_cambio(ctx, evaluacion)

        # 4. Vale: folio, token y responsable (RG-06, F-03, F-05).
        datos = manejador.datos_vale(ctx, normal, evaluacion)
        vale = self.repository.add_vale(
            Vale(
                id=nuevo_id(),
                id_cliente=cuerpo.id_cliente,
                tipo=manejador.tipo,
                folio=self._asignar_folio(ctx, manejador.tipo),
                almacen_id=ctx.almacen.id,
                trabajador_id=datos.trabajador_id,
                periodo_contrato_id=datos.periodo_contrato_id,
                destino_almacen_id=datos.destino_almacen_id,
                vale_origen_id=datos.vale_origen_id,
                estado=datos.estado,
                responsable_id=usuario.id,
                autorizacion_id=autorizacion.id if autorizacion else None,
                observacion=datos.observacion or cuerpo.observacion,
                firma_modo=datos.firma_modo,
                token=secrets.token_urlsafe(16),  # 128 bits
                dispositivo=dispositivo[:200] if dispositivo else None,
                creado_en=ctx.ahora,
            )
        )

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

        if commit:
            self.session.commit()
        else:
            self.session.flush()
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

    def _bloquear(self, plan: PlanBloqueo, ctx: ContextoVale, manejador: ManejadorTipo) -> None:
        """Orden canónico: vales, trabajador, existencias (por ubicación y artículo), piezas por
        id y, al final, el contador de folios. Todos los tipos lo siguen: sin interbloqueos."""
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
            tipo=TipoAdjunto.FIRMA, contenido=contenido, subido_por=usuario.id, vale_id=vale.id
        )
        # `vale` y `adjunto` se apuntan entre sí: el vale ya existe; aquí se completa su alta.
        vale.firma_adjunto_id = adjunto.id
        self.session.flush()

    def _registrar_codigos(self, vale: Vale) -> None:
        """El QR del vale lleva su `token`; el folio también se puede teclear (RG-10)."""
        self.codigos.registrar(vale.token, TipoCodigo.VALE, vale.id)
        self.codigos.registrar(vale.folio, TipoCodigo.VALE, vale.id)

    def _repetido(self, vale: Vale, usuario: Usuario, cuerpo: ConfirmarIn) -> ValeConfirmadoOut:
        """Idempotencia: el mismo `id_cliente` devuelve el vale ya guardado, nunca otro."""
        if vale.responsable_id != usuario.id or vale.tipo != cuerpo.tipo:
            raise IdClienteEnUso()
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

    def obtener(self, usuario: Usuario, vale_id: uuid.UUID) -> ValeDetalleOut:
        """`GET /api/vales/{id}`. Fuera de su alcance (AC-06) responde 404."""
        vale = self.repository.vale(vale_id)
        if vale is None or not self._en_alcance(usuario, vale):
            raise ValeNoEncontrado()
        return self.detalle(vale)

    def obtener_por_token(self, usuario: Usuario, token: str) -> ValeDetalleOut:
        """`GET /api/vales/por-token/{token}`: el vale que abre su QR."""
        vale = self.repository.vale_por_token(token.strip())
        if vale is None or not self._en_alcance(usuario, vale):
            raise ValeNoEncontrado()
        return self.detalle(vale)

    def _en_alcance(self, usuario: Usuario, vale: Vale) -> bool:
        if self.acceso.puede_operar_todos_los_almacenes(usuario):
            return True
        return usuario.almacen_id is not None and usuario.almacen_id in (
            vale.almacen_id,
            vale.destino_almacen_id,
        )

    def listar(
        self, usuario: Usuario, filtros: ValeFilters, paginacion: Paginacion
    ) -> Pagina[ValeListItem]:
        """`GET /api/vales`. Sin `almacenes.todos`, solo los del almacén asignado (AC-06), también
        al filtrar por otro almacén o por usuario."""
        almacen_id = filtros.almacen_id
        if not self.acceso.puede_operar_todos_los_almacenes(usuario):
            if usuario.almacen_id is None:
                raise SinPermiso("No tienes un almacén asignado.")
            if almacen_id is not None and almacen_id != usuario.almacen_id:
                return Pagina[ValeListItem](elementos=[], total=0)
            almacen_id = usuario.almacen_id
        filas, total = self.repository.listar(
            FiltroVales(
                tipo=filtros.tipo,
                almacen_id=almacen_id,
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

    def detalle(self, vale: Vale) -> ValeDetalleOut:
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
        filas = self.repository.renglones_de(vale.id)
        ubicaciones = self.repository.ubicaciones(
            [m.origen_id for m, _, _ in filas] + [m.destino_id for m, _, _ in filas]
        )

        def ubicacion(ubicacion_id: uuid.UUID) -> UbicacionOut:
            ub, nombre, clave = ubicaciones[ubicacion_id]
            return UbicacionOut(tipo=ub.virtual or ub.tipo, nombre=nombre, clave=clave)

        origen_vale = self.repository.vale(vale.vale_origen_id) if vale.vale_origen_id else None
        return ValeDetalleOut(
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
            responsable=PersonaOut(id=responsable.id, nombre=responsable.nombre),
            observacion=vale.observacion,
            firma_modo=vale.firma_modo,
            tiene_firma=vale.firma_adjunto_id is not None,
            valido=self._valido(vale),
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

    def _valido(self, vale: Vale) -> ValidoOut | None:
        """A-04: "Validó", con los datos de `autorizaciones`."""
        if vale.autorizacion_id is None:
            return None
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
            motivos=[MotivoOut(regla=m.regla, nivel=m.nivel, mensaje=m.mensaje) for m in r.motivos],
            pide_observacion=r.pide_observacion,
            autorizable=r.autorizable,
            requiere_confirmacion=r.requiere_confirmacion,
            autorizado=r.autorizado,
        )

    def _salida_evaluacion(self, ctx: ContextoVale, evaluacion: Evaluacion) -> EvaluacionOut:
        almacen = ctx.almacen
        return EvaluacionOut(
            nivel=evaluacion.nivel,
            puede_confirmar=evaluacion.puede_confirmar,
            motivos=[
                MotivoOut(regla=m.regla, nivel=m.nivel, mensaje=m.mensaje)
                for m in evaluacion.motivos_vale
            ],
            almacen=AlmacenResumenOut(id=almacen.id, clave=almacen.clave, nombre=almacen.nombre),
            trabajador=evaluacion.trabajador,
            autorizacion_error=evaluacion.autorizacion_error,
            renglones=[self._salida_renglon(r) for r in evaluacion.renglones],
        )

    # ================================================== operaciones propias de otros endpoints

    def traspasos_por_recibir(self, usuario: Usuario):
        """`GET /api/traspasos/por-recibir`: lo resuelve el tipo RECEPCION."""
        manejador = self.exigir_permiso_del_tipo(usuario, TipoVale.RECEPCION)
        return manejador.por_recibir(self, usuario)

    def emitir_no_adeudo(self, usuario: Usuario, trabajador_id: uuid.UUID, datos):
        """`POST /api/trabajadores/{id}/no-adeudo`: lo resuelve el tipo NO_ADEUDO."""
        manejador = self.exigir_permiso_del_tipo(usuario, TipoVale.NO_ADEUDO)
        return manejador.emitir_no_adeudo(self, usuario, trabajador_id, datos)

    def cancelar(self, usuario: Usuario, vale_id: uuid.UUID, datos):
        """`POST /api/vales/{id}/cancelacion`: lo resuelve el tipo CANCELACION."""
        manejador = self.exigir_permiso_del_tipo(usuario, TipoVale.CANCELACION)
        return manejador.cancelar(self, usuario, vale_id, datos)


def _inicio_del_dia(dia: date) -> datetime:
    """Medianoche del centro de México de ese día, en UTC sin zona (como se guarda)."""
    return _a_utc_naive(datetime.combine(dia, time.min, tzinfo=ZONA_MX))
