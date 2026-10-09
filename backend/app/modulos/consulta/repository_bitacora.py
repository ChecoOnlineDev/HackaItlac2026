"""BT-01/02/03: paginar operaciones en SQL; agregar sólo vales de esa página."""

from sqlalchemy import and_, case, func, or_, select

from app.modulos.catalogo.models import Articulo, Categoria, Pieza
from app.modulos.movimientos.models import Movimiento, Vale


def coincidencia(f):
    condiciones = []
    if f.articulo_id:
        condiciones.append(Movimiento.articulo_id == f.articulo_id)
    if len(f.q.strip()) >= 2:
        # LIKE literal: '%' y '_' escritos por la persona no son comodines.
        for palabra in f.q.strip().split()[:6]:
            condiciones.append(
                or_(
                    *(
                        c.contains(palabra, autoescape=True)
                        for c in (
                            Articulo.codigo,
                            Articulo.nombre,
                            Pieza.codigo,
                            Pieza.numero_serie,
                        )
                    )
                )
            )
    return and_(*condiciones) if condiciones else None


class BitacoraRepository:
    def __init__(self, session):
        self.session = session

    def alcance(self, ids):
        return (
            True if ids is None else or_(Vale.almacen_id.in_(ids), Vale.destino_almacen_id.in_(ids))
        )

    def base(self, f, ids, actor_id, inicio, fin):
        q = select(Vale).where(self.alcance(ids))
        if f.almacen_id:
            q = q.where(
                or_(Vale.almacen_id == f.almacen_id, Vale.destino_almacen_id == f.almacen_id)
            )
        for campo in ("tipo", "usuario_id", "proyecto_id", "lote_id"):
            valor = getattr(f, campo)
            if valor is not None:
                q = q.where(
                    getattr(Vale, "responsable_id" if campo == "usuario_id" else campo) == valor
                )
        if inicio:
            q = q.where(Vale.creado_en >= inicio)
        if fin:
            q = q.where(Vale.creado_en < fin)
        if f.solo_mios:
            q = q.where(Vale.responsable_id == actor_id)
        if f.trabajador_id:
            q = q.where(
                or_(
                    Vale.trabajador_id == f.trabajador_id,
                    select(Movimiento.id)
                    .where(
                        Movimiento.vale_id == Vale.id, Movimiento.trabajador_id == f.trabajador_id
                    )
                    .exists(),
                )
            )
        match = coincidencia(f)
        if match is not None:
            q = q.where(
                select(Movimiento.id)
                .select_from(Movimiento)
                .join(Articulo, Articulo.id == Movimiento.articulo_id)
                .outerjoin(Pieza, Pieza.id == Movimiento.pieza_id)
                .where(Movimiento.vale_id == Vale.id, match)
                .exists()
            )
        return q

    def pagina(self, f, ids, actor_id, inicio, fin, pagina, tamano):
        base = self.base(f, ids, actor_id, inicio, fin).subquery()
        grupo = func.coalesce(base.c.lote_id, base.c.id)
        operaciones = (
            select(grupo.label("grupo"), func.max(base.c.creado_en).label("fecha"))
            .group_by(grupo)
            .subquery()
        )
        total = self.session.scalar(select(func.count()).select_from(operaciones))
        grupos = list(
            self.session.scalars(
                select(operaciones.c.grupo)
                .order_by(operaciones.c.fecha.desc(), operaciones.c.grupo.desc())
                .offset((pagina - 1) * tamano)
                .limit(tamano)
            )
        )
        if not grupos:
            return [], total
        # Un filtro por pieza encuentra el lote entero, pero jamás partes fuera del alcance.
        vales = list(
            self.session.scalars(
                select(Vale)
                .where(self.alcance(ids), func.coalesce(Vale.lote_id, Vale.id).in_(grupos))
                .order_by(Vale.creado_en.desc(), Vale.folio)
            )
        )
        return vales, total

    def totales(self, vale_ids, f):
        match = coincidencia(f)
        q = (
            select(
                Movimiento.vale_id,
                func.count().label("renglones"),
                func.sum(Movimiento.cantidad).label("unidades"),
                func.sum(case((match, 1), else_=0)).label("coincidencias")
                if match is not None
                else func.count().label("coincidencias"),
            )
            .select_from(Movimiento)
            .join(Articulo, Articulo.id == Movimiento.articulo_id)
            .outerjoin(Pieza, Pieza.id == Movimiento.pieza_id)
            .where(Movimiento.vale_id.in_(vale_ids))
            .group_by(Movimiento.vale_id)
        )
        return {r.vale_id: r for r in self.session.execute(q)}

    def renglones(self, vale_id, q, pagina, tamano):
        from app.modulos.consulta.schemas_bitacora import BitacoraFilters

        consulta = (
            select(Movimiento, Articulo, Pieza)
            .select_from(Movimiento)
            .join(Articulo, Articulo.id == Movimiento.articulo_id)
            .outerjoin(Pieza, Pieza.id == Movimiento.pieza_id)
            .where(Movimiento.vale_id == vale_id)
        )
        match = coincidencia(BitacoraFilters(q=q))
        if match is not None:
            consulta = consulta.where(match)
        total = self.session.scalar(select(func.count()).select_from(consulta.subquery()))
        return self.session.execute(
            consulta.order_by(Movimiento.renglon).offset((pagina - 1) * tamano).limit(tamano)
        ).all(), total

    def resumen(self, vale_id):
        return self.session.execute(
            select(
                Categoria.id,
                Categoria.nombre,
                func.count().label("renglones"),
                func.sum(Movimiento.cantidad).label("unidades"),
                func.count(func.distinct(Articulo.id)).label("articulos"),
                func.sum(func.coalesce(Articulo.costo_unitario, 0) * Movimiento.cantidad).label(
                    "valor"
                ),
            )
            .select_from(Movimiento)
            .join(Articulo, Articulo.id == Movimiento.articulo_id)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .where(Movimiento.vale_id == vale_id)
            .group_by(Categoria.id, Categoria.nombre)
            .order_by(func.count().desc())
        ).all()

    def lote(self, lote_id, ids):
        return list(
            self.session.scalars(
                select(Vale).where(Vale.lote_id == lote_id, self.alcance(ids)).order_by(Vale.folio)
            )
        )

    def relacionados(self, vale):
        reglas = [Vale.vale_origen_id == vale.id]
        if vale.vale_origen_id:
            reglas.append(Vale.id == vale.vale_origen_id)
        if vale.lote_id:
            reglas.append(and_(Vale.lote_id == vale.lote_id, Vale.id != vale.id))
        return list(self.session.scalars(select(Vale).where(or_(*reglas)).order_by(Vale.creado_en)))

    def archivo_repetido(self, lote_id):
        from app.modulos.auditoria.models import Auditoria

        registro = self.session.scalar(
            select(Auditoria)
            .where(
                Auditoria.entidad_id == str(lote_id),
                Auditoria.accion.in_(("importacion.confirmar", "importacion.traspaso")),
            )
            .order_by(Auditoria.creado_en.desc())
            .limit(1)
        )
        return bool(
            registro and isinstance(registro.despues, dict) and registro.despues.get("repetido")
        )
