"""Web Push: las tareas abren una sesión propia después de confirmar la operación (NT-07)."""

import hashlib
import json
import uuid
from datetime import timedelta

import requests
from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.excepciones import DemasiadosIntentos, NoEncontrado
from app.core.tiempo import ahora_utc
from app.db import get_sessionmaker
from app.modulos.acceso.permisos import P
from app.modulos.acceso.service import AccesoService
from app.modulos.auditoria.service import AuditoriaService
from app.modulos.notificaciones.models import SuscripcionPush
from app.modulos.notificaciones.repository import NotificacionRepository
from app.modulos.notificaciones.schemas import PruebaOut, SuscripcionIn


class TransportePush:
    def enviar(self, s, payload, ttl):
        # No seguir redirecciones: las claves no salen del proveedor validado (NT-03).
        class SinRedireccion(requests.Session):
            def post(self, url, *args, **kwargs):
                kwargs["allow_redirects"] = False
                return super().post(url, *args, **kwargs)

        cfg = get_settings()
        with SinRedireccion() as http:
            return webpush(
                subscription_info={
                    "endpoint": s.endpoint,
                    "keys": {
                        "p256dh": s.p256dh,
                        "auth": s.auth,
                    },
                },
                data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=cfg.vapid_clave_privada,
                vapid_claims={"sub": cfg.vapid_contacto},
                ttl=ttl,
                timeout=5,
                requests_session=http,
            )


