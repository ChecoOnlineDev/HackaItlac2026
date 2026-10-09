"""P-11: pendientes y conteos se filtran y paginan en la base de datos."""

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import aliased

from app.config import get_settings
from app.core.tiempo import hoy_mx
from app.modulos.almacenes.models import Almacen, TipoUbicacion, Ubicacion
from app.modulos.catalogo.models import Articulo, Categoria, EstadoPieza, Pieza
from app.modulos.movimientos.models import Movimiento, Vale
from app.modulos.trabajadores.models import Trabajador


class PendientesRepository:
    def __init__(self, session):
        self.session = session

    def consultar(self, alcance, filtros, pagina, tamano, solo_contar=False):
        ultima = aliased(Movimiento)
        ultimo_id = (
            select(ultima.id)
            .where(ultima.pieza_id == Pieza.id, ultima.destino_id == Pieza.ubicacion_id)
            .order_by(ultima.creado_en.desc(), ultima.id.desc())
            .limit(1)
            .correlate(Pieza)
            .scalar_subquery()
        )
        almacen_id = case(
            (Ubicacion.tipo == TipoUbicacion.ALMACEN, Ubicacion.almacen_id), else_=Vale.almacen_id
        )
        dias = func.coalesce(
            Articulo.dias_aviso_inspeccion,
            Categoria.dias_aviso_inspeccion,
            get_settings().inspeccion_aviso_dias,
        )
        restantes = func.datediff(Pieza.inspeccion_vigente_hasta, hoy_mx())
        base = (
            select(
                Pieza,
                Articulo,
                Categoria,
                Ubicacion,
                Almacen,
                Trabajador,
                Vale,
                Movimiento,
                dias.label("aviso"),
                restantes.label("restantes"),
            )
            .select_from(Pieza)
            .join(Articulo, Articulo.id == Pieza.articulo_id)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .join(Ubicacion, Ubicacion.id == Pieza.ubicacion_id)
            .outerjoin(Movimiento, Movimiento.id == ultimo_id)
            .outerjoin(Vale, Vale.id == Movimiento.vale_id)
            .outerjoin(Almacen, Almacen.id == almacen_id)
            .outerjoin(Trabajador, Trabajador.id == Ubicacion.trabajador_id)
            .where(Pieza.estado != EstadoPieza.BAJA, Articulo.requiere_inspeccion.is_(True))
        )
        if alcance is not None:
            base = base.where(
                or_(
                    almacen_id.in_(alcance),
                    and_(Ubicacion.virtual == "EN_TRANSITO", Vale.destino_almacen_id.in_(alcance)),
                )
            )
        if filtros.get("almacen_id"):
            aid = filtros["almacen_id"]
            base = base.where(
                or_(
                    almacen_id == aid,
                    and_(Ubicacion.virtual == "EN_TRANSITO", Vale.destino_almacen_id == aid),
                )
            )
        if filtros.get("categoria_id"):
            base = base.where(Articulo.categoria_id == filtros["categoria_id"])
        if filtros.get("ubicacion"):
            base = base.where(Ubicacion.tipo == filtros["ubicacion"])
        if filtros.get("q"):
            texto = "%" + filtros["q"].replace("%", r"\%").replace("_", r"\_") + "%"
            base = base.where(
                or_(
                    Pieza.codigo.like(texto),
                    Pieza.numero_serie.like(texto),
                    Articulo.codigo.like(texto),
                    Articulo.nombre.like(texto),
                    Trabajador.nombre.like(texto),
                    Trabajador.numero_empleado.like(texto),
                )
            )
        apta = Pieza.estado == EstadoPieza.APTO
        reglas = {
            "VENCIDA": and_(apta, restantes < 0),
            "POR_VENCER": and_(apta, restantes >= 0, restantes <= dias),
            "SIN_INSPECCION": and_(apta, Pieza.inspeccion_vigente_hasta.is_(None)),
        }
        agregados = base.with_only_columns(
            func.coalesce(func.sum(case((reglas["VENCIDA"], 1), else_=0)), 0),
            func.coalesce(func.sum(case((reglas["POR_VENCER"], 1), else_=0)), 0),
            func.coalesce(func.sum(case((reglas["SIN_INSPECCION"], 1), else_=0)), 0),
            func.coalesce(func.sum(case((Pieza.estado == EstadoPieza.NO_APTO, 1), else_=0)), 0),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Pieza.estado.in_(
                                [EstadoPieza.EN_MANTENIMIENTO, EstadoPieza.EN_CALIBRACION]
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Pieza.estado == EstadoPieza.NO_APTO,
                                Ubicacion.tipo == TipoUbicacion.TRABAJADOR,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            maintain_column_froms=False,
        )
        conteos = dict(
            zip(
                (
                    "vencidas",
                    "por_vencer",
                    "sin_inspeccion",
                    "no_aptas",
                    "en_mantenimiento",
                    "no_aptas_con_trabajador",
                ),
                map(int, self.session.execute(agregados).one()),
                strict=True,
            )
        )
        if solo_contar:
            return conteos, [], 0
        consulta = base.where(reglas[filtros.get("estado", "VENCIDA")])
        total = self.session.scalar(select(func.count()).select_from(consulta.subquery())) or 0
        filas = self.session.execute(
            consulta.order_by(Pieza.inspeccion_vigente_hasta, Pieza.codigo)
            .offset((pagina - 1) * tamano)
            .limit(tamano)
        ).all()
        return conteos, filas, total
