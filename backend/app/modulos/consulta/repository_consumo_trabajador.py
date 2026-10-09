"""DU-08: consumo neto por artículo/proyecto, fechado con su entrega original."""

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import aliased

from app.modulos.almacenes.models import Ubicacion
from app.modulos.catalogo.models import Articulo
from app.modulos.movimientos.models import Movimiento, TipoVale, Vale
from app.modulos.proyectos.models import Proyecto


class ConsumoTrabajadorRepository:
    def __init__(self, session):
        self.session = session

    def consultar(self, trabajador_id, desde, hasta):
        origen = aliased(Ubicacion)
        destino = aliased(Ubicacion)
        original = aliased(Vale)
        cancelacion = and_(Vale.tipo == TipoVale.CANCELACION, original.id.is_not(None))
        signo = case(
            (destino.virtual == "CONSUMIDO", Movimiento.cantidad), else_=-Movimiento.cantidad
        )
        fecha = case((cancelacion, original.creado_en), else_=Movimiento.creado_en)
        persona = func.coalesce(
            Movimiento.trabajador_id, Vale.trabajador_id, original.trabajador_id
        )
        proyecto_id = case((cancelacion, original.proyecto_id), else_=Vale.proyecto_id)
        neto = func.sum(signo)
        consulta = (
            select(
                Articulo.id.label("articulo_id"),
                Articulo.codigo,
                Articulo.nombre,
                Articulo.unidad,
                Articulo.costo_unitario,
                proyecto_id.label("proyecto_id"),
                Proyecto.nombre.label("proyecto_nombre"),
                neto.label("cantidad"),
            )
            .select_from(Movimiento)
            .join(Vale, Vale.id == Movimiento.vale_id)
            .outerjoin(original, original.id == Vale.vale_origen_id)
            .join(Articulo, Articulo.id == Movimiento.articulo_id)
            .join(origen, origen.id == Movimiento.origen_id)
            .join(destino, destino.id == Movimiento.destino_id)
            .outerjoin(Proyecto, Proyecto.id == proyecto_id)
            .where(
                persona == trabajador_id,
                Articulo.retornable.is_(False),
                or_(destino.virtual == "CONSUMIDO", origen.virtual == "CONSUMIDO"),
                fecha >= desde,
                fecha < hasta,
            )
            .group_by(
                Articulo.id,
                Articulo.codigo,
                Articulo.nombre,
                Articulo.unidad,
                Articulo.costo_unitario,
                proyecto_id,
                Proyecto.nombre,
            )
            .having(neto != 0)
            .order_by(Articulo.nombre, Proyecto.nombre)
        )
        return self.session.execute(consulta).all()
