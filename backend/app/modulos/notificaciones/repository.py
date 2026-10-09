import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.tiempo import ahora_utc
from app.modulos.acceso.models import Rol, SesionDispositivo, Usuario
from app.modulos.notificaciones.models import SuscripcionPush


class NotificacionRepository:
    def __init__(self, session: Session):
        self.session = session

    def activas(self, usuario_id=None, familia_id=None):
        q = select(SuscripcionPush).where(SuscripcionPush.revocada_en.is_(None))
        if usuario_id:
            q = q.where(SuscripcionPush.usuario_id == usuario_id)
        if familia_id:
            q = q.where(SuscripcionPush.familia_id == familia_id)
        return list(self.session.scalars(q))

    def agregar(self, suscripcion):
        self.session.add(suscripcion)
        self.session.flush()

    def autorizacion(self, id):
        from app.modulos.autorizaciones.models import Autorizacion

        return self.session.get(Autorizacion, id)

    def pendientes(self, almacen_id):
        from app.modulos.autorizaciones.models import Autorizacion

        return self.session.scalar(
            select(func.count())
            .select_from(Autorizacion)
            .where(
                Autorizacion.almacen_id == almacen_id,
                Autorizacion.estado == "PENDIENTE",
                Autorizacion.vence_en > ahora_utc(),
            )
        )

    def almacen(self, id):
        from app.modulos.almacenes.models import Almacen

        return self.session.get(Almacen, id)

    def usuario(self, id):
        return self.session.get(Usuario, id)

    def trabajador(self, id):
        from app.modulos.trabajadores.models import Trabajador

        return self.session.get(Trabajador, id) if id else None

    def vale(self, id):
        from app.modulos.movimientos.models import Vale

        return self.session.get(Vale, id)

    def get(self, id: uuid.UUID, *, bloquear=False):
        q = select(SuscripcionPush).where(SuscripcionPush.id == id)
        if bloquear:
            q = q.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(q)

    def por_endpoint(self, huella):
        return self.session.scalar(
            select(SuscripcionPush)
            .where(SuscripcionPush.endpoint_activo == huella)
            .with_for_update()
        )

    def sesion_valida(self, s: SuscripcionPush):
        now = ahora_utc()
        return self.session.scalar(
            select(Usuario)
            .join(Rol, Rol.id == Usuario.rol_id)
            .join(SesionDispositivo, SesionDispositivo.usuario_id == Usuario.id)
            .where(
                Usuario.id == s.usuario_id,
                Usuario.activo.is_(True),
                Rol.activo.is_(True),
                SesionDispositivo.familia_id == s.familia_id,
                SesionDispositivo.revocada_en.is_(None),
                SesionDispositivo.expira_en > now,
                SesionDispositivo.vence_absoluto > now,
                SesionDispositivo.version_sesion == Usuario.version_sesion,
            )
            .limit(1)
        )
