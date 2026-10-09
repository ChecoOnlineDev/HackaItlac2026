"""TB-05/06/08: consultas agregadas; nunca escribe inventario ni proyectos."""

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import aliased

from app.modulos.acceso.alcance_almacenes import condicion_almacenes
from app.modulos.almacenes.models import Almacen, Ubicacion, UbicacionVirtual
from app.modulos.catalogo.models import Articulo, Categoria
from app.modulos.movimientos.models import Movimiento, TipoVale, Vale
from app.modulos.proyectos.models import Proyecto


class TableroProyectosRepository:
    def __init__(self, session):
        self.session = session

    def proyectos(self, alcance, proyecto_id=None):
        consulta = select(Proyecto).order_by(Proyecto.nombre, Proyecto.id)
        if alcance is not None:
            consulta = consulta.where(condicion_almacenes(Proyecto.almacen_id, alcance))
        if proyecto_id is not None:
            consulta = consulta.where(Proyecto.id == proyecto_id)
        return list(self.session.scalars(consulta))

    def consumibles(self, desde, hasta, alcance):
        origen, destino = aliased(Ubicacion), aliased(Ubicacion)
        original = aliased(Vale)
        proyecto = func.coalesce(Vale.proyecto_id, original.proyecto_id)
        almacen = func.coalesce(original.almacen_id, Vale.almacen_id)
        fecha = case(
            (and_(Vale.tipo == TipoVale.CANCELACION, original.id.is_not(None)), original.creado_en),
            else_=Movimiento.creado_en,
        )
        cantidad = func.sum(
            case(
                (destino.virtual == UbicacionVirtual.CONSUMIDO, Movimiento.cantidad),
                else_=-Movimiento.cantidad,
            )
        )
        columnas = (
            proyecto.label("proyecto_id"),
            almacen.label("almacen_id"),
            Articulo.id.label("articulo_id"),
            Categoria.id.label("categoria_id"),
            Categoria.nombre.label("categoria"),
            Articulo.costo_unitario.label("costo"),
        )
        consulta = (
            select(*columnas, cantidad.label("cantidad"))
            .select_from(Movimiento)
            .join(Vale, Vale.id == Movimiento.vale_id)
            .outerjoin(original, original.id == Vale.vale_origen_id)
            .outerjoin(Proyecto, Proyecto.id == proyecto)
            .join(Articulo, Articulo.id == Movimiento.articulo_id)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .join(origen, origen.id == Movimiento.origen_id)
            .join(destino, destino.id == Movimiento.destino_id)
            .where(
                Articulo.retornable.is_(False),
                fecha >= desde,
                fecha < hasta,
                or_(
                    destino.virtual == UbicacionVirtual.CONSUMIDO,
                    origen.virtual == UbicacionVirtual.CONSUMIDO,
                ),
            )
        )
        if alcance is not None:
            consulta = consulta.where(
                or_(
                    and_(proyecto.is_not(None), condicion_almacenes(Proyecto.almacen_id, alcance)),
                    and_(proyecto.is_(None), condicion_almacenes(almacen, alcance)),
                )
            )
        return list(self.session.execute(consulta.group_by(*columnas).having(cantidad != 0)))

    def almacenes(self, alcance):
        consulta = select(Almacen).order_by(Almacen.nombre, Almacen.id)
        if alcance is not None:
            consulta = consulta.where(condicion_almacenes(Almacen.id, alcance))
        return list(self.session.scalars(consulta))

    def categorias(self):
        return {c.id: c.nombre for c in self.session.scalars(select(Categoria))}

    def almacenes_sin_proyecto(self, alcance):
        activos = (
            select(Proyecto.id)
            .where(Proyecto.almacen_id == Almacen.id, Proyecto.estado == "ACTIVO")
            .exists()
        )
        consulta = (
            select(Almacen)
            .where(Almacen.tipo == "PROYECTO", Almacen.estado == "ACTIVO", ~activos)
            .order_by(Almacen.nombre, Almacen.id)
        )
        if alcance is not None:
            consulta = consulta.where(condicion_almacenes(Almacen.id, alcance))
        return list(self.session.scalars(consulta))

    def proyectos_por_vencer(self, alcance, hasta):
        consulta = (
            select(Proyecto)
            .where(Proyecto.estado == "ACTIVO", Proyecto.fin_estimado <= hasta)
            .order_by(Proyecto.fin_estimado, Proyecto.nombre, Proyecto.id)
        )
        if alcance is not None:
            consulta = consulta.where(condicion_almacenes(Proyecto.almacen_id, alcance))
        return list(self.session.scalars(consulta))
