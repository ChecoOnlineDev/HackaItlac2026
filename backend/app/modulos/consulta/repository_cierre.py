"""Lecturas agrupadas para cierre; no escribe inventario ni consulta por cada renglón."""

from sqlalchemy import or_, select

from app.modulos.almacenes.models import Almacen, Ubicacion
from app.modulos.catalogo.models import Articulo
from app.modulos.movimientos.models import Movimiento, Vale
from app.modulos.trabajadores.models import Trabajador


class CierreRepository:
    def __init__(self, session):
        self.session = session

    def almacen(self, id):
        return self.session.get(Almacen, id)

    def ubicacion(self, almacen_id):
        return self.session.scalar(select(Ubicacion).where(Ubicacion.almacen_id == almacen_id))

    def historial(self, ubicacion_id, hasta_exclusivo):
        candidatos = (
            select(Movimiento.articulo_id)
            .where(
                or_(Movimiento.origen_id == ubicacion_id, Movimiento.destino_id == ubicacion_id),
                Movimiento.creado_en < hasta_exclusivo,
            )
            .distinct()
        )
        articulos = list(
            self.session.scalars(
                select(Articulo).where(Articulo.id.in_(candidatos)).order_by(Articulo.codigo)
            )
        )
        if not articulos:
            return [], [], {}, {}
        filas = list(
            self.session.execute(
                select(Movimiento, Vale.tipo, Vale.vale_origen_id)
                .join(Vale, Vale.id == Movimiento.vale_id)
                .where(
                    Movimiento.articulo_id.in_([a.id for a in articulos]),
                    Movimiento.creado_en < hasta_exclusivo,
                )
                .order_by(Movimiento.creado_en, Movimiento.id)
            )
        )
        ids = {i for m, _, _ in filas for i in (m.origen_id, m.destino_id)}
        ubicaciones = {
            u.id: u for u in self.session.scalars(select(Ubicacion).where(Ubicacion.id.in_(ids)))
        }
        trabajadores_ids = {u.trabajador_id for u in ubicaciones.values() if u.trabajador_id}
        trabajadores = {
            t.id: t
            for t in self.session.scalars(
                select(Trabajador).where(Trabajador.id.in_(trabajadores_ids))
            )
        }
        return articulos, filas, ubicaciones, trabajadores
