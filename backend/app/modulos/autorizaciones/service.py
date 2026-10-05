"""Reglas de negocio y control de la transaccion del modulo `autorizaciones`.

Maquina de estados (TRANSICIONES):

    PENDIENTE -> APROBADA | RECHAZADA | VENCIDA
    APROBADA  -> USADA
    RECHAZADA, VENCIDA, USADA: terminales.

Servicios que usan otros modulos (`movimientos` al confirmar un vale):
`obtener`, `validar_para_vale`, `marcar_usada` y `datos_valido`. Ninguno hace commit: el vale y la
autorizacion usada van en la MISMA transaccion y el commit lo hace `movimientos`.
"""

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import errores_bd
from app.core.excepciones import NoEncontrado, SinPermiso
from app.core.paginacion import Paginacion
from app.core.reintento import reintentar_si_interbloqueo
from app.core.tiempo import ahora_utc
from app.modulos.acceso.exceptions import PinIncorrecto
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.auditoria.service import AuditoriaService
from app.modulos.autorizaciones.exceptions import (
    AutorizacionInvalida,
    AutorizacionPropia,
    AutorizacionResuelta,
)
from app.modulos.autorizaciones.models import Autorizacion, EstadoAutorizacion, MedioAutorizacion
from app.modulos.autorizaciones.repository import AutorizacionRepository
from app.modulos.autorizaciones.schemas import (
    AutorizacionOut,
    PersonaOut,
    RenglonSolicitud,
    RenglonSolicitudIn,
    ResolucionIn,
    SolicitudCreate,
    SolicitudListItem,
    TrabajadorOut,
    ValidoOut,
)
from app.seguridad import HASH_RELLENO, verificar_secreto

E = EstadoAutorizacion

TRANSICIONES: dict[str, frozenset[str]] = {
    E.PENDIENTE: frozenset({E.APROBADA, E.RECHAZADA, E.VENCIDA}),
    E.APROBADA: frozenset({E.USADA}),
    E.RECHAZADA: frozenset(),
    E.VENCIDA: frozenset(),
    E.USADA: frozenset(),
}

# Punto de integracion con la evaluacion real (A-02, A-06). Recibe (almacen_id, trabajador_id,
# renglones pedidos: solo `codigo` y `cantidad`) y devuelve los renglones tal como los evaluo el
# SERVIDOR (articulo, limite, tiene, excedente, regla y mensaje), que son los que se guardan y lee
# quien autoriza. Lanza `RenglonNoAutorizable` si algun renglon no es naranja (verde, amarillo o
# rojo). Lo arma `movimientos` (`verificador.py`).
VerificadorRenglones = Callable[
    [uuid.UUID, uuid.UUID, Sequence[RenglonSolicitudIn]], list[RenglonSolicitud]
]


@dataclass(frozen=True)
class RenglonVale:
    """Un renglon del vale que requiere autorizacion, para `validar_para_vale`."""

    codigo: str
    cantidad: int


class AutorizacionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = AutorizacionRepository(session)
        self.acceso = AccesoService(session)
        self.auditoria = AuditoriaService(session)

    # ------------------------------------------------------------ solicitar

    def solicitar(
        self,
        solicitante: Usuario,
        datos: SolicitudCreate,
        *,
        verificador_renglones: VerificadorRenglones,
    ) -> Autorizacion:
        """Crea una solicitud PENDIENTE (A-02: motivo obligatorio, ya validado en el schema).

        El almacen sale del usuario de la sesion (RG-07, AC-06). `vence_en` es ahora mas la
        vigencia general (15 min por defecto).

        A-06 (un rojo no se autoriza) y A-02/A-04 (lo que lee el supervisor es real): del cliente
        solo se toman `codigo` y `cantidad`; `verificador_renglones` (la evaluacion de
        `movimientos`) devuelve los renglones con articulo, limite, excedente y regla del
        servidor, y lanza `RenglonNoAutorizable` ante un renglon que no sea naranja.
        """
        almacen_id = self.acceso.resolver_almacen(solicitante, datos.almacen_id)
        if self.repository.trabajador(datos.trabajador_id) is None:
            raise NoEncontrado("No se encontró al trabajador.")
        renglones = verificador_renglones(almacen_id, datos.trabajador_id, datos.renglones)

        ahora = ahora_utc()
        vigencia = timedelta(minutes=get_settings().autorizacion_vigencia_minutos)
        autorizacion = self.repository.add(
            Autorizacion(
                almacen_id=almacen_id,
                trabajador_id=datos.trabajador_id,
                solicitada_por=solicitante.id,
                motivo=datos.motivo,
                detalle={"renglones": [r.model_dump(mode="json") for r in renglones]},
                estado=E.PENDIENTE,
                creado_en=ahora,
                vence_en=ahora + vigencia,
            )
        )
        self.auditoria.registrar(
            usuario_id=solicitante.id,
            accion="autorizacion.solicitar",
            entidad="autorizacion",
            entidad_id=autorizacion.id,
            despues={
                "trabajador_id": datos.trabajador_id,
                "motivo": datos.motivo,
                "renglones": autorizacion.detalle["renglones"],
            },
        )
        self.session.commit()
        return autorizacion

    # ------------------------------------------------------------- consultas

    def consultar(self, autorizacion_id: uuid.UUID, actor: Usuario) -> AutorizacionOut:
        """Estado de una solicitud para quien la pidió o quien puede resolverla (A-01).

        Si venció, informa VENCIDA y lo guarda. Quien no la puede ver recibe 404.
        """
        autorizacion = self.obtener(autorizacion_id)
        if not self._puede_ver(autorizacion, actor):
            raise NoEncontrado("No se encontró la solicitud.")
        self.session.commit()  # guarda el vencimiento, si lo hubo
        return self._salida(autorizacion)

    def listar(
        self, actor: Usuario, estado: str | None, paginacion: Paginacion
    ) -> tuple[list[SolicitudListItem], int]:
        """Solicitudes para el supervisor. Sin `almacenes.todos`, solo las de su almacén (AC-06)."""
        almacen_id = self._alcance_almacen(actor)
        self.repository.vencer_pendientes(ahora_utc(), almacen_id)
        self.session.commit()
        filas, total = self.repository.listar(
            estado=estado, almacen_id=almacen_id, offset=paginacion.offset, limit=paginacion.limit
        )
        elementos = []
        for autorizacion, trabajador, solicitante in filas:
            renglones = self._renglones(autorizacion)
            elementos.append(
                SolicitudListItem(
                    id=autorizacion.id,
                    estado=autorizacion.estado,
                    almacen_id=autorizacion.almacen_id,
                    trabajador=TrabajadorOut(
                        id=trabajador.id,
                        nombre=trabajador.nombre,
                        numero_empleado=trabajador.numero_empleado,
                    ),
                    solicitada_por=PersonaOut(id=solicitante.id, nombre=solicitante.nombre),
                    motivo=autorizacion.motivo,
                    renglones=renglones,
                    excedente_total=sum(r.excedente or 0 for r in renglones),
                    creado_en=autorizacion.creado_en,
                    vence_en=autorizacion.vence_en,
                )
            )
        return elementos, total

    # ------------------------------------------------------------ resolución

    def resolver(
        self, autorizacion_id: uuid.UUID, actor: Usuario, datos: ResolucionIn
    ) -> AutorizacionOut:
        """Aprueba o rechaza una solicitud pendiente (ver `_resolver`). Un interbloqueo de la base
        se reintenta desde el principio: antes de verificar el PIN no se escribe nada."""
        return reintentar_si_interbloqueo(
            self.session, lambda: self._resolver(autorizacion_id, actor, datos)
        )

    def _resolver(
        self, autorizacion_id: uuid.UUID, actor: Usuario, datos: ResolucionIn
    ) -> AutorizacionOut:
        """Aprueba o rechaza una solicitud pendiente.

        Sin `usuario`/`pin`: medio REMOTA, resuelve `actor` (el supervisor desde su celular) y
        debe tener `autorizaciones.resolver`. Con `usuario` y `pin`: medio PIN, desde el
        dispositivo del almacenista; `actor` (el almacenista) debe poder pedir autorizaciones y
        el permiso se verifica sobre el supervisor identificado por `usuario`.

        Reglas: A-05 quien pidió no se autoriza; una solicitud resuelta o vencida no se resuelve
        de nuevo; el PIN se verifica ANTES de escribir nada (en fallo ya hace commit del
        contador de intentos).
        """
        autorizacion = self.repository.get(autorizacion_id, bloquear=True)
        if autorizacion is None:
            raise NoEncontrado("No se encontró la solicitud.")
        por_pin = datos.usuario is not None
        if por_pin:
            self.acceso.exigir_permiso(actor, P.ENTREGAS_CREAR)
        else:
            self.acceso.exigir_permiso(actor, P.AUTORIZACIONES_RESOLVER)
        if not self._en_alcance(autorizacion, actor):
            raise NoEncontrado("No se encontró la solicitud.")

        # Una vencida o ya resuelta no se resuelve de nuevo (y no gasta intentos de PIN).
        self._vencer_si_corresponde(autorizacion)
        if autorizacion.estado != E.PENDIENTE:
            self.session.commit()  # guarda el vencimiento, si lo hubo
            raise AutorizacionResuelta(_mensaje_no_pendiente(autorizacion.estado))

        if por_pin:
            autorizador = self._autorizador_por_pin(autorizacion, datos.usuario, datos.pin)
            medio = MedioAutorizacion.PIN
        else:
            autorizador = actor
            medio = MedioAutorizacion.REMOTA

        if autorizador.id == autorizacion.solicitada_por:
            raise AutorizacionPropia()  # A-05, AC-07

        nuevo = E.APROBADA if datos.decision == "APROBAR" else E.RECHAZADA
        antes = autorizacion.estado
        self._transicionar(autorizacion, nuevo)
        autorizacion.resuelta_por = autorizador.id
        autorizacion.medio = medio
        autorizacion.resuelta_en = ahora_utc()
        self.auditoria.registrar(
            usuario_id=autorizador.id,
            accion="autorizacion.aprobar" if nuevo == E.APROBADA else "autorizacion.rechazar",
            entidad="autorizacion",
            entidad_id=autorizacion.id,
            antes={"estado": antes},
            despues={
                "estado": nuevo,
                "medio": medio,
                "solicitada_por": autorizacion.solicitada_por,
                "motivo": autorizacion.motivo,
                "excedente": sum(r.excedente or 0 for r in self._renglones(autorizacion)),
            },
        )
        try:
            self.session.commit()
        except DBAPIError as exc:
            self.session.rollback()
            if errores_bd.es_restriccion(exc, "ck_autorizacion_no_autorizarse"):
                raise AutorizacionPropia() from exc
            raise
        return self._salida(autorizacion)

    # ------------------------------------------- servicios para otros módulos

    def obtener(self, autorizacion_id: uuid.UUID) -> Autorizacion:
        """La autorización por `id` (404 `NO_ENCONTRADO` si no existe). Sin comprobar permisos.

        Si estaba PENDIENTE y ya venció, la pasa a VENCIDA (solo `flush`; commit de quien llama).
        """
        autorizacion = self.repository.get(autorizacion_id)
        if autorizacion is None:
            raise NoEncontrado("No se encontró la autorización.")
        self._vencer_si_corresponde(autorizacion)
        return autorizacion

    def validar_para_vale(
        self,
        autorizacion_id: uuid.UUID,
        almacen_id: uuid.UUID,
        trabajador_id: uuid.UUID,
        renglones: Sequence[RenglonVale],
        usuario: Usuario,
    ) -> Autorizacion:
        """Comprueba que la autorización sirve para confirmar este vale (A-03, A-05).

        Debe estar APROBADA, vigente (antes de `vence_en`), sin usar, del mismo almacén y del
        mismo trabajador, y cubrir CADA renglón de `renglones` (los que requieren autorización:
        mismo `codigo` y misma `cantidad` que se autorizó; si cambió la cantidad ya no cubre).
        `usuario` es quien confirma el vale: no puede ser quien autorizó (A-05). Lanza
        `AutorizacionInvalida` (409) con la causa. No escribe nada; después se llama a
        `marcar_usada` en la misma transacción del vale.
        """
        autorizacion = self.obtener(autorizacion_id)
        if autorizacion.estado == E.USADA:
            raise AutorizacionInvalida("Esta autorización ya se usó; solo sirve una vez (A-03).")
        if autorizacion.estado != E.APROBADA:
            raise AutorizacionInvalida("La autorización no está aprobada.")
        if autorizacion.vence_en <= ahora_utc():
            raise AutorizacionInvalida("La autorización venció.")
        if autorizacion.almacen_id != almacen_id:
            raise AutorizacionInvalida("La autorización es de otro almacén.")
        if autorizacion.trabajador_id != trabajador_id:
            raise AutorizacionInvalida("La autorización es de otro trabajador.")
        if autorizacion.resuelta_por == usuario.id:
            raise AutorizacionPropia()
        autorizados = {(r.codigo, r.cantidad) for r in self._renglones(autorizacion)}
        for renglon in renglones:
            if (renglon.codigo, renglon.cantidad) not in autorizados:
                raise AutorizacionInvalida(
                    f"La autorización no cubre el renglón {renglon.codigo} con esa cantidad "
                    "(A-03).",
                    {"codigo": renglon.codigo, "cantidad": renglon.cantidad},
                )
        return autorizacion

    def marcar_usada(self, autorizacion_id: uuid.UUID) -> Autorizacion:
        """APROBADA -> USADA (A-03: un solo uso). Solo `flush`: va en la transacción del vale.

        Toma el renglón `FOR UPDATE`, así dos vales a la vez no usan la misma autorización.
        """
        autorizacion = self.repository.get(autorizacion_id, bloquear=True)
        if autorizacion is None:
            raise NoEncontrado("No se encontró la autorización.")
        if autorizacion.estado != E.APROBADA:
            raise AutorizacionInvalida("Esta autorización ya se usó o no está aprobada (A-03).")
        self._transicionar(autorizacion, E.USADA)
        self.session.flush()
        return autorizacion

    def datos_valido(self, autorizacion: Autorizacion) -> ValidoOut | None:
        """Quién autorizó, cuándo y por qué medio, para imprimir "Validó" (A-04).

        `None` si la autorización aún no se aprobó. Sirve también cuando ya está USADA.
        """
        if autorizacion.resuelta_por is None or autorizacion.estado not in (E.APROBADA, E.USADA):
            return None
        autorizador = self.repository.usuario(autorizacion.resuelta_por)
        return ValidoOut(
            usuario_id=autorizacion.resuelta_por,
            nombre=autorizador.nombre if autorizador else "",
            medio=MedioAutorizacion(autorizacion.medio),
            resuelta_en=autorizacion.resuelta_en,
            motivo=autorizacion.motivo,
        )

    # ------------------------------------------------------------- internos

    def _transicionar(self, autorizacion: Autorizacion, nuevo: str) -> None:
        if nuevo not in TRANSICIONES[autorizacion.estado]:
            raise AutorizacionResuelta(f"No se puede pasar de {autorizacion.estado} a {nuevo}.")
        autorizacion.estado = nuevo

    def _vencer_si_corresponde(self, autorizacion: Autorizacion) -> None:
        if autorizacion.estado == E.PENDIENTE and autorizacion.vence_en <= ahora_utc():
            self._transicionar(autorizacion, E.VENCIDA)
            self.session.flush()

    def _autorizador_por_pin(self, autorizacion: Autorizacion, nombre: str, pin: str) -> Usuario:
        supervisor = self.repository.usuario_por_nombre(nombre)
        if supervisor is None or not supervisor.activo:
            verificar_secreto(pin, HASH_RELLENO)  # mismo tiempo que un usuario real
            raise PinIncorrecto()
        self.acceso.verificar_pin(supervisor, pin)  # ANTES de escribir; en fallo hace commit
        if not self.acceso.tiene_permiso(supervisor, P.AUTORIZACIONES_RESOLVER):
            raise SinPermiso("Ese usuario no puede autorizar.")
        if not self._en_alcance(autorizacion, supervisor):
            raise SinPermiso("Ese usuario no puede autorizar en este almacén.")
        return supervisor

    def _alcance_almacen(self, usuario: Usuario) -> uuid.UUID | None:
        """AC-06: `None` (todos) con `almacenes.todos`; si no, solo el almacén del usuario."""
        if self.acceso.puede_operar_todos_los_almacenes(usuario):
            return None
        if usuario.almacen_id is None:
            raise SinPermiso("No tienes un almacén asignado.")
        return usuario.almacen_id

    def _en_alcance(self, autorizacion: Autorizacion, usuario: Usuario) -> bool:
        if self.acceso.puede_operar_todos_los_almacenes(usuario):
            return True
        return usuario.almacen_id == autorizacion.almacen_id

    def _puede_ver(self, autorizacion: Autorizacion, actor: Usuario) -> bool:
        if autorizacion.solicitada_por == actor.id:
            return True
        return self.acceso.tiene_permiso(actor, P.AUTORIZACIONES_RESOLVER) and self._en_alcance(
            autorizacion, actor
        )

    @staticmethod
    def _renglones(autorizacion: Autorizacion) -> list[RenglonSolicitud]:
        detalle = autorizacion.detalle or {}
        return [RenglonSolicitud.model_validate(r) for r in detalle.get("renglones", [])]

    def _salida(self, autorizacion: Autorizacion) -> AutorizacionOut:
        solicitante = self.repository.usuario(autorizacion.solicitada_por)
        autorizador = (
            self.repository.usuario(autorizacion.resuelta_por)
            if autorizacion.resuelta_por
            else None
        )
        return AutorizacionOut(
            id=autorizacion.id,
            estado=autorizacion.estado,
            medio=autorizacion.medio,
            motivo=autorizacion.motivo,
            trabajador_id=autorizacion.trabajador_id,
            almacen_id=autorizacion.almacen_id,
            renglones=self._renglones(autorizacion),
            solicitada_por=PersonaOut(id=solicitante.id, nombre=solicitante.nombre),
            resuelta_por=PersonaOut(id=autorizador.id, nombre=autorizador.nombre)
            if autorizador
            else None,
            creado_en=autorizacion.creado_en,
            resuelta_en=autorizacion.resuelta_en,
            vence_en=autorizacion.vence_en,
        )


def _mensaje_no_pendiente(estado: str) -> str:
    return {
        E.VENCIDA: "La solicitud venció. Quita el renglón y entrega lo demás (A-07).",
        E.APROBADA: "La solicitud ya se aprobó.",
        E.RECHAZADA: "La solicitud ya se rechazó.",
        E.USADA: "La solicitud ya se usó.",
    }.get(estado, "Esta solicitud ya no está pendiente.")


__all__ = ["AutorizacionService", "RenglonVale", "TRANSICIONES", "VerificadorRenglones"]
