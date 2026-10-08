"""Reglas de negocio y control de la transacción de las solicitudes de compra urgentes.

Flujo (transcripción del track: «el supervisor hace una solicitud de compra de manera urgente, la
recibe Compras, la compra, la ingresa al almacén y ya está disponible»):

    PENDIENTE -> EN_COMPRA | RECHAZADA | CANCELADA
    EN_COMPRA -> COMPRADA | RECHAZADA
    COMPRADA  -> INGRESADA
    INGRESADA, RECHAZADA, CANCELADA: terminales.

El módulo NO escribe inventario: la entrada al almacén es un vale de ENTRADA que hace `movimientos`
y aquí solo se LEE para ligarlo (SC-06, SC-11); siempre es de Kepler (EK-05). Cada operación es
una transacción: la solicitud cambia junto con su evento (SC-08). Las reglas llevan su ID `SC-xx`
(reglas-de-negocio.md, 7.13).
"""

import hashlib
import json
import uuid
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core import errores_bd
from app.core.excepciones import DatosInvalidos, SinPermiso
from app.core.paginacion import Pagina, Paginacion
from app.core.reintento import reintentar_si_interbloqueo
from app.core.tiempo import ZONA_MX, ahora_utc
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.almacenes.exceptions import AlmacenCerrado
from app.modulos.almacenes.models import EstadoAlmacen
from app.modulos.almacenes.service import AlmacenService
from app.modulos.catalogo.service import CatalogoService
from app.modulos.movimientos.models import EstadoVale, TipoVale, Vale
from app.modulos.solicitudes_compra.exceptions import (
    IdClienteEnUso,
    IdClienteOtroCuerpo,
    SinPermisoParaCancelar,
    SolicitudNoCancelable,
    SolicitudNoEncontrada,
    TransicionInvalida,
    detalle_campo,
)
from app.modulos.solicitudes_compra.models import (
    EstadoSolicitud,
    SolicitudCompra,
    SolicitudCompraEvento,
)
from app.modulos.solicitudes_compra.repository import (
    ConsultaSolicitudes,
    Fila,
    SolicitudCompraRepository,
)
from app.modulos.solicitudes_compra.schemas import (
    Accion,
    AlmacenOut,
    ArticuloOut,
    CambioEstadoIn,
    CancelacionIn,
    ConteoOut,
    EventoOut,
    FiltrosSolicitudes,
    PersonaOut,
    SolicitudCreate,
    SolicitudDetalleOut,
    SolicitudOut,
    ValeEntradaOut,
)

E = EstadoSolicitud

# SC-04: las únicas transiciones que existen. Cancelar (PENDIENTE -> CANCELADA) tiene su propio
# endpoint y su propio permiso (SC-07), así que no está entre las que pide Compras.
TRANSICIONES_DE_COMPRAS: dict[str, tuple[str, ...]] = {
    E.PENDIENTE: (E.EN_COMPRA, E.RECHAZADA),
    E.EN_COMPRA: (E.COMPRADA, E.RECHAZADA),
    E.COMPRADA: (E.INGRESADA,),
}

# Qué acción de la interfaz lleva a cada estado nuevo (la calcula el servidor, SC-04).
ACCION_DE_ESTADO: dict[str, Accion] = {
    E.EN_COMPRA: "tomar",
    E.RECHAZADA: "rechazar",
    E.COMPRADA: "comprar",
    E.INGRESADA: "ingresar",
}


