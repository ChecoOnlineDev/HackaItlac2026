"""DU-01/06: unión de resguardo y agrupación/paginación por trabajador en SQL."""

from sqlalchemy import (
    String,
    Uuid,
    and_,
    case,
    cast,
    exists,
    func,
    literal,
    null,
    or_,
    select,
    union_all,
)
from sqlalchemy.orm import aliased

from app.core.tiempo import ahora_utc, hoy_mx
from app.modulos.almacenes.models import Almacen, TipoUbicacion, Ubicacion
from app.modulos.catalogo.alto_valor import expresion_alto_valor
from app.modulos.catalogo.models import (
    Articulo,
    Categoria,
    Codigo,
    Control,
    EstadoPieza,
    Pieza,
    TipoCodigo,
)
from app.modulos.movimientos.models import EstadoVale, Existencia, Movimiento, TipoVale, Vale
from app.modulos.proyectos.models import Proyecto
from app.modulos.trabajadores.models import PeriodoContrato, Trabajador


class DeudoresRepository:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def deudas():
        # Sólo una ENTREGA vigente atribuye almacén/proyecto/antigüedad: no cancelaciones.
        mov = aliased(Movimiento)
        vale = aliased(Vale)
        destino = aliased(Ubicacion)
        ultimo = (
            select(
                mov.pieza_id,
                mov.articulo_id,
                mov.destino_id,
                mov.creado_en.label("desde"),
                vale.id.label("vale_id"),
                vale.folio,
                vale.almacen_id,
                vale.proyecto_id,
                func.row_number()
                .over(
                    partition_by=(mov.pieza_id, mov.destino_id, mov.articulo_id),
                    order_by=(mov.creado_en.desc(), mov.id.desc()),
                )
                .label("rn"),
            )
            .select_from(mov)
            .join(vale, vale.id == mov.vale_id)
            .join(destino, destino.id == mov.destino_id)
            .where(
                vale.tipo == TipoVale.ENTREGA,
                vale.estado != EstadoVale.CANCELADO,
                destino.tipo == TipoUbicacion.TRABAJADOR,
            )
            .subquery("ultima_entrega_du")
        )

        def columnas(pieza_id, codigo, serie, cantidad):
            return (
                Ubicacion.trabajador_id.label("trabajador_id"),
                Articulo.id.label("articulo_id"),
                pieza_id.label("pieza_id"),
                codigo.label("pieza_codigo"),
                serie.label("numero_serie"),
                cantidad.label("cantidad"),
                ultimo.c.desde,
                ultimo.c.vale_id,
                ultimo.c.folio,
                ultimo.c.almacen_id,
                ultimo.c.proyecto_id,
            )

        piezas = (
            select(*columnas(Pieza.id, Pieza.codigo, Pieza.numero_serie, literal(1)))
            .select_from(Pieza)
            .join(Ubicacion, Ubicacion.id == Pieza.ubicacion_id)
            .join(Articulo, Articulo.id == Pieza.articulo_id)
            .join(
                ultimo,
                and_(
                    ultimo.c.pieza_id == Pieza.id,
                    ultimo.c.destino_id == Pieza.ubicacion_id,
                    ultimo.c.rn == 1,
                ),
            )
            .where(
                Ubicacion.tipo == TipoUbicacion.TRABAJADOR,
                Articulo.retornable.is_(True),
                Pieza.estado != EstadoPieza.BAJA,
            )
        )
        cantidades = (
            select(
                *columnas(
                    literal(None, type_=Uuid()),
                    cast(null(), String(64)),
                    cast(null(), String(100)),
                    Existencia.cantidad,
                )
            )
            .select_from(Existencia)
            .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
            .join(Articulo, Articulo.id == Existencia.articulo_id)
            .join(
                ultimo,
                and_(
                    ultimo.c.pieza_id.is_(None),
                    ultimo.c.destino_id == Existencia.ubicacion_id,
                    ultimo.c.articulo_id == Existencia.articulo_id,
                    ultimo.c.rn == 1,
                ),
            )
            .where(
                Ubicacion.tipo == TipoUbicacion.TRABAJADOR,
                Articulo.control == Control.CANTIDAD,
                Articulo.retornable.is_(True),
                Existencia.cantidad > 0,
            )
        )
        return union_all(piezas, cantidades).subquery("deuda")

    @staticmethod
    def vigente():
        return and_(
            Trabajador.estado == "ACTIVO",
            exists(
                select(1).where(
                    PeriodoContrato.trabajador_id == Trabajador.id,
                    PeriodoContrato.inicio <= hoy_mx(),
                    PeriodoContrato.fin >= hoy_mx(),
                )
            ).correlate(Trabajador),
        )

    def base(self, alcance, filtros, omitir_tarjetas=False):
        d = self.deudas()
        alto = func.coalesce(expresion_alto_valor(), False)
        vigente = self.vigente()
        base = (
            select(
                d,
                Trabajador.nombre.label("trabajador_nombre"),
                Trabajador.numero_empleado,
                Trabajador.foto_adjunto_id,
                Articulo.codigo.label("articulo_codigo"),
                Articulo.nombre.label("articulo_nombre"),
                Articulo.marca,
                Articulo.requiere_inspeccion,
                Categoria.id.label("categoria_id"),
                Almacen.clave.label("almacen_clave"),
                Almacen.nombre.label("almacen_nombre"),
                Almacen.estado.label("almacen_estado"),
                Proyecto.nombre.label("proyecto_nombre"),
                Proyecto.estado.label("proyecto_estado"),
                alto.label("alto_valor"),
                vigente.label("vigente"),
            )
            .select_from(d)
            .join(Trabajador, Trabajador.id == d.c.trabajador_id)
            .join(Articulo, Articulo.id == d.c.articulo_id)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .join(Almacen, Almacen.id == d.c.almacen_id)
            .outerjoin(Proyecto, Proyecto.id == d.c.proyecto_id)
        )
        if alcance is not None:
            base = base.where(d.c.almacen_id.in_(alcance))
        for campo in ("almacen_id", "proyecto_id", "trabajador_id"):
            if filtros.get(campo):
                base = base.where(getattr(d.c, campo) == filtros[campo])
        if filtros.get("sin_proyecto"):
            base = base.where(d.c.proyecto_id.is_(None))
        if filtros.get("categoria_id"):
            base = base.where(Articulo.categoria_id == filtros["categoria_id"])
        if filtros.get("alto_valor"):
            base = base.where(alto.is_(True))
        for palabra in (filtros.get("q") or "").split()[:6]:
            patron = "%" + palabra.replace("%", r"\%").replace("_", r"\_") + "%"
            credencial = exists(
                select(1).where(
                    Codigo.tipo == TipoCodigo.TRABAJADOR,
                    Codigo.ref_id == Trabajador.id,
                    Codigo.codigo.like(patron),
                )
            ).correlate(Trabajador)
            base = base.where(
                or_(
                    Trabajador.nombre.like(patron),
                    Trabajador.numero_empleado.like(patron),
                    Articulo.codigo.like(patron),
                    Articulo.nombre.like(patron),
                    d.c.pieza_codigo.like(patron),
                    d.c.numero_serie.like(patron),
                    credencial,
                )
            )
        if not omitir_tarjetas:
            if filtros.get("vigencia") == "VIGENTES":
                base = base.where(vigente)
            if filtros.get("vigencia") == "NO_VIGENTES":
                base = base.where(~vigente)
            if filtros.get("antiguedad_dias") is not None:
                # Se aplica después de agrupar, para conservar toda la deuda del trabajador.
                pass
        return base.subquery("deuda_filtrada")

    def listado(self, alcance, filtros, pagina, tamano, completo=False):
        d = self.base(alcance, filtros)
        piezas = func.sum(case((d.c.pieza_id.is_not(None), 1), else_=0))
        unidades = func.sum(case((d.c.pieza_id.is_(None), d.c.cantidad), else_=0))
        alto = func.sum(case((d.c.alto_valor.is_(True), d.c.cantidad), else_=0))
        no_vigente_alto = case((and_(d.c.vigente.is_(False), alto > 0), 0), else_=1)
        agrupados = select(
            d.c.trabajador_id,
            d.c.trabajador_nombre,
            d.c.numero_empleado,
            d.c.foto_adjunto_id,
            d.c.vigente,
            piezas.label("piezas"),
            unidades.label("unidades"),
            alto.label("alto_valor"),
            func.min(d.c.desde).label("desde"),
        ).group_by(
            d.c.trabajador_id,
            d.c.trabajador_nombre,
            d.c.numero_empleado,
            d.c.foto_adjunto_id,
            d.c.vigente,
        )
        if filtros.get("antiguedad_dias") is not None:
            from datetime import timedelta

            agrupados = agrupados.having(
                func.min(d.c.desde) < ahora_utc() - timedelta(days=filtros["antiguedad_dias"])
            )
        total = self.session.scalar(select(func.count()).select_from(agrupados.subquery())) or 0
        consulta = agrupados.order_by(no_vigente_alto, func.min(d.c.desde), d.c.trabajador_nombre)
        if not completo:
            consulta = consulta.offset((pagina - 1) * tamano).limit(tamano)
        filas = self.session.execute(consulta).all()
        ids = [x.trabajador_id for x in filas]
        detalles = (
            self.session.execute(
                select(d).where(d.c.trabajador_id.in_(ids)).order_by(d.c.desde, d.c.articulo_nombre)
            ).all()
            if ids
            else []
        )
        otros = {}
        if alcance is not None and ids:
            todos = self.deudas()
            otros = dict(
                self.session.execute(
                    select(todos.c.trabajador_id, func.count())
                    .where(todos.c.trabajador_id.in_(ids), todos.c.almacen_id.not_in(alcance))
                    .group_by(todos.c.trabajador_id)
                ).all()
            )
        return filas, detalles, total, otros

    def tarjetas(self, alcance, filtros):
        from datetime import timedelta

        d = self.base(alcance, filtros, omitir_tarjetas=True)
        fila = self.session.execute(
            select(
                func.count(func.distinct(d.c.trabajador_id)),
                func.coalesce(func.sum(case((d.c.alto_valor.is_(True), d.c.cantidad), else_=0)), 0),
                func.count(func.distinct(case((d.c.vigente.is_(False), d.c.trabajador_id)))),
                func.count(
                    func.distinct(
                        case((d.c.desde < ahora_utc() - timedelta(days=30), d.c.trabajador_id))
                    )
                ),
            )
        ).one()
        return dict(
            zip(
                (
                    "trabajadores_con_adeudo",
                    "alto_valor_fuera",
                    "no_vigentes_con_adeudo",
                    "mas_de_30_dias",
                ),
                map(int, fila),
                strict=True,
            )
        )

    def resumen(self, alcance, filtros):
        d = self.base(alcance, filtros)
        resultado = {}
        for agrupacion, campos in (
            ("almacenes", (d.c.almacen_id, d.c.almacen_clave, d.c.almacen_nombre)),
            ("proyectos", (d.c.proyecto_id, d.c.proyecto_nombre)),
        ):
            consulta = select(
                *campos,
                func.count(func.distinct(d.c.trabajador_id)).label("trabajadores"),
                func.sum(case((d.c.pieza_id.is_not(None), 1), else_=0)).label("piezas"),
                func.sum(case((d.c.pieza_id.is_(None), d.c.cantidad), else_=0)).label("unidades"),
                func.sum(case((d.c.alto_valor.is_(True), d.c.cantidad), else_=0)).label(
                    "alto_valor"
                ),
                func.count(func.distinct(case((d.c.vigente.is_(False), d.c.trabajador_id)))).label(
                    "no_vigentes"
                ),
            ).group_by(*campos)
            if filtros.get("antiguedad_dias") is not None:
                from datetime import timedelta

                antiguos = (
                    select(d.c.trabajador_id)
                    .group_by(d.c.trabajador_id)
                    .having(
                        func.min(d.c.desde)
                        < ahora_utc() - timedelta(days=filtros["antiguedad_dias"])
                    )
                )
                consulta = consulta.where(d.c.trabajador_id.in_(antiguos))
            resultado[agrupacion] = [dict(x._mapping) for x in self.session.execute(consulta).all()]
        return resultado
