"""Reglas de negocio y control de la transaccion del modulo `autorizaciones`.

Maquina de estados (TRANSICIONES):

    PENDIENTE -> APROBADA | RECHAZADA | VENCIDA
    APROBADA  -> USADA
    RECHAZADA, VENCIDA, USADA: terminales.

Tipos (`TipoAutorizacion`): EXCEDENTE (un naranja de una entrega), TRASLADO (un traslado entre
almacenes de tercer nivel, X-17 y X-19: sin trabajador, `almacen_id` es el origen y el `detalle`
lleva `origen_almacen_id`, `destino_almacen_id` y los renglones) y DESPACHO (FEAT-014).
El permiso de pedir depende del tipo y se verifica aqui, por clave.

Servicios que usan otros modulos (`movimientos` al confirmar un vale):
`obtener`, `validar_para_vale`, `validar_traslado_para_vale`, `marcar_usada` y `datos_valido`.
Ninguno hace commit: el vale y la autorizacion usada van en la MISMA transaccion y el commit
lo hace `movimientos`.
"""

import hashlib
import json
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import errores_bd
from app.core.excepciones import AppError, Conflicto, DatosInvalidos, NoEncontrado, SinPermiso
from app.core.paginacion import Paginacion
from app.core.reintento import reintentar_si_interbloqueo
from app.core.tiempo import ahora_utc
from app.modulos.acceso.exceptions import PinIncorrecto
from app.modulos.acceso.models import Usuario
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.auditoria.service import AuditoriaService
from app.modulos.autorizaciones.exceptions import (
    AprobacionInvalida,
    AutorizacionInvalida,
    AutorizacionPropia,
    AutorizacionResuelta,
    RenglonNoAutorizable,
)
from app.modulos.autorizaciones.models import (
    Autorizacion,
    EstadoAutorizacion,
    MedioAutorizacion,
    TipoAutorizacion,
)
from app.modulos.autorizaciones.repository import AutorizacionRepository
from app.modulos.autorizaciones.schemas import (
    AlmacenRefOut,
    AutorizacionOut,
    PersonaOut,
    RenglonSolicitud,
    RenglonSolicitudIn,
    ResolucionIn,
    ResolucionMultipleIn,
    ResolucionMultipleOut,
    ResultadoResolucion,
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


# Lo mismo para un TRASLADO (X-17, A-06): recibe (origen_id, destino_id, renglones pedidos) y
# devuelve los renglones evaluados por el servidor. Lanza `RenglonNoAutorizable` si algun renglon
# esta en rojo, si el vale esta en rojo o si el traslado no necesita autorizacion. Lo arma
# `movimientos` (`verificador.py`).
VerificadorTraslado = Callable[
    [uuid.UUID, uuid.UUID, Sequence[RenglonSolicitudIn]], list[RenglonSolicitud]
]


@dataclass(frozen=True)
class RenglonVale:
    """Un renglon del vale que requiere autorizacion, para `validar_para_vale`."""

    codigo: str
    cantidad: int
    renglon: int | None = None


class AutorizacionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = AutorizacionRepository(session)
        self.acceso = AccesoService(session)
        self.auditoria = AuditoriaService(session)

    # ------------------------------------------------------------ solicitar

    def solicitar(self, solicitante, datos, *, verificador_renglones, verificador_traslado=None):
        """DE-04: la misma identidad y cuerpo reutilizan la solicitud, sin nuevo aviso."""
        self.acceso.exigir_permiso(solicitante, _permiso_de_pedir(datos.tipo))
        self.repetida = False
        claves = [_clave_codigo(r.codigo) for r in datos.renglones]
        if len(set(claves)) != len(claves):
            raise DatosInvalidos(
                "Agrupa la cantidad de cada código en un solo renglón.", {"regla": "DE-04"}
            )
        almacen = self.acceso.resolver_almacen(solicitante, datos.almacen_id)
        cuerpo = datos.model_dump(mode="json", exclude={"id_cliente"})
        cuerpo["almacen_id"] = str(almacen)
        cuerpo["solicitada_por"] = str(solicitante.id)
        huella = hashlib.sha256(
            json.dumps(cuerpo, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        if datos.tipo == TipoAutorizacion.DESPACHO and datos.id_cliente is None:
            raise DatosInvalidos(
                "Falta identificar esta solicitud.", [{"campo": "id_cliente", "regla": "DE-04"}]
            )

        def existente():
            previa = self.repository.por_id_cliente(datos.id_cliente)
            if previa is None:
                return None
            if previa.huella_cuerpo != huella:
                raise Conflicto("La solicitud ya existe con otros datos.", {"regla": "DE-04"})
            self.repetida = True
            return previa

        if datos.id_cliente:
            previa = existente()
            if previa:
                return previa
        try:
            return self._solicitar(
                solicitante,
                datos,
                verificador_renglones=verificador_renglones,
                verificador_traslado=verificador_traslado,
                huella=huella,
            )
        except DBAPIError as exc:
            self.session.rollback()
            if datos.id_cliente and errores_bd.es_restriccion(exc, "uq_autorizacion_id_cliente"):
                previa = existente()
                if previa:
                    return previa
            raise
        except Exception:
            self.session.rollback()
            raise

    def _solicitar(
        self,
        solicitante: Usuario,
        datos: SolicitudCreate,
        *,
        verificador_renglones: VerificadorRenglones,
        verificador_traslado: VerificadorTraslado | None = None,
        huella: str | None = None,
    ) -> Autorizacion:
        """Crea una solicitud PENDIENTE (A-02: motivo obligatorio, ya validado en el schema).

        El permiso depende del tipo y se verifica aqui, por clave: `entregas.crear` para un
        EXCEDENTE y `traspasos.operar` para un TRASLADO. El almacen sale del usuario de la sesion
        (RG-07, AC-06; en un TRASLADO es el origen). `vence_en` es ahora mas la vigencia general
        (15 min por defecto).

        A-06 (un rojo no se autoriza) y A-02/A-04 (lo que lee el supervisor es real): del cliente
        solo se toman `codigo` y `cantidad`; el verificador (la evaluacion de `movimientos`)
        devuelve los renglones con lo que dice el servidor y lanza `RenglonNoAutorizable` ante un
        renglon que no se pueda autorizar.
        """
        es_traslado = datos.tipo == TipoAutorizacion.TRASLADO
        self.acceso.exigir_permiso(
            solicitante, P.TRASPASOS_OPERAR if es_traslado else P.ENTREGAS_CREAR
        )
        almacen_id = self.acceso.resolver_almacen(solicitante, datos.almacen_id)
        detalle: dict
        motivo = datos.motivo
        if es_traslado:
            assert datos.destino_almacen_id is not None and verificador_traslado is not None
            existentes = self.repository.almacenes([datos.destino_almacen_id])
            if datos.destino_almacen_id not in existentes:
                raise NoEncontrado("No se encontró el almacén de destino.")
            renglones = verificador_traslado(almacen_id, datos.destino_almacen_id, datos.renglones)
            detalle = {
                "origen_almacen_id": str(almacen_id),
                "destino_almacen_id": str(datos.destino_almacen_id),
            }
        else:
            assert datos.trabajador_id is not None
            if self.repository.trabajador(datos.trabajador_id) is None:
                raise NoEncontrado("No se encontró al trabajador.")
            from app.modulos.autorizaciones.verificador_despacho import evaluar_solicitud

            clasificados, proyecto = [], None
            if datos.tipo == TipoAutorizacion.DESPACHO or self.repository.contiene_epp(
                [r.codigo for r in datos.renglones]
            ):
                clasificados, proyecto = evaluar_solicitud(
                    self.session, solicitante, almacen_id, datos
                )
            necesita = (
                any(r.clase == "EPP" for r in clasificados)
                and self.modo_despacho(solicitante, almacen_id) == "CON_APROBACION"
            )
            if datos.tipo == TipoAutorizacion.DESPACHO:
                if not necesita:
                    raise RenglonNoAutorizable(
                        "Este despacho no necesita aprobación; vuelve a evaluar.",
                        {"regla": "DE-01"},
                    )
                renglones = clasificados
                if not any(r.incluye_excedente for r in renglones):
                    motivo = "Despacho de EPP"
            else:
                if necesita:
                    raise RenglonNoAutorizable(
                        "Envía toda la entrega a aprobación del despacho.", {"regla": "DE-04"}
                    )
                renglones = verificador_renglones(almacen_id, datos.trabajador_id, datos.renglones)
                for indice, r in enumerate(renglones, 1):
                    r.renglon = indice
                    r.incluye_excedente = True
            detalle = {"proyecto": proyecto, "nota": datos.nota}
        if not motivo or not motivo.strip():
            raise DatosInvalidos(
                "Escribe el motivo del excedente.", [{"campo": "motivo", "regla": "DE-05"}]
            )
        detalle["renglones"] = [r.model_dump(mode="json") for r in renglones]
        from app.modulos.notificaciones.service import NotificacionService

        detalle["avisados"] = NotificacionService(self.session).contar_destinatarios(
            almacen_id, solicitante.id
        )

        ahora = ahora_utc()
        vigencia = timedelta(minutes=get_settings().autorizacion_vigencia_minutos)
        autorizacion = self.repository.add(
            Autorizacion(
                tipo=datos.tipo,
                almacen_id=almacen_id,
                trabajador_id=datos.trabajador_id,
                solicitada_por=solicitante.id,
                motivo=motivo,
                id_cliente=datos.id_cliente,
                huella_cuerpo=huella,
                detalle=detalle,
                estado=E.PENDIENTE,
                creado_en=ahora,
                vence_en=ahora + vigencia,
            )
        )
        despues = {
            "tipo": datos.tipo,
            "trabajador_id": datos.trabajador_id,
            "motivo": datos.motivo,
            "renglones": detalle["renglones"],
        }
        if es_traslado:
            despues["destino_almacen_id"] = datos.destino_almacen_id
        self.auditoria.registrar(
            usuario_id=solicitante.id,
            accion="autorizacion.solicitar",
            entidad="autorizacion",
            entidad_id=autorizacion.id,
            despues=despues,
        )
        self.session.commit()
        # El router programa el aviso después de confirmar esta transacción (NT-07).
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
        self,
        actor: Usuario,
        estado: str | None,
        paginacion: Paginacion,
        tipo: str | None = None,
        almacen_id_filtro: uuid.UUID | None = None,
    ) -> tuple[list[SolicitudListItem], int]:
        """Solicitudes para el supervisor. Sin `almacenes.todos`, solo las de su almacén (AC-06)."""
        almacen_id = self._alcance_almacen(actor)
        if almacen_id_filtro is not None:
            almacen_id = (
                {almacen_id_filtro}
                if almacen_id is None or almacen_id_filtro in almacen_id
                else set()
            )
        self.repository.vencer_pendientes(ahora_utc(), almacen_id)
        self.session.commit()
        filas, total = self.repository.listar(
            estado=estado,
            almacen_id=almacen_id,
            offset=paginacion.offset,
            limit=paginacion.limit,
            tipo=tipo,
        )
        almacenes = self.repository.almacenes(
            i for a, _, _ in filas for i in self._almacenes_de_traslado(a)
        )
        elementos = []
        for autorizacion, trabajador, solicitante in filas:
            renglones = self._renglones(autorizacion)
            origen, destino = self._origen_y_destino(autorizacion, almacenes)
            elementos.append(
                SolicitudListItem(
                    id=autorizacion.id,
                    tipo=autorizacion.tipo,
                    servidor_ahora=ahora_utc(),
                    avisados=(autorizacion.detalle or {}).get("avisados", 0),
                    nota=(autorizacion.detalle or {}).get("nota"),
                    proyecto=(autorizacion.detalle or {}).get("proyecto"),
                    renglones_resueltos=autorizacion.renglones_resueltos,
                    incluye_excedente=(
                        autorizacion.tipo == TipoAutorizacion.EXCEDENTE
                        or any(r.incluye_excedente for r in renglones)
                    ),
                    almacen=AlmacenRefOut.model_validate(
                        self.repository.almacenes([autorizacion.almacen_id])[
                            autorizacion.almacen_id
                        ],
                        from_attributes=True,
                    ),
                    estado=autorizacion.estado,
                    almacen_id=autorizacion.almacen_id,
                    trabajador=_trabajador_out(trabajador),
                    origen=origen,
                    destino=destino,
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
            # El PIN se da en el dispositivo de quien pidió: debe poder pedir esta clase de
            # solicitud (`entregas.crear`, o `traspasos.operar` en un traslado).
            self.acceso.exigir_permiso(actor, _permiso_de_pedir(autorizacion.tipo))
        else:
            self.acceso.exigir_permiso(actor, P.AUTORIZACIONES_RESOLVER)
        if not self._en_alcance(autorizacion, actor):
            raise NoEncontrado("No se encontró la solicitud.")  # no es supervisor del origen
        if datos.renglones is not None and autorizacion.tipo == TipoAutorizacion.TRASLADO:
            raise DatosInvalidos(
                "Un traslado se aprueba o se rechaza completo.",
                [{"campo": "renglones", "regla": "X-19"}],
            )

        # Una vencida o ya resuelta no se resuelve de nuevo (y no gasta intentos de PIN).
        self._vencer_si_corresponde(autorizacion)
        if autorizacion.estado != E.PENDIENTE:
            self.session.commit()  # guarda el vencimiento, si lo hubo
            raise AutorizacionResuelta(
                _mensaje_no_pendiente(autorizacion.estado), self._detalle_resuelta(autorizacion)
            )

        if por_pin:
            autorizador = self._autorizador_por_pin(autorizacion, datos.usuario, datos.pin)
            medio = MedioAutorizacion.PIN
        else:
            autorizador = actor
            medio = MedioAutorizacion.REMOTA

        if autorizador.id == autorizacion.solicitada_por:
            raise AutorizacionPropia()  # A-05, AC-07

        resueltos = self._resolver_renglones(autorizacion, datos)
        nuevo = E.APROBADA if any(r["decision"] == "APROBADO" for r in resueltos) else E.RECHAZADA
        autorizacion.renglones_resueltos = resueltos
        antes = autorizacion.estado
        self._transicionar(autorizacion, nuevo)
        autorizacion.resuelta_por = autorizador.id
        autorizacion.medio = medio
        autorizacion.resuelta_en = ahora_utc()
        if nuevo == E.APROBADA:
            autorizacion.vence_en = autorizacion.resuelta_en + timedelta(
                minutes=get_settings().autorizacion_vigencia_minutos
            )
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
                "renglones_resueltos": resueltos,
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
        autorizacion = self.repository.get(autorizacion_id, bloquear=True)
        if autorizacion is None:
            raise NoEncontrado("No se encontró la autorización.")
        self._exigir_aprobada_y_vigente(autorizacion)
        if autorizacion.tipo != TipoAutorizacion.EXCEDENTE:
            raise AutorizacionInvalida("Esta autorización es de un traslado, no de una entrega.")
        if autorizacion.almacen_id != almacen_id:
            raise AutorizacionInvalida("La autorización es de otro almacén.")
        if autorizacion.trabajador_id != trabajador_id:
            raise AutorizacionInvalida("La autorización es de otro trabajador.")
        if autorizacion.resuelta_por == usuario.id:
            raise AutorizacionPropia()
        self._validar_cobertura(autorizacion, renglones)
        return autorizacion

    def validar_traslado_para_vale(
        self,
        autorizacion_id: uuid.UUID,
        origen_id: uuid.UUID,
        destino_id: uuid.UUID,
        renglones: Sequence[RenglonVale],
        usuario: Usuario,
    ) -> Autorizacion:
        """X-19: comprueba que la autorización de traslado sirve para este vale.

        Debe ser de tipo TRASLADO, estar APROBADA, vigente y sin usar, y ser del mismo origen y
        del mismo destino. Cubre cada renglón del vale con su código y una cantidad que no pase
        de la autorizada: después de aprobada se pueden QUITAR renglones (o bajar una cantidad),
        pero no agregar uno, subir una cantidad ni cambiar el destino. `usuario` es quien
        confirma: no puede ser quien autorizó (A-05). Lanza `AutorizacionInvalida` (409) con la
        causa. No escribe nada; `movimientos` llama después a `marcar_usada` en la misma
        transacción del vale.
        """
        autorizacion = self.obtener(autorizacion_id)
        self._exigir_aprobada_y_vigente(autorizacion)
        if autorizacion.tipo != TipoAutorizacion.TRASLADO:
            raise AutorizacionInvalida("Esta autorización no es de un traslado.")
        if autorizacion.almacen_id != origen_id:
            raise AutorizacionInvalida("La autorización es de otro almacén de origen.")
        if (autorizacion.detalle or {}).get("destino_almacen_id") != str(destino_id):
            raise AutorizacionInvalida("La autorización es para otro destino (X-19).")
        if autorizacion.resuelta_por == usuario.id:
            raise AutorizacionPropia()
        autorizados = {_clave_codigo(r.codigo): r.cantidad for r in self._renglones(autorizacion)}
        for renglon in renglones:
            tope = autorizados.get(_clave_codigo(renglon.codigo))
            if tope is None or renglon.cantidad > tope:
                raise AutorizacionInvalida(
                    f"La autorización no cubre el renglón {renglon.codigo} con esa cantidad "
                    "(X-19): solo se pueden quitar renglones.",
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

    def modo_despacho(self, usuario, almacen_id):
        almacen = self.repository.almacenes([almacen_id]).get(almacen_id)
        if almacen is None:
            raise NoEncontrado("No se encontró el almacén.")
        if self.acceso.es_supervisor_de(usuario, almacen_id):
            return "SUPERVISOR"
        if not almacen.despacho_epp_con_aprobacion:
            return "AUTONOMO_ALMACEN"
        if usuario.despacho_autonomo:
            return "AUTONOMO_USUARIO"
        return "CON_APROBACION"

    def _detalle_resuelta(self, a):
        quien = self.repository.usuario(a.resuelta_por) if a.resuelta_por else None
        return {
            "estado": a.estado,
            "resuelta_por": {"id": str(quien.id), "nombre": quien.nombre} if quien else None,
            "resuelta_en": a.resuelta_en.isoformat() + "Z" if a.resuelta_en else None,
            "medio": a.medio,
        }

    def _resolver_renglones(self, a, datos):
        todos = self._renglones(a)
        requeridos = [(r.renglon or i, r) for i, r in enumerate(todos, 1) if r.clase != "CONTEXTO"]
        pedidos = {r.renglon: r for r in datos.renglones or []}
        if datos.renglones is not None and (
            len(pedidos) != len(datos.renglones) or set(pedidos) != {i for i, _ in requeridos}
        ):
            raise DatosInvalidos(
                "Decide una vez por cada artículo que pide aprobación.",
                [{"campo": "renglones", "regla": "DE-06"}],
            )
        salida = []
        for i, r in requeridos:
            pedido = pedidos.get(i)
            decision = pedido.decision if pedido else datos.decision
            motivo = pedido.motivo if pedido else datos.motivo
            if (
                decision == "RECHAZAR"
                and a.tipo != TipoAutorizacion.TRASLADO
                and not (motivo or "").strip()
            ):
                raise DatosInvalidos(
                    "Escribe el motivo de cada rechazo.",
                    [{"campo": "motivo", "renglon": i, "regla": "DE-06"}],
                )
            salida.append(
                {
                    "renglon": i,
                    "codigo": r.codigo,
                    "cantidad": r.cantidad,
                    "decision": "APROBADO" if decision == "APROBAR" else "RECHAZADO",
                    "motivo": motivo.strip() if motivo else None,
                }
            )
        return salida

    def _validar_cobertura(self, a, renglones):
        if a.renglones_resueltos is None:
            autorizados = {
                _clave_codigo(r.codigo): {"cantidad": r.cantidad, "decision": "APROBADO"}
                for r in self._renglones(a)
            }
        else:
            autorizados = {_clave_codigo(r["codigo"]): r for r in a.renglones_resueltos}
        invalidos = []
        acumulados = {}
        for indice, r in enumerate(renglones, 1):
            codigo = _clave_codigo(r.codigo)
            acumulados[codigo] = acumulados.get(codigo, 0) + r.cantidad
            cubierto = autorizados.get(codigo)
            causa = (
                "NO_INCLUIDO"
                if cubierto is None
                else "RECHAZADO"
                if cubierto["decision"] != "APROBADO"
                else "CANTIDAD_MAYOR"
                if acumulados[codigo] > cubierto["cantidad"]
                else None
            )
            if causa:
                invalidos.append(
                    {"renglon": r.renglon or indice, "codigo": r.codigo, "causa": causa}
                )
        if invalidos:
            raise AprobacionInvalida(detalles={"regla": "DE-08", "renglones": invalidos})

    def validar_despacho_para_vale(
        self,
        autorizacion_id,
        almacen_id,
        trabajador_id,
        proyecto_id,
        renglones,
        usuario,
        *,
        bloquear=True,
    ):
        a = self.repository.get(autorizacion_id, bloquear=bloquear)
        if a is None:
            raise AutorizacionInvalida("No se encontró la aprobación.")
        self._exigir_aprobada_y_vigente(a)
        if (
            a.tipo != TipoAutorizacion.DESPACHO
            or a.almacen_id != almacen_id
            or a.trabajador_id != trabajador_id
        ):
            raise AutorizacionInvalida("La aprobación corresponde a otra entrega.")
        proyecto = (a.detalle or {}).get("proyecto")
        if (proyecto or {}).get("id") != (str(proyecto_id) if proyecto_id else None):
            raise AutorizacionInvalida(
                "La aprobación corresponde a otro proyecto.", {"regla": "DE-13"}
            )
        if a.resuelta_por == usuario.id:
            raise AutorizacionPropia()
        self._validar_cobertura(a, renglones)
        return a

    def resolver_multiple(self, actor, datos: ResolucionMultipleIn):
        self.acceso.exigir_permiso(actor, P.AUTORIZACIONES_RESOLVER)
        resultados = []
        for item in datos.resoluciones:
            try:
                a = self.repository.get(item.id)
                if a is None or not self._puede_ver(a, actor):
                    raise NoEncontrado("No se encontró la solicitud.")
                if item.decision == "APROBAR" and (
                    a.tipo == TipoAutorizacion.EXCEDENTE
                    or any(r.incluye_excedente for r in self._renglones(a))
                ):
                    raise RenglonNoAutorizable(
                        "Abre esta solicitud para revisar el excedente.", {"regla": "DE-12"}
                    )
                resuelta = self.resolver(
                    item.id, actor, ResolucionIn(decision=item.decision, motivo=item.motivo)
                )
                resultados.append(ResultadoResolucion(id=item.id, estado=resuelta.estado))
            except AppError as exc:
                self.session.rollback()
                resultados.append(
                    ResultadoResolucion(
                        id=item.id, error={"codigo": exc.codigo, "mensaje": exc.mensaje}
                    )
                )
        return ResolucionMultipleOut(resultados=resultados)

    # ------------------------------------------------------------- internos

    def _exigir_aprobada_y_vigente(self, autorizacion: Autorizacion) -> None:
        if autorizacion.estado == E.USADA:
            raise AutorizacionInvalida("Esta autorización ya se usó; solo sirve una vez (A-03).")
        if autorizacion.estado != E.APROBADA:
            raise AutorizacionInvalida("La autorización no está aprobada.")
        if autorizacion.vence_en <= ahora_utc():
            raise AutorizacionInvalida("La autorización venció.")

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

    def _alcance_almacen(self, usuario):
        alcance = self.acceso.alcance_del_usuario(usuario.id)
        if alcance == set():
            raise SinPermiso("No tienes almacenes asignados.")
        return alcance

    def _en_alcance(self, autorizacion, usuario):
        return self.acceso.en_alcance(usuario, autorizacion.almacen_id)

    def _puede_ver(self, autorizacion: Autorizacion, actor: Usuario) -> bool:
        if autorizacion.solicitada_por == actor.id:
            return True
        return self.acceso.tiene_permiso(actor, P.AUTORIZACIONES_RESOLVER) and self._en_alcance(
            autorizacion, actor
        )

    @staticmethod
    def _almacenes_de_traslado(autorizacion: Autorizacion) -> list[uuid.UUID]:
        """Origen y destino de un TRASLADO (vacío en los demás tipos)."""
        if autorizacion.tipo != TipoAutorizacion.TRASLADO:
            return []
        detalle = autorizacion.detalle or {}
        return [autorizacion.almacen_id, uuid.UUID(detalle["destino_almacen_id"])]

    @staticmethod
    def _origen_y_destino(
        autorizacion: Autorizacion, almacenes: dict
    ) -> tuple[AlmacenRefOut | None, AlmacenRefOut | None]:
        if autorizacion.tipo != TipoAutorizacion.TRASLADO:
            return None, None
        destino_id = uuid.UUID((autorizacion.detalle or {})["destino_almacen_id"])
        origen, destino = almacenes[autorizacion.almacen_id], almacenes[destino_id]
        return (
            AlmacenRefOut(id=origen.id, clave=origen.clave, nombre=origen.nombre),
            AlmacenRefOut(id=destino.id, clave=destino.clave, nombre=destino.nombre),
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
        trabajador = (
            self.repository.trabajador(autorizacion.trabajador_id)
            if autorizacion.trabajador_id
            else None
        )
        almacenes = self.repository.almacenes(self._almacenes_de_traslado(autorizacion))
        origen, destino = self._origen_y_destino(autorizacion, almacenes)
        return AutorizacionOut(
            id=autorizacion.id,
            tipo=autorizacion.tipo,
            servidor_ahora=ahora_utc(),
            avisados=(autorizacion.detalle or {}).get("avisados", 0),
            nota=(autorizacion.detalle or {}).get("nota"),
            proyecto=(autorizacion.detalle or {}).get("proyecto"),
            renglones_resueltos=autorizacion.renglones_resueltos,
            incluye_excedente=(
                autorizacion.tipo == TipoAutorizacion.EXCEDENTE
                or any(r.incluye_excedente for r in self._renglones(autorizacion))
            ),
            almacen=AlmacenRefOut.model_validate(
                self.repository.almacenes([autorizacion.almacen_id])[autorizacion.almacen_id],
                from_attributes=True,
            ),
            estado=autorizacion.estado,
            medio=autorizacion.medio,
            motivo=autorizacion.motivo,
            trabajador_id=autorizacion.trabajador_id,
            trabajador=_trabajador_out(trabajador),
            almacen_id=autorizacion.almacen_id,
            origen=origen,
            destino=destino,
            renglones=self._renglones(autorizacion),
            solicitada_por=PersonaOut(id=solicitante.id, nombre=solicitante.nombre),
            resuelta_por=PersonaOut(id=autorizador.id, nombre=autorizador.nombre)
            if autorizador
            else None,
            creado_en=autorizacion.creado_en,
            resuelta_en=autorizacion.resuelta_en,
            vence_en=autorizacion.vence_en,
        )


def _permiso_de_pedir(tipo: str) -> str:
    """El permiso que se necesita para PEDIR una autorización de ese tipo."""
    return P.TRASPASOS_OPERAR if tipo == TipoAutorizacion.TRASLADO else P.ENTREGAS_CREAR


def _clave_codigo(codigo: str) -> str:
    return codigo.strip().casefold()


def _trabajador_out(trabajador) -> TrabajadorOut | None:
    if trabajador is None:
        return None
    return TrabajadorOut(
        id=trabajador.id,
        nombre=trabajador.nombre,
        numero_empleado=trabajador.numero_empleado,
        tiene_foto=trabajador.foto_adjunto_id is not None,
    )


def _mensaje_no_pendiente(estado: str) -> str:
    return {
        E.VENCIDA: "La solicitud venció. Quita el renglón y entrega lo demás (A-07).",
        E.APROBADA: "La solicitud ya se aprobó.",
        E.RECHAZADA: "La solicitud ya se rechazó.",
        E.USADA: "La solicitud ya se usó.",
    }.get(estado, "Esta solicitud ya no está pendiente.")


__all__ = [
    "AutorizacionService",
    "RenglonVale",
    "TRANSICIONES",
    "VerificadorRenglones",
    "VerificadorTraslado",
]