class NotificacionService:
    def __init__(self, session: Session, transporte=None):
        self.session = session
        self.repository = NotificacionRepository(session)
        self.acceso = AccesoService(session)
        self.transporte = transporte or TransportePush()

    def configurada(self):
        cfg = get_settings()
        return bool(cfg.vapid_clave_publica and cfg.vapid_clave_privada)

    def registrar(self, actor, familia, datos: SuscripcionIn, agente=None):
        self.acceso.exigir_permiso(actor, P.AUTORIZACIONES_RESOLVER)
        try:
            huella = hashlib.sha256(datos.endpoint.encode()).hexdigest()
            anterior = self.repository.por_endpoint(huella)
            repetida = bool(
                anterior and anterior.usuario_id == actor.id and anterior.familia_id == familia
            )
            if repetida:
                s = anterior
                s.p256dh, s.auth = datos.keys.p256dh, datos.keys.auth
            else:
                if anterior:
                    anterior.revocada_en = ahora_utc()
                    self.session.flush()
                s = SuscripcionPush(
                    usuario_id=actor.id,
                    familia_id=familia,
                    endpoint=datos.endpoint,
                    huella_endpoint=huella,
                    p256dh=datos.keys.p256dh,
                    auth=datos.keys.auth,
                    agente=(agente or "")[:120] or None,
                )
                self.repository.agregar(s)
            AuditoriaService(self.session).registrar(
                usuario_id=actor.id,
                accion="notificacion.suscribir",
                entidad="suscripcion_push",
                entidad_id=s.id,
                despues={"familia_id": str(familia)},
            )
            self.session.commit()
            return s, repetida
        except Exception:
            self.session.rollback()
            raise

    def revocar(self, id, actor, familia):
        s = self.repository.get(id, bloquear=True)
        if s is None or s.usuario_id != actor.id or s.familia_id != familia:
            raise NoEncontrado("No se encontró la suscripción de este dispositivo.")
        s.revocada_en = ahora_utc()
        self.session.commit()

    def destinatarias(self, almacen_id, solicitante_id=None):
        if not self.configurada():
            return []
        validas = []
        for s in self.repository.activas():
            u = self.repository.sesion_valida(s)
            if u is None:
                s.revocada_en = ahora_utc()
                continue
            if u.id == solicitante_id or self.acceso.tiene_permiso(u, P.ALMACENES_TODOS):
                continue
            if self.acceso.tiene_permiso(u, P.AUTORIZACIONES_RESOLVER) and almacen_id in (
                self.acceso.almacenes_del_usuario(u.id)
            ):
                validas.append(s)
        return validas

    def contar_destinatarios(self, almacen_id, solicitante_id):
        return len({s.usuario_id for s in self.destinatarias(almacen_id, solicitante_id)})

    def _enviar(self, id, payload, ttl=900, permiso=P.AUTORIZACIONES_RESOLVER):
        s = self.repository.get(id, bloquear=True)
        if not s or s.revocada_en:
            self.session.rollback()
            return False
        u = self.repository.sesion_valida(s)
        if u is None:
            s.revocada_en = ahora_utc()
            self.session.commit()
            return False
        if not self.acceso.tiene_permiso(u, permiso):
            # NT-02: perder el permiso suspende avisos, conserva el dispositivo.
            self.session.rollback()
            return False
        almacen_id = payload.get("almacen_id")
        if almacen_id and uuid.UUID(almacen_id) not in self.acceso.almacenes_del_usuario(u.id):
            self.session.rollback()
            return False
        now = ahora_utc()
        payload = dict(payload)
        payload["silencioso"] = payload.get("silencioso", False) or bool(
            s.ultimo_envio
            and s.ultima_etiqueta == payload.get("etiqueta")
            and now - s.ultimo_envio < timedelta(minutes=1)
        )
        s.ultimo_envio = now
        s.ultima_etiqueta = payload.get("etiqueta")
        self.session.commit()  # liberar bloqueos antes de la red
        try:
            response = self.transporte.enviar(s, payload, ttl)
            codigo = getattr(response, "status_code", 201)
            exito = 200 <= codigo < 300
        except WebPushException as exc:
            codigo = getattr(exc.response, "status_code", 0)
            exito = False
        except Exception:
            codigo, exito = 0, False
        s = self.repository.get(id, bloquear=True)
        s.ultimo_error = None if exito else f"El servicio de notificaciones falló ({codigo})."
        if codigo in (404, 410):
            s.revocada_en = ahora_utc()
        self.session.commit()
        return exito

    def prueba(self, actor, familia):
        self.acceso.exigir_permiso(actor, P.AUTORIZACIONES_RESOLVER)
        suscripciones = self.repository.activas(actor.id, familia)
        now = ahora_utc()
        for s in suscripciones:
            actual = self.repository.get(s.id, bloquear=True)
            if actual.ultima_prueba and now - actual.ultima_prueba < timedelta(seconds=10):
                self.session.rollback()
                raise DemasiadosIntentos(10, "Espera diez segundos antes de probar de nuevo.")
        for s in suscripciones:
            s.ultima_prueba = now
        self.session.commit()
        enviadas = (
            sum(
                self._enviar(
                    s.id,
                    {
                        "titulo": "Notificaciones listas",
                        "cuerpo": "Recibirás las solicitudes de tu almacén.",
                        "url": "/autorizaciones",
                        "etiqueta": "imhotep-prueba",
                        "silencioso": False,
                    },
                    60,
                )
                for s in suscripciones
            )
            if self.configurada()
            else 0
        )
        return PruebaOut(enviadas=enviadas, fallidas=len(suscripciones) - enviadas)

    def avisar(self, id: uuid.UUID, evento="SOLICITADA", excluir_familia=None):
        a = self.repository.autorizacion(id)
        if a is None or a.vence_en <= ahora_utc() or a.estado == "VENCIDA":
            return
        almacen = self.repository.almacen(a.almacen_id)
        pendientes = self.repository.pendientes(a.almacen_id)
        suscripciones = self.destinatarias(a.almacen_id, a.solicitada_por)
        self.session.commit()
        titulo = f"{almacen.nombre} · " + (
            "EPP por aprobar"
            if a.tipo == "DESPACHO"
            else "Traslado por autorizar"
            if a.tipo == "TRASLADO"
            else "Excedente por autorizar"
        )
        trabajador = self.repository.trabajador(a.trabajador_id)
        solicitante = self.repository.usuario(a.solicitada_por)
        renglones = (a.detalle or {}).get("renglones", [])
        cantidad = sum(r.get("clase") != "CONTEXTO" for r in renglones)
        cuerpo = (
            f"Para {trabajador.nombre if trabajador else 'el almacén de destino'}: "
            f"{cantidad} artículos. Lo pide {solicitante.nombre}."
        )
        if evento != "SOLICITADA":
            resolutor = self.repository.usuario(a.resuelta_por) if a.resuelta_por else None
            accion = {"APROBADA": "aprobó", "RECHAZADA": "rechazó", "USADA": "atendió"}.get(
                a.estado, "atendió"
            )
            nombre = resolutor.nombre if resolutor else "El supervisor"
            titulo = f"{almacen.nombre} · {nombre} ya la {accion}"
        if pendientes > 1:
            titulo = f"{almacen.nombre} · {pendientes} solicitudes por aprobar"
        payload = {
            "evento": evento,
            "autorizacion_id": str(a.id),
            "tipo": a.tipo,
            "almacen": {"clave": almacen.clave, "nombre": almacen.nombre},
            "almacen_id": str(almacen.id),
            "pendientes": pendientes,
            "titulo": titulo,
            "cuerpo": cuerpo,
            "url": f"/autorizaciones/{a.id}" if pendientes <= 1 else "/autorizaciones",
            "etiqueta": f"imhotep-autorizaciones-{a.almacen_id}",
            "silencioso": evento != "SOLICITADA",
        }
        ttl = max(1, int((a.vence_en - ahora_utc()).total_seconds()))
        for s in suscripciones:
            if s.familia_id != excluir_familia:
                self._enviar(s.id, payload, ttl)

    def avisar_traslado(self, id):
        from app.modulos.movimientos.repository import MovimientoRepository

        vale = self.repository.vale(id)
        if vale is None or vale.tipo != "TRASPASO" or vale.destino_almacen_id is None:
            return
        reglas = {
            regla
            for m, _, _ in MovimientoRepository(self.session).renglones_de(id)
            for regla in m.reglas or []
        }
        if not reglas.intersection({"X-16", "X-17"}) or not self.configurada():
            return
        almacen = self.repository.almacen(vale.destino_almacen_id)
        recipients = []
        for s in self.repository.activas():
            actor = self.repository.sesion_valida(s)
            if (
                actor
                and self.acceso.tiene_permiso(actor, P.TRASPASOS_RECIBIR)
                and (almacen.id in self.acceso.almacenes_del_usuario(actor.id))
            ):
                recipients.append(s.id)
        self.session.commit()
        payload = {
            "evento": "TRASLADO_ENVIADO",
            "titulo": "Traslado por recibir",
            "cuerpo": f"{almacen.clave}: llegó el aviso del traslado {vale.folio}.",
            "almacen_id": str(almacen.id),
            "url": "/recibir",
            "silencioso": False,
            "etiqueta": f"imhotep-traslados-{almacen.id}",
            "vale_id": str(vale.id),
        }
        for destinataria in recipients:
            self._enviar(destinataria, payload, 900, P.TRASPASOS_RECIBIR)


def enviar_aviso_autorizacion(id, evento="SOLICITADA", excluir_familia=None):
    """Trabajo de BackgroundTasks: ningún fallo de push invalida el movimiento (NT-07)."""
    with get_sessionmaker()() as session:
        try:
            NotificacionService(session).avisar(id, evento, excluir_familia)
        except Exception:
            session.rollback()


def enviar_aviso_traslado(id):
    with get_sessionmaker()() as session:
        try:
            NotificacionService(session).avisar_traslado(id)
        except Exception:
            session.rollback()