def huella_del_cuerpo(almacen_id: uuid.UUID, datos: SolicitudCreate) -> str:
    """SHA-256 del cuerpo canónico (llaves ordenadas, sin espacios) con el almacén ya resuelto: así
    pedir con el almacén propio o sin indicarlo es lo mismo (SC-10). Con artículo, el texto libre
    no cuenta porque se ignora (SC-02)."""
    cuerpo = {
        "almacen_id": str(almacen_id),
        "articulo_id": str(datos.articulo_id) if datos.articulo_id else None,
        "descripcion": None if datos.articulo_id else datos.descripcion,
        "cantidad": datos.cantidad,
        "motivo": datos.motivo,
        "urgencia": str(datos.urgencia),
    }
    canonico = json.dumps(cuerpo, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _rango_utc(desde: date | None, hasta: date | None) -> tuple[datetime | None, datetime | None]:
    """Fechas locales de México como `[inicio, fin)` en UTC sin zona; el día `hasta` entra
    completo. Un rango invertido se rechaza (422)."""
    if desde is not None and hasta is not None and desde > hasta:
        raise DatosInvalidos(
            "La fecha inicial es posterior a la final.",
            [{"campo": "desde", "mensaje": "La fecha inicial es posterior a la final."}],
        )

    def _utc(dia: date) -> datetime:
        return datetime.combine(dia, time.min, tzinfo=ZONA_MX).astimezone(UTC).replace(tzinfo=None)

    inicio = _utc(desde) if desde is not None else None
    fin = _utc(hasta + timedelta(days=1)) if hasta is not None else None
    return inicio, fin


class SolicitudCompraService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = SolicitudCompraRepository(session)
        self.acceso = AccesoService(session)
        self.almacenes = AlmacenService(session)
        self.catalogo = CatalogoService(session)

    # ------------------------------------------------------------------- permisos

    def _permisos(self, usuario: Usuario) -> frozenset[str]:
        return self.acceso.permisos_de(usuario)

    def _exigir_ver(self, usuario: Usuario) -> frozenset[str]:
        """Ver solicitudes lo puede quien las pide o quien las atiende (verificado aquí porque la
        ruta acepta cualquiera de los dos permisos). Devuelve sus permisos."""
        permisos = self._permisos(usuario)
        if P.COMPRAS_SOLICITAR not in permisos and P.COMPRAS_ATENDER not in permisos:
            raise SinPermiso()
        return permisos

    def _alcance(self, usuario: Usuario, permisos: frozenset[str]) -> tuple[bool, uuid.UUID | None]:
        """SC-03: `(ve_todos, almacen_propio)`. Quien atiende compras ve las de todos los
        almacenes (una solicitud no es inventario); el Administrador también (AC-06); los demás,
        solo las de su almacén, y sin almacén no ven nada."""
        ve_todos = P.COMPRAS_ATENDER in permisos or P.ALMACENES_TODOS in permisos
        return ve_todos, usuario.almacen_id

    def _puede_ver(self, solicitud: SolicitudCompra, usuario: Usuario, permisos) -> bool:
        ve_todos, propio = self._alcance(usuario, permisos)
        return ve_todos or (propio is not None and propio == solicitud.almacen_id)

    def _puede_cancelar(
        self, solicitud: SolicitudCompra, usuario: Usuario, permisos: frozenset[str]
    ) -> bool:
        """SC-07: quien la pidió; un supervisor de su almacén (`vales.cancelar_todos`, «cancelar los
        de cualquiera de su almacén»); o quien opera todos los almacenes. Siempre con
        `compras.solicitar`."""
        if P.COMPRAS_SOLICITAR not in permisos:
            return False
        if solicitud.solicitante_id == usuario.id:
            return True
        if P.ALMACENES_TODOS in permisos:
            return True
        return P.VALES_CANCELAR_TODOS in permisos and usuario.almacen_id == solicitud.almacen_id

    def acciones(
        self, solicitud: SolicitudCompra, usuario: Usuario, permisos: frozenset[str]
    ) -> list[Accion]:
        """Lo que el usuario puede hacer ahora con la solicitud (SC-04, SC-07), en este orden:
        tomar, rechazar, comprar, ingresar, cancelar."""
        acciones: list[Accion] = []
        if P.COMPRAS_ATENDER in permisos:
            acciones += [
                ACCION_DE_ESTADO[nuevo]
                for nuevo in TRANSICIONES_DE_COMPRAS.get(solicitud.estado, ())
            ]
        if solicitud.estado == E.PENDIENTE and self._puede_cancelar(solicitud, usuario, permisos):
            acciones.append("cancelar")
        orden = ["tomar", "rechazar", "comprar", "ingresar", "cancelar"]
        return sorted(acciones, key=orden.index)

    # ---------------------------------------------------------------------- crear

    def crear(
        self, usuario: Usuario, datos: SolicitudCreate, *, commit: bool = True
    ) -> tuple[SolicitudDetalleOut, bool]:
        """`POST /api/solicitudes-compra` (SC-01, SC-02, SC-09, SC-10). Devuelve
        `(solicitud, creada)`: `creada` es falso si el `id_cliente` ya existía y se devuelve la que
        se guardó la primera vez. La ruta exige `compras.solicitar`.

        `commit=False` es para los datos de prueba, que corren dentro de la transacción de
        `app/datos_prueba.py`."""
        if not commit:
            return self._crear_una_vez(usuario, datos, commit=False)
        return reintentar_si_interbloqueo(
            self.session, lambda: self._crear_con_idempotencia(usuario, datos)
        )

    def _crear_con_idempotencia(
        self, usuario: Usuario, datos: SolicitudCreate
    ) -> tuple[SolicitudDetalleOut, bool]:
        try:
            return self._crear_una_vez(usuario, datos, commit=True)
        except DBAPIError as exc:
            self.session.rollback()
            if errores_bd.es_restriccion(exc, "uq_solicitud_compra_id_cliente"):
                existente = self.repository.get_por_id_cliente(datos.id_cliente)
                if existente is not None:  # otra petición igual ganó mientras esperábamos
                    almacen_id = self.acceso.resolver_almacen(usuario, datos.almacen_id)
                    return self._repetida(existente, usuario, almacen_id, datos), False
            raise

    def _crear_una_vez(
        self, usuario: Usuario, datos: SolicitudCreate, *, commit: bool
    ) -> tuple[SolicitudDetalleOut, bool]:
        # SC-01: el almacén sale del usuario; con `almacenes.todos` se indica. Sin almacén
        # asignado y sin `almacenes.todos`: el error de siempre (403).
        almacen_id = self.acceso.resolver_almacen(usuario, datos.almacen_id)

        existente = self.repository.get_por_id_cliente(datos.id_cliente)
        if existente is not None:
            return self._repetida(existente, usuario, almacen_id, datos), False

        articulo = None
        descripcion = datos.descripcion
        if datos.articulo_id is not None:
            articulo = self.catalogo.obtener_articulo(datos.articulo_id)  # 404 si no existe
            if not articulo.activo:  # SC-02 (CF-10): no se compra lo que no puede entrar
                raise DatosInvalidos(
                    "Ese artículo está inactivo: no se puede pedir (SC-02).",
                    detalle_campo("articulo_id", "El artículo está inactivo.", "SC-02"),
                )
            descripcion = articulo.nombre
        assert descripcion is not None  # el schema exige artículo o descripción

        almacen = self.repository.almacen(almacen_id)
        if almacen.estado == EstadoAlmacen.CERRADO:  # AL-04: sin solicitudes nuevas
            raise AlmacenCerrado(almacen)
        serie = self.repository.bloquear_serie(almacen_id)
        serie.ultimo += 1
        self.session.flush()
        ahora = ahora_utc()
        solicitud = self.repository.add(
            SolicitudCompra(
                id_cliente=datos.id_cliente,
                huella_cuerpo=huella_del_cuerpo(almacen_id, datos),
                folio=f"{almacen.clave}-SOL-{serie.ultimo:06d}",
                almacen_id=almacen_id,
                solicitante_id=usuario.id,
                articulo_id=articulo.id if articulo else None,
                descripcion=descripcion,
                cantidad=datos.cantidad,
                motivo=datos.motivo,
                urgencia=datos.urgencia,
                estado=E.PENDIENTE,
                creada_en=ahora,
                actualizada_en=ahora,
            )
        )
        self._evento(solicitud, None, E.PENDIENTE, usuario, None, ahora)
        if commit:
            self.session.commit()
        return self._detalle(solicitud, usuario), True

    def _repetida(
        self,
        solicitud: SolicitudCompra,
        usuario: Usuario,
        almacen_id: uuid.UUID,
        datos: SolicitudCreate,
    ) -> SolicitudDetalleOut:
        """SC-10: el mismo `id_cliente` con el MISMO cuerpo devuelve la solicitud ya guardada; con
        otro cuerpo o de otro usuario, 409: no se oculta un cambio devolviendo la original."""
        if solicitud.solicitante_id != usuario.id:
            raise IdClienteEnUso()
        if solicitud.huella_cuerpo != huella_del_cuerpo(almacen_id, datos):
            raise IdClienteOtroCuerpo()
        return self._detalle(solicitud, usuario)

    # --------------------------------------------------------------------- listar

    def listar(
        self, usuario: Usuario, filtros: FiltrosSolicitudes, pagina: Paginacion
    ) -> Pagina[SolicitudOut] | ConteoOut:
        """`GET /api/solicitudes-compra` (SC-03). Pide `compras.solicitar` o `compras.atender`."""
        permisos = self._exigir_ver(usuario)
        ve_todos, propio = self._alcance(usuario, permisos)
        # Sin almacén y sin permiso de verlo todo: no se ve nada (AC-06).
        vacia = not ve_todos and propio is None
        desde, hasta = _rango_utc(filtros.desde, filtros.hasta)
        consulta = ConsultaSolicitudes(
            almacen_alcance=None if ve_todos else propio,
            almacen_id=filtros.almacen_id,
            estado=filtros.estado,
            urgencia=filtros.urgencia,
            q=filtros.q.strip() if filtros.q else None,
            desde=desde,
            hasta=hasta,
            solicitante_id=usuario.id if filtros.mias else None,
        )
        if vacia:
            return ConteoOut(total=0) if filtros.solo_contar else Pagina(elementos=[], total=0)
        if filtros.solo_contar:
            return ConteoOut(total=self.repository.contar(consulta))
        filas = self.repository.listar(consulta, offset=pagina.offset, limit=pagina.limit)
        total = self.repository.contar(consulta)
        return Pagina(
            elementos=[self._item(f, usuario, permisos) for f in filas],
            total=total,
        )

    # -------------------------------------------------------------------- detalle

    def detalle(self, usuario: Usuario, solicitud_id: uuid.UUID) -> SolicitudDetalleOut:
        """`GET /api/solicitudes-compra/{id}`. Fuera del alcance del usuario, 404 (SC-03)."""
        permisos = self._exigir_ver(usuario)
        solicitud = self.repository.get(solicitud_id)
        if solicitud is None or not self._puede_ver(solicitud, usuario, permisos):
            raise SolicitudNoEncontrada()
        return self._detalle(solicitud, usuario, permisos)

    # ------------------------------------------------------------- cambio de estado

    def cambiar_estado(
        self,
        usuario: Usuario,
        solicitud_id: uuid.UUID,
        datos: CambioEstadoIn,
        *,
        commit: bool = True,
    ) -> SolicitudDetalleOut:
        """`POST /api/solicitudes-compra/{id}/estado` (SC-04, SC-05, SC-06). La ruta exige
        `compras.atender`. Toma la solicitud `FOR UPDATE`: dos cambios a la vez se serializan."""
        solicitud = self.repository.get(solicitud_id, bloquear=True)
        if solicitud is None:
            raise SolicitudNoEncontrada()

        permitidos = TRANSICIONES_DE_COMPRAS.get(solicitud.estado, ())
        if datos.estado not in permitidos:
            raise TransicionInvalida(solicitud.estado, datos.estado, [str(p) for p in permitidos])

        if datos.estado == E.RECHAZADA and datos.nota is None:
            raise DatosInvalidos(
                "Escribe por qué se rechaza la solicitud (SC-05).",
                detalle_campo("nota", "La nota es obligatoria al rechazar.", "SC-05"),
            )
        if datos.vale_entrada_id is not None and datos.estado != E.INGRESADA:
            raise DatosInvalidos(
                "El vale de entrada solo se liga al ingresar la solicitud (SC-06).",
                detalle_campo("vale_entrada_id", "Solo se indica al pasar a INGRESADA.", "SC-06"),
            )
        vale = self._validar_vale_entrada(usuario, datos.vale_entrada_id)

        anterior = solicitud.estado
        ahora = ahora_utc()
        solicitud.estado = datos.estado
        solicitud.actualizada_en = ahora
        if datos.nota is not None:
            solicitud.nota_compras = datos.nota
        if vale is not None:
            solicitud.vale_entrada_id = vale.id
        self._evento(solicitud, anterior, datos.estado, usuario, datos.nota, ahora)
        if commit:
            self.session.commit()
        return self._detalle(solicitud, usuario)

    def _validar_vale_entrada(self, usuario: Usuario, vale_id: uuid.UUID | None) -> Vale | None:
        """SC-06, EK-05: un vale de ENTRADA que existe, no está cancelado y es del almacén central
        (Kepler), dentro del alcance de quien lo liga. El almacén que pidió la compra la recibe
        después por traspaso. Si no, 422."""
        if vale_id is None:
            return None
        vale = self.repository.vale(vale_id)
        problema = None
        if vale is None or not self.acceso.en_alcance(usuario, vale.almacen_id):
            problema = "No se encontró ese vale de entrada en tu almacén."
        elif vale.tipo != TipoVale.ENTRADA:
            problema = "Ese vale no es de entrada de inventario."
        elif vale.estado == EstadoVale.CANCELADO:
            problema = "Ese vale de entrada está cancelado."
        elif vale.almacen_id != self.almacenes.obtener_central().id:
            problema = "Ese vale no es de Kepler: las compras se ingresan por Kepler (EK-05)."
        if problema is not None:
            raise DatosInvalidos(
                f"{problema} (SC-06)", detalle_campo("vale_entrada_id", problema, "SC-06")
            )
        return vale

    # ------------------------------------------------------------------ cancelación

    def cancelar(
        self,
        usuario: Usuario,
        solicitud_id: uuid.UUID,
        datos: CancelacionIn,
        *,
        commit: bool = True,
    ) -> SolicitudDetalleOut:
        """`POST /api/solicitudes-compra/{id}/cancelacion` (SC-07). La ruta exige
        `compras.solicitar`. Solo mientras está PENDIENTE y solo por quien la pidió, un supervisor
        de su almacén o el Administrador."""
        permisos = self._permisos(usuario)
        solicitud = self.repository.get(solicitud_id, bloquear=True)
        if solicitud is None or not self._puede_ver(solicitud, usuario, permisos):
            raise SolicitudNoEncontrada()
        if not self._puede_cancelar(solicitud, usuario, permisos):
            raise SinPermisoParaCancelar()
        if solicitud.estado != E.PENDIENTE:
            raise SolicitudNoCancelable(solicitud.estado)

        ahora = ahora_utc()
        anterior = solicitud.estado
        solicitud.estado = E.CANCELADA
        solicitud.actualizada_en = ahora
        self._evento(solicitud, anterior, E.CANCELADA, usuario, datos.nota, ahora)
        if commit:
            self.session.commit()
        return self._detalle(solicitud, usuario)

    # -------------------------------------------------------------------- internos

    def _evento(
        self,
        solicitud: SolicitudCompra,
        anterior: str | None,
        nuevo: str,
        usuario: Usuario,
        nota: str | None,
        ahora: datetime,
    ) -> None:
        """SC-08: cada cambio de estado agrega un evento; nunca se edita ni se borra uno."""
        self.repository.add_evento(
            SolicitudCompraEvento(
                solicitud_id=solicitud.id,
                estado_anterior=anterior,
                estado_nuevo=nuevo,
                usuario_id=usuario.id,
                nota=nota,
                creado_en=ahora,
            )
        )

    def _fila(self, solicitud: SolicitudCompra) -> Fila:
        return (
            solicitud,
            self.repository.almacen(solicitud.almacen_id),
            self.repository.usuario(solicitud.solicitante_id),
            self.repository.articulo(solicitud.articulo_id),
            self.repository.vale(solicitud.vale_entrada_id),
        )

    def _item(self, fila: Fila, usuario: Usuario, permisos: frozenset[str]) -> SolicitudOut:
        solicitud, almacen, solicitante, articulo, vale = fila
        return SolicitudOut(
            id=solicitud.id,
            folio=solicitud.folio,
            estado=solicitud.estado,
            urgencia=solicitud.urgencia,
            almacen=AlmacenOut(id=almacen.id, clave=almacen.clave, nombre=almacen.nombre),
            solicitante=PersonaOut(id=solicitante.id, nombre=solicitante.nombre),
            articulo=ArticuloOut(id=articulo.id, codigo=articulo.codigo, nombre=articulo.nombre)
            if articulo
            else None,
            descripcion=solicitud.descripcion,
            cantidad=solicitud.cantidad,
            motivo=solicitud.motivo,
            nota_compras=solicitud.nota_compras,
            vale_entrada=ValeEntradaOut(id=vale.id, folio=vale.folio) if vale else None,
            creada_en=solicitud.creada_en,
            actualizada_en=solicitud.actualizada_en,
            acciones=self.acciones(solicitud, usuario, permisos),
        )

    def _detalle(
        self,
        solicitud: SolicitudCompra,
        usuario: Usuario,
        permisos: frozenset[str] | None = None,
    ) -> SolicitudDetalleOut:
        permisos = permisos if permisos is not None else self._permisos(usuario)
        item = self._item(self._fila(solicitud), usuario, permisos)
        eventos = [
            EventoOut(
                id=e.id,
                estado_anterior=e.estado_anterior,
                estado_nuevo=e.estado_nuevo,
                usuario=PersonaOut(id=u.id, nombre=u.nombre),
                nota=e.nota,
                creado_en=e.creado_en,
            )
            for e, u in self.repository.eventos(solicitud.id)
        ]
        return SolicitudDetalleOut(**dict(item), eventos=eventos)
