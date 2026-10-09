"""Persistencia y bloqueos; no controla commits."""

import uuid
from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modulos.almacenes.models import Almacen
from app.modulos.proyectos.models import AsignacionProyecto, Proyecto
from app.modulos.trabajadores.models import Trabajador


class ProyectoRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, id: uuid.UUID, *, bloquear=False):
        query = select(Proyecto).where(Proyecto.id == id)
        if bloquear:
            query = query.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(query)

    def almacen_ref(self, id: uuid.UUID):
        return self.session.get(Almacen, id)

    def asignacion(self, id: uuid.UUID):
        return self.session.get(AsignacionProyecto, id)

    def almacen(self, id: uuid.UUID):
        return self.session.scalar(
            select(Almacen)
            .where(Almacen.id == id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def trabajador(self, id: uuid.UUID, *, bloquear=False):
        q = select(Trabajador).where(Trabajador.id == id)
        if bloquear:
            q = q.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(q)

    def listar(
        self,
        pagina,
        hoy,
        *,
        alcance=None,
        almacen_id=None,
        situacion=None,
        q=None,
        asignables=False,
        por_vencer=False,
    ):
        consulta = select(Proyecto)
        if alcance is not None:
            consulta = consulta.where(Proyecto.almacen_id.in_(alcance))
        if almacen_id is not None:
            consulta = consulta.where(Proyecto.almacen_id == almacen_id)
        if situacion == "CERRADO":
            consulta = consulta.where(Proyecto.estado == "CERRADO")
        elif situacion:
            consulta = consulta.where(Proyecto.estado == "ACTIVO")
            if situacion == "POR_INICIAR":
                consulta = consulta.where(Proyecto.inicio > hoy)
            elif situacion == "FIN_VENCIDO":
                consulta = consulta.where(Proyecto.fin_estimado < hoy)
            else:
                consulta = consulta.where(Proyecto.inicio <= hoy, Proyecto.fin_estimado >= hoy)
        if asignables:
            consulta = consulta.where(Proyecto.estado == "ACTIVO", Proyecto.fin_estimado >= hoy)
        if por_vencer:
            consulta = consulta.where(
                Proyecto.estado == "ACTIVO", Proyecto.fin_estimado <= hoy + timedelta(days=7)
            )
        if q:
            consulta = consulta.where(
                or_(
                    Proyecto.clave.contains(q, autoescape=True),
                    Proyecto.nombre.contains(q, autoescape=True),
                )
            )
        total = self.session.scalar(select(func.count()).select_from(consulta.subquery())) or 0
        proyectos = self.session.scalars(
            consulta.order_by(Proyecto.nombre, Proyecto.id)
            .offset(pagina.offset)
            .limit(pagina.limit)
        ).all()
        return proyectos, total

    def clave_existe(self, clave: str, excluir=None):
        q = select(Proyecto.id).where(Proyecto.clave == clave)
        if excluir:
            q = q.where(Proyecto.id != excluir)
        return self.session.scalar(q) is not None

    def tiene_vales(self, proyecto_id: uuid.UUID):
        # Lectura del modelo de movimientos; su dueño sigue siendo movimientos.
        from app.modulos.movimientos.models import Vale

        return (
            self.session.scalar(select(Vale.id).where(Vale.proyecto_id == proyecto_id).limit(1))
            is not None
        )

    def asignaciones(self, trabajador_id: uuid.UUID, *, bloquear=False):
        consulta = (
            select(AsignacionProyecto)
            .where(AsignacionProyecto.trabajador_id == trabajador_id)
            .order_by(AsignacionProyecto.creado_en.desc(), AsignacionProyecto.id.desc())
        )
        if bloquear:
            consulta = consulta.with_for_update().execution_options(populate_existing=True)
        return self.session.scalars(consulta).all()

    def refrescar_asignacion(self, asignacion):
        self.session.refresh(asignacion)

    def activas(self, proyecto_id: uuid.UUID):
        return self.session.scalars(
            select(AsignacionProyecto)
            .where(
                AsignacionProyecto.proyecto_id == proyecto_id,
                AsignacionProyecto.terminada_en.is_(None),
            )
            .order_by(AsignacionProyecto.trabajador_id)
        ).all()

    def conteo(self, proyecto_id: uuid.UUID):
        return (
            self.session.scalar(
                select(func.count())
                .select_from(AsignacionProyecto)
                .join(Trabajador, Trabajador.id == AsignacionProyecto.trabajador_id)
                .where(
                    AsignacionProyecto.proyecto_id == proyecto_id,
                    AsignacionProyecto.terminada_en.is_(None),
                    Trabajador.estado == "ACTIVO",
                )
            )
            or 0
        )

    def add(self, obj):
        self.session.add(obj)
        self.session.flush()
        return obj
