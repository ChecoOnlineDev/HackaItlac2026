"""Consultas de SOLO LECTURA del módulo `consulta`: nunca `add`, `flush` ni `commit`.

Lee las tablas de otros módulos (vale, movimiento, existencia, ubicacion, pieza, articulo,
categoria, trabajador, usuario, inspeccion, evento_pieza y ajuste_vigencia) con joins directos.
Devuelve filas (`Row`) y dataclasses; el service las convierte en contratos.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.modulos.acceso.models import Usuario
from app.modulos.almacenes.models import Almacen, TipoUbicacion, Ubicacion, UbicacionVirtual
from app.modulos.autorizaciones.models import Autorizacion
from app.modulos.catalogo.models import Articulo, Categoria, Control, EstadoPieza, Pieza
from app.modulos.inspecciones.models import AjusteVigencia, EventoPieza, Inspeccion
from app.modulos.movimientos.models import Existencia, Movimiento, TipoVale, Vale
from app.modulos.trabajadores.models import Trabajador


def escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _patron(texto: str) -> str:
    return f"%{escapar_like(texto.strip())}%"


def _contar(session: Session, consulta: Select) -> int:
    subconsulta = consulta.order_by(None).subquery()
    return int(session.scalar(select(func.count()).select_from(subconsulta)) or 0)


class Lugar:
    """Una ubicación unida a su almacén o su trabajador, para mostrar dónde está algo.

    Uso: `lugar = Lugar("origen")`, `consulta = lugar.unir(consulta, Movimiento.origen_id)` y
    `lugar.columnas()` en el `select`; `Lugar.texto(fila, "origen")` arma el texto legible.
    """

    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        self.u = aliased(Ubicacion, name=f"u_{nombre}")
        self.a = aliased(Almacen, name=f"a_{nombre}")
        self.t = aliased(Trabajador, name=f"t_{nombre}")

    def unir(self, consulta: Select, columna_ubicacion, *, externa: bool = False) -> Select:
        union = consulta.outerjoin if externa else consulta.join
        return (
            union(self.u, self.u.id == columna_ubicacion)
            .outerjoin(self.a, self.a.id == self.u.almacen_id)
            .outerjoin(self.t, self.t.id == self.u.trabajador_id)
        )

    def columnas(self) -> tuple:
        n = self.nombre
        return (
            self.u.tipo.label(f"{n}_tipo"),
            self.a.id.label(f"{n}_almacen_id"),
            self.a.clave.label(f"{n}_clave"),
            self.a.nombre.label(f"{n}_almacen"),
            self.t.id.label(f"{n}_trabajador_id"),
            self.t.numero_empleado.label(f"{n}_numero"),
            self.t.nombre.label(f"{n}_trabajador"),
            self.u.virtual.label(f"{n}_virtual"),
        )


@dataclass(frozen=True)
class Pendiente:
    """Un retornable en resguardo de un trabajador, con su última entrega."""

    trabajador: Trabajador
    articulo: Articulo
    pieza: Pieza | None
    cantidad: int
    desde: datetime | None
    folio: str | None
    almacen_id: uuid.UUID | None
    almacen_clave: str | None
    almacen: str | None


class ConsultaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def usuarios_que_hicieron_vales(self, almacen_id: uuid.UUID | None) -> list[Usuario]:
        """Quienes hicieron algún vale (en el almacén indicado o en cualquiera), por nombre."""
        consulta = select(Usuario).join(Vale, Vale.responsable_id == Usuario.id).distinct()
        if almacen_id is not None:
            consulta = consulta.where(Vale.almacen_id == almacen_id)
        return list(self.session.scalars(consulta.order_by(Usuario.nombre, Usuario.id)))

    # ------------------------------------------------------------------ escaneo

    def articulo(self, articulo_id: uuid.UUID) -> tuple[Articulo, str] | None:
        fila = self.session.execute(
            select(Articulo, Categoria.nombre)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .where(Articulo.id == articulo_id)
        ).first()
        return (fila[0], fila[1]) if fila else None

    def pieza(self, pieza_id: uuid.UUID) -> tuple[Pieza, Articulo] | None:
        fila = self.session.execute(
            select(Pieza, Articulo)
            .join(Articulo, Articulo.id == Pieza.articulo_id)
            .where(Pieza.id == pieza_id)
        ).first()
        return (fila[0], fila[1]) if fila else None

    def existencia_total_en_almacenes(self, articulo_id: uuid.UUID) -> int:
        total = self.session.scalar(
            select(func.coalesce(func.sum(Existencia.cantidad), 0))
            .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
            .where(Existencia.articulo_id == articulo_id, Ubicacion.tipo == TipoUbicacion.ALMACEN)
        )
        return int(total or 0)

    def vale_resumen(self, vale_id: uuid.UUID):
        """`(Vale, clave del almacén, nombre del trabajador, nombre del responsable)`."""
        return self.session.execute(
            select(Vale, Almacen.clave, Trabajador.nombre, Usuario.nombre)
            .join(Almacen, Almacen.id == Vale.almacen_id)
            .outerjoin(Trabajador, Trabajador.id == Vale.trabajador_id)
            .join(Usuario, Usuario.id == Vale.responsable_id)
            .where(Vale.id == vale_id)
        ).first()

    def vale_id_por_token_o_folio(self, texto: str) -> uuid.UUID | None:
        """El QR del vale lleva su token; también se acepta el folio tecleado."""
        por_token = self.session.scalar(select(Vale.id).where(Vale.token == texto))
        if por_token is not None:
            return por_token
        return self.session.scalar(select(Vale.id).where(Vale.folio == texto))

    def trabajador_por_numero(self, numero_empleado: str) -> Trabajador | None:
        return self.session.scalar(
            select(Trabajador).where(Trabajador.numero_empleado == numero_empleado)
        )

    def trabajador(self, trabajador_id: uuid.UUID) -> Trabajador | None:
        return self.session.get(Trabajador, trabajador_id)

    def ubicacion(self, ubicacion_id: uuid.UUID):
        """La fila de `Lugar` de una ubicación (almacén, trabajador o virtual)."""
        lugar = Lugar("ub")
        consulta = (
            select(*lugar.columnas())
            .select_from(lugar.u)
            .outerjoin(lugar.a, lugar.a.id == lugar.u.almacen_id)
            .outerjoin(lugar.t, lugar.t.id == lugar.u.trabajador_id)
            .where(lugar.u.id == ubicacion_id)
        )
        return self.session.execute(consulta).first()

    # ----------------------------------------------------------------- búsqueda

    def buscar_articulos(self, q: str, offset: int, limit: int) -> tuple[list, int]:
        patron = _patron(q)
        condicion = or_(
            Articulo.nombre.like(patron, escape="\\"),
            Articulo.codigo.like(patron, escape="\\"),
        )
        consulta = (
            select(
                Articulo.id,
                Articulo.codigo,
                Articulo.nombre,
                Articulo.marca,
                Categoria.nombre.label("categoria"),
                Articulo.control,
                Articulo.activo,
            )
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .where(condicion)
        )
        total = _contar(self.session, consulta)
        filas = self.session.execute(
            consulta.order_by(Articulo.nombre, Articulo.codigo).offset(offset).limit(limit)
        ).all()
        return list(filas), total

    def buscar_piezas(self, q: str, offset: int, limit: int) -> tuple[list, int]:
        """Por número de serie, por código de la pieza y por nombre de su artículo ("detector"
        lista los detectores y quién tiene cada uno)."""
        patron = _patron(q)
        lugar = Lugar("ub")
        condicion = or_(
            Pieza.numero_serie.like(patron, escape="\\"),
            Pieza.codigo.like(patron, escape="\\"),
            Articulo.nombre.like(patron, escape="\\"),
        )
        consulta = (
            select(
                Pieza.id,
                Pieza.codigo,
                Pieza.numero_serie,
                Pieza.articulo_id,
                Articulo.nombre.label("articulo"),
                Pieza.estado,
                *lugar.columnas(),
            )
            .select_from(Pieza)
            .join(Articulo, Articulo.id == Pieza.articulo_id)
        )
        consulta = lugar.unir(consulta, Pieza.ubicacion_id, externa=True).where(condicion)
        total = _contar(self.session, consulta)
        filas = self.session.execute(
            consulta.order_by(Articulo.nombre, Pieza.numero_serie, Pieza.codigo)
            .offset(offset)
            .limit(limit)
        ).all()
        return list(filas), total

    def buscar_trabajadores(self, q: str, offset: int, limit: int) -> tuple[list, int]:
        patron = _patron(q)
        consulta = select(
            Trabajador.id, Trabajador.numero_empleado, Trabajador.nombre, Trabajador.estado
        ).where(
            or_(
                Trabajador.nombre.like(patron, escape="\\"),
                Trabajador.numero_empleado.like(patron, escape="\\"),
            )
        )
        total = _contar(self.session, consulta)
        filas = self.session.execute(
            consulta.order_by(Trabajador.nombre, Trabajador.numero_empleado)
            .offset(offset)
            .limit(limit)
        ).all()
        return list(filas), total

    # ----------------------------------------------------------- ficha de pieza

    def ultima_inspeccion(self, pieza_id: uuid.UUID):
        """`(Inspeccion, nombre de quien la hizo)` de la más reciente."""
        return self.session.execute(
            select(Inspeccion, Usuario.nombre)
            .join(Usuario, Usuario.id == Inspeccion.usuario_id)
            .where(Inspeccion.pieza_id == pieza_id)
            .order_by(Inspeccion.creado_en.desc(), Inspeccion.fecha.desc())
            .limit(1)
        ).first()

    def historial_movimientos(self, pieza_id: uuid.UUID) -> list:
        origen, destino = Lugar("origen"), Lugar("destino")
        consulta = (
            select(
                Movimiento.id,
                Movimiento.creado_en,
                Movimiento.condicion,
                Vale.id.label("vale_id"),
                Vale.folio,
                Vale.tipo,
                Vale.estado.label("vale_estado"),
                Usuario.nombre.label("responsable"),
                *origen.columnas(),
                *destino.columnas(),
            )
            .select_from(Movimiento)
            .join(Vale, Vale.id == Movimiento.vale_id)
            .join(Usuario, Usuario.id == Vale.responsable_id)
        )
        consulta = origen.unir(consulta, Movimiento.origen_id)
        consulta = destino.unir(consulta, Movimiento.destino_id)
        consulta = consulta.where(Movimiento.pieza_id == pieza_id)
        return list(self.session.execute(consulta).all())

    def historial_inspecciones(self, pieza_id: uuid.UUID) -> list:
        return list(
            self.session.execute(
                select(Inspeccion, Usuario.nombre)
                .join(Usuario, Usuario.id == Inspeccion.usuario_id)
                .where(Inspeccion.pieza_id == pieza_id)
            ).all()
        )

    def historial_cambios_estado(self, pieza_id: uuid.UUID) -> list:
        return list(
            self.session.execute(
                select(EventoPieza, Usuario.nombre)
                .join(Usuario, Usuario.id == EventoPieza.usuario_id)
                .where(EventoPieza.pieza_id == pieza_id)
            ).all()
        )

    def historial_ajustes_vigencia(self, pieza_id: uuid.UUID) -> list:
        return list(
            self.session.execute(
                select(AjusteVigencia, Usuario.nombre)
                .join(Usuario, Usuario.id == AjusteVigencia.usuario_id)
                .where(AjusteVigencia.pieza_id == pieza_id)
            ).all()
        )

    # ------------------------------------------------------------ reporte: existencias

    @staticmethod
    def _disponible():
        """Lo que se puede entregar: en piezas, solo las Aptas que están ahí (I-05)."""
        aptas = (
            select(func.count(Pieza.id))
            .where(
                Pieza.ubicacion_id == Existencia.ubicacion_id,
                Pieza.articulo_id == Existencia.articulo_id,
                Pieza.estado == EstadoPieza.APTO,
            )
            .correlate(Existencia)
            .scalar_subquery()
        )
        return case((Articulo.control == Control.PIEZA, aptas), else_=Existencia.cantidad)

    def reporte_existencias(
        self,
        *,
        almacen_id: uuid.UUID | None,
        categoria_id: uuid.UUID | None,
        offset: int | None,
        limit: int | None,
    ) -> tuple[list, int]:
        consulta = (
            select(
                Almacen.id.label("almacen_id"),
                Almacen.clave.label("almacen_clave"),
                Almacen.nombre.label("almacen"),
                Articulo.id.label("articulo_id"),
                Articulo.codigo,
                Articulo.nombre.label("articulo"),
                Categoria.nombre.label("categoria"),
                Articulo.unidad,
                Articulo.activo,
                Existencia.cantidad,
                self._disponible().label("disponible"),
            )
            .select_from(Existencia)
            .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
            .join(Almacen, Almacen.id == Ubicacion.almacen_id)
            .join(Articulo, Articulo.id == Existencia.articulo_id)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .where(Ubicacion.tipo == TipoUbicacion.ALMACEN, Existencia.cantidad > 0)
        )
        if almacen_id is not None:
            consulta = consulta.where(Almacen.id == almacen_id)
        if categoria_id is not None:
            consulta = consulta.where(Articulo.categoria_id == categoria_id)
        total = _contar(self.session, consulta)
        consulta = consulta.order_by(Almacen.clave, Articulo.nombre, Articulo.codigo)
        if offset is not None and limit is not None:
            consulta = consulta.offset(offset).limit(limit)
        return list(self.session.execute(consulta).all()), total

    # ------------------------------------------------------------ reporte: movimientos

    def reporte_movimientos(
        self,
        *,
        desde: datetime | None,
        hasta_excluyente: datetime | None,
        almacen_id: uuid.UUID | None,
        tipo: str | None,
        trabajador_id: uuid.UUID | None,
        articulo_id: uuid.UUID | None,
        usuario_id: uuid.UUID | None,
        offset: int | None,
        limit: int | None,
    ) -> tuple[list, int]:
        """La bitácora. `almacen_id` es el almacén del vale (el que lo emitió); `trabajador_id`
        coincide con el trabajador del vale o el que se anotó en el renglón."""
        origen, destino = Lugar("origen"), Lugar("destino")
        trabajador = aliased(Trabajador, name="t_vale")
        responsable = aliased(Usuario, name="responsable")
        autorizador = aliased(Usuario, name="autorizador")
        consulta = (
            select(
                Movimiento.id,
                Movimiento.creado_en,
                Movimiento.cantidad,
                Movimiento.saldo_origen,
                Movimiento.saldo_destino,
                Vale.id.label("vale_id"),
                Vale.folio,
                Vale.tipo,
                Articulo.id.label("articulo_id"),
                Articulo.codigo.label("codigo_articulo"),
                Articulo.nombre.label("articulo"),
                Pieza.codigo.label("pieza"),
                responsable.nombre.label("responsable"),
                trabajador.numero_empleado.label("numero_empleado"),
                trabajador.nombre.label("trabajador"),
                autorizador.nombre.label("autorizado_por"),
                func.coalesce(Autorizacion.motivo, Movimiento.motivo_baja).label("motivo"),
                *origen.columnas(),
                *destino.columnas(),
            )
            .select_from(Movimiento)
            .join(Vale, Vale.id == Movimiento.vale_id)
            .join(Articulo, Articulo.id == Movimiento.articulo_id)
            .outerjoin(Pieza, Pieza.id == Movimiento.pieza_id)
            .join(responsable, responsable.id == Vale.responsable_id)
            .outerjoin(Autorizacion, Autorizacion.id == Vale.autorizacion_id)
            .outerjoin(autorizador, autorizador.id == Autorizacion.resuelta_por)
            .outerjoin(
                trabajador,
                trabajador.id == func.coalesce(Movimiento.trabajador_id, Vale.trabajador_id),
            )
        )
        consulta = origen.unir(consulta, Movimiento.origen_id)
        consulta = destino.unir(consulta, Movimiento.destino_id)
        if desde is not None:
            consulta = consulta.where(Movimiento.creado_en >= desde)
        if hasta_excluyente is not None:
            consulta = consulta.where(Movimiento.creado_en < hasta_excluyente)
        if almacen_id is not None:
            consulta = consulta.where(Vale.almacen_id == almacen_id)
        if tipo is not None:
            consulta = consulta.where(Vale.tipo == tipo)
        if trabajador_id is not None:
            consulta = consulta.where(
                or_(Movimiento.trabajador_id == trabajador_id, Vale.trabajador_id == trabajador_id)
            )
        if articulo_id is not None:
            consulta = consulta.where(Movimiento.articulo_id == articulo_id)
        if usuario_id is not None:
            consulta = consulta.where(Vale.responsable_id == usuario_id)
        total = _contar(self.session, consulta)
        consulta = consulta.order_by(Movimiento.creado_en.desc(), Vale.folio, Movimiento.renglon)
        if offset is not None and limit is not None:
            consulta = consulta.offset(offset).limit(limit)
        return list(self.session.execute(consulta).all()), total

    # --------------------------------------------------------------- reporte: adeudos

    def pendientes(self) -> list[Pendiente]:
        """Todos los retornables en resguardo de algún trabajador (B-03: sin consumibles), cada
        uno con la última entrega que lo llevó ahí. Ordenados por trabajador y fecha."""
        por_pieza = self.session.execute(
            select(Trabajador, Articulo, Pieza, Ubicacion.id)
            .select_from(Pieza)
            .join(Ubicacion, Ubicacion.id == Pieza.ubicacion_id)
            .join(Trabajador, Trabajador.id == Ubicacion.trabajador_id)
            .join(Articulo, Articulo.id == Pieza.articulo_id)
            .where(Articulo.retornable.is_(True))
        ).all()
        por_cantidad = self.session.execute(
            select(Trabajador, Articulo, Existencia.cantidad, Ubicacion.id)
            .select_from(Existencia)
            .join(Ubicacion, Ubicacion.id == Existencia.ubicacion_id)
            .join(Trabajador, Trabajador.id == Ubicacion.trabajador_id)
            .join(Articulo, Articulo.id == Existencia.articulo_id)
            .where(
                Existencia.cantidad > 0,
                Articulo.retornable.is_(True),
                Articulo.control == Control.CANTIDAD,
            )
        ).all()
        ubicaciones = {u for *_, u in por_pieza} | {u for *_, u in por_cantidad}
        entregas = self._ultimas_entregas(ubicaciones)

        resultado: list[Pendiente] = []
        for trabajador, articulo, pieza, ubicacion_id in por_pieza:
            e = entregas.get((ubicacion_id, pieza.id))
            resultado.append(self._pendiente(trabajador, articulo, pieza, 1, e))
        for trabajador, articulo, cantidad, ubicacion_id in por_cantidad:
            e = entregas.get((ubicacion_id, articulo.id))
            resultado.append(self._pendiente(trabajador, articulo, None, cantidad, e))
        return resultado

    @staticmethod
    def _pendiente(trabajador, articulo, pieza, cantidad, entrega) -> Pendiente:
        return Pendiente(
            trabajador=trabajador,
            articulo=articulo,
            pieza=pieza,
            cantidad=cantidad,
            desde=entrega.creado_en if entrega else None,
            folio=entrega.folio if entrega else None,
            almacen_id=entrega.almacen_id if entrega else None,
            almacen_clave=entrega.clave if entrega else None,
            almacen=entrega.nombre if entrega else None,
        )

    def _ultimas_entregas(self, ubicaciones: set[uuid.UUID]) -> dict:
        """Por (ubicación del trabajador, pieza o artículo), el movimiento que se lo entregó:
        se prefiere el de un vale de ENTREGA y, entre varios, el más reciente. Un vale de
        cancelación que regresa el equipo al trabajador no cambia desde cuándo lo tiene."""
        if not ubicaciones:
            return {}
        referencia = func.coalesce(Movimiento.pieza_id, Movimiento.articulo_id)
        orden = func.row_number().over(
            partition_by=(Movimiento.destino_id, referencia),
            order_by=(
                case((Vale.tipo == TipoVale.ENTREGA, 0), else_=1),
                Movimiento.creado_en.desc(),
            ),
        )
        sub = (
            select(
                Movimiento.destino_id.label("ubicacion_id"),
                referencia.label("ref"),
                Movimiento.creado_en,
                Vale.folio,
                Vale.almacen_id,
                Almacen.clave,
                Almacen.nombre,
                orden.label("rn"),
            )
            .select_from(Movimiento)
            .join(Vale, Vale.id == Movimiento.vale_id)
            .join(Almacen, Almacen.id == Vale.almacen_id)
            .where(Movimiento.destino_id.in_(ubicaciones))
            .subquery()
        )
        filas = self.session.execute(select(sub).where(sub.c.rn == 1)).all()
        return {(f.ubicacion_id, f.ref): f for f in filas}

    # ---------------------------------------------------------------- reporte: consumo

    def consumo(
        self,
        *,
        desde: datetime | None,
        hasta_excluyente: datetime | None,
        almacen_id: uuid.UUID | None,
        categoria_id: uuid.UUID | None,
        articulo_id: uuid.UUID | None,
        trabajador_id: uuid.UUID | None,
    ) -> list:
        """Consumo neto por artículo consumible y trabajador (C-08).

        Suma los movimientos que van a CONSUMIDO (entregas de consumibles, E-21) y resta los que
        salen de CONSUMIDO (cancelaciones, K-02, y la devolución de sobrante, V-10). Una
        cancelación se fecha con el vale que cancela, así un vale cancelado no cuenta en ningún
        periodo. Devuelve `(articulo..., trabajador_id, cantidad)`; sin renglones en cero.
        """
        origen = aliased(Ubicacion, name="u_origen")
        destino = aliased(Ubicacion, name="u_destino")
        vale_cancelado = aliased(Vale, name="vale_cancelado")

        signo = case(
            (destino.virtual == UbicacionVirtual.CONSUMIDO, Movimiento.cantidad),
            else_=-Movimiento.cantidad,
        )
        fecha = case(
            (
                and_(Vale.tipo == TipoVale.CANCELACION, vale_cancelado.id.is_not(None)),
                vale_cancelado.creado_en,
            ),
            else_=Movimiento.creado_en,
        )
        trabajador = func.coalesce(
            Movimiento.trabajador_id, Vale.trabajador_id, vale_cancelado.trabajador_id
        )
        neto = func.sum(signo)
        consulta = (
            select(
                Articulo.id.label("articulo_id"),
                Articulo.codigo,
                Articulo.nombre.label("articulo"),
                Articulo.unidad,
                Categoria.nombre.label("categoria"),
                trabajador.label("trabajador_id"),
                neto.label("cantidad"),
            )
            .select_from(Movimiento)
            .join(Vale, Vale.id == Movimiento.vale_id)
            .outerjoin(vale_cancelado, vale_cancelado.id == Vale.vale_origen_id)
            .join(Articulo, Articulo.id == Movimiento.articulo_id)
            .join(Categoria, Categoria.id == Articulo.categoria_id)
            .join(origen, origen.id == Movimiento.origen_id)
            .join(destino, destino.id == Movimiento.destino_id)
            .where(
                or_(
                    destino.virtual == UbicacionVirtual.CONSUMIDO,
                    origen.virtual == UbicacionVirtual.CONSUMIDO,
                ),
                Articulo.retornable.is_(False),
            )
        )
        if desde is not None:
            consulta = consulta.where(fecha >= desde)
        if hasta_excluyente is not None:
            consulta = consulta.where(fecha < hasta_excluyente)
        if almacen_id is not None:
            consulta = consulta.where(Vale.almacen_id == almacen_id)
        if categoria_id is not None:
            consulta = consulta.where(Articulo.categoria_id == categoria_id)
        if articulo_id is not None:
            consulta = consulta.where(Articulo.id == articulo_id)
        if trabajador_id is not None:
            consulta = consulta.where(trabajador == trabajador_id)
        consulta = consulta.group_by(
            Articulo.id,
            Articulo.codigo,
            Articulo.nombre,
            Articulo.unidad,
            Categoria.nombre,
            trabajador,
        ).having(neto != 0)
        return list(self.session.execute(consulta).all())

    def trabajadores_por_id(self, ids: set[uuid.UUID]) -> dict[uuid.UUID, Trabajador]:
        if not ids:
            return {}
        filas = self.session.scalars(select(Trabajador).where(Trabajador.id.in_(ids)))
        return {t.id: t for t in filas}
